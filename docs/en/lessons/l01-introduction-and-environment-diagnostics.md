---
lesson: L01
slug: introduction-and-environment-diagnostics
locale: en
title: "Introduction, Runtime Platforms, and Environment Diagnostics"
duration_minutes: 30
hardware: cpu-ok
status: cpu-verified
---

# L01 · Introduction, Runtime Platforms, and Environment Diagnostics

> **Hardware contract:** CPU is enough for this lesson and the minimum exercises
> in L01–L06. An AMD ROCm GPU is the reference path for later data generation,
> policy training, and closed-loop evaluation, but it is not an L01 requirement.

## The course in one view

RoboGenesis 101 follows one practical robot-learning loop:

```text
Genesis simulation → robot control and IK → scripted demonstrations
                   → LeRobot dataset → ACT/SmolVLA training
                   → closed-loop evaluation
```

By the end of the course, you will understand how a Franka arm can learn a
fruit-picking task in simulation. The lessons build that result in order:

- L01–L06 introduce the environment, simulation, control, cameras, and grasping scene;
- L07–L10 generate demonstrations and turn them into training data; and
- L11–L12 train policies and test them in closed-loop rollouts.

Training loss and a plausible open-loop action are not task success. The final
evidence comes from applying the policy in the simulator and measuring the task
outcome.

## What you need to accomplish today

L01 has a deliberately small job. After this lesson, you should be able to:

1. locate each major stage in the course workflow;
2. run the environment notebook from top to bottom and identify the Python,
   Genesis, PyTorch, and selected compute backend; and
3. confirm that Genesis can build and step one tiny scene before moving to L02.

You do not need to learn an environment-diagnostic framework. The notebook is a
short entry check, not the subject of the course.

## Before opening the notebook

Environment installation is pre-class preparation. From the repository root,
install the base environment and start Jupyter with the same interpreter:

```sh
uv sync --locked
uv run jupyter lab
```

Then open
`notebooks/en/l01-introduction-and-environment-diagnostics.ipynb`, confirm that
the project `.venv` is the selected kernel, and choose **Run All** once.

The portable lockfile does not by itself select the reviewed AMD PyTorch build.
If you are preparing the full AMD training environment, follow the wheel and
checksum instructions in the
[compatibility matrix](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md).

## CPU and AMD are both valid here

The notebook automatically prefers the verified AMD backend when a ROCm build
of PyTorch and an AMD GPU are both visible. Otherwise it uses Genesis on CPU and
prints that choice clearly.

ROCm builds of PyTorch reuse the `torch.cuda` API. Therefore `cuda:0` can mean
an AMD GPU in this course. These two fields tell the difference:

```python
torch.version.hip       # set for a ROCm build
torch.version.cuda      # None on the verified ROCm build
```

No visible GPU is not an L01 failure. CPU learners can continue through the
minimum L01–L06 path; the full training lessons later state their stronger
hardware requirements.

## Run the self-check

The notebook contains four short executable stages:

| Stage | What you should see |
|---|---|
| Environment summary | Python, Genesis, PyTorch, HIP, and device information from the active kernel |
| Backend and tensor | `amdgpu` when the reviewed ROCm path is available, otherwise `cpu`; a small tensor result |
| Genesis smoke | A plane and sphere build successfully; the sphere's height decreases after stepping |
| Final summary | `ENVIRONMENT CHECK: PASSED`, the selected backend, and the next lesson |

The scene code is intentionally shown directly, but L01 does not explain every
Genesis object yet. L02 introduces `Scene`, `Entity`, `build()`, and `step()` in
detail. Here the tiny scene only proves that the installed runtime can perform
real work instead of merely importing a package.

The notebook also writes a small report to `outputs/l01/env_report.json`. It is
useful when asking for help: share it together with the error message. You do
not need to open or edit the report itself.

## What is required and what is only a preview

| Result | Meaning in L01 |
|---|---|
| Python 3.12, PyTorch, and Genesis 1.3.3 work | Required before continuing |
| A tensor operation succeeds on the selected device | Required before continuing |
| The minimal scene builds, steps, and produces finite changed state | Required before continuing |
| AMD GPU and HIP are visible | Useful confirmation for the reference platform; CPU fallback is allowed |
| LeRobot 0.6.0 is installed | Useful preview for later training; not required for L01–L06 |
| Camera rendering, YCB assets, and policy training work | Not checked here; later lessons verify them when first needed |

## Quick troubleshooting

| Symptom | Next action |
|---|---|
| The notebook uses the wrong Python | Select the repository `.venv` kernel and restart. |
| `torch` or `genesis` cannot import | Run `uv sync --locked` from the repository root, then restart the kernel. |
| AMD hardware exists but the notebook selects CPU | Check the reviewed ROCm wheels, `torch.version.hip`, device permissions, and `ROCR_VISIBLE_DEVICES`. |
| The first scene build seems slow | Wait for Genesis's first kernel compilation; this smoke is not a benchmark. |
| Rerunning fails after `gs.init()` | Restart the kernel, then use **Run All** once from the top. |

If the final line says `PASSED`, continue to L02. If a required cell stops with
an exception, fix that cell's concrete message before continuing. Optional GPU
or LeRobot notices do not block the CPU fundamentals path.

## Checkpoint and next lesson

Before leaving L01, make sure you can answer:

- Which backend did this notebook actually select?
- Did the tensor operation and sphere state change both succeed?
- If CPU was selected, which later part of the course will eventually require a GPU?

L02 takes the tiny smoke scene apart and explains the simulation lifecycle:
declaring entities, calling `build()`, stepping the world, reading state, and
optionally rendering an image.

## Sources

- [Genesis documentation](https://genesis-world.readthedocs.io/) — installation and backend initialization.
- [PyTorch HIP semantics](https://docs.pytorch.org/docs/stable/notes/hip.html) — why ROCm uses `torch.cuda` interfaces.
- [Project compatibility matrix](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md) — verified versions and AMD platform evidence.
