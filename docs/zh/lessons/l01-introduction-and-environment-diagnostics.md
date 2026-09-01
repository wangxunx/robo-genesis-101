---
lesson: L01
slug: introduction-and-environment-diagnostics
locale: zh
title: "导论、运行平台与环境诊断"
duration_minutes: 30
hardware: cpu-ok
status: cpu-verified
---

# L01 · 导论、运行平台与环境诊断

> **硬件约定：**本讲以及 L01–L06 的最小实验可以使用 CPU 完成。AMD ROCm GPU 是
> 后续数据生成、策略训练和闭环评估的参考路径，但不是 L01 的必需条件。

## 一张图看懂课程主线

RoboGenesis 101 围绕一条完整的机器人学习工作流展开：

```text
Genesis 仿真 → 机器人控制与 IK → 脚本化演示
             → LeRobot 数据集 → ACT/SmolVLA 训练
             → 闭环评估
```

完成课程后，你将理解 Franka 机械臂如何在仿真中学习水果抓取任务。课程按依赖顺序
展开：

- L01–L06 学习环境、仿真、控制、相机和抓取场景；
- L07–L10 生成演示，并把演示整理成训练数据；
- L11–L12 训练策略，再通过闭环 rollout 检验任务结果。

训练 loss 或看起来合理的开环动作并不等于任务成功。最终证据来自把策略真正放回
仿真器，并根据明确标准衡量任务结果。

## 今天只需要完成什么

L01 的任务刻意保持简单。完成本讲后，你只需要能够：

1. 在课程地图中找到从仿真到闭环评估的各个阶段；
2. 从头运行环境 notebook，并认出 Python、Genesis、PyTorch 和实际选择的计算后端；
3. 确认 Genesis 能构建并推进一个最小场景，然后进入 L02。

你不需要学习一套环境诊断框架。这个 notebook 只是开课前的简短检查，不是课程主题。

## 打开 notebook 之前

环境安装属于课前准备。在仓库根目录安装基础环境，并使用同一个解释器启动 Jupyter：

```sh
uv sync --locked
uv run jupyter lab
```

然后打开 `notebooks/zh/l01-introduction-and-environment-diagnostics.ipynb`，确认 kernel
选择的是项目 `.venv`，再执行一次 **Run All**。

可移植 lockfile 本身不会自动选择经过验证的 AMD PyTorch 构建。如果你在准备完整 AMD
训练环境，请按照[兼容性矩阵](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
中的 wheel 和校验和说明安装。

## CPU 和 AMD 在本讲都有效

当 notebook 同时看到 ROCm PyTorch 和 AMD GPU 时，会自动优先使用已验证的 AMD
backend；否则使用 Genesis CPU，并明确打印这个选择。

PyTorch 的 ROCm 构建复用了 `torch.cuda` API，所以本课程中的 `cuda:0` 可能指 AMD
GPU。可以通过下面两个字段区分：

```python
torch.version.hip       # ROCm 构建中有值
torch.version.cuda      # 已验证的 ROCm 构建中为 None
```

没有可见 GPU 并不代表 L01 失败。CPU 学习者可以继续完成 L01–L06 的最小路径；后续
完整训练课程会单独说明更高的硬件要求。

## 运行环境自检

notebook 只有四个简短的可执行阶段：

| 阶段 | 应当看到什么 |
|---|---|
| 环境摘要 | 当前 kernel 的 Python、Genesis、PyTorch、HIP 和设备信息 |
| 后端与 tensor | ROCm 路径可用时为 `amdgpu`，否则为 `cpu`；一个最小 tensor 结果 |
| Genesis smoke | 平面和球体成功 build；step 后球体高度下降 |
| 最终总结 | `ENVIRONMENT CHECK: PASSED`、实际后端和下一讲提示 |

notebook 会直接展示这段最小场景代码，但 L01 不展开解释每个 Genesis 对象。L02 会
详细介绍 `Scene`、`Entity`、`build()` 和 `step()`。这里的场景只用于证明当前环境能够
执行真实工作，而不只是成功 import 一个包。

notebook 还会把一份简短结果写到 `outputs/l01/env_report.json`。需要排错时，可以把它
和报错信息一起发给助教；无需打开或修改报告内容。

## 哪些是必需结果，哪些只是预告

| 结果 | 在 L01 中的含义 |
|---|---|
| Python 3.12、PyTorch 和 Genesis 1.3.3 正常 | 继续学习前必须满足 |
| 选中设备上的 tensor 运算成功 | 继续学习前必须满足 |
| 最小场景成功 build、step，得到有限且发生变化的状态 | 继续学习前必须满足 |
| AMD GPU 与 HIP 可见 | 参考平台的有用确认；允许 CPU fallback |
| LeRobot 0.6.0 已安装 | 后续训练环境的提前提示；L01–L06 不要求 |
| 相机渲染、YCB 资产和策略训练正常 | 本讲不检查；后续首次使用时再验证 |

## 快速排错

| 现象 | 下一步 |
|---|---|
| Notebook 使用了错误的 Python | 选择仓库 `.venv` kernel，然后重启。 |
| `torch` 或 `genesis` 无法 import | 在仓库根目录运行 `uv sync --locked`，然后重启 kernel。 |
| 有 AMD 硬件但 notebook 选择了 CPU | 检查指定 ROCm wheels、`torch.version.hip`、设备权限和 `ROCR_VISIBLE_DEVICES`。 |
| 第一次 scene build 看起来很慢 | 等待 Genesis 首次编译 kernel；这个 smoke 不是性能基准。 |
| 再次运行时在 `gs.init()` 后失败 | 重启 kernel，再从顶部执行一次 **Run All**。 |

如果最后一行显示 `PASSED`，就可以继续 L02。如果必需 cell 因异常停止，应先按该 cell
给出的具体信息修复。GPU 或 LeRobot 的可选提示不阻塞 CPU 基础路径。

## 检查点与下一讲

离开 L01 前，确认自己能回答：

- 这个 notebook 实际选择了哪个 backend？
- tensor 运算和球体状态变化是否都成功？
- 如果当前使用 CPU，课程的哪个阶段最终需要 GPU？

L02 会拆开这个最小 smoke 场景，解释仿真生命周期：声明实体、调用 `build()`、推进世界、
读取状态，以及按需渲染图像。

## 资料来源

- [Genesis 文档](https://genesis-world.readthedocs.io/)：安装与后端初始化。
- [PyTorch HIP 语义](https://docs.pytorch.org/docs/stable/notes/hip.html)：ROCm 为什么复用 `torch.cuda` 接口。
- [项目兼容性矩阵](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)：已验证版本与 AMD 平台证据。
