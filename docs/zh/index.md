---
layout: home
title: RoboGenesis 101

hero:
  name: RoboGenesis 101
  text: 基于 Genesis 的机器人学习实践
  tagline: 面向具备 Python 基础的学习者，贯通仿真、控制、数据、策略训练与闭环评估
  actions:
    - theme: brand
      text: 从 L01 开始
      link: /zh/lessons/l01-introduction-and-environment-diagnostics
    - theme: alt
      text: English
      link: /en/

features:
  - title: Genesis 基础
    details: 学习环境诊断、场景、刚体物理、机器人控制、逆运动学、相机与并行仿真。
  - title: 从控制到抓取
    details: 搭建抓取场景，理解脚本化专家和演示数据获取。
  - title: 从数据到策略
    details: 依次学习数据录制、模仿学习、域随机化、策略训练与闭环评估。
---

## 课程状态

> L01–L07 已通过各自的 CPU clean-kernel 验证，状态均为 `cpu-verified`；这些讲次的
> 附加 AMD 路径也已在参考 R9700 环境按各自合同通过。L08 已通过双语 CPU 数值路径、
> CPU+EGL 和参考 R9700 AMD+EGL 的脚本化专家验证，状态为 `gpu-verified`。重编号后的
> L12 训练内容也已通过 ACT、SmolVLA GPU smoke、checkpoint 审计和重载验证，状态为
> `gpu-verified`。其余 4 讲仍为 `planned`。

| 讲次 | 主题 | 预计时长 | 硬件 | 状态 |
|---|---|---:|---|---|
| L01 | [导论、运行平台与环境诊断](/zh/lessons/l01-introduction-and-environment-diagnostics) | 30 分钟 | `cpu-ok` | `cpu-verified` |
| L02 | [场景、实体与仿真生命周期](/zh/lessons/l02-scenes-entities-and-simulation-lifecycle) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L03 | [刚体物理与稳定仿真](/zh/lessons/l03-rigid-body-physics-and-stable-simulation) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L04 | [机器人模型、DOF 与关节控制](/zh/lessons/l04-robot-models-dofs-and-joint-control) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L05 | [逆运动学、末端位姿与相机](/zh/lessons/l05-inverse-kinematics-end-effector-poses-and-cameras) | 120 分钟 | `cpu-ok` | `cpu-verified` |
| L06 | [并行仿真与批量 Franka 控制](/zh/lessons/l06-parallel-simulation-and-batched-franka-control) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L07 | [抓取任务场景搭建](/zh/lessons/l07-building-a-grasping-task-scene) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L08 | [演示数据获取与脚本化专家](/zh/lessons/l08-demonstration-acquisition-and-scripted-experts) | 120 分钟 | `gpu-recommended` | `gpu-verified` |
| L09 | [合成数据录制与采数吞吐](/zh/lessons/l09-synthetic-data-recording-and-throughput) | 120 分钟 | `gpu-recommended` | `planned` |
| L10 | [数据集解剖与模仿学习 101](/zh/lessons/l10-dataset-anatomy-and-imitation-learning) | 90 分钟 | `gpu-recommended` | `planned` |
| L11 | [域随机化](/zh/lessons/l11-domain-randomization) | 90 分钟 | `gpu-recommended` | `planned` |
| L12 | [ACT 与 SmolVLA 策略训练](/zh/lessons/l12-act-and-smolvla-policy-training) | 150 分钟 | `gpu-required` | `gpu-verified` |
| L13 | [闭环评估与 Capstone](/zh/lessons/l13-closed-loop-evaluation-and-capstone) | 120 分钟 | `gpu-required` | `planned` |
