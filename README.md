# RoboGenesis 101

[English](README_en.md)

> **项目状态：Alpha / 课程开发阶段。** L02 已通过 CPU clean-kernel 验证，状态为
> `cpu-verified`；L11 已在 AMD Radeon AI PRO R9700 上通过 ACT 与 SmolVLA 的 GPU
> smoke 和 checkpoint 重载验证，状态为 `gpu-verified`；其余 10 讲仍为 `planned`。
> 页面和 notebook 已建立不代表对应课程已经完成验证。

RoboGenesis 101 是一门 Datawhale 开源课程，面向具备 Python 基础、希望系统进入机器人学习实践的学习者。课程以 Genesis 为仿真平台，从环境诊断、场景和刚体物理出发，逐步连接机器人控制、逆运动学、抓取、演示数据、模仿学习、策略训练与闭环评估。

课程强调“概念—代码—实验—证据”的完整链路：讲义解释机制，可复用实现位于 Python 包中，notebook 提供可执行练习，课程状态只根据实际内容和验证结果更新。

## 在线阅读

- 中文课程：<https://wangxunx.github.io/robo-genesis-101/zh/>
- English course: <https://wangxunx.github.io/robo-genesis-101/en/>

在线站点目前展示课程目录和材料发布状态。完整学习内容将在准备完成并通过实际验证后逐步发布。

## 适合谁

建议学习者具备：

- Python 基础，能够阅读函数、类、NumPy 数组和命令行参数；
- 基本的终端、Git 和虚拟环境使用经验；
- 对机器人仿真、操作学习或模仿学习感兴趣。

不要求预先掌握 Genesis、机器人运动学或策略训练。课程会在概念成为后续实践的必要前提时进行讲解。

## 学习路径

课程按以下依赖关系推进：

1. Genesis 环境、场景、实体、物理和仿真生命周期；
2. 机器人自由度、关节控制、逆运动学、末端位姿和相机；
3. 抓取任务、脚本化专家、演示获取和数据录制；
4. 数据集、模仿学习、域随机化、ACT/SmolVLA 训练和闭环评估。

训练 loss 或开环动作预测不等同于任务成功。课程最终以闭环 rollout 和明确的成功判据评价策略。

## 课程进度

`course.json` 是课程顺序、标题、时长、硬件要求和状态的唯一结构化来源。

| 讲次 | 主题 | 预计时长 | 硬件 | 状态 |
|---|---|---:|---|---|
| L01 | [导论、运行平台与环境诊断](docs/zh/lessons/l01-introduction-and-environment-diagnostics.md) | 60 分钟 | `cpu-ok` | `planned` |
| L02 | [场景、实体与仿真生命周期](docs/zh/lessons/l02-scenes-entities-and-simulation-lifecycle.md) | 90 分钟 | `cpu-ok` | `cpu-verified` |
| L03 | [刚体物理与稳定仿真](docs/zh/lessons/l03-rigid-body-physics-and-stable-simulation.md) | 90 分钟 | `cpu-ok` | `planned` |
| L04 | [机器人模型、DOF 与关节控制](docs/zh/lessons/l04-robot-models-dofs-and-joint-control.md) | 90 分钟 | `cpu-ok` | `planned` |
| L05 | [逆运动学、末端位姿与相机](docs/zh/lessons/l05-inverse-kinematics-end-effector-poses-and-cameras.md) | 120 分钟 | `cpu-ok` | `planned` |
| L06 | [抓取任务场景搭建](docs/zh/lessons/l06-building-a-grasping-task-scene.md) | 120 分钟 | `cpu-ok` | `planned` |
| L07 | [演示数据获取与脚本化专家](docs/zh/lessons/l07-demonstration-acquisition-and-scripted-experts.md) | 120 分钟 | `gpu-recommended` | `planned` |
| L08 | [合成数据录制与采数吞吐](docs/zh/lessons/l08-synthetic-data-recording-and-throughput.md) | 120 分钟 | `gpu-recommended` | `planned` |
| L09 | [数据集解剖与模仿学习 101](docs/zh/lessons/l09-dataset-anatomy-and-imitation-learning.md) | 90 分钟 | `gpu-recommended` | `planned` |
| L10 | [域随机化](docs/zh/lessons/l10-domain-randomization.md) | 90 分钟 | `gpu-recommended` | `planned` |
| L11 | [ACT 与 SmolVLA 策略训练](docs/zh/lessons/l11-act-and-smolvla-policy-training.md) | 150 分钟 | `gpu-required` | `gpu-verified` |
| L12 | [闭环评估与 Capstone](docs/zh/lessons/l12-closed-loop-evaluation-and-capstone.md) | 120 分钟 | `gpu-required` | `planned` |

