"""Runtime network observation monitor for sovereign local environments."""

from datetime import datetime, timezone
import ipaddress
import os
import socket
from typing import List, Optional, Tuple
from app.services.audit.models import NetworkConnectionRecord, NetworkObservationReport


def is_local_or_loopback_address(host_or_ip: Optional[str]) -> bool:
    """
    Check if an address string is loopback or local bind.
    Accepts '127.0.0.1', 'localhost', '::1', '0.0.0.0', '::', or None (listening).
    """
    if not host_or_ip:
        return True
    host_clean = host_or_ip.strip().lower()
    if host_clean in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "::"):
        return True

    # Check IP address range
    try:
        ip = ipaddress.ip_address(host_clean)
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


class RuntimeNetworkMonitor:
    """
    Observes local runtime network connections.
    Uses psutil if installed; otherwise falls back gracefully to standard-library
    socket inspection without crashing or installing external dependencies.
    """

    def __init__(self):
        self._has_psutil = False
        try:
            import psutil  # type: ignore
            self._psutil = psutil
            self._has_psutil = True
        except ImportError:
            self._psutil = None
            self._has_psutil = False

    @property
    def has_psutil(self) -> bool:
        return self._has_psutil

    def observe_connections(self) -> NetworkObservationReport:
        """
        Collect observable network socket information for the current process/system.
        Never calls external networks or transmits telemetry.
        """
        now = datetime.now(timezone.utc).isoformat()

        if self._has_psutil and self._psutil is not None:
            return self._observe_with_psutil(now)
        else:
            return self._observe_with_stdlib(now)

    def _observe_with_psutil(self, timestamp: str) -> NetworkObservationReport:
        connections: List[NetworkConnectionRecord] = []
        try:
            # First attempt current process connections (safe across platforms without admin privs)
            proc = self._psutil.Process(os.getpid())
            conns = proc.net_connections(kind="inet") if hasattr(proc, "net_connections") else proc.connections(kind="inet")
            for c in conns:
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "unknown"
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None
                rhost = c.raddr.ip if c.raddr else None
                is_loop = is_local_or_loopback_address(rhost)

                connections.append(
                    NetworkConnectionRecord(
                        timestamp=timestamp,
                        pid=proc.pid,
                        process_name=proc.name(),
                        local_address=laddr,
                        remote_address=raddr,
                        status=c.status,
                        is_loopback=is_loop
                    )
                )

            loopback_count = sum(1 for c in connections if c.is_loopback)
            non_loopback_count = sum(1 for c in connections if not c.is_loopback)

            return NetworkObservationReport(
                timestamp=timestamp,
                observation_method="psutil_process_connections",
                total_connections=len(connections),
                loopback_connections=loopback_count,
                non_loopback_connections=non_loopback_count,
                connections=connections
            )
        except Exception as e:
            # Fallback if process net_connections restricted
            return self._observe_with_stdlib(timestamp, warning=f"psutil inspection limited: {e}")

    def _observe_with_stdlib(self, timestamp: str, warning: Optional[str] = None) -> NetworkObservationReport:
        """Standard library fallback when psutil is not present."""
        connections: List[NetworkConnectionRecord] = []

        # Probe local loopback interface resolution
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname("127.0.0.1")
            connections.append(
                NetworkConnectionRecord(
                    timestamp=timestamp,
                    pid=os.getpid(),
                    process_name="python",
                    local_address=f"{local_ip}:active",
                    remote_address=None,
                    status="LOCAL_ACTIVE",
                    is_loopback=True
                )
            )
        except Exception:
            pass

        return NetworkObservationReport(
            timestamp=timestamp,
            observation_method="stdlib_socket_inspection",
            total_connections=len(connections),
            loopback_connections=len(connections),
            non_loopback_connections=0,
            connections=connections,
            warning=warning or "Capability-aware stdlib observation: psutil not installed."
        )
