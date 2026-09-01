import argparse
import json
from pathlib import Path

import pytest

from robo_genesis.train_policy import build_command
from robo_genesis.training_contract import (
    SMOLVLA_BASE_REPO_ID,
    SMOLVLA_BASE_REVISION,
    SMOLVLA_CAMERA_RENAME,
    SMOLVLA_VLM_REPO_ID,
    SMOLVLA_VLM_REVISION,
    SNAPSHOT_PROVENANCE_FILE,
    audit_checkpoint,
    audit_smolvla_snapshots,
    command_options,
    horizon_evidence,
    parse_training_metrics,
    resolve_numeric_checkpoint,
)


def _snapshot(tmp_path: Path, repo_id: str, revision: str, files: tuple[str, ...]) -> Path:
    path = tmp_path / f"models--{repo_id.replace('/', '--')}" / "snapshots" / revision
    path.mkdir(parents=True)
    for name in files:
        (path / name).write_text("data", encoding="utf-8")
    return path


def _training_args(tmp_path: Path, base: Path, vlm: Path) -> argparse.Namespace:
    return argparse.Namespace(
        policy="smolvla",
        policy_path=str(base),
        policy_type=None,
        smolvla_vlm_path=str(vlm),
        dataset_root=str(tmp_path / "dataset"),
        repo_id="local/example",
        batch_size=1,
        name="smoke",
        output_dir=str(tmp_path / "run"),
        steps=1,
        save_freq=1,
        log_freq=1,
        num_workers=0,
        seed=1000,
        device="cuda",
        push_to_hub=False,
        wandb=False,
        video_backend="pyav",
        rename_map=None,
    )


def _smolvla_snapshots(tmp_path: Path) -> tuple[Path, Path]:
    base = _snapshot(
        tmp_path,
        SMOLVLA_BASE_REPO_ID,
        SMOLVLA_BASE_REVISION,
        (
            "config.json",
            "model.safetensors",
            "policy_preprocessor.json",
            "policy_postprocessor.json",
        ),
    )
    (base / "config.json").write_text(
        json.dumps({"type": "smolvla", "vlm_model_name": SMOLVLA_VLM_REPO_ID}),
        encoding="utf-8",
    )
    vlm = _snapshot(
        tmp_path,
        SMOLVLA_VLM_REPO_ID,
        SMOLVLA_VLM_REVISION,
        ("config.json", "model.safetensors", "processor_config.json", "tokenizer_config.json"),
    )
    return base, vlm


def test_pinned_smolvla_command_audits_both_snapshots(tmp_path: Path) -> None:
    base, vlm = _smolvla_snapshots(tmp_path)

    evidence = audit_smolvla_snapshots(base, vlm)
    command = build_command(_training_args(tmp_path, base, vlm), [])
    options = command_options(command)

    assert evidence.base.revision == SMOLVLA_BASE_REVISION
    assert evidence.vlm.revision == SMOLVLA_VLM_REVISION
    assert options["--policy.path"] == str(base)
    assert options["--policy.vlm_model_name"] == str(vlm)
    assert json.loads(str(options["--rename_map"])) == SMOLVLA_CAMERA_RENAME


def test_snapshot_audit_rejects_a_different_revision(tmp_path: Path) -> None:
    base, vlm = _smolvla_snapshots(tmp_path)
    wrong = vlm.parent / ("0" * 40)
    vlm.rename(wrong)

    with pytest.raises(ValueError, match="does not match expected"):
        audit_smolvla_snapshots(base, wrong)


def test_snapshot_audit_accepts_explicit_provenance_for_copied_content(tmp_path: Path) -> None:
    cached_base, cached_vlm = _smolvla_snapshots(tmp_path / "cache")
    copied_base = tmp_path / "copied-base"
    copied_vlm = tmp_path / "copied-vlm"
    cached_base.rename(copied_base)
    cached_vlm.rename(copied_vlm)
    for path, repo_id, revision in (
        (copied_base, SMOLVLA_BASE_REPO_ID, SMOLVLA_BASE_REVISION),
        (copied_vlm, SMOLVLA_VLM_REPO_ID, SMOLVLA_VLM_REVISION),
    ):
        (path / SNAPSHOT_PROVENANCE_FILE).write_text(
            json.dumps({"repo_id": repo_id, "revision": revision}),
            encoding="utf-8",
        )

    evidence = audit_smolvla_snapshots(copied_base, copied_vlm)

    assert evidence.base.identity_source == SNAPSHOT_PROVENANCE_FILE
    assert evidence.vlm.identity_source == SNAPSHOT_PROVENANCE_FILE


def test_horizon_and_log_checks_reject_invalid_evidence() -> None:
    assert horizon_evidence(chunk_size=40, n_action_steps=8, fps=10)["replan_seconds"] == 0.8
    with pytest.raises(ValueError, match="n_action_steps"):
        horizon_evidence(chunk_size=10, n_action_steps=11, fps=10)

    metrics = parse_training_metrics(
        "step:1 loss:6.305 grdn:42.467 lr:1.0e-4 updt_s:2.75"
    )
    assert metrics == {
        "records": 1,
        "step": 1,
        "loss": 6.305,
        "gradient_norm": 42.467,
        "update_seconds": 2.75,
    }
    with pytest.raises(ValueError, match="no optimizer-step"):
        parse_training_metrics("training process exited")
    with pytest.raises(ValueError, match="non-finite"):
        parse_training_metrics("step:1 loss:nan grdn:42.467 updt_s:2.75")


def test_checkpoint_audit_uses_numeric_directory_and_processor_state(tmp_path: Path) -> None:
    run = tmp_path / "run"
    model = run / "checkpoints" / "000001" / "pretrained_model"
    model.mkdir(parents=True)
    (run / "checkpoints" / "last").symlink_to("000001")
    (model / "config.json").write_text(
        json.dumps(
            {
                "type": "smolvla",
                "chunk_size": 50,
                "n_action_steps": 10,
                "output_features": {"action": {"shape": [9]}},
            }
        ),
        encoding="utf-8",
    )
    (model / "train_config.json").write_text(
        json.dumps(
            {
                "dataset": {"repo_id": "local/example", "root": "/tmp/example"},
                "seed": 1000,
                "rename_map": SMOLVLA_CAMERA_RENAME,
            }
        ),
        encoding="utf-8",
    )
    (model / "model.safetensors").write_bytes(b"weights")
    (model / "policy_preprocessor.json").write_text(
        json.dumps({"steps": [{"state_file": "normalizer.safetensors"}]}),
        encoding="utf-8",
    )
    (model / "policy_postprocessor.json").write_text(
        json.dumps({"steps": []}), encoding="utf-8"
    )
    (model / "normalizer.safetensors").write_bytes(b"state")

    assert resolve_numeric_checkpoint(run) == model
    evidence = audit_checkpoint(model, expected_policy_type="smolvla")
    assert evidence["action_dim"] == 9
    assert evidence["rename_map"] == SMOLVLA_CAMERA_RENAME
    assert evidence["processor_state_files"] == ["normalizer.safetensors"]
