# M0.7 兼容性矩阵与版本基线

> 状态：M0.7 已由项目负责人验收
>
> 验证日期：2026-08-28（Asia/Shanghai）
>
> 范围：V1 课程的参考运行环境、精确依赖基线、实测能力和未验证平台。M0.6 的逐项原始证据保留在 `COMPATIBILITY_SPIKE.md`。

## 1. 结论

V1 的完整训练参考平台确定为 **Python 3.12 + Linux x86_64 + AMD Radeon AI PRO R9700 + ROCm 7.2**。在从系统 Python 3.12.3 新建的临时虚拟环境中，以下组合通过依赖检查、ROCm 张量、Genesis 场景/IK/渲染、LeRobot 数据读取、ACT 与 SmolVLA 的 1 step 训练、checkpoint 重新加载和真实数据样本单次推理：

- `genesis-world==1.3.3`；
- `lerobot==0.6.0`；
- AMD 提供的 PyTorch `2.9.1` ROCm 7.2.1 wheel 组合；
- 本文第 3 节列出的精确敏感依赖。

因此，课程不再回退验证 Genesis 1.3.1。M1.1 应以本文件为输入新建当前仓库自己的 `pyproject.toml` 和 `uv.lock`，不得复制任一源课程的 lockfile。

这些 smoke 结果只证明接口和最小执行链路可用，不证明策略已经收敛，也不构成闭环抓取成功率结果。

## 2. 状态定义

| 状态 | 含义 |
| --- | --- |
| **已验证** | 在本文记录的参考主机上实际执行并通过；证据来自 M0.7 干净依赖环境，或明确标注为 M0.6 已执行结果。 |
| **未验证** | 本轮没有实际执行，不能根据相似平台或静态检查推断可用。 |
| **不支持** | 不在 V1 的安装、测试和问题排查承诺范围内；不等于技术上绝对无法运行。 |

## 3. 精确版本基线

### 3.1 参考系统

| 项目 | 锁定或实测值 | 说明 |
| --- | --- | --- |
| 操作系统 | Linux x86_64，kernel `7.0.0-28-generic` | M0.7 实测主机；kernel 不作为 Python 依赖锁定项。 |
| Python | `3.12.3` | V1 支持线为 Python `3.12.x`；M0.7 的精确解释器版本为 3.12.3。 |
| GPU | AMD Radeon AI PRO R9700，单卡可见显存 `30576 MB` | 主机共 4 张卡；M0.7 干净验证使用物理 GPU 2。 |
| 系统 ROCm | `7.2.0` | 来自主机 `amd-smi`；amdgpu 内核模块版本未能可靠读取，故不填写。 |
| PyTorch HIP runtime | `7.2.53211-e1a6bc5663` | `torch.version.hip` 实测值；与系统 ROCm 版本和 wheel 发布标签是三个不同字段。 |

### 3.2 PyTorch ROCm wheel

| 包 | 精确版本 |
| --- | --- |
| PyTorch | `2.9.1+rocm7.2.1.lw.gitff65f5bc` |
| torchvision | `0.24.0+rocm7.2.1.gitb919bd0c` |
| torchaudio | `2.9.0+rocm7.2.1.gite3c6ee2b` |
| Triton | `3.5.1+rocm7.2.1.gita272dfa8` |

PyTorch 的已安装 distribution 版本包含 `.lw.`，而该构建的 `torch.__version__` 运行时字符串为 `2.9.1+rocm7.2.1.gitff65f5bc`；二者已分别核对，不是安装了不同 wheel。

这四个 wheel 是 CPython 3.12 / Linux x86_64 构建，来源为 AMD 官方目录 `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/`：

| 文件 | 官方 URL | SHA-256 |
| --- | --- | --- |
| `torch-2.9.1+rocm7.2.1.lw.gitff65f5bc-cp312-cp312-linux_x86_64.whl` | `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torch-2.9.1%2Brocm7.2.1.lw.gitff65f5bc-cp312-cp312-linux_x86_64.whl` | `fb45ace0a27e9f0d0e3c4c6efd8932162743f8376f2aa4752a4d31ef5a1bd3d7` |
| `torchvision-0.24.0+rocm7.2.1.gitb919bd0c-cp312-cp312-linux_x86_64.whl` | `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torchvision-0.24.0%2Brocm7.2.1.gitb919bd0c-cp312-cp312-linux_x86_64.whl` | `d5fca8cda173235a3b7434baeebe04c3ebffec3c6fc191e79aa8aa300633f2c9` |
| `torchaudio-2.9.0+rocm7.2.1.gite3c6ee2b-cp312-cp312-linux_x86_64.whl` | `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torchaudio-2.9.0%2Brocm7.2.1.gite3c6ee2b-cp312-cp312-linux_x86_64.whl` | `023d1ce5d847b2a0fbebacf52d35b4c7a233ca07b3dbd0f1cbde84362cbcf33d` |
| `triton-3.5.1+rocm7.2.1.gita272dfa8-cp312-cp312-linux_x86_64.whl` | `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/triton-3.5.1%2Brocm7.2.1.gita272dfa8-cp312-cp312-linux_x86_64.whl` | `07787af1d28c273852f897bfeaa7bca29f2fa4a13ca0f28f535832b240ce7016` |

