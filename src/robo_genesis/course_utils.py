"""Small, transparent helpers shared by the course notebooks.

The helpers handle environment reporting and assertions only. Scene construction,
entities, control, IK, rendering, and stepping remain explicit in every notebook so
learners see the real Genesis API.
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def environment_report() -> dict[str, Any]:
    """Return and print the versions and accelerators relevant to this course."""
    try:
        import torch

        torch_version = torch.__version__
        hip_version = torch.version.hip
        cuda_available = bool(torch.cuda.is_available())
        device_count = int(torch.cuda.device_count()) if cuda_available else 0
        device_name = torch.cuda.get_device_name(0) if device_count else "none"
    except Exception as exc:  # environment diagnosis must survive a broken torch install
        torch_version = f"unavailable ({type(exc).__name__})"
        hip_version = None
        cuda_available = False
        device_count = 0
        device_name = "none"

    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "genesis_world": _version("genesis-world"),
        "torch": torch_version,
        "torch_hip": hip_version or "none",
        "accelerator_available": cuda_available,
        "accelerator_count": device_count,
        "accelerator_0": device_name,
    }
    for key, value in report.items():
        print(f"{key:>24}: {value}")
    return report


def select_backend(prefer_rocm: bool = True):
    """Select the Genesis backend: AMD ROCm first, otherwise CPU.

    PyTorch exposes ROCm devices through ``torch.cuda`` for compatibility, so the
    decisive check is ``torch.version.hip`` rather than the namespace name.
    """
    import genesis as gs
    import torch

    is_rocm = bool(torch.version.hip) and bool(torch.cuda.is_available())
    if prefer_rocm and is_rocm and hasattr(gs, "amdgpu"):
        print(f"Backend: AMD ROCm ({torch.cuda.get_device_name(0)})")
        return gs.amdgpu
    print("Backend: CPU fallback (the same API, lower simulation/rendering throughput)")
    return gs.cpu


def to_numpy(value: Any) -> np.ndarray:
    """Convert a Genesis/Torch/NumPy value into a detached CPU NumPy array."""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def assert_pose_close(actual: Any, target: Any, atol: float = 0.03, *, label: str = "position") -> float:
    """Assert Euclidean pose-component error and return the measured error."""
    actual_array = to_numpy(actual).reshape(-1)
    target_array = to_numpy(target).reshape(-1)
    if actual_array.shape != target_array.shape:
        raise AssertionError(f"{label}: shape mismatch {actual_array.shape} != {target_array.shape}")
    if not np.isfinite(actual_array).all():
        raise AssertionError(f"{label}: non-finite values: {actual_array}")
    error = float(np.linalg.norm(actual_array - target_array))
    if error > atol:
        raise AssertionError(f"{label}: error {error:.5f} exceeds tolerance {atol:.5f}")
    print(f"PASS — {label} error: {error:.5f} (tolerance: {atol:.5f})")
    return error


def notebook_mode(output_name: str, *, show_viewer: bool | None = None) -> dict[str, Any]:
    """Return consistent notebook runtime settings and create its output directory."""
    output_root = Path(os.environ.get("GENESIS_COURSE_OUTPUT", "outputs"))
    output_dir = output_root / output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    if show_viewer is None:
        show_viewer = os.environ.get("GENESIS_COURSE_VIEWER", "0") == "1"
    config = {"show_viewer": show_viewer, "output_dir": output_dir}
    print(f"viewer={show_viewer}; output_dir={output_dir.resolve()}")
    return config


__all__ = [
    "assert_pose_close",
    "environment_report",
    "notebook_mode",
    "select_backend",
    "to_numpy",
]
