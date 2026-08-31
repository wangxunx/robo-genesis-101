# RoboGenesis 101

[简体中文](README.md)

> **Project status: Alpha / course development.** L02 now has bilingual lecture
> and notebook content and has passed clean-kernel CPU verification, so its
> status is `cpu-verified`; the other 11 lessons remain `planned`. The presence
> of a page or notebook does not mean that lesson has been verified.

RoboGenesis 101 is a Datawhale open-source course for learners with basic Python experience who want a structured, hands-on introduction to robot learning. Using Genesis as its simulation platform, the course connects environment diagnostics, scenes, and rigid-body physics with robot control, inverse kinematics, grasping, demonstration data, imitation learning, policy training, and closed-loop evaluation.

The course follows a concept–code–experiment–evidence loop: lectures explain mechanisms, reusable behavior lives in the Python package, notebooks provide executable practice, and course status changes only when the corresponding content and verification evidence exist.

## Read online

- English course: <https://wangxunx.github.io/robo-genesis-101/en/>
- 中文课程：<https://wangxunx.github.io/robo-genesis-101/zh/>

The online site currently presents the course outline and material status. Complete lesson content will be published progressively once it is ready and has been verified.

## Audience and prerequisites

Learners should have:

- basic Python skills, including functions, classes, NumPy arrays, and command-line arguments;
- basic experience with a terminal, Git, and virtual environments;
- an interest in robot simulation, manipulation learning, or imitation learning.

Prior experience with Genesis, robot kinematics, or policy training is not required. Each concept is introduced when it first becomes a prerequisite for the practical work.

## Learning path

The course follows these dependencies:

1. Genesis environments, scenes, entities, physics, and the simulation lifecycle;
2. robot degrees of freedom, joint control, inverse kinematics, end-effector poses, and cameras;
3. grasping tasks, scripted experts, demonstration acquisition, and data recording;
4. datasets, imitation learning, domain randomization, ACT/SmolVLA training, and closed-loop evaluation.

Training loss or open-loop action prediction is not treated as task success. The final evaluation uses closed-loop rollouts and explicit success criteria.

## Course progress

`course.json` is the canonical structured source for lesson order, titles, duration, hardware requirements, and status.

| Lesson | Topic | Planned duration | Hardware | Status |
|---|---|---:|---|---|
| L01 | [Introduction, Runtime Platforms, and Environment Diagnostics](docs/en/lessons/l01-introduction-and-environment-diagnostics.md) | 60 min | `cpu-ok` | `planned` |
| L02 | [Scenes, Entities, and the Simulation Lifecycle](docs/en/lessons/l02-scenes-entities-and-simulation-lifecycle.md) | 90 min | `cpu-ok` | `cpu-verified` |
| L03 | [Rigid-Body Physics and Stable Simulation](docs/en/lessons/l03-rigid-body-physics-and-stable-simulation.md) | 90 min | `cpu-ok` | `planned` |
| L04 | [Robot Models, Degrees of Freedom, and Joint Control](docs/en/lessons/l04-robot-models-dofs-and-joint-control.md) | 90 min | `cpu-ok` | `planned` |
| L05 | [Inverse Kinematics, End-Effector Poses, and Cameras](docs/en/lessons/l05-inverse-kinematics-end-effector-poses-and-cameras.md) | 120 min | `cpu-ok` | `planned` |
| L06 | [Building a Grasping Task Scene](docs/en/lessons/l06-building-a-grasping-task-scene.md) | 120 min | `cpu-ok` | `planned` |
| L07 | [Demonstration Acquisition and Scripted Experts](docs/en/lessons/l07-demonstration-acquisition-and-scripted-experts.md) | 120 min | `gpu-recommended` | `planned` |
| L08 | [Synthetic Data Recording and Collection Throughput](docs/en/lessons/l08-synthetic-data-recording-and-throughput.md) | 120 min | `gpu-recommended` | `planned` |
| L09 | [Dataset Anatomy and Imitation Learning 101](docs/en/lessons/l09-dataset-anatomy-and-imitation-learning.md) | 90 min | `gpu-recommended` | `planned` |
| L10 | [Domain Randomization](docs/en/lessons/l10-domain-randomization.md) | 90 min | `gpu-recommended` | `planned` |
| L11 | [Training ACT and SmolVLA Policies](docs/en/lessons/l11-act-and-smolvla-policy-training.md) | 150 min | `gpu-required` | `planned` |
| L12 | [Closed-Loop Evaluation and Capstone](docs/en/lessons/l12-closed-loop-evaluation-and-capstone.md) | 120 min | `gpu-required` | `planned` |