状态从 `planned` 依次推进到 `draft`、`reviewed`、`cpu-verified` 或
`gpu-verified`，最终才是 `published`。详细证据要求见[课程内容规范](CONTENT_GUIDE.md)。

## 环境基线

- Python：`3.12.x`；项目声明范围为 `>=3.12,<3.13`。
- Genesis：`genesis-world==1.3.3`。
- LeRobot：训练扩展固定为 `lerobot==0.6.0`。
- 完整训练参考平台：Linux x86_64、AMD Radeon AI PRO R9700、系统 ROCm 7.2.0，以及经实测的 ROCm 7.2.1 PyTorch wheels。

其他 AMD GPU、NVIDIA CUDA、CPU-only 完整链路、Apple Silicon、Windows 和其他 Python 版本尚未验证。精确版本、wheel 校验和、已验证能力和限制见[兼容性矩阵](COMPATIBILITY.md)。

## 快速开始

### 本地阅读文档

文档 CI 使用 Node.js 24；建议本地采用相同主版本：

```sh
npm ci
npm run docs:dev
```

构建静态站点：

```sh
npm run docs:build
```

### 运行轻量质量门禁

以下环境只安装 pytest 和当前项目，不安装 Genesis、PyTorch 或训练栈：

```sh
UV_PROJECT_ENVIRONMENT=.venv uv sync --only-group dev --locked
uv pip install --python .venv/bin/python --no-deps --editable .
.venv/bin/python -m robo_genesis.course_validation
.venv/bin/python -m pytest
```

也可以在安装后运行 `robo-genesis-validate`。

### 安装完整课程依赖

```sh
uv sync --locked --all-extras
```

该命令使用仓库的可移植依赖解析，并不自动构成 AMD ROCm 环境验证。参考 AMD 平台还需要按[兼容性矩阵](COMPATIBILITY.md)安装并校验指定的 ROCm wheels。安装后可验证仓库内置的四个 YCB 对象：

```sh
uv run python -m robo_genesis.setup_assets
```

课程 notebook 和完整实验尚未发布。当前占位文件只展示计划中的课程结构，请勿将其作为完整教程使用。

## 仓库结构

```text
docs/                       VitePress 站点与双语讲义
notebooks/{zh,en}/          双语课程 notebook
src/robo_genesis/           可复用场景、数据、训练和评估实现
scripts/                    仓库级开发与校验入口
tests/                      纯逻辑和仓库契约测试
assets/third_party/         经审计并保留原许可的第三方资产
course.json                 课程元数据和状态真相源
```

## 参与贡献

提交 Issue 或 Pull Request 前，请阅读：

- [贡献指南](CONTRIBUTING.md)：开发环境、工作流程、验证和 PR 清单；
- [课程内容规范](CONTENT_GUIDE.md)：双语讲义、notebook、代码、状态和证据标准；
- [第三方材料说明](NOTICE.md)：来源、许可和再分发边界。

## 贡献者

| 姓名 | 职责 |
|---|---|
| 王迅（Xun Wang） | 项目负责人；课程设计、开发与维护 |

贡献者名单只根据已经合入的实际贡献更新。

## 许可

除另有注明的第三方材料外，本项目有权许可的原创代码、讲义、notebook、练习和原创课程媒体均采用 [MIT License](LICENSE)。提交原创贡献即表示同意按该许可证提供贡献。

第三方代码、资产、数据集、模型、商标及其他材料保留各自原始许可与限制，不受项目 MIT License 覆盖。具体边界见 [NOTICE.md](NOTICE.md) 和 [LICENSE_POLICY.md](LICENSE_POLICY.md)。仓库内置的 YCB 资产采用 CC BY-NC 4.0，不属于 MIT 范围。

## 致谢

感谢 [Datawhale](https://github.com/datawhalechina) 开源学习社区。本课程使用 [Genesis](https://github.com/Genesis-Embodied-AI/Genesis) 和 [LeRobot](https://github.com/huggingface/lerobot) 构建教学实践；项目与第三方组件之间不存在因引用而产生的官方背书关系。
