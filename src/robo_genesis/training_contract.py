"""Dependency-light checks shared by the L11 training notebook and CLI.

The helpers in this module inspect commands and on-disk artifacts. They do not
import LeRobot, allocate a model, contact the Hugging Face Hub, or claim that a
training run succeeded.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SMOLVLA_BASE_REPO_ID = "lerobot/smolvla_base"
SMOLVLA_BASE_REVISION = "c83c3163b8ca9b7e67c509fffd9121e66cb96205"
SMOLVLA_VLM_REPO_ID = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
SMOLVLA_VLM_REVISION = "7b375e1b73b11138ff12fe22c8f2822d8fe03467"

SMOLVLA_CAMERA_RENAME = {
    "observation.images.world": "observation.images.camera1",
    "observation.images.wrist": "observation.images.camera2",
}

SNAPSHOT_PROVENANCE_FILE = "robo_genesis_snapshot.json"
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_FLOAT_PATTERN = r"(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[-+]?inf|nan)"
_LOSS_PATTERN = re.compile(rf"(?:^|\s)loss:({_FLOAT_PATTERN})(?=\s|$)", re.IGNORECASE)
_GRAD_PATTERN = re.compile(
    rf"(?:^|\s)(?:grdn|grad_norm):({_FLOAT_PATTERN})(?=\s|$)", re.IGNORECASE
)
_STEP_PATTERN = re.compile(r"(?:^|\s)step:(\d+)(?=\s|$)")
_UPDATE_PATTERN = re.compile(rf"(?:^|\s)updt_s:({_FLOAT_PATTERN})(?=\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class SnapshotEvidence:
    """Verified identity and required files for one local model snapshot."""

    repo_id: str
    revision: str
    path: Path
    identity_source: str
    required_files: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "repo_id": self.repo_id,
            "revision": self.revision,
            "path": str(self.path),
            "identity_source": self.identity_source,
            "required_files": list(self.required_files),
        }


@dataclass(frozen=True)
class SmolVLASnapshotEvidence:
    """Pinned base and VLM content required for a reproducible SmolVLA run."""

    base: SnapshotEvidence
    vlm: SnapshotEvidence

    def as_dict(self) -> dict[str, object]:
        return {"base": self.base.as_dict(), "vlm": self.vlm.as_dict()}


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _cache_repo_id(path: Path) -> str | None:
    if path.parent.name != "snapshots" or not path.parent.parent.name.startswith("models--"):
        return None
    encoded = path.parent.parent.name.removeprefix("models--")
    parts = encoded.split("--")
    if len(parts) < 2:
        return None
    return "/".join(parts)


def _snapshot_identity(path: Path) -> tuple[str, str, str]:
    cache_repo_id = _cache_repo_id(path)
    if cache_repo_id is not None and _COMMIT_PATTERN.fullmatch(path.name):
        return cache_repo_id, path.name, "huggingface-cache-path"

    provenance_path = path / SNAPSHOT_PROVENANCE_FILE
    if not provenance_path.is_file():
        raise ValueError(
            f"Cannot prove the model revision for {path}. Use an exact Hugging Face "
            f"snapshots/<40-hex-commit> directory or add {SNAPSHOT_PROVENANCE_FILE}."
        )
    provenance = _read_json_object(provenance_path)
    repo_id = provenance.get("repo_id")
    revision = provenance.get("revision")
    if not isinstance(repo_id, str) or not isinstance(revision, str):
        raise ValueError(
            f"{provenance_path} must contain string repo_id and revision fields"
        )
    return repo_id, revision, SNAPSHOT_PROVENANCE_FILE


def audit_model_snapshot(
    path: str | Path,
    *,
    expected_repo_id: str,
    expected_revision: str,
    required_files: Iterable[str],
) -> SnapshotEvidence:
    """Verify a local snapshot's identity and minimally required files."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Model snapshot directory does not exist: {resolved}")

    repo_id, revision, identity_source = _snapshot_identity(resolved)
    if repo_id != expected_repo_id:
        raise ValueError(
            f"Snapshot repo_id {repo_id!r} does not match expected {expected_repo_id!r}"
        )
    if revision != expected_revision:
        raise ValueError(
            f"Snapshot revision {revision!r} does not match expected {expected_revision!r}"
        )

    checked_files: list[str] = []
    for relative_name in required_files:
        file_path = resolved / relative_name
        if not file_path.is_file():
            raise ValueError(f"Required snapshot file is missing: {file_path}")
        if file_path.stat().st_size <= 0:
            raise ValueError(f"Required snapshot file is empty: {file_path}")
        checked_files.append(relative_name)

    return SnapshotEvidence(
        repo_id=repo_id,
        revision=revision,
        path=resolved,
        identity_source=identity_source,
        required_files=tuple(checked_files),
    )


