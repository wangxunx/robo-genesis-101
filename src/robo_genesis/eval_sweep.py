"""Sweep every checkpoint of a training run and plot a success-rate curve.

Builds the Genesis scene *once*, then loads each checkpoint in turn and evaluates
it with an identical, fixed protocol (same seeds -> same initial conditions), so
the resulting curve isolates the effect of training progress. Outputs:

  * ``<out-dir>/sweep.json``  -- full structured results (per checkpoint + per episode)
  * ``<out-dir>/sweep.csv``   -- one row per checkpoint (step, success_rate, ...)
  * ``<out-dir>/success_curve.png`` -- success rate vs training step

This is the base building block for the train->eval comparisons: fine-tuning
learning curves now, and later DR ablations (run the same sweep on each training
condition and overlay the curves).

Usage:
    uv run python -m robo_genesis.eval_sweep \
        --run-dir outputs/train/act_banana_pick_50ep \
        --repo-id genesis/banana_pick \
        --dataset-root datasets/banana_pick_50ep \
        --episodes 20 --pick 011_banana

    # Layer B: robustness to runtime physics DR (per-episode friction/mass), fixed
    # across checkpoints. Combine with --dr-appearance for appearance + physics OOD.
    uv run python -m robo_genesis.eval_sweep --run-dir ... --repo-id ... \
        --episodes 20 --dr-runtime --dr-friction 0.6 1.4 --dr-mass 0.8 1.2
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import genesis as gs

from .build_scene import SceneDomainRandomizationConfig, build_scene
from .eval_policy import _str2bool, evaluate_policy, load_policy
from .paths import DATASETS_DIR, EVAL_RESULTS_DIR, resolve_cli_path
from .randomize import DomainRandomizationConfig, EnvRandomizer, RandomizationConfig
from .stats import wilson, wilson_err


def _make_scene_dr(args: argparse.Namespace, domain_index: int) -> SceneDomainRandomizationConfig:
    """Layer A config for appearance domain ``domain_index`` (scene seed = base + index).

    Each domain is a distinct built scene (colors/textures/FOV baked at build time). Within
    a domain, every checkpoint is evaluated on identical initial conditions, so the sweep
    stays a fair comparison; across domains, appearance varies to probe robustness.
    """
    base = args.dr_seed if args.dr_seed is not None else args.seed
    return SceneDomainRandomizationConfig(
        enabled=args.dr_appearance,
        table_color_jitter=args.dr_table_jitter,
        randomize_object_color=args.dr_object_color,
        fov_jitter_deg=args.dr_fov_jitter,
        seed=base + domain_index,
    )


def _build(args: argparse.Namespace, scene_dr: SceneDomainRandomizationConfig | None):
    return build_scene(
        show_viewer=args.vis, n_envs=1, add_world_cam=True, add_wrist_cam=True, scene_dr=scene_dr
    )


def _make_runtime_dr(args: argparse.Namespace) -> DomainRandomizationConfig:
    """Layer B config: per-episode runtime friction / mass / world-cam extrinsics.

    Enabled -> the sweep's ``EnvRandomizer`` re-samples physics/camera every episode. Since the
    randomizer re-seeds off ``seed + ep`` each reset, every checkpoint sees the identical DR
    sequence within a domain, so the comparison stays fair.
    """
    return DomainRandomizationConfig(
        enabled=args.dr_runtime,
        friction_ratio_range=tuple(args.dr_friction),
        mass_ratio_range=tuple(args.dr_mass),
        cam_pos_jitter=args.dr_cam_pos,
        cam_lookat_jitter=args.dr_cam_lookat,
    )


def discover_checkpoints(run_dir: Path, only_steps: list[int] | None = None) -> list[tuple[int, Path]]:
    """Return sorted (step, pretrained_model_dir) for a training run.

    Looks under ``<run_dir>/checkpoints/<step>/pretrained_model``. The ``last``
    symlink is skipped (it duplicates a numbered step). Non-numeric step dirs are
    kept with step=-1 so they still get evaluated (sorted first).
    """
    ckpt_root = run_dir / "checkpoints"
    if not ckpt_root.is_dir():
        raise SystemExit(f"[sweep] no checkpoints dir at {ckpt_root}")

    found: dict[int, Path] = {}
    for child in sorted(ckpt_root.iterdir()):
        if child.is_symlink() or not child.is_dir():
            continue  # skip 'last' symlink and stray files
        pm = child / "pretrained_model"
        if not (pm / "config.json").exists():
            continue
        step = int(child.name) if child.name.isdigit() else -1
        if only_steps and step not in only_steps:
            continue
        found[step] = pm
    return sorted(found.items())


def plot_curve(rows: list[dict], out_png: Path, title: str, per_domain: list[dict] | None = None) -> None:
    steps = [r["step"] for r in rows]
    rates = [r["success_rate"] * 100.0 for r in rows]
    # 95% Wilson error bars on the aggregate (pooled over domains/episodes at each step).
    errs = [wilson_err(r["n_success"], r["episodes"]) for r in rows]
    yerr = [[e[1] * 100.0 for e in errs], [e[2] * 100.0 for e in errs]]
    plt.figure(figsize=(7, 4.5))

    # Faint per-domain curves (when sweeping multiple appearance domains), then the
    # bold aggregate (mean over domains) on top.
    if per_domain and len(per_domain) > 1:
        for dom in per_domain:
            d_steps = [r["step"] for r in dom["rows"]]
            d_rates = [r["success_rate"] * 100.0 for r in dom["rows"]]
            plt.plot(d_steps, d_rates, marker=".", linewidth=1, alpha=0.35, label=f"domain {dom['domain']}")

    agg_label = "aggregate (mean over domains)" if per_domain and len(per_domain) > 1 else None
    plt.errorbar(steps, rates, yerr=yerr, marker="o", linewidth=2.5, color="black",
                 capsize=4, elinewidth=1.2, label=agg_label)
    for x, y in zip(steps, rates):
        plt.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
    plt.xlabel("training step")
    plt.ylabel("success rate (%)")
    plt.title(title)
    plt.ylim(-2, 102)
    plt.grid(True, alpha=0.3)
    if per_domain and len(per_domain) > 1:
        plt.legend(fontsize=8, loc="best")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=120)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep checkpoints -> success-rate curve.")
    parser.add_argument("--run-dir", required=True, help="Training run dir (contains checkpoints/).")
    parser.add_argument("--repo-id", required=True, help="Dataset repo id the policy trained on.")
    parser.add_argument(
        "--dataset-root",
        default=None,
        help="Local dataset directory (default: configured datasets/<repo-name>).",
    )
    parser.add_argument("--device", default="cuda", help="Inference device (cuda | cpu | mps).")
    parser.add_argument("--use-amp", action="store_true")
    parser.add_argument("-c", "--cpu", action="store_true", help="Run the Genesis sim on CPU backend.")
    parser.add_argument("-v", "--vis", action="store_true")
    parser.add_argument("--episodes", type=int, default=20, help="Eval episodes per checkpoint.")
    parser.add_argument("--seed", type=int, default=1000, help="Base eval seed (fixed across checkpoints).")
    parser.add_argument("--max-seconds", type=float, default=15.0)
    parser.add_argument("--pick", nargs="+", default=["011_banana"], help="Object(s) to evaluate on.")
    parser.add_argument("--place", default="024_bowl")
    parser.add_argument("--tol", type=float, default=0.06)
    parser.add_argument("--no-task", action="store_true")
    parser.add_argument("--jitter", type=float, default=0.03)
    parser.add_argument(
        "--balanced",
        type=_str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Stratified near-equal per-object sampling (default). --balanced=false restores the "
        "legacy i.i.d. sampling used by pre-`balanced` sweeps.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        nargs="+",
        default=None,
        help="Only evaluate these checkpoint steps (default: all found).",
    )
    parser.add_argument(
        "--output-dir",
        "--out-dir",
        dest="output_dir",
        default=None,
        help="Output directory (default: configured outputs/eval_results/sweep_<run-name>).",
    )
    # -- Layer A domain randomization (appearance-OOD evaluation) --
    parser.add_argument(
        "--dr-appearance",
        action="store_true",
        help="Evaluate under Layer A appearance domains. The scene is rebuilt once per "
        "domain (domain-outer / checkpoint-inner) so every checkpoint sees the identical "
        "set of domains -- the sweep stays a fair comparison.",
    )
    parser.add_argument(
        "--dr-domains",
        type=int,
        default=3,
        help="Number of appearance domains to sweep (needs --dr-appearance). Total rollouts "
        "= domains x checkpoints x episodes.",
    )
    parser.add_argument(
        "--dr-table-jitter", type=float, default=0.15, help="Layer-A: +/- per-RGB-channel table color jitter."
    )
    parser.add_argument(
        "--dr-object-color", action="store_true", help="Layer-A: recolor objects within DR_APPEARANCE_PRIORS."
    )
    parser.add_argument(
        "--dr-fov-jitter", type=float, default=0.0, help="Layer-A: +/- deg jitter on both cameras' vertical FOV."
    )
    parser.add_argument(
        "--dr-seed",
        type=int,
        default=None,
        help="Base seed for the appearance-domain sequence (default: --seed). Domain d uses base + d.",
    )
    # -- Layer B domain randomization (per-episode runtime physics / camera extrinsics) --
    parser.add_argument(
        "--dr-runtime",
        action="store_true",
        help="Evaluate under Layer B runtime DR: friction/mass/world-cam extrinsics are "
        "re-sampled every episode. Orthogonal to --dr-appearance; the per-episode DR sequence "
        "is fixed across checkpoints so the sweep stays a fair comparison.",
    )
    parser.add_argument(
        "--dr-friction",
        type=float,
        nargs=2,
        metavar=("LO", "HI"),
        default=(0.7, 1.3),
        help="Layer-B: friction-ratio range (shared across object/finger/table).",
    )
    parser.add_argument(
        "--dr-mass",
        type=float,
        nargs=2,
        metavar=("LO", "HI"),
        default=(0.8, 1.2),
        help="Layer-B: per-object multiplicative mass-ratio range.",
    )
    parser.add_argument(
        "--dr-cam-pos", type=float, default=0.0, help="Layer-B: world-cam position jitter (+/- m)."
    )
    parser.add_argument(
        "--dr-cam-lookat", type=float, default=0.0, help="Layer-B: world-cam lookat jitter (+/- m)."
    )
    args = parser.parse_args()

    run_dir = resolve_cli_path(args.run_dir)
    dataset_root = resolve_cli_path(
        args.dataset_root,
        default=DATASETS_DIR / args.repo_id.split("/")[-1],
    )
    checkpoints = discover_checkpoints(run_dir, args.steps)
    if not checkpoints:
        raise SystemExit(f"[sweep] no usable checkpoints found under {run_dir}/checkpoints")
    out_dir = resolve_cli_path(
        args.output_dir,
        default=EVAL_RESULTS_DIR / f"sweep_{run_dir.name}",
    )

    print(f"[sweep] {len(checkpoints)} checkpoint(s): {[s for s, _ in checkpoints]}")

    n_domains = args.dr_domains if args.dr_appearance else 1
    if args.dr_appearance:
        print(f"[sweep] appearance DR: {n_domains} domain(s), domain-outer / checkpoint-inner")

    runtime_dr = _make_runtime_dr(args)
    if args.dr_runtime:
        print(
            f"[sweep] runtime DR (Layer B) on: friction={runtime_dr.friction_ratio_range} "
            f"mass_ratio={runtime_dr.mass_ratio_range} cam_pos={runtime_dr.cam_pos_jitter} "
            f"cam_lookat={runtime_dr.cam_lookat_jitter}"
        )

    backend = gs.cpu if args.cpu else gs.gpu
    gs.init(backend=backend)

    # Aggregate per checkpoint across all domains (preserves checkpoint order).
    agg: dict[int, dict] = {
        step: {"checkpoint": str(pm), "n_success": 0, "episodes": 0, "n_diverged": 0} for step, pm in checkpoints
    }
    per_ckpt_full: list[dict] = []   # one entry per (domain, checkpoint)
    per_domain: list[dict] = []      # per-domain curve rows, for plotting/overlay

    for d in range(n_domains):
        scene_dr = _make_scene_dr(args, d) if args.dr_appearance else None
        # Rebuild the scene for each new appearance domain (gs.destroy()+init() is the
        # supported repeated-init pattern). The eval seed is offset per domain so poses
        # also vary across domains, while staying identical across checkpoints within a domain.
        if d == 0:
            bundle = _build(args, scene_dr)
        else:
            gs.destroy()
            gs.init(backend=backend)
            bundle = _build(args, scene_dr)
        eval_seed = args.seed + d * args.episodes
        scene_seed = scene_dr.seed if scene_dr is not None else None
        if args.dr_appearance:
            print(f"\n[sweep] ===== appearance domain {d} (scene_seed={scene_seed}, eval_seed={eval_seed}) =====")

        # One randomizer per (rebuilt) bundle. Layer-B runtime DR lives in its config; because
        # reset() re-seeds off eval_seed+ep, the per-episode physics/camera sequence is identical
        # across checkpoints within this domain -> fair comparison. When runtime DR is off this
        # is behaviorally identical to evaluate_policy's default randomizer.
        randomizer = EnvRandomizer(
            bundle,
            RandomizationConfig(pos_jitter=args.jitter, randomize_pick=False, seed=eval_seed, dr=runtime_dr),
        )

        domain_rows: list[dict] = []
        for step, pm in checkpoints:
            label = f"dom{d}:step{step}" if args.dr_appearance else str(step)
            print(f"[sweep] --- domain {d} checkpoint step={step} ---")
            pb = load_policy(
                str(pm),
                args.repo_id,
                str(dataset_root),
                args.device,
                use_amp=args.use_amp,
            )
            res = evaluate_policy(
                bundle, pb,
                episodes=args.episodes,
                seed=eval_seed,
                max_seconds=args.max_seconds,
                pick=args.pick,
                place=args.place,
                tol=args.tol,
                no_task=args.no_task,
                jitter=args.jitter,
                balanced=args.balanced,
                randomizer=randomizer,
                label=label,
            )
            agg[step]["n_success"] += res["n_success"]
            agg[step]["episodes"] += res["episodes"]
            agg[step]["n_diverged"] += res.get("n_diverged", 0)
            agg[step]["policy_type"] = pb.policy_type
            domain_rows.append(
                {"step": step, "success_rate": res["success_rate"],
                 "n_success": res["n_success"], "episodes": res["episodes"],
                 "n_diverged": res.get("n_diverged", 0)}
            )
            per_ckpt_full.append(
                {"domain": d, "scene_seed": scene_seed, "eval_seed": eval_seed,
                 "step": step, "checkpoint": str(pm), **res}
            )
        per_domain.append({"domain": d, "scene_seed": scene_seed, "eval_seed": eval_seed, "rows": domain_rows})

    # Aggregate rows (pooled over domains) per checkpoint, with a 95% Wilson CI over all episodes.
    rows: list[dict] = []
    for step, v in agg.items():
        ci_lo, ci_hi = wilson(v["n_success"], v["episodes"])
        rows.append({
            "step": step,
            "success_rate": v["n_success"] / max(1, v["episodes"]),
            "n_success": v["n_success"],
            "episodes": v["episodes"],
            "n_diverged": v["n_diverged"],
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "policy_type": v.get("policy_type"),
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    sweep = {
        "meta": {
            "run_dir": str(run_dir),
            "repo_id": args.repo_id,
            "episodes": args.episodes,
            "seed": args.seed,
            "pick": args.pick,
            "max_seconds": args.max_seconds,
            "jitter": args.jitter,
            "balanced": args.balanced,
            "dr_appearance": args.dr_appearance,
            "dr_domains": n_domains,
            "dr_table_jitter": args.dr_table_jitter,
            "dr_object_color": args.dr_object_color,
            "dr_fov_jitter": args.dr_fov_jitter,
            "dr_seed_base": (args.dr_seed if args.dr_seed is not None else args.seed) if args.dr_appearance else None,
            "dr_runtime": args.dr_runtime,
            "dr_friction": list(args.dr_friction) if args.dr_runtime else None,
            "dr_mass_ratio": list(args.dr_mass) if args.dr_runtime else None,
            "dr_cam_pos_jitter": args.dr_cam_pos if args.dr_runtime else None,
            "dr_cam_lookat_jitter": args.dr_cam_lookat if args.dr_runtime else None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
        "aggregate": rows,
        "per_domain": per_domain,
        "evaluations": per_ckpt_full,
    }
    with open(out_dir / "sweep.json", "w") as f:
        json.dump(sweep, f, indent=2)
    with open(out_dir / "sweep.csv", "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["step", "success_rate", "ci_lo", "ci_hi", "n_success", "episodes",
                        "n_diverged", "policy_type"],
        )
        w.writeheader()
        w.writerows(rows)
    title = f"{run_dir.name}: success vs step"
    if args.dr_appearance:
        title += f" ({n_domains} appearance domains)"
    plot_curve(rows, out_dir / "success_curve.png", title=title, per_domain=per_domain)

    total_diverged = sum(r["n_diverged"] for r in rows)
    print("\n[sweep] summary (aggregate over domains):")
    for r in rows:
        note = f"  ({r['n_diverged']} diverged)" if r["n_diverged"] else ""
        print(
            f"  step {r['step']:>7}: {r['n_success']}/{r['episodes']} = {r['success_rate']:.1%} "
            f"[95% CI {r['ci_lo']:.1%}, {r['ci_hi']:.1%}]{note}"
        )
    if total_diverged:
        print(
            f"[sweep] NOTE: {total_diverged} episode(s) diverged (NaN physics) and were counted as "
            f"failures. Consider narrowing the DR ranges or raising sim substeps if this is large."
        )
    print(f"\n[sweep] wrote: {out_dir}/sweep.json, sweep.csv, success_curve.png")


if __name__ == "__main__":
    main()