Statuses progress from `planned` to `draft`, `reviewed`, `cpu-verified` or
`gpu-verified`, and finally `published`. See the [course content guide](CONTENT_GUIDE.md) for the evidence required at each stage.

## Environment baseline

- Python: `3.12.x`; the declared project range is `>=3.12,<3.13`.
- Genesis: `genesis-world==1.3.3`.
- LeRobot: the training extra pins `lerobot==0.6.0`.
- Full-training reference platform: Linux x86_64, AMD Radeon AI PRO R9700, system ROCm 7.2.0, and the tested ROCm 7.2.1 PyTorch wheels.

Other AMD GPUs, NVIDIA CUDA, the complete CPU-only path, Apple Silicon, Windows, and other Python versions have not been verified. See the [compatibility matrix](COMPATIBILITY.md) for exact versions, wheel checksums, verified capabilities, and limitations.

## Quick start

### Read the documentation locally

The documentation CI uses Node.js 24; using the same major version locally is recommended:

```sh
npm ci
npm run docs:dev
```

Build the static site with:

```sh
npm run docs:build
```

### Run the lightweight quality gates

This environment installs only pytest and the current project. It does not install Genesis, PyTorch, or the training stack:

```sh
UV_PROJECT_ENVIRONMENT=.venv uv sync --only-group dev --locked
uv pip install --python .venv/bin/python --no-deps --editable .
.venv/bin/python -m robo_genesis.course_validation
.venv/bin/python -m pytest
```

After installation, the same validator is available as `robo-genesis-validate`.

### Install the complete course dependencies

```sh
uv sync --locked --all-extras
```

This command uses the repository's portable dependency resolution; by itself it is not a verified AMD ROCm environment. The AMD reference platform must additionally install and verify the ROCm wheels documented in the [compatibility matrix](COMPATIBILITY.md). After installation, validate the four vendored YCB objects with:

```sh
uv run python -m robo_genesis.setup_assets
```

The lesson notebooks and full experiments have not been published yet. The current placeholders show the planned course structure and are not finished tutorials.

## Repository layout

```text
docs/                       VitePress site and bilingual lectures
notebooks/{zh,en}/          paired lesson notebooks
src/robo_genesis/           reusable scene, data, training, and evaluation code
scripts/                    repository-level development and validation entry points
tests/                      pure-logic and repository-contract tests
assets/third_party/         audited third-party assets under their original terms
course.json                 canonical course metadata and status
```

## Contributing

Before opening an issue or pull request, read:

- the [contribution guide](CONTRIBUTING.md) for environments, workflow, verification, and the PR checklist;
- the [course content guide](CONTENT_GUIDE.md) for bilingual lectures, notebooks, code, status, and evidence requirements;
- the [third-party notices](NOTICE.md) for provenance, licensing, and redistribution boundaries.

## Contributors

| Name | Role |
|---|---|
| Xun Wang（王迅） | Project lead; course design, development, and maintenance |

The contributor list is updated only for contributions that have actually been merged.

## License

Unless otherwise noted, original code, lectures, notebooks, exercises, and original course media that this project has the right to license are released under the [MIT License](LICENSE). By submitting an original contribution, contributors agree to provide it under that license.

Third-party code, assets, datasets, models, trademarks, and other materials retain their original terms and are not covered by the project MIT License. See [NOTICE.md](NOTICE.md) and [LICENSE_POLICY.md](LICENSE_POLICY.md) for the exact boundary. The vendored YCB assets are CC BY-NC 4.0 material, not MIT material.

## Acknowledgements

Thanks to the [Datawhale](https://github.com/datawhalechina) open-source learning community. This course uses [Genesis](https://github.com/Genesis-Embodied-AI/Genesis) and [LeRobot](https://github.com/huggingface/lerobot) for its practical workflow; these references do not imply endorsement by those projects.
