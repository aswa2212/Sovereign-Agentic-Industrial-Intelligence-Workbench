"""
Unit tests for RuntimeNetworkMonitor child process inspection and failure handling.
Verifies:
1. Current process connections are still observed.
2. A child process with a foreign/non-loopback connection is included.
3. Multiple child processes are aggregated.
4. Recursive descendants are included.
5. A child process disappearing during inspection (NoSuchProcess) does not crash the monitor.
6. Loopback child connections are not counted as foreign.
7. Foreign child connections are counted correctly.
8. Existing no-foreign-egress behavior still works.
9. No unrelated OS processes are included.
10. Existing stdlib fallback behavior remains unchanged.
"""

from collections import namedtuple
from unittest.mock import MagicMock, patch
import pytest

from app.services.audit.models import NetworkObservationReport
from app.services.audit.network_monitor import RuntimeNetworkMonitor

# Helper tuples matching psutil connection interface
Addr = namedtuple("Addr", ["ip", "port"])
Conn = namedtuple("Conn", ["laddr", "raddr", "status"])


class FakeProcess:
    """Mock process mimicking psutil.Process."""

    def __init__(self, pid: int, name: str, connections=None, children=None):
        self.pid = pid
        self._name = name
        self._connections = connections or []
        self._children = children or []

    def name(self):
        return self._name

    def children(self, recursive=True):
        if not recursive:
            return list(self._children)
        # Flatten recursive children
        result = []
        for ch in self._children:
            result.append(ch)
            result.extend(ch.children(recursive=True))
        return result

    def net_connections(self, kind="inet"):
        return list(self._connections)


def test_current_process_connections_still_observed():
    """Requirement 1: Current process connections are still observed."""
    monitor = RuntimeNetworkMonitor()
    report = monitor.observe_connections()

    assert isinstance(report, NetworkObservationReport)
    assert report.total_connections >= 0
    assert report.loopback_connections >= 0
    assert report.non_loopback_connections >= 0
    assert report.observation_method == "psutil_process_connections"


def test_child_process_with_foreign_connection_included():
    """Requirements 2 & 7: A child process with a foreign connection is included and counted."""
    monitor = RuntimeNetworkMonitor()
    assert monitor.has_psutil

    parent = FakeProcess(
        pid=1000,
        name="python-parent",
        connections=[Conn(laddr=Addr("127.0.0.1", 8000), raddr=None, status="LISTEN")],
    )
    child = FakeProcess(
        pid=1001,
        name="python-child-worker",
        connections=[Conn(laddr=Addr("192.168.1.10", 54321), raddr=Addr("93.184.216.34", 443), status="ESTABLISHED")],
    )
    parent._children = [child]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    assert report.total_connections == 2
    assert report.loopback_connections == 1
    assert report.non_loopback_connections == 1
    assert any(c.pid == 1001 and c.process_name == "python-child-worker" and not c.is_loopback for c in report.connections)


def test_multiple_child_processes_aggregated():
    """Requirement 3: Multiple child processes are aggregated."""
    monitor = RuntimeNetworkMonitor()

    parent = FakeProcess(pid=2000, name="backend-main")
    child1 = FakeProcess(
        pid=2001,
        name="worker-1",
        connections=[Conn(laddr=Addr("127.0.0.1", 9001), raddr=Addr("127.0.0.1", 11434), status="ESTABLISHED")],
    )
    child2 = FakeProcess(
        pid=2002,
        name="worker-2",
        connections=[Conn(laddr=Addr("127.0.0.1", 9002), raddr=Addr("127.0.0.1", 11434), status="ESTABLISHED")],
    )
    parent._children = [child1, child2]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    assert report.total_connections == 2
    assert report.loopback_connections == 2
    assert report.non_loopback_connections == 0
    pids = {c.pid for c in report.connections}
    assert pids == {2001, 2002}


def test_recursive_descendants_included():
    """Requirement 4: Recursive descendants (grandchildren) are included."""
    monitor = RuntimeNetworkMonitor()

    parent = FakeProcess(pid=3000, name="root-proc")
    child = FakeProcess(pid=3001, name="sub-proc")
    grandchild = FakeProcess(
        pid=3002,
        name="grandchild-tool",
        connections=[Conn(laddr=Addr("127.0.0.1", 8888), raddr=None, status="LISTEN")],
    )
    child._children = [grandchild]
    parent._children = [child]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    assert report.total_connections == 1
    assert report.connections[0].pid == 3002
    assert report.connections[0].process_name == "grandchild-tool"