def audit_smolvla_snapshots(
    base_path: str | Path,
    vlm_path: str | Path,
) -> SmolVLASnapshotEvidence:
    """Verify the exact SmolVLA base and VLM snapshots used by this course."""
    base = audit_model_snapshot(
        base_path,
        expected_repo_id=SMOLVLA_BASE_REPO_ID,
        expected_revision=SMOLVLA_BASE_REVISION,
        required_files=(
            "config.json",
            "model.safetensors",
            "policy_preprocessor.json",
            "policy_postprocessor.json",
        ),
    )
    vlm = audit_model_snapshot(
        vlm_path,
        expected_repo_id=SMOLVLA_VLM_REPO_ID,
        expected_revision=SMOLVLA_VLM_REVISION,
        required_files=(
            "config.json",
            "model.safetensors",
            "processor_config.json",
            "tokenizer_config.json",
        ),
    )

    base_config = _read_json_object(base.path / "config.json")
    if base_config.get("type") != "smolvla":
        raise ValueError(f"Expected a smolvla policy in {base.path / 'config.json'}")
    if base_config.get("vlm_model_name") != SMOLVLA_VLM_REPO_ID:
        raise ValueError(
            "The SmolVLA base config does not name the expected VLM repository: "
            f"{base_config.get('vlm_model_name')!r}"
        )
    return SmolVLASnapshotEvidence(base=base, vlm=vlm)


def horizon_evidence(*, chunk_size: int, n_action_steps: int, fps: float) -> dict[str, float | int]:
    """Validate action horizons and convert both of them to seconds."""
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    if isinstance(n_action_steps, bool) or not isinstance(n_action_steps, int):
        raise ValueError("n_action_steps must be an integer")
    if not 1 <= n_action_steps <= chunk_size:
        raise ValueError("n_action_steps must satisfy 1 <= n_action_steps <= chunk_size")
    if not math.isfinite(float(fps)) or fps <= 0:
        raise ValueError("fps must be a positive finite number")
    return {
        "chunk_size": chunk_size,
        "n_action_steps": n_action_steps,
        "fps": float(fps),
        "prediction_seconds": chunk_size / float(fps),
        "replan_seconds": n_action_steps / float(fps),
    }


def command_options(command: Sequence[str]) -> dict[str, str | bool]:
    """Return the final value of each GNU-style option in a command list."""
    options: dict[str, str | bool] = {}
    index = 0
    while index < len(command):
        token = command[index]
        if not token.startswith("--") or token == "--":
            index += 1
            continue
        if "=" in token:
            name, value = token.split("=", 1)
            options[name] = value
        elif index + 1 < len(command) and not command[index + 1].startswith("--"):
            options[token] = command[index + 1]
            index += 1
        else:
            options[token] = True
        index += 1
    return options


def parse_training_metrics(log_text: str) -> dict[str, float | int]:
    """Extract and validate the final LeRobot loss/gradient record from a log."""
    records: list[tuple[int, float, float, float]] = []
    for line in log_text.splitlines():
        step_match = _STEP_PATTERN.search(line)
        loss_match = _LOSS_PATTERN.search(line)
        grad_match = _GRAD_PATTERN.search(line)
        update_match = _UPDATE_PATTERN.search(line)
        if all(match is not None for match in (step_match, loss_match, grad_match, update_match)):
            assert step_match is not None
            assert loss_match is not None
            assert grad_match is not None
            assert update_match is not None
            step = int(step_match.group(1))
            loss = float(loss_match.group(1))
            gradient_norm = float(grad_match.group(1))
            update_seconds = float(update_match.group(1))
            if not all(math.isfinite(value) for value in (loss, gradient_norm, update_seconds)):
                raise ValueError(f"Training log contains non-finite metrics: {line}")
            records.append((step, loss, gradient_norm, update_seconds))
    if not records:
        raise ValueError(
            "Training log contains no optimizer-step line with finite loss and gradient norm"
        )
    step, loss, gradient_norm, update_seconds = records[-1]
    return {
        "records": len(records),
        "step": step,
        "loss": loss,
        "gradient_norm": gradient_norm,
        "update_seconds": update_seconds,
    }


