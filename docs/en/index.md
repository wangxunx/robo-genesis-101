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
    details: Learn environment diagnostics, scenes, rigid-body physics, robot control, inverse kinematics, and cameras.
  - title: From control to grasping
    details: Build a grasping scene and understand scripted experts and demonstration acquisition.
  - title: From data to policies
    details: Continue through data recording, imitation learning, domain randomization, policy training, and closed-loop evaluation.
---

## Course status

> L01–L04 are `cpu-verified` after their clean-kernel CPU verification; their
> additional AMD paths also passed their respective contracts on the reference R9700.
> L11 is `gpu-verified` after ACT and SmolVLA GPU smoke and checkpoint-reload
> verification. The other 7 lessons remain `planned`; an existing page does not
> mean that lesson has been verified.

| Lesson | Topic | Planned duration | Hardware | Status |
|---|---|---:|---|---|
| L01 | [Introduction, Runtime Platforms, and Environment Diagnostics](/en/lessons/l01-introduction-and-environment-diagnostics) | 30 min | `cpu-ok` | `cpu-verified` |
| L02 | [Scenes, Entities, and the Simulation Lifecycle](/en/lessons/l02-scenes-entities-and-simulation-lifecycle) | 90 min | `cpu-ok` | `cpu-verified` |
| L03 | [Rigid-Body Physics and Stable Simulation](/en/lessons/l03-rigid-body-physics-and-stable-simulation) | 90 min | `cpu-ok` | `cpu-verified` |
| L04 | [Robot Models, Degrees of Freedom, and Joint Control](/en/lessons/l04-robot-models-dofs-and-joint-control) | 90 min | `cpu-ok` | `cpu-verified` |
| L05 | [Inverse Kinematics, End-Effector Poses, and Cameras](/en/lessons/l05-inverse-kinematics-end-effector-poses-and-cameras) | 120 min | `cpu-ok` | `planned` |
| L06 | [Building a Grasping Task Scene](/en/lessons/l06-building-a-grasping-task-scene) | 120 min | `cpu-ok` | `planned` |
| L07 | [Demonstration Acquisition and Scripted Experts](/en/lessons/l07-demonstration-acquisition-and-scripted-experts) | 120 min | `gpu-recommended` | `planned` |
| L08 | [Synthetic Data Recording and Collection Throughput](/en/lessons/l08-synthetic-data-recording-and-throughput) | 120 min | `gpu-recommended` | `planned` |
| L09 | [Dataset Anatomy and Imitation Learning 101](/en/lessons/l09-dataset-anatomy-and-imitation-learning) | 90 min | `gpu-recommended` | `planned` |
| L10 | [Domain Randomization](/en/lessons/l10-domain-randomization) | 90 min | `gpu-recommended` | `planned` |
| L11 | [Training ACT and SmolVLA Policies](/en/lessons/l11-act-and-smolvla-policy-training) | 150 min | `gpu-required` | `gpu-verified` |
| L12 | [Closed-Loop Evaluation and Capstone](/en/lessons/l12-closed-loop-evaluation-and-capstone) | 120 min | `gpu-required` | `planned` |