正式安装说明必须校验 SHA-256，且不得把本机下载目录之类的个人绝对路径写入项目配置或 lockfile。

### 3.3 Python 敏感依赖

以下版本是 M0.7 干净环境实际安装并验证的直接或兼容性敏感依赖，M1.1 应据此声明精确约束：

| 包 | 精确版本 | 选择原因或边界 |
| --- | --- | --- |
| `genesis-world` | `1.3.3` | 首选候选通过完整 smoke，不再回退 1.3.1。 |
| `lerobot` | `0.6.0` | 数据、ACT、SmolVLA 训练及推理共同基线。 |
| `av` | `15.1.0` | `pyav` 视频后端实测；避免依赖系统 FFmpeg ABI 的 torchcodec 解码路径。 |
| `numpy` | `2.2.6` | 与本轮 Numba/Genesis/LeRobot 组合实测。 |
| `numba` / `llvmlite` | `0.66.0` / `0.48.0` | Genesis JIT 路径实测。 |
| `trimesh` | `5.0.0` | Genesis 资产处理路径实测。 |
| `opencv-python` | `5.0.0.93` | 图像处理路径实测。 |
| `transformers` | `5.5.4` | SmolVLA 加载、训练和推理实测。 |
| `tokenizers` | `0.22.2` | SmolVLA 实测。 |
| `accelerate` | `1.14.0` | SmolVLA/训练依赖实测。 |
| `safetensors` | `0.8.0` | 两类 checkpoint 保存和加载实测。 |
| `num2words` | `0.5.14` | SmolVLA 文本处理依赖实测。 |
| `pyarrow` | `25.0.0` | LeRobot Parquet 数据读取实测。 |

本轮解析得到 150 个包且 `uv pip check` 返回 `All installed packages are compatible`。例如 `quadrants` 在干净解析中为 `1.3.0`，不同于源虚拟环境中的 1.2.0；其他传递依赖必须由 M1.1 在当前仓库重新解析并写入 `uv.lock`，不能从源仓库或本临时环境手抄一份不完整列表。

解析结果还包含 `nvidia-cuda-nvrtc-cu12==12.9.86` 和 `nvidia-nvjitlink-cu12==12.9.86`。它们来自上游依赖元数据，在本次 ROCm 链路中没有执行；其存在不代表 NVIDIA CUDA 已验证或受支持。M1.1 应检查能否在不改变功能的前提下去除这部分冗余体积。

### 3.4 SmolVLA 模型内容版本

M0.7 在断网模式下从已有 Hugging Face 缓存读取以下 revision：