def resolve_numeric_checkpoint(run_directory: str | Path) -> Path:
    """Return the durable newest numeric ``pretrained_model`` checkpoint."""
    checkpoints = Path(run_directory).expanduser().resolve() / "checkpoints"
    numeric = sorted(
        (entry for entry in checkpoints.iterdir() if entry.is_dir() and entry.name.isdigit()),
        key=lambda entry: int(entry.name),
    ) if checkpoints.is_dir() else []
    if not numeric:
        raise ValueError(f"No numeric checkpoint directory found under {checkpoints}")

    newest = numeric[-1]
    last = checkpoints / "last"
    if not last.exists():
        raise ValueError(f"Checkpoint pointer does not exist: {last}")
    if last.resolve() != newest.resolve():
        raise ValueError(f"{last} does not resolve to newest numeric checkpoint {newest}")

    pretrained_model = newest / "pretrained_model"
    if not pretrained_model.is_dir():
        raise ValueError(f"Checkpoint model directory does not exist: {pretrained_model}")
    return pretrained_model


def _processor_state_files(value: object) -> tuple[str, ...]:
    found: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if key == "state_file" and isinstance(child, str):
                    found.add(child)
                else:
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return tuple(sorted(found))


def audit_checkpoint(
    pretrained_model: str | Path,
    *,
    expected_policy_type: str,
    expected_action_dim: int = 9,
) -> dict[str, object]:
    """Inspect the configuration, weights, and processor state of a checkpoint."""
    root = Path(pretrained_model).expanduser().resolve()
    required = (
        "config.json",
        "train_config.json",
        "model.safetensors",
        "policy_preprocessor.json",
        "policy_postprocessor.json",
    )
    for name in required:
        path = root / name
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"Required non-empty checkpoint file is missing: {path}")

    config = _read_json_object(root / "config.json")
    train_config = _read_json_object(root / "train_config.json")
    preprocessor = _read_json_object(root / "policy_preprocessor.json")
    postprocessor = _read_json_object(root / "policy_postprocessor.json")

    policy_type = config.get("type")
    if policy_type != expected_policy_type:
        raise ValueError(
            f"Checkpoint policy type {policy_type!r} does not match {expected_policy_type!r}"
        )
    action_shape = config.get("output_features", {}).get("action", {}).get("shape")
    if action_shape != [expected_action_dim]:
        raise ValueError(
            f"Checkpoint action shape {action_shape!r} does not match [{expected_action_dim}]"
        )

    chunk_size = config.get("chunk_size")
    n_action_steps = config.get("n_action_steps")
    if not isinstance(chunk_size, int) or not isinstance(n_action_steps, int):
        raise ValueError("Checkpoint is missing integer chunk_size/n_action_steps")
    horizon_evidence(chunk_size=chunk_size, n_action_steps=n_action_steps, fps=1.0)

    state_files = sorted(
        set(_processor_state_files(preprocessor)) | set(_processor_state_files(postprocessor))
    )
    for name in state_files:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Processor state file escapes the checkpoint directory: {name}")
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"Processor state file is missing or empty: {path}")

    dataset = train_config.get("dataset")
    if not isinstance(dataset, Mapping):
        raise ValueError("train_config.json does not contain a dataset object")
    rename_map = train_config.get("rename_map") or {}
    if not isinstance(rename_map, Mapping):
        raise ValueError("train_config.json rename_map must be an object")
    if expected_policy_type == "smolvla" and dict(rename_map) != SMOLVLA_CAMERA_RENAME:
        raise ValueError(
            f"SmolVLA checkpoint rename_map {dict(rename_map)!r} does not match the course contract"
        )

    return {
        "path": str(root),
        "policy_type": policy_type,
        "action_dim": expected_action_dim,
        "chunk_size": chunk_size,
        "n_action_steps": n_action_steps,
        "dataset_repo_id": dataset.get("repo_id"),
        "dataset_root": dataset.get("root"),
        "seed": train_config.get("seed"),
        "rename_map": dict(rename_map),
        "weight_bytes": (root / "model.safetensors").stat().st_size,
        "processor_state_files": state_files,
    }


__all__ = [
    "SMOLVLA_BASE_REPO_ID",
    "SMOLVLA_BASE_REVISION",
    "SMOLVLA_CAMERA_RENAME",
    "SMOLVLA_VLM_REPO_ID",
    "SMOLVLA_VLM_REVISION",
    "SNAPSHOT_PROVENANCE_FILE",
    "SmolVLASnapshotEvidence",
    "SnapshotEvidence",
    "audit_checkpoint",
    "audit_model_snapshot",
    "audit_smolvla_snapshots",
    "command_options",
    "horizon_evidence",
    "parse_training_metrics",
    "resolve_numeric_checkpoint",
]
