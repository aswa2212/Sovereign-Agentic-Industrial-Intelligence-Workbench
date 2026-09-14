"""
SIH26117 — Phase 14: Hardware Resource Monitor

Monitors GPU VRAM (via nvidia-smi query) and system RAM (via psutil)
before, during, and after inference / model operations.
"""

import subprocess
import time
from typing import Any, Dict, Optional

from experiments.evaluation.config import get_system_ram_mb


class ResourceMonitor:
    """Monitors system RAM and NVIDIA GPU VRAM without altering system state."""

    @staticmethod
    def get_snapshot() -> Dict[str, Any]:
        """Capture current RAM and GPU VRAM snapshot."""
        ram = get_system_ram_mb()
        snapshot: Dict[str, Any] = {
            "timestamp": time.time(),
            "ram_total_mb": ram["total_mb"],
            "ram_used_mb": ram["used_mb"],
            "ram_percent": ram["percent"],
            "gpu_telemetry_status": "UNAVAILABLE",
            "vram_total_mb": None,
            "vram_used_mb": None,
            "vram_free_mb": None,
            "gpu_utilization_percent": None,
        }

        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 4:
                    snapshot["gpu_telemetry_status"] = "OBSERVED"
                    snapshot["vram_total_mb"] = float(parts[0])
                    snapshot["vram_used_mb"] = float(parts[1])
                    snapshot["vram_free_mb"] = float(parts[2])
                    snapshot["gpu_utilization_percent"] = float(parts[3])
        except Exception:
            snapshot["gpu_telemetry_status"] = "UNAVAILABLE"

        return snapshot


class ResourceTracker:
    """Context manager / helper to record resource deltas across an operation."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_snapshot: Optional[Dict[str, Any]] = None
        self.end_snapshot: Optional[Dict[str, Any]] = None
        self.duration_sec: float = 0.0

    def start(self) -> "ResourceTracker":
        self.start_snapshot = ResourceMonitor.get_snapshot()
        self._start_time = time.perf_counter()
        return self

    def stop(self) -> Dict[str, Any]:
        self.duration_sec = round(time.perf_counter() - self._start_time, 4)
        self.end_snapshot = ResourceMonitor.get_snapshot()

        delta_vram = None
        if (
            self.start_snapshot.get("vram_used_mb") is not None
            and self.end_snapshot.get("vram_used_mb") is not None
        ):
            delta_vram = round(self.end_snapshot["vram_used_mb"] - self.start_snapshot["vram_used_mb"], 2)

        delta_ram = None
        if (
            self.start_snapshot.get("ram_used_mb") is not None
            and self.end_snapshot.get("ram_used_mb") is not None
        ):
            delta_ram = round(self.end_snapshot["ram_used_mb"] - self.start_snapshot["ram_used_mb"], 2)

        return {
            "operation": self.name,
            "duration_sec": self.duration_sec,
            "vram_before_mb": self.start_snapshot.get("vram_used_mb"),
            "vram_after_mb": self.end_snapshot.get("vram_used_mb"),
            "vram_delta_mb": delta_vram,
            "ram_before_mb": self.start_snapshot.get("ram_used_mb"),
            "ram_after_mb": self.end_snapshot.get("ram_used_mb"),
            "ram_delta_mb": delta_ram,
            "gpu_telemetry_status": self.end_snapshot.get("gpu_telemetry_status"),
        }

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