def test_disappearing_child_process_handled_safely():
    """Requirement 5: A child process disappearing during inspection does not crash the monitor."""
    monitor = RuntimeNetworkMonitor()

    parent = FakeProcess(
        pid=4000,
        name="parent",
        connections=[Conn(laddr=Addr("127.0.0.1", 8000), raddr=None, status="LISTEN")],
    )

    # Disappearing child raises NoSuchProcess when net_connections is called
    dying_child = MagicMock()
    dying_child.pid = 4001
    dying_child.name.return_value = "terminating-worker"
    dying_child.net_connections.side_effect = monitor._psutil.NoSuchProcess(4001)

    parent._children = [dying_child]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    # Must safely succeed without exception, capturing parent connections
    assert report.total_connections == 1
    assert report.connections[0].pid == 4000


def test_disappearing_children_call_handled_safely():
    """Requirement 5b: If proc.children() raises NoSuchProcess or AccessDenied, monitor does not crash."""
    monitor = RuntimeNetworkMonitor()

    parent = MagicMock()
    parent.pid = 4500
    parent.name.return_value = "parent"
    parent.children.side_effect = monitor._psutil.NoSuchProcess(4500)
    parent.net_connections.return_value = [Conn(laddr=Addr("127.0.0.1", 8000), raddr=None, status="LISTEN")]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    assert report.total_connections == 1
    assert report.connections[0].pid == 4500


def test_loopback_child_connections_not_counted_as_foreign():
    """Requirement 6: Loopback child connections are counted as loopback, not foreign."""
    monitor = RuntimeNetworkMonitor()

    parent = FakeProcess(pid=5000, name="parent")
    child = FakeProcess(
        pid=5001,
        name="local-worker",
        connections=[
            Conn(laddr=Addr("127.0.0.1", 50000), raddr=Addr("127.0.0.1", 11434), status="ESTABLISHED"),
            Conn(laddr=Addr("::1", 50001), raddr=Addr("::1", 8000), status="ESTABLISHED"),
        ],
    )
    parent._children = [child]

    with patch.object(monitor._psutil, "Process", return_value=parent):
        report = monitor.observe_connections()

    assert report.total_connections == 2
    assert report.loopback_connections == 2
    assert report.non_loopback_connections == 0


def test_existing_no_foreign_egress_behavior_verified():
    """Requirement 8: Standard sovereign local execution observes 0 foreign sockets."""
    monitor = RuntimeNetworkMonitor()
    report = monitor.observe_connections()

    # In local test environment, the test runner process has no foreign sockets
    assert report.non_loopback_connections == 0


def test_no_unrelated_os_processes_included():
    """Requirement 9: Only current process and its children are inspected, not unrelated OS processes."""
    monitor = RuntimeNetworkMonitor()

    parent = FakeProcess(pid=6000, name="workbench-fastapi")
    child = FakeProcess(pid=6001, name="workbench-worker")
    parent._children = [child]

    mock_process_class = MagicMock(return_value=parent)

    with patch.object(monitor._psutil, "Process", mock_process_class):
        with patch.object(monitor._psutil, "net_connections", side_effect=RuntimeError("Host-wide net_connections must not be called!")):
            report = monitor.observe_connections()

    # Verify Process was only instantiated once (for os.getpid())
    mock_process_class.assert_called_once()
    assert report.total_connections == 0


def test_existing_stdlib_fallback_remains_unchanged():
    """Requirement 10: Fallback behavior when psutil is not available remains identical."""
    monitor = RuntimeNetworkMonitor()
    # Force stdlib fallback path
    report = monitor._observe_with_stdlib(timestamp="2026-09-19T00:00:00Z")

    assert report.observation_method == "stdlib_socket_inspection"
    assert report.loopback_connections == 1
    assert report.non_loopback_connections == 0
    assert "psutil not installed" in report.warning
    assert report.connections[0].local_address == "127.0.0.1:active"
    assert report.connections[0].is_loopback is True
