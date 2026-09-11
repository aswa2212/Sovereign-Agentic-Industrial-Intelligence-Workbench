"""Network monitoring and locality observation services."""

from app.services.audit.network_monitor import (
    RuntimeNetworkMonitor,
    is_local_or_loopback_address,
)

__all__ = [
    "RuntimeNetworkMonitor",
    "is_local_or_loopback_address",
]
