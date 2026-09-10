---
layout: home
title: RoboGenesis 101

hero:
  name: RoboGenesis 101
  text: Practical Robot Learning with Genesis
  tagline: A progressive path through simulation, control, data, policy training, and closed-loop evaluation for learners with basic Python experience
  actions:
    - theme: brand
      text: Start with L01
      link: /en/lessons/l01-introduction-and-environment-diagnostics
    - theme: alt
      text: 中文
      link: /zh/

features:
  - title: Genesis foundations
    details: Learn environment diagnostics, scenes, rigid-body physics, robot control, inverse kinematics, cameras, and parallel simulation.
  - title: From control to grasping
    details: Build a grasping scene and understand scripted experts and demonstration acquisition.
  - title: From data to policies
    details: Continue through data recording, imitation learning, domain randomization, policy training, and closed-loop evaluation.
---

## Course status

> L01–L07 are `cpu-verified` after their clean-kernel CPU verification; their
> additional AMD paths also passed their respective contracts on the reference R9700.
> L08 is `gpu-verified` after its bilingual CPU numerical paths, CPU+EGL path, and
> scripted-expert path on a reference R9700 all passed. L09 is also `gpu-verified`:
> its bilingual CPU diagnostics, CPU+EGL path, and dual-camera recording and readback
> on a reference R9700 all passed. The renumbered L12 training content is
> `gpu-verified` after ACT and SmolVLA GPU smoke, checkpoint audit, and reload checks.
> L10 is `cpu-verified` after its bilingual CPU-only data-readback and inspection
> paths passed. L11 and L13 remain `planned`.

| Lesson | Topic | Planned duration | Hardware | Status |
|---|---|---:|---|---|
| L01 | [Introduction, Runtime Platforms, and Environment Diagnostics](/en/lessons/l01-introduction-and-environment-diagnostics) | 30 min | `cpu-ok` | `cpu-verified` |
| L02 | [Scenes, Entities, and the Simulation Lifecycle](/en/lessons/l02-scenes-entities-and-simulation-lifecycle) | 90 min | `cpu-ok` | `cpu-verified` |
| L03 | [Rigid-Body Physics and Stable Simulation](/en/lessons/l03-rigid-body-physics-and-stable-simulation) | 90 min | `cpu-ok` | `cpu-verified` |
| L04 | [Robot Models, Degrees of Freedom, and Joint Control](/en/lessons/l04-robot-models-dofs-and-joint-control) | 90 min | `cpu-ok` | `cpu-verified` |
| L05 | [Inverse Kinematics, End-Effector Poses, and Cameras](/en/lessons/l05-inverse-kinematics-end-effector-poses-and-cameras) | 120 min | `cpu-ok` | `cpu-verified` |
| L06 | [Parallel Simulation and Batched Franka Control](/en/lessons/l06-parallel-simulation-and-batched-franka-control) | 90 min | `cpu-ok` | `cpu-verified` |
| L07 | [Building a Grasping Task Scene](/en/lessons/l07-building-a-grasping-task-scene) | 90 min | `cpu-ok` | `cpu-verified` |
| L08 | [Demonstration Acquisition and Scripted Experts](/en/lessons/l08-demonstration-acquisition-and-scripted-experts) | 120 min | `gpu-recommended` | `gpu-verified` |
| L09 | [Synthetic Data Recording and Collection Throughput](/en/lessons/l09-synthetic-data-recording-and-throughput) | 120 min | `gpu-recommended` | `gpu-verified` |
| L10 | [Dataset Anatomy and Imitation Learning 101](/en/lessons/l10-dataset-anatomy-and-imitation-learning) | 90 min | `gpu-recommended` | `cpu-verified` |
| L11 | [Domain Randomization](/en/lessons/l11-domain-randomization) | 90 min | `gpu-recommended` | `planned` |
| L12 | [Training ACT and SmolVLA Policies](/en/lessons/l12-act-and-smolvla-policy-training) | 150 min | `gpu-required` | `gpu-verified` |
| L13 | [Closed-Loop Evaluation and Capstone](/en/lessons/l13-closed-loop-evaluation-and-capstone) | 120 min | `gpu-required` | `planned` |
