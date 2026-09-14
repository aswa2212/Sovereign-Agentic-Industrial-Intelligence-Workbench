"""
SIH26117 — Phase 14: Evaluation Environment Configuration & Discovery

Dynamically discovers local hardware (NVIDIA GPU, RAM, CPU) and runtime services
(Ollama, local vector stores) without hardcoding machine-specific paths or usernames.
"""

import ctypes
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Portable root paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
EXPERIMENTS_DIR = REPO_ROOT / "experiments"
EVAL_DIR = EXPERIMENTS_DIR / "evaluation"
RESULTS_DIR = EVAL_DIR / "results"
DOCS_EVAL_DIR = REPO_ROOT / "docs" / "evaluation"

# Ensure directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_EVAL_DIR.mkdir(parents=True, exist_ok=True)

# Ensure backend is in sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_system_ram_mb() -> Dict[str, float]:
    """Retrieve system physical RAM using Windows Win32 API without external dependencies."""
    try:
        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_mb = round(stat.ullTotalPhys / (1024 * 1024), 2)
            avail_mb = round(stat.ullAvailPhys / (1024 * 1024), 2)
            used_mb = round(total_mb - avail_mb, 2)
            pct = round((used_mb / total_mb) * 100.0, 1) if total_mb > 0 else 0.0
            return {"total_mb": total_mb, "used_mb": used_mb, "avail_mb": avail_mb, "percent": pct}
    except Exception:
        pass
    return {"total_mb": 0.0, "used_mb": 0.0, "avail_mb": 0.0, "percent": 0.0}


def detect_hardware_environment() -> Dict[str, Any]:
    """Detect local hardware specifications and operating system metadata."""
    ram = get_system_ram_mb()
    cpu_count = os.cpu_count() or 1
    env = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python_version": platform.python_version(),
        "cpu_count_logical": cpu_count,
        "total_ram_gb": round(ram["total_mb"] / 1024, 2),
        "available_ram_gb": round(ram["avail_mb"] / 1024, 2),
        "gpu_available": False,
        "gpu_name": "Unavailable",
        "gpu_total_vram_mib": 0,
        "gpu_free_vram_mib": 0,
        "gpu_driver": "Unavailable",
    }

    # Probe NVIDIA GPU via nvidia-smi
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                env["gpu_available"] = True
                env["gpu_name"] = parts[0]
                env["gpu_total_vram_mib"] = int(float(parts[1]))
                env["gpu_free_vram_mib"] = int(float(parts[2]))
                env["gpu_driver"] = parts[3]
    except Exception as e:
        env["gpu_probe_error"] = str(e)

    return env


def get_ollama_base_url() -> str:
    """Return configured Ollama base URL or default to local endpoint."""
    return os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