| 仓库 | 实测 revision |
| --- | --- |
| `lerobot/smolvla_base` | `c83c3163b8ca9b7e67c509fffd9121e66cb96205` |
| `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` | `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |

正式训练配置或 artifact 清单必须固定并核对这两个 revision，不能只依赖可漂移的仓库默认分支。本轮没有验证从空缓存联网下载模型的流程。

## 4. 功能兼容矩阵

| 能力 | 状态 | 验证范围与关键证据 |
| --- | --- | --- |
| 从 Python 3.12.3 新建隔离虚拟环境 | **已验证** | 未继承源课程 site-packages；安装 150 个包，`uv pip check` 通过。 |
| 核心包导入 | **已验证** | 包从 `/tmp` 中的新虚拟环境加载；ROCm PyTorch 未被解析器替换。 |
| ROCm GPU 张量计算 | **已验证** | 单张 R9700 可见，张量结果为 `[1, 2, 5, 10, 17, 26, 37, 50]`。 |
| Genesis 内置 Franka 场景构建 | **已验证** | `genesis-world==1.3.3`，场景 build 成功。 |
| Genesis IK | **已验证** | 解为有限值，最大位姿误差 `0.0002107024`。 |
| Genesis 离屏相机 | **已验证** | 输出 `(120, 160, 3)` `uint8` RGB，像素范围 `[10, 255]`。 |
| Franka 位置控制 | **已验证** | M0.6 实际 step 后关节状态发生变化；M0.7 使用相同精确栈验证场景/IK/渲染。 |
| 七阶段脚本专家抓放 | **已验证** | M0.6 中香蕉放入碗成功；尚未在 M1.4 的最终内置资产路径上重跑。 |
| LeRobot 数据录制 | **已验证** | M0.6 录制 1 个成功 episode、42 frames、5 FPS、两路 H.264 RGB。 |
| LeRobot 数据读取 | **已验证** | 干净环境读取 metadata、Parquet、两路 PyAV 视频，并向两种策略提供真实样本。 |
| ACT 训练 smoke | **已验证** | 干净环境 1 step，loss `20.499`，gradient norm `208.584`，checkpoint 已保存。 |
| ACT checkpoint 加载与推理 | **已验证** | 通用加载接口在 GPU 上返回有限的 `(9,) float32` 动作。 |
| SmolVLA 训练 smoke | **已验证** | 干净环境 1 step，loss `6.305`，gradient norm `42.467`，checkpoint 已保存。 |
| SmolVLA checkpoint 加载与推理 | **已验证** | 恢复 `world/wrist → camera1/camera2` 映射，在 GPU 上返回有限的 `(9,) float32` 动作。 |
| 长训练、收敛和闭环成功率 | **未验证** | 1 step loss 和单次开环推理不能代替闭环 rollout；后续里程碑单独验证。 |
| 从空 Hugging Face 缓存下载 SmolVLA | **未验证** | 本轮主动使用离线模式和本机已有缓存。 |

ACT 和 SmolVLA 的 checkpoint 都由 M0.7 干净环境生成，随后通过源课程当前的 `load_policy()` 与 `PolicyBundle.select_action()` 通用路径重新加载。输入来自 M0.6 真实录制数据集的首个样本，而不是合成的随机张量。

## 5. 平台支持矩阵

| 平台 | 状态 | V1 说明 |
| --- | --- | --- |
| Linux x86_64 / R9700 / 系统 ROCm 7.2.0 / 本文 wheel | **已验证** | 完整训练参考平台。 |
| 其他 AMD GPU 或 ROCm 组合 | **未验证** | 不能从 R9700 结果外推；欢迎后续补充实测矩阵。 |
| NVIDIA CUDA | **未验证** | 解析器出现 CUDA 包不构成验证；V1 不承诺完整链路支持。 |
| CPU-only 完整链路 | **未验证** | L01–L06 仍计划提供 CPU 最小实验，但训练全链路未在 CPU-only 环境验证。 |
| Apple Silicon / macOS | **未验证** | 本轮没有执行 MPS、Genesis 或 LeRobot 兼容性测试。 |
| Windows | **未验证** | 本轮没有执行原生 Windows 或 WSL 测试。 |
| Python 3.11、3.13 或其他版本 | **不支持** | V1 的可复现环境限定为 Python 3.12.x。 |

课程内容继续保持平台中立；“完整训练参考平台”仅描述验证和维护基线，不应把通用机器人学习概念写成 AMD 专有概念。

## 6. 设备与缓存规则

在多 AMD GPU 主机上选择物理 GPU `N` 时，本轮可靠做法是只设置：

```sh
ROCR_VISIBLE_DEVICES=N <command>
```

该物理设备会映射为进程内的 `cuda:0`。不要把 `ROCR_VISIBLE_DEVICES`、`HIP_VISIBLE_DEVICES` 和 `CUDA_VISIBLE_DEVICES` 同时设为同一个非零物理索引；本机实测会导致 PyTorch 看不到 GPU，LeRobot 随后回退到 CPU。

SmolVLA 离线加载依赖已有 Hugging Face 模型缓存。将 `XDG_CACHE_HOME` 临时改到空目录会同时改变缓存查找位置，导致离线加载失败；如果只需要隔离数据集写缓存，应单独设置 `HF_DATASETS_CACHE`，不要遮蔽已有模型缓存。

## 7. M1.1 锁定要求

M1.1 应完成而 M0.7 不提前实现以下工作：

1. 创建当前仓库自己的 `pyproject.toml`，把 Python 3.12、Genesis 1.3.3、LeRobot 0.6.0 和第 3 节的敏感依赖写成明确约束；
2. 为 AMD ROCm wheel 提供可复现、无个人绝对路径的来源配置或安装步骤，并校验本文 SHA-256；
3. 在当前仓库重新生成 `uv.lock`，检查解析结果仍使用 ROCm PyTorch，且 `uv pip check` 通过；
4. 固定 SmolVLA 及其底层 VLM 的 revision；
5. 评估并记录解析器带入的未使用 CUDA wheel，避免把它误写成 CUDA 支持证据；
6. 在 lock 生成后重跑最小导入和与改动风险相称的 smoke。

源课程的 `uv.lock` 当前会解析到未经本轮验证的 PyTorch/LeRobot 版本，不能复制。M0.7 的临时虚拟环境和 checkpoint 位于 `/tmp`，仅作为本轮证据，不是课程发布 artifact。

## 8. 当前限制与后续复验点

- Genesis 加载 Franka 时出现 tendon 近似、neutral pose 关节限制、solver `timeconst` 调整和 neutral pose 自碰撞过滤等警告；M1.4 切换到最终资产路径后需要复核并重跑抓放 smoke。
- ACT 和 SmolVLA 仅运行 1 step，结果不用于比较模型质量。
- 闭环策略 rollout、成功判据、成功率和置信区间留到 M3.8/L12，不得由当前开环动作推断。
- 文档站构建验证只证明当前站点没有因本次 Markdown 文件变化而回归；`COMPATIBILITY.md` 尚未接入 VitePress 导航。
- 本文件验收后成为 M1.1 的版本输入；后续若升级任一核心版本，必须重跑对应兼容性验证并更新本矩阵。
