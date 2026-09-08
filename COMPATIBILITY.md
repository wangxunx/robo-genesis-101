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
| CPU-only 完整链路 | **部分验证** | L01–L07 的 CPU 最小实验已实际通过并完成对应运行验收，状态均为 `cpu-verified`；训练全链路未在 CPU-only 环境验证。 |
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
- 闭环策略 rollout、成功判据、成功率和置信区间留到 L13，不得由当前开环动作推断。
- 文档站构建验证只证明当前站点没有因本次 Markdown 文件变化而回归；`COMPATIBILITY.md` 尚未接入 VitePress 导航。
- 本文件验收后成为 M1.1 的版本输入；后续若升级任一核心版本，必须重跑对应兼容性验证并更新本矩阵。

## 9. L02 干净 kernel 验证

> 验证日期：2026-08-31（Asia/Shanghai）
>
> 范围：L02 双语 notebook 的 CPU 最低能力、参考 AMD 后端和离屏渲染。以下结果不扩大第 5 节的平台支持范围。

验证环境从系统 Python 3.12.3 新建，先用当前 `uv.lock` 安装默认依赖和 dev 组，再安装第 3.2 节列出的四个已校验 ROCm 7.2.1 wheels。PyTorch wheel 所需的 `filelock==3.32.4`、`sympy==1.14.0` 和 `mpmath==1.3.0` 取自同一 lock；当前项目以 editable 方式从本仓库加载。`uv pip check` 检查 175 个包并返回 `All installed packages are compatible`。

| 项目 | 实测值 |
| --- | --- |
| Python | `3.12.3` |
| Genesis | `1.3.3` |
| PyTorch distribution | `2.9.1+rocm7.2.1.lw.gitff65f5bc` |
| `torch.__version__` | `2.9.1+rocm7.2.1.gitff65f5bc` |
| PyTorch HIP runtime | `7.2.53211-e1a6bc5663` |
| 参考设备 | AMD Radeon AI PRO R9700；本轮将一张物理卡映射为进程内 `cuda:0` |

四次执行均由 `jupyter nbconvert --execute --to notebook` 启动独立 kernel；执行后的 notebook 写入临时目录，仓库中的 notebook 保持无 output、`execution_count: null`。命令中的 `<env>` 和 `<tmp>` 分别表示本轮临时虚拟环境及临时输出目录：

```sh
ROCR_VISIBLE_DEVICES=0 ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=0 \
  <env>/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-auto.ipynb --output-dir <tmp> \
  notebooks/en/l02-scenes-entities-and-simulation-lifecycle.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  <env>/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output zh-cpu.ipynb --output-dir <tmp> \
  notebooks/zh/l02-scenes-entities-and-simulation-lifecycle.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  <env>/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-cpu.ipynb --output-dir <tmp> \
  notebooks/en/l02-scenes-entities-and-simulation-lifecycle.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 \
  ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
  <env>/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-amd-render.ipynb --output-dir <tmp> \
  notebooks/en/l02-scenes-entities-and-simulation-lifecycle.ipynb
```

| notebook / 能力路径 | backend mode → 实际 backend | 渲染 | 执行时间 | 关键观察 |
| --- | --- | --- | ---: | --- |
| EN / AMD 核心路径 | `auto` → `gs.amdgpu` | 关闭并明确报告 `SKIP` | 38.90 秒 | build、单 link/geom 层级、20 步状态和两个预期异常均通过；状态张量位于 `cuda:0`。 |
| ZH / CPU 最低路径 | `cpu` → `gs.cpu` | 关闭并明确报告 `SKIP` | 32.65 秒 | 与 AMD 路径相同的核心断言全部通过；状态张量位于 CPU。 |
| EN / CPU 最低路径 | `cpu` → `gs.cpu` | 关闭并明确报告 `SKIP` | 33.18 秒 | 状态更新后再次从头执行；输出报告 `lesson_status: cpu-verified`，核心断言全部通过。 |
| EN / AMD 离屏渲染 | `auto` → `gs.amdgpu` | `PASS` | 51.17 秒 | RGB 为 `(360, 640, 3)`、`uint8`、全部有限，像素范围 `[10, 204]`；未触发 fallback。 |

四次运行的初始高度均为 `0.5 m`，20 步后为约 `0.298895 m`，下降约 `0.201105 m`。这些数值记录本次 smoke 的实际观察，不是面向所有硬件的硬编码课程预期。EN/ZH 两份 notebook 都已从头执行；英文 notebook 本身同时通过 AMD 与 CPU 路径，双语 code cell 源码和 ID 保持一致。

### 9.1 教学可视化调整后的复验

M2.5 验收后，L02 增加了运行前预测问题、状态分支的初始/最终 Box 对比与高度轨迹，以及渲染分支的初始/最终 RGB 对比。核心生命周期断言、后端选择和显式渲染开关没有改变。2026-08-31 使用本节记录的同一隔离环境和命令结构重新执行最终 notebook：

| notebook / 能力路径 | backend mode → 实际 backend | 执行时间 | 调整后结果 |
| --- | --- | ---: | --- |
| EN / AMD 状态可视化 | `auto` → `gs.amdgpu` | 37.17 秒 | 核心断言全部通过；生成初始/最终 Box 状态对比和 20 步高度轨迹，明确标注为非相机图像。 |
| ZH / CPU 状态可视化 | `cpu` → `gs.cpu` | 32.57 秒 | 中文 notebook 从干净 kernel 自上而下通过，与英文使用相同 code cell 和 ID；最终输出文字调整后又以独立 kernel 和已有编译缓存复验一次，用时 9.90 秒。 |
| EN / AMD 初始/最终 RGB | `auto` → `gs.amdgpu` | 51.20 秒 | 初始和最终 RGB 均为 `(360, 640, 3)` `uint8`；各自范围为 `[10, 206]` 和 `[10, 204]`，并排对比图生成成功。 |

三次复验中的状态值仍为初始 `z=0.5 m`、20 步后约 `z=0.298895 m`。仓库中的双语 notebook 继续保持无 output、`execution_count: null`，所有图像仍只写入已忽略的 `outputs/`。

## 10. 当时 L11（当前 L12）/ M2.10 GPU kernel 验证

> 验证日期：2026-09-01（Asia/Shanghai）
>
> 范围：当时编号为 L11 的真实数据门禁、ACT/SmolVLA 命令审计、双策略 1 step GPU
> smoke、checkpoint 审计和同一样本开环重载。完整训练、收敛和 Genesis 闭环评估
> 均未运行。

本轮按项目负责人要求复用 M1.5 已按当前兼容性基线建立的仓库 `.venv`，而不是重复
下载 PyTorch。环境原有四个第 3.2 节列出的 ROCm wheel；补齐当前项目 `training`
extra 后，`uv pip check` 检查 221 个包并返回
`All installed packages are compatible`。notebook 仍由 `nbconvert --execute` 启动
独立 kernel，从首个 code cell 顺序执行，不复用交互式 notebook 状态。

| 项目 | 本轮实测值 |
| --- | --- |
| Python | `3.12.3` |
| LeRobot | `0.6.0` |
| PyTorch distribution | `2.9.1+rocm7.2.1.lw.gitff65f5bc` |
| `torch.__version__` | `2.9.1+rocm7.2.1.gitff65f5bc` |
| PyTorch HIP / CUDA runtime | `7.2.53211-e1a6bc5663` / `None` |
| 系统 ROCm | `7.2.0` |
| 参考设备 | 物理 GPU 1：AMD Radeon AI PRO R9700，映射为进程内 `cuda:0`；仅一张设备可见 |
| 运行前显存 | 总计 `30576 MB`，空闲 `30519 MB` |
| 模型缓存模式 | `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`；未验证空缓存联网下载 |

先用最小张量检查拒绝 CPU fallback。`torch.cuda.is_available()` 为真，设备名精确为
`AMD Radeon AI PRO R9700`，张量 `arange(8).square() + 1` 的结果为
`[1, 2, 5, 10, 17, 26, 37, 50]`。

### 10.1 数据与模型身份

验收数据是 M0.6 通过课程脚本专家与录制入口生成的真实临时 LeRobot 数据集，不是
随机 tensor，也不是发布数据 artifact：

| 字段 | 值 |
| --- | --- |
| repo ID / 本地路径 | `local/m06_g133` / `/tmp/rg101-m06.n7DcFk/dataset-g133` |
| 规模 | 1 episode、42 frames、5 FPS |
| state / action | 均为 `(9,) float32`，关节顺序与课程合同一致 |
| 图像 | `observation.images.world` 与 `observation.images.wrist`；均解码为 `(3, 120, 160)` 有限值 |
| task | `pick the banana and place it in the bowl` |

SmolVLA 从已有离线缓存读取并核对两个固定 revision：

- `lerobot/smolvla_base@c83c3163b8ca9b7e67c509fffd9121e66cb96205`；
- `HuggingFaceTB/SmolVLM2-500M-Video-Instruct@7b375e1b73b11138ff12fe22c8f2822d8fe03467`。

### 10.2 执行方式与结果

英文 notebook 使用如下命令结构完成全部 GPU 路径；`<repo>`、`<run-root>`、
`<base-snapshot>` 和 `<vlm-snapshot>` 代表本轮已记录的实际本地路径：

```sh
ROCR_VISIBLE_DEVICES=1 \
RG101_REPO_ID=local/m06_g133 \
RG101_DATASET_ROOT=/tmp/rg101-m06.n7DcFk/dataset-g133 \
RG101_OUTPUT_ROOT=<run-root>/train RG101_SEED=1000 RG101_RUN_SMOKE=1 \
RG101_SMOLVLA_BASE_SNAPSHOT=<base-snapshot> \
RG101_SMOLVLA_VLM_SNAPSHOT=<vlm-snapshot> \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
<repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=3600 \
  --output l11-en-executed.ipynb --output-dir <run-root> \
  notebooks/en/l11-act-and-smolvla-policy-training.ipynb
```

中文 notebook 随后在另一独立 GPU kernel 中以 `RG101_RUN_SMOKE=0` 从头执行，完成
相同的数据门禁、配置读取、双 snapshot 审计、双 dry-run 和 smoke 命令 preflight；
双语 code cell 源码与 ID 的规范化 SHA-256 均为
`1ccfae76827291e0214ce39651b7111dd8343179b9263a49f8096e8812e03409`。
训练没有重复执行，因为两种语言共用完全相同的可执行单元。

状态同步为 `gpu-verified` 后，最终 EN/ZH notebook 又各自在新的 R9700 kernel 中
以 `RG101_RUN_SMOKE=0` 自上而下执行一次；两次都通过最终状态断言、真实数据门禁、
snapshot 审计和双 dry-run，确认提交版本不依赖先前 kernel 状态。

| 策略 | 训练配置 | 本轮日志观察 | checkpoint 证据 |
| --- | --- | --- | --- |
| ACT | pipeline-only 缩小配置，batch 1、seed 1000、1 step | loss `20.499`、gradient norm `208.584`、update `1.013 s`、报告显存 `0.36 GB` | 数字目录 `000001`；权重 `45384956` bytes；`last → 000001` |
| SmolVLA | 固定 base/VLM、默认冻结策略、batch 1、seed 1000、1 step | loss `6.305`、gradient norm `42.467`、update `1.402 s`、报告显存 `1.81 GB` | 数字目录 `000001`；权重 `906712520` bytes；`last → 000001` |

两次日志都明确报告真实数据的 42 frames / 1 episode、有限 loss 与 gradient norm、一次
optimizer update 和 checkpoint 保存。上述 loss、耗时与显存只是本次 smoke 的观察值，
不是跨环境阈值，也不用于比较两种策略的质量。

两个 checkpoint 均包含 `config.json`、`train_config.json`、非空
`model.safetensors`、preprocessor/postprocessor 配置及各自的 processor state 文件。
ACT 保存 9 维输出、`chunk_size=10`、`n_action_steps=10`；SmolVLA 保存 9 维输出、
`chunk_size=50`、`n_action_steps=50`，并恢复
`world/wrist → camera1/camera2` 映射和固定 VLM snapshot。两者都由当前项目的
`robo_genesis.eval_policy.load_policy()` 对同一真实样本重新加载，在 `cuda` 设备上返回
`(9,) float32` 且全部有限的动作。

这只是 **open-loop single-sample probe**。本轮没有执行完整长训练，没有证明 loss
收敛，也没有在 Genesis 中施加动作、运行闭环 rollout 或计算抓放成功率；这些证据在
当时结构中属于 L12，13 讲结构中属于 L13。执行后的 notebook、临时数据、checkpoint、训练日志和缓存均不提交到 Git。

## 11. L01 / M3.1 简明环境自检

> 验证日期：2026-09-01（Asia/Shanghai）
>
> 范围：简化版 L01 notebook 的 Python/包摘要、PyTorch tensor、自动 backend 选择与
> 最小 Genesis `build/step`。本讲不检查渲染、YCB/Franka 资产、训练或闭环评估。

本轮按项目负责人要求复用已经按本文基线安装的仓库 `.venv`，没有重新安装环境或下载
PyTorch。英文 notebook 隐藏 GPU 后验证 CPU 最低路径；中文 notebook 暴露物理 GPU 1，
验证同一份代码能自动选择 AMD backend。执行后的 notebook 和环境摘要均写入临时目录：

```sh
ROCR_VISIBLE_DEVICES=-1 ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output l01-en-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/en/l01-introduction-and-environment-diagnostics.ipynb

ROCR_VISIBLE_DEVICES=-1 ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-cpu-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output l01-zh-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l01-introduction-and-environment-diagnostics.ipynb

ROCR_VISIBLE_DEVICES=1 ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output l01-zh-amd.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l01-introduction-and-environment-diagnostics.ipynb
```

| Notebook / 路径 | 实际 backend 与设备 | 最小运行证据 |
| --- | --- | --- |
| EN / 强制隐藏 GPU | `gs.cpu`；tensor 位于 CPU | Python 3.12.3、Genesis 1.3.3 和 PyTorch 导入成功；tensor 为 `[1, 2, 5, 10]`；球体经过 20 步从 `z=0.5 m` 降至约 `0.298895 m`。 |
| ZH / 强制隐藏 GPU | `gs.cpu`；tensor 位于 CPU | 独立 clean kernel 从头执行相同必需检查，结果与英文 CPU 路径一致。 |
| ZH / AMD 自动选择 | `gs.amdgpu`；AMD Radeon AI PRO R9700 映射为 `cuda:0` | HIP 为 `7.2.53211-e1a6bc5663`；相同 tensor 和 20 步 Genesis smoke 通过，球体高度结果与 CPU 路径一致。 |

两次执行的最终摘要均为 `ENVIRONMENT CHECK: PASSED`。当前环境还观察到 LeRobot
0.6.0，但该项只是后续训练提示，不属于当前 L01–L07 的通过条件。本次复验时两份提交 notebook 都只有
4 个 code cell，其当时源码和 ID 的规范化 SHA-256 均为
`68dfad0c9af76db3e6f904781c536833829594b72f5068f2da076515cacecf4b`；提交文件保持
`execution_count: null` 且没有 output。13 讲结构迁移只把后续课程提示从 L06/L11
更新为 L07/L12，因此当前 code source 与这个历史 hash 不同；本节不把旧 hash
声称为重编号后的复验证据。

这些结果支持 L01 的 `cpu-verified` 最低能力状态，并额外证明同一简明 notebook 能在
参考 R9700 环境自动选择 AMD backend。L01 没有运行相机渲染、资产加载、ACT/SmolVLA
训练、模型收敛、机器人控制、抓取或闭环任务；这些能力由后续讲次在首次需要时验证。

## 12. L03 / M3.L03.5 刚体物理 clean-kernel 验证

> 验证日期：2026-09-01（Asia/Shanghai）
>
> 范围：L03 双语 notebook 的 CPU 最低路径、参考 AMD 后端、N1–N4 接触关系、
> 两组摩擦实验和输出目录合同。本轮不涉及渲染、机器人、资产、训练或闭环评估。

本轮复用已按本文基线安装的仓库 `.venv`，没有重新安装环境或下载
PyTorch。实测环境为 Python 3.12.3、Genesis 1.3.3、PyTorch distribution
`2.9.1+rocm7.2.1.lw.gitff65f5bc`、`torch.__version__`
`2.9.1+rocm7.2.1.gitff65f5bc` 和 HIP `7.2.53211-e1a6bc5663`。

AMD 路径只暴露物理 GPU 0，它被进程映射为 `cuda:0`。运行前张量探针确认：

- `torch.cuda.is_available()` 为真，且仅一张卡可见；
- 设备名为 `AMD Radeon AI PRO R9700`；
- `arange(8).square() + 1` 在 `cuda` 上返回
  `[1, 2, 5, 10, 17, 26, 37, 50]`，因此未发生 CPU fallback。

### 12.1 执行方式

三次最终执行都由 `jupyter nbconvert --execute` 启动新 kernel，并从首个
code cell 顺序运行。`<repo>` 和 `<tmp>` 分别代表仓库根目录与本轮临时目录：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-cpu \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-en-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/en/l03-rigid-body-physics-and-stable-simulation.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-cpu \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-zh-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l03-rigid-body-physics-and-stable-simulation.ipynb

ROCR_VISIBLE_DEVICES=0 ROBO_GENESIS_BACKEND=auto \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-amd \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-en-amd.ipynb \
  --output-dir <tmp> \
  notebooks/en/l03-rigid-body-physics-and-stable-simulation.ipynb
```

执行后的 notebook、`.npz`、PNG 和缓存全部写入 `<tmp>`；提交的 notebook
保持 `execution_count: null` 且没有 output。

### 12.2 运行结果

| Notebook / 路径 | 请求后端 → 实际后端 | 结果 |
| --- | --- | --- |
| EN / CPU | `cpu` → `cpu` | 四个接触 case、baseline 摩擦和单变量摩擦实验全部完成；`L03 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 独立 clean kernel 完成同样的六组实验，结果与英文 CPU 路径一致；`L03 CHECK: PASSED` |
| EN / AMD | `auto` → `amdgpu` | 六个 runner 都在 R9700 上运行，没有 CPU fallback；`L03 CHECK: PASSED` |

Part A 的 CPU 与 AMD 观测一致：

| Case | `dt` | substeps | 穿透代理值 |
| --- | ---: | ---: | ---: |
| N1 | 0.01 s | 1 | 13.193 mm |
| N2 | 0.01 s | 2 | 7.797 mm |
| N3 | 0.02 s | 1 | 23.984 mm |
| N4 | 0.02 s | 2 | 13.193 mm |

N1→N2 与 N3→N4 均下降。N1/N4 共有 75 个采样时刻，对齐后的最大
`z` 与 `vz` 差异在本轮显示精度下均为 0。N2 同时观测到 70 ms 几何分离，
其他三组为 0 ms；这正好说明更小穿透不等于所有稳定性指标都单调改善。

Part B 在两种后端都满足相同关系。CPU 的 baseline 停止距离为
0.4104 m / 0.2241 m（低/高摩擦 lane）；桌面摩擦由 0.50 降到 0.30 后为
0.6746 m / 0.2240 m。AMD 对应数值为 0.4104 m / 0.2239 m 和
0.6746 m / 0.2239 m。高摩擦 lane 的 CPU/AMD 持续停止时刻相差一个 0.02 s
采样间隔，但停止距离和已审定关系均通过；这些数值是本轮观测，不是跨平台标准答案。

双语 notebook 的 code-cell ID/source 规范化 SHA-256 均为
`c15baafec459ab85a2eb74cc26eec1c5753d576aa751cb5965f1203c8c8498e0`。本节证据只支持
L03 的 `cpu-ok` 最低能力和额外 AMD 可运行性；课程状态仍由 M3.L03.6 验收后同步，
不在 M3.L03.5 提前更新。

### 12.3 接触与摩擦 runner 核心代码展示调整后的复验

> 复验日期：2026-09-02（Asia/Shanghai）

M3.L03.6 review 指出，notebook 虽然已经展开物理常量、case 配置、指标重算和关系检查，
但在运行 N1–N4 前只显示 `robo_genesis.experiments.rigid_contact` 的模块调用，学习者无法
直接看到 Scene 构建与逐步采样。双语 notebook 因此在子进程调用前增加同构 Markdown
单元，展示 runner 实际执行的后端初始化、`SimOptions`、实体创建、`build()` 和
`scene.step()` 后的高度、竖直速度及接触数量采样。可执行实现仍只保留在公共模块；测试
会把 notebook 中的 Python 代码块与 runner 标记区域逐字核对，防止两者漂移。

后续 review 指出 Part B 的 `robo_genesis.experiments.rigid_friction` 调用存在相同断点。
双语 notebook 又在该调用前增加同构 Markdown 单元，展示桌面与两方块的创建、沉降以
建立接触、相同六自由度初速度的设置，以及位移、线速度、角速度和接触数量的同步采样。
持续停止指标仍在后续 notebook 单元中从原始轨迹重算；测试同样逐字核对该展示片段与
`rigid_friction.py` 的标记区域。

第三轮 review 确认原课程一的四段式 `Guided interpretation` 在当前 notebook 中被压缩
成较弱的 `Evidence-based interpretation` 摘要。双语 notebook 因此恢复基于当前实测
数组动态生成的四段式引导：固定 `dt` 比较 substeps、匹配 `substep_dt` 比较外层边界、
限定结论范围，以及联合几何净空、竖直速度、contact count 和沉降误差判断反弹。文案会
根据实际关系选择 `decreased`/`did not decrease` 与 `within`/`outside`，不预设结果，
也不写死本机数值。

第四轮 review 指出 Part B 同样缺少原课程一的运行后解释。基准摩擦实验现在动态生成
四段式 `Guided friction interpretation`，说明受控变量、有效接触对摩擦、持续停止、
角速度/contact 证据和结论边界；桌面摩擦练习动态生成四段式 `Guided one-factor
interpretation`，核对唯一改动、两个有效摩擦值、停止距离方向及高摩擦控制通道容差。
未停止、方向不符或超出容差时都会显示对应失败措辞，不把预测写成观察结果。

前两轮返工只新增教学展示、源码范围标记和同步测试；后两轮修改了 notebook 的纯 NumPy
结果解释 code cell。四轮都没有改变 runner 可执行语句、实验参数、指标定义或最终状态
断言。仍使用第 12.1 节的命令结构，在独立 kernel 中重新执行两条受影响的 CPU 路径：

| Notebook / 路径 | 请求后端 → 实际后端 | 复验结果 |
| --- | --- | --- |
| EN / CPU | `cpu` → `cpu` | 四个接触 case 与两组摩擦实验通过；`L03 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 独立 kernel 完成相同实验；`L03 CHECK: PASSED` |

两次运行继续得到 N1–N4 穿透代理值 13.193、7.797、23.984、13.193 mm；baseline
低/高摩擦 lane 停止距离约为 0.410/0.224 m，桌面摩擦改为 0.30 后约为
0.675/0.224 m。方向关系与 M3.L03.5 证据一致。这些绝对数值仍只是本机观察。

本次没有重跑 AMD，因为 runner 可执行语句、物理参数和数据 schema 均未变化，而新增的
四段式解释只消费已经通过有限性与 shape 检查的 NumPy 结果。第 12.2 节已验收的 R9700
`auto → amdgpu` 仿真证据仍适用于当前 runner，但不能把本次 CPU 复验表述成新的 GPU
notebook 运行证据。执行后 notebook 和产物只写入 `/tmp`，提交版 EN/ZH notebook 均为
20 个 cell、10 个 code cell，且无 output 或 execution count。

### 12.4 Genesis 相机关键帧恢复后的复验

> 复验日期：2026-09-02（Asia/Shanghai）

L03 验收后的迁移复查发现，原课程一在接触与摩擦 runner 中通过 `add_camera` 保存真实
初始/最终场景画面，而当前 L03 只保留了基于状态的 Matplotlib 示意图。双语 notebook
因此恢复显式的 `ROBO_GENESIS_RENDER=0/1` 能力分支：两个 runner 只在 `--render`
启用时于 `build()` 前加入相机，启用后的相机或 RGB 校验错误会使运行失败；关闭时保存
明确的空画面字段并打印 `SKIP`，不把状态示意图称为 Genesis 渲染结果。

三次最终执行继续使用独立 clean kernel。命令结构如下，其中 `<tmp>` 表示本轮位于
`/tmp` 的隔离输出与缓存目录：

```sh
PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 \
ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/amd-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-en-amd-render.ipynb \
  --output-dir <tmp> \
  notebooks/en/l03-rigid-body-physics-and-stable-simulation.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-cpu-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-en-cpu-no-render.ipynb \
  --output-dir <tmp> \
  notebooks/en/l03-rigid-body-physics-and-stable-simulation.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-cpu-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l03-zh-cpu-no-render.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l03-rigid-body-physics-and-stable-simulation.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | 渲染结果 | code cell 执行时长 | 最终结果 |
| --- | --- | --- | ---: | --- |
| EN / AMD + EGL | `auto` → `amdgpu` | 四组接触和两组摩擦均返回真实 RGB | 186.41 秒 | `L03 CHECK: PASSED` |
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP`；六个结果均含空画面字段 | 103.33 秒 | `L03 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP`；六个结果均含空画面字段 | 52.06 秒 | `L03 CHECK: PASSED` |

AMD 路径中，N1–N4 的初始与最终图像均为 `(360, 640, 3)` `uint8`，像素范围分别落在
`[10, 165]` 与 `[10, 163]`；两组摩擦实验的图像均为 `(400, 720, 3)` `uint8`，初始
范围为 `[10, 214]`，最终范围为 `[10, 213]`。所有图像非空且数值有限。人工检查生成的
组合图后，接触实验能看到共享初始场景及 N1–N4 的最终场景；摩擦实验能看到沉降后和
测量结束后的双通道状态；桌面摩擦单变量对照中，橙色低摩擦方块的最终位移变化清楚，
蓝色控制通道近似不变。Matplotlib 轨迹仍作为定量证据，与相机画面并列而不是被替换。

三条路径继续得到第 12.2 节记录的接触与摩擦关系，新增渲染没有改变物理参数或最终
断言。执行后 notebook、`.npz`、PNG 和渲染缓存均只写入 `/tmp`。提交版双语 notebook
仍为 20 个 cell、10 个 code cell，无 output 或 execution count；两份 notebook 的
code-cell ID/source 规范化 SHA-256 均为
`bd5db9c7c3427f1ba9b13fc0f0f3786b51497077e4da36f1cd533e718734e955`。这些证据新增的是
参考 AMD 环境的 L03 离屏渲染能力，不改变 L03 以 CPU 为最低合同的 `cpu-verified`
状态。

## 13. L04 / M3.L04.5 机器人模型与关节控制 clean-kernel 验证

> 验证日期：2026-09-02（Asia/Shanghai）

L04 使用 Genesis 1.3.3 内置 Franka，在同一固定初态上完成 joint4 基准位置阶跃及三组
KP/KV 单变量对照。双语 CPU 路径和英文参考 AMD + EGL camera 路径均由
`jupyter nbconvert --execute --to notebook` 启动独立 kernel；执行后 notebook、PNG 和
缓存只写入 `/tmp`，提交版 notebook 保持无 output、`execution_count: null`。

命令结构如下，其中 `<tmp>` 表示本轮隔离输出与缓存目录：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-cpu-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l04-en-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/en/l04-robot-models-dofs-and-joint-control.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-cpu-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l04-zh-cpu.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l04-robot-models-dofs-and-joint-control.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 \
ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-amd-render-outputs \
  <repo>/.venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l04-en-amd-render.ipynb \
  --output-dir <tmp> \
  notebooks/en/l04-robot-models-dofs-and-joint-control.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | 姿态证据 | code cell 执行时长 | 最终结果 |
| --- | --- | --- | ---: | --- |
| EN / CPU | `cpu` → `cpu` | render 明确 `SKIP`；实测 Link 位置示意 | 49.26 秒 | `L04 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | render 明确 `SKIP`；实测 Link 位置示意 | 45.78 秒 | `L04 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | Genesis camera 初始/最终 RGB | 90.40 秒 | `L04 CHECK: PASSED` |

三条路径都解析到 11 Links、9 Joints、9 DOFs 和 9 qpos，并按名称得到 7 个 arm DOF 与
2 个 finger DOF。joint4 的目标是 `-1.7500 rad`；基准误差从 `0.250000 rad` 降至
`0.006180 rad`，观测窗末速度约为 `0.000012 rad/s`。三组运行结果一致：

| case | joint4 KP | joint4 KV | rise | overshoot | settling | final error | peak speed | peak control | saturation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| G1 | 3500 | 100 | 0.120 s | 0 rad | 0.130 s | 0.00618 rad | 3.234 rad/s | 87.00 N·m | 70 ms |
| G2 | 7000 | 100 | 0.110 s | 0.0447 rad | 0.190 s | 0.00309 rad | 3.670 rad/s | 87.00 N·m | 190 ms |
| G3 | 7000 | 300 | 0.170 s | 0 rad | 0.210 s | 0.00309 rad | 2.471 rad/s | 87.00 N·m | 100 ms |

因此 G1→G2 的提高 KP 对照满足“90% rise 不更晚且过冲增大”，G2→G3 的提高 KV 对照
满足“过冲和峰值速度下降”。三组都触及配置的 `±87 N·m` force range，所以这些曲线
同时验证了 notebook 对饱和边界的解释，不能当作无限制理想 PD 响应。

AMD 渲染路径在 `build()` 前创建分辨率为 `720 × 540` 的 camera；初始和最终返回值均
通过非空 H×W×3/4、有限数值检查，没有触发 fallback。保存的双帧组合图为可读的
1511 × 624 RGBA PNG。人工检查确认 Franka 完整位于画面中，初末视角一致，joint4 运动
带来的手臂和末端姿态差异可见，标题没有重叠。两张定量图也经人工检查：baseline 的
目标、q、qdot、控制力和上下限可区分；G1–G3 图能看出 G2 过冲、G3 阻尼变化及力矩饱和。
camera 图只作为场景和姿态证据，瞬态结论仍由数组、曲线和动态指标支撑。

两条 CPU 路径生成的三张 PNG 哈希逐项相同，且都明确把姿态图标为 measured-Link
schematic、不是 camera frame。三条运行均保留 Genesis 1.3.3 的 tendon approximation、
neutral qpos、constraint time constant adjustment 和 neutral self-collision filtering
warning；这些已知 warning 没有代替结构、shape、有限性、limit、受控变量和最终关系
检查。L04 的最低课程合同仍是 CPU；本节新增的 R9700 证据不把 GPU 变成学习门槛。

## 14. L05 / M3.L05R.5 FK、IK、末端位姿与 fixed camera clean-kernel 验证

> 验证日期：2026-09-04（Asia/Shanghai）

重构后的 L05 使用 Genesis 1.3.3 内置 Franka，沿一条单环境主线验证 world-frame hand
pose、reachable/unreachable IK、显式 FK prediction、180-step 关节位置控制，以及一个
fixed camera 的 RGB/depth。新版 notebook 不再包含 Jacobian/SVD、DLS、wrist camera、
intrinsics/extrinsics、diagnostic override、B=4 batched control 或 selective update。

四条最终路径都由 `jupyter nbconvert --execute --to notebook` 启动独立 kernel；执行副本、
PNG 和缓存只写入 `/tmp`，提交版 EN/ZH notebook 继续保持无 output、
`execution_count: null`。每份提交版 notebook 为 15 个 cell，其中 7 个 code cell、330 行
code source；双语 code-cell ID/source 逐字一致。

### 14.1 环境与执行矩阵

本轮复用仓库 `.venv`：Python 3.12.3、Genesis 1.3.3、PyTorch
`2.9.1+rocm7.2.1.gitff65f5bc` 和 HIP `7.2.53211-e1a6bc5663`。系统可见 4 张
AMD Radeon AI PRO R9700；AMD notebook 路径使用运行前基本空闲的物理 GPU 0，进程内
实际 backend 报告为 `amdgpu`。

命令结构如下，其中 `<tmp>` 是本轮隔离目录：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output l05-en-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/en/l05-inverse-kinematics-end-effector-poses-and-cameras.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output l05-zh-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l05-inverse-kinematics-end-effector-poses-and-cameras.ipynb

PYOPENGL_PLATFORM=egl ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=900 --output l05-en-cpu-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l05-inverse-kinematics-end-effector-poses-and-cameras.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 \
CUDA_VISIBLE_DEVICES=0 ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=900 --output l05-en-amd-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l05-inverse-kinematics-end-effector-poses-and-cameras.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | camera 证据 | 最终结果 |
| --- | --- | --- | --- |
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有伪 camera frame | `L05 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有伪 camera frame | `L05 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | 一个 fixed-camera RGB/depth | `L05 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | 一个 fixed-camera RGB/depth | `L05 CHECK: PASSED` |

四份执行后 notebook 的 7 个 code cell 均取得 execution count，没有 error output，并且
各含一次最终通过标记。英文与中文 CPU 数值结果一致；英文 CPU+EGL 与 AMD+EGL 都实际
进入 render 分支。执行副本 code source 与提交版逐项一致，运行证据不是来自临时改写。

### 14.2 IK、FK、动态与负例证据

CPU 的 reachable position/rotation solver residual 为约 0.000110217 m /
0.000002741 rad，AMD 为约 0.000110271 m / 0.000002465 rad；相应 FK prediction error
与 solver residual 一致。两种后端的 180-step 动态结果也一致：position error 从约
0.235073 m 降到 0.005211 m，orientation final error 约 0.011822 rad，满足 notebook 的
0.02 m / 0.05 rad 末态阈值。solver residual、FK prediction 和动态 tracking error 在输出
中分别报告，不能相互替代。

unreachable `[2,0,2]` 在 CPU 的 position/rotation residual 约为 2.062891 m /
1.088002 rad，AMD 约为 2.055613 m / 1.120848 rad。两条路径都得到 finite q，但 residual
超过 tolerance，因此 `IK valid: False`；notebook 明确记录 `command sent: no`，不再提供
会执行 rejected q 的 diagnostic override。

本节证据保持三层边界：IK residual 只支持 candidate；FK 只预测 q 对应的 pose，不推进
动态场景；最终到达质量来自 180-step 后读取的 measured hand pose。它们都不证明无碰撞
路径、抓取成功或无限时域稳定性。

### 14.3 相机数组与人工视觉检查

CPU+EGL 和 AMD+EGL 得到相同的轻量相机数组合同：fixed-camera RGB 为
`(360,640,3)` `uint8`，depth 为 `(360,640)` `float32`，全部像素 finite。Notebook 只检查
shape、dtype 和 finite，不教授 K、intrinsics/extrinsics、clipping analysis 或 attached
camera lifecycle。

人工检查 CPU 和 AMD 的 RGB/depth 两联图后确认：RGB 中 Franka 与棋盘地面清晰可辨，
没有空白、全黑、错位或损坏画面；depth 中机器人轮廓与 RGB 位置一致，并呈现合理的
近远层次。误差图显示 position error 在 180 step 内降至阈值以下；orientation error 有
短暂上升，但最终低于 `0.05 rad`。相机图只证明场景可观察，不替代 IK、FK 或 tracking
数组证据。

### 14.4 已知 warning、状态结论与限制

四条路径均观察到 Genesis 1.3.3 已知的 tendon approximation、neutral qpos、solver time
constant adjustment 和 neutral self-collision filtering warning；它们没有导致非有限状态、
shape、residual、tracking 或 camera 检查失败。沙箱内第一次启动 Jupyter kernel 还因
本地 socket 权限返回 `Operation not permitted`，在获得授权后于沙箱外复跑同一命令并
通过；这不是 notebook 行为失败。

基于已经验收的 M3.L05R.5 证据，重构后的 L05 继续使用 `cpu-verified`：该状态对应本讲
最低 `cpu-ok` 合同和已通过的 EN/ZH CPU clean-kernel。参考 R9700 的 AMD+EGL 结果是附加
兼容性证据，不把本讲改成 GPU 必修，也不表示 L05 已经 `published`。

本轮没有验证其他 AMD/ROCm 组合、NVIDIA、Apple Silicon、Windows、viewer 模式、真实
相机、抓取成功、碰撞安全或无限时域稳定性；当前结果不得外推到这些平台或能力。

## 15. M3.R13.2 课程重编号的证据边界

> 迁移日期：2026-09-06（Asia/Shanghai）
>
> 范围：在 L05 之后插入新 L06，并将原 L06–L12 顺延为 L07–L13。

第 10 节的 GPU 证据是在训练课尚编号为 L11 时生成的历史记录。M3.R13.2 已将该课的
manifest lookup、讲义/notebook 路径、cell ID、训练运行名、输出目录和闭环交接从
L11/L12 语义迁移到 L12/L13。因为 code source 已变，旧执行副本不能直接证明新
L12 可执行；`course.json` 因此暂将 L12 标为 `reviewed`。

M3.R13.2 只执行静态课程合同、单元测试、Python 编译和文档构建门禁；不重复 Genesis
notebook、GPU 训练或 checkpoint 重载。M3.R13.3 将针对当前 L12 重跑 dry-run、
ACT/SmolVLA 1-step GPU smoke 和 checkpoint audit/reload；只有该步通过后才能恢复
`gpu-verified`。本次编号迁移不改变第 10 节的历史数值，也不扩大平台支持范围。

## 16. L12 / M3.R13.3 重编号后的 GPU 复验

> 验证日期：2026-09-06（Asia/Shanghai）
>
> 范围：当前 L12 的真实数据门禁、双策略命令审计、ACT/SmolVLA 1 step
> GPU smoke、checkpoint 审计、同一样本开环重载，以及状态同步后的双语
> clean-kernel。完整训练、收敛和 L13 Genesis 闭环评估均未运行。

### 16.1 环境、数据与模型身份

本轮复用已按本文基线安装的仓库 `.venv`。`uv pip check` 检查 221 个包并返回
`All installed packages are compatible`。实测版本为 Python 3.12.3、LeRobot 0.6.0、
PyTorch `2.9.1+rocm7.2.1.gitff65f5bc`、HIP `7.2.53211-e1a6bc5663`。训练前
物理 GPU 2 为 AMD Radeon AI PRO R9700，空闲可见显存约 `30519 MB`；
`ROCR_VISIBLE_DEVICES=2` 将它单独暴露为进程内 `cuda:0`。最小 ROCm tensor 运算返回
`[1, 2, 5, 10, 17, 26, 37, 50]`，未回退到 CPU。

复验数据仍是课程脚本专家生成的真实临时 LeRobot 数据集 `local/m06_g133`：
1 episode、42 frames、5 FPS，`observation.state` 和 `action` 均为 9 维有限
`float32`，`world`/`wrist` 视频均解码为 `(3, 120, 160)`，task 为
`pick the banana and place it in the bowl`。SmolVLA 继续从本地离线缓存核对：

- `lerobot/smolvla_base@c83c3163b8ca9b7e67c509fffd9121e66cb96205`；
- `HuggingFaceTB/SmolVLM2-500M-Video-Instruct@7b375e1b73b11138ff12fe22c8f2822d8fe03467`。

### 16.2 clean-kernel 执行顺序与 GPU 结果

首先在独立中文 kernel 中以 `RG101_RUN_SMOKE=0` 执行当时仍为 `reviewed` 的
notebook；数据门禁、安装配置读取、双 snapshot 审计、双 dry-run 和 smoke 命令
preflight 全部通过，训练与 checkpoint 声明正确标为 `SKIP`。

英文 notebook 随后在另一个独立 kernel 中以 `RG101_RUN_SMOKE=1` 从头执行，
仅暴露物理 GPU 2。两种策略均读取上述 42-frame 数据集，完成前向、有限
loss、反向、有限 gradient norm、一次 optimizer update 和 checkpoint 保存：

| 策略 | 训练配置 | 本轮日志观察 | checkpoint 证据 |
| --- | --- | --- | --- |
| ACT | pipeline-only 缩小配置，batch 1、seed 1000、1 step | loss `20.499`、gradient norm `208.584`、update `0.872 s`、报告显存 `0.36 GB` | `000001`；权重 `45384956` bytes；`last → 000001` |
| SmolVLA | 固定 base/VLM、默认冻结策略、batch 1、seed 1000、1 step | loss `6.305`、gradient norm `42.467`、update `1.328 s`、报告显存 `1.81 GB` | `000001`；权重 `906712520` bytes；`last → 000001` |

上述数值是本次 smoke 观察，不是质量比较、收敛证据或跨环境阈值。两个数值
checkpoint 都包含策略配置、训练配置、非空权重、预/后处理配置和必需状态文件。
ACT 恢复 9 维 action 以及 `chunk_size=n_action_steps=10`；SmolVLA 恢复 9 维 action、
`chunk_size=n_action_steps=50`、固定 VLM 以及
`world/wrist → camera1/camera2` 映射。

当前项目的通用 loader 在同一 GPU 上重载两个 checkpoint，并对同一真实数据样本
各返回 `(9,) float32` 有限动作。这仍然只是 **open-loop single-sample probe**，
没有把动作施加到 Genesis，也没有计算抓放成功率。

### 16.3 状态同步后复验与结论

完成上述 GPU 证据后，L12 在 manifest、双语讲义/notebook、README 和首页中同步
为 `gpu-verified`。最终 EN/ZH notebook 又各自在新的 R9700 kernel 中以
`RG101_RUN_SMOKE=0` 从头执行；两者都通过新状态断言、真实数据门禁、snapshot 审计、
双 dry-run 和命令 preflight，且执行副本的 cell type、ID 和 source 与对应提交版
完全一致。提交版 EN/ZH code cell 的 ID/source 也完全一致，并保持无 output、
`execution_count: null`。

本轮观察到非阻断的 Jupyter `IProgress not found` 提示和 Transformers `torch_dtype`
弃用提示，均未影响数据、训练、checkpoint 或重载断言。所有执行后 notebook、
checkpoint、日志和训练输出都位于 `/tmp/rg101-r133.sPlI2O`，未进入 Git。

以上证据支持当前 L12 恢复 `gpu-verified`。它不证明长训练收敛、策略质量、空缓存
联网下载、Genesis 闭环运行或任务成功率；后两项仍属于 L13。

## 17. L06 / M3.L06.5 并行仿真与批量 Franka 控制 clean-kernel 验证

> 验证日期：2026-09-07（Asia/Shanghai）
>
> 范围：L06 双语 CPU 最低路径、English CPU+EGL 四环境相机路径，以及参考 R9700
> 的 English AMD+EGL 附加回归。`M3.L06.5` 已于 2026-09-07 通过项目负责人验收；
> `M3.L06.6` 据此把 L06 从 `planned` 同步为 `cpu-verified`，并于 2026-09-07 通过
> 项目负责人验收。

### 17.1 环境与执行矩阵

本轮复用仓库 `.venv`：Python 3.12.3、Genesis 1.3.3、PyTorch
`2.9.1+rocm7.2.1.gitff65f5bc` 和 HIP `7.2.53211-e1a6bc5663`。系统可见 4 张
AMD Radeon AI PRO R9700；AMD 路径将物理 GPU 0 单独映射为进程内设备，并实际选择
`amdgpu`。四条路径均由 `jupyter nbconvert --execute --to notebook` 启动独立 kernel，
执行副本、图片与缓存只写入隔离的 `/tmp` 目录。

命令结构如下，其中 `<tmp>` 表示本轮隔离目录：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-cpu-outputs \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=900 --output l06-en-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/en/l06-parallel-simulation-and-batched-franka-control.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/zh-cpu-outputs \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=900 --output l06-zh-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l06-parallel-simulation-and-batched-franka-control.ipynb

PYOPENGL_PLATFORM=egl ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=1 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-cpu-egl-outputs \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l06-en-cpu-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l06-parallel-simulation-and-batched-franka-control.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 \
CUDA_VISIBLE_DEVICES=0 ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
ROBO_GENESIS_OUTPUTS_DIR=<tmp>/en-amd-egl-outputs \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l06-en-amd-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l06-parallel-simulation-and-batched-franka-control.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | 相机证据 | 最终结果 |
| --- | --- | --- | --- |
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有创建 camera | `L06 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有创建 camera | `L06 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | 四环境 RGB/depth batch | `L06 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | 四环境 RGB/depth batch | `L06 CHECK: PASSED` |

四份执行后 notebook 的 7 个 code cell 都取得 execution count，没有 error output。
`M3.L06.5` 执行时，四份执行副本与当时提交版 EN/ZH notebook 的 code-cell ID/source
规范化 SHA-256 均为
`d1bab5f21645f42148ee0c6c29d7e294b0ac50fda1d5a90b06a8dd28d88160ee`；运行证据不是来自
临时改写。`M3.L06.6` 只把 setup 中的 manifest status 断言改为 `cpu-verified`，当前双语
code source 哈希因此变为
`7be4b1574090ed727f084f03b6f74d1c65ff2c562a1e74311eb81e592bbfb97d`，提交版仍保持空
output 和 `execution_count: null`。

### 17.2 Batch、IK、动态控制与 selective update 证据

四条路径均得到 qpos `(4,9)`、full target `(4,3)/(4,4)`、full IK
`(4,9)/(4,6)`，以及 selective IK `(2,9)/(2,6)`。CPU 的四行 baseline IK
position residual 约为 `0.000001`、`0.000015`、`0.000159`、`0.000492 m`；rotation
residual 约为 `0.000000`、`0.000007`、`0.000252`、`0.000297 rad`，逐行满足
`5e-4 m` / `5e-3 rad` 阈值。

180-step baseline 控制后，env 0–3 的 position error 约为 `0.004860`、`0.005578`、
`0.005593`、`0.005106 m`，orientation error 约为 `0.011410`、`0.012569`、
`0.012505`、`0.010948 rad`，均低于 `0.02 m` / `0.05 rad`。selective update 的 row 0
和 row 1 分别映射到 env 1 和 env 3；二者末态 position error 约为 `0.005276`、
`0.006059 m`，orientation error 约为 `0.012084`、`0.013394 rad`。未选择的 env 0/2
继续保留 baseline target，本轮报告的额外 motion 与 position-error change 均为
`0.000000 m`，满足 `<0.005 m` 和 `<=0.002 m` 的联合检查。

EN/ZH CPU 结果逐项一致。AMD+EGL 与 CPU 的 IK residual 一致，动态误差只在末位出现
浮点差异，例如 env 0 orientation error 为 `0.011409 rad`、selected env 1 position
error 为 `0.005275 m`；所有逐环境断言继续通过。这里的结果证明 batch row 语义、
有限控制窗内的 measured pose 和 selective indexing，不证明固定吞吐加速、碰撞安全、
抓取成功或完整并行数据录制。

### 17.3 四环境相机与人工检查

English CPU+EGL 与 AMD+EGL 都实际进入 `render=1` 分支。Rasterizer 返回 RGB
`(4,360,640,3)` `uint8` 与 depth `(4,360,640)` `float32`；shape、dtype、全部像素
finite、每幅 RGB 非零变化和每幅 depth 存在正值的检查均通过。

人工检查两条路径生成的 2×2 RGB mosaic 后确认，env 0–3 四幅图都能看到对应 Franka
与棋盘地面，不存在空白、全黑、明显错位或损坏画面；四幅机器人姿态与 selective
阶段结束状态相符。depth 本轮只作为数组、有限性和正值像素证据，没有把未显示的 depth
数组描述为人工视觉检查结果。相机 batch 证明 batched rendering 可用，不替代逐环境
IK 或动态控制证据。

### 17.4 已知 warning、状态边界与限制

运行观察到 Genesis 1.3.3 已知的 tendon approximation、neutral qpos、solver time
constant adjustment 和 neutral self-collision filtering warning；它们没有导致非有限
状态、shape、residual、tracking、index mapping 或 camera 检查失败。沙箱内首次启动
English CPU kernel 因 Jupyter 本地 socket 权限返回 `Operation not permitted`，随后在
获准环境以同一命令复跑并通过；这不是 notebook 行为失败。

本节证据支持 L06 的 CPU 最低路径、当前 Linux CPU+EGL 四环境相机路径和一张参考 R9700
的 AMD+EGL 附加路径。它不外推到其他 AMD/ROCm、NVIDIA、Apple Silicon、Windows、
viewer 模式、更大 batch、固定 speedup 或长时间稳定性。

### 17.5 M3.L06.6 状态结论

已验收的双语 CPU clean-kernel 证明 L06 满足 `cpu-ok` 最低硬件合同，因此 L06 在
`M3.L06.6` 同步为 `cpu-verified`。English CPU+EGL 与参考 R9700 AMD+EGL 的通过结果
继续作为附加兼容性证据，不把 GPU 变成最低要求，也不表示本讲已经 `published`。

状态同步后，当前 English notebook 又在独立 CPU、`render=0` kernel 中从头执行，7 个
code cell 全部完成、没有 error output，并再次得到 `L06 CHECK: PASSED`。执行副本与当前
双语提交版的 code-cell ID/source 哈希均为
`7be4b1574090ed727f084f03b6f74d1c65ff2c562a1e74311eb81e592bbfb97d`。这次复验确认新的
manifest 状态断言和未改变的数值主线能共同通过；`.5` 已验收的中文 CPU、CPU+EGL 与
AMD+EGL 结果继续适用，不因单一状态 literal 变化而被描述为重新执行。

`M3.L06.6` 已于 2026-09-07 通过项目负责人验收；L06 的最终公开状态为
`cpu-verified`。

## 18. L07 / M3.L07.5–M3.L07.6 抓取任务场景验证与状态同步

> 验证日期：2026-09-07（Asia/Shanghai）
>
> 范围：L07 双语 CPU 无渲染数值路径、English CPU+EGL 双相机路径，以及参考 R9700
> 的 English AMD+EGL 附加回归。`M3.L07.5` 已于 2026-09-07 通过项目负责人验收；
> `M3.L07.6` 据此把 L07 从 `planned` 同步为 `cpu-verified`，并执行更新后复验；本步
> 已于 2026-09-07 通过项目负责人验收。

### 18.1 环境与执行矩阵

本轮复用仓库 `.venv`：Python 3.12.3、Genesis 1.3.3、PyTorch
`2.9.1+rocm7.2.1.gitff65f5bc` 和 HIP `7.2.53211-e1a6bc5663`。系统可见 4 张
AMD Radeon AI PRO R9700；AMD 路径只设置 `ROCR_VISIBLE_DEVICES=0`，把一张物理卡
映射为进程内设备，并由 notebook 确认实际 backend 为 `amdgpu`。四条路径均由
`jupyter nbconvert --execute --to notebook` 启动独立 kernel。

命令结构如下，其中 `<tmp>` 表示本轮隔离目录；Jupyter runtime、IPython、Matplotlib
和 Numba cache 也分别指向该目录，以下省略这些不影响实验语义的 cache 环境变量：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-cpu.ipynb --output-dir <tmp> \
  notebooks/en/l07-building-a-grasping-task-scene.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output zh-cpu.ipynb --output-dir <tmp> \
  notebooks/zh/l07-building-a-grasping-task-scene.ipynb

PYOPENGL_PLATFORM=egl ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-cpu-egl.ipynb --output-dir <tmp> \
  notebooks/en/l07-building-a-grasping-task-scene.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 \
ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 --output en-amd-egl.ipynb --output-dir <tmp> \
  notebooks/en/l07-building-a-grasping-task-scene.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | 相机证据 | 执行时间 | 最终结果 |
| --- | --- | --- | ---: | --- |
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有创建 camera | 29.23 秒 | `L07 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP`；没有创建 camera | 28.01 秒 | `L07 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | world/wrist RGB + depth | 43.19 秒 | `L07 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | world/wrist RGB + depth | 78.22 秒 | `L07 CHECK: PASSED` |

四份执行后 notebook 的 8 个 code cell 都取得 execution count，没有 error output。执行副本
与提交版 EN/ZH notebook 的 code-cell ID/source 规范化 SHA-256 均为
`b059f41ac40c5eeb545c8c795e01cf57ca04eadd89345bc99b3c1083550ca3be`，因此证据来自当前
提交源码而不是临时改写。提交版 notebook 仍保持空 output 和 `execution_count: null`。

执行后 notebook、Markdown 转换、PNG 与 cache 只写入隔离的 `/tmp` 目录；notebook 报告的
仓库 `outputs/l07-grasping-task-scene` 是既有 ignored 输出目录，本轮没有向其中保存文件、
rollout 或视频。

### 18.2 Asset、布局与静置状态证据

四条路径都通过相同的 asset、layout、bundle 与 state 检查：

- `setup_assets()` 和 `get_ycb_assets()` 解析出 banana、lemon、plum、bowl 四个支持对象，
  mesh path 存在，`rest_z_offset` / `radius_xy` 为正且 finite；
- table xy bounds 为 `[-0.25,0.95] × [-0.40,0.40] m`，course working region 为
  `[0.30,0.50] × [-0.22,0.28] m`；四个中心和保守 footprint 均通过边界检查；
- 六个 pairwise conservative margin 全为正，最小值为 lemon–bowl 的 `0.004790 m`；
- `SceneBundle` 含 5 个 table entity、4 个具名 YCB entity、finite `(9,)` Franka qpos，
  且没有 video camera；
- 60 steps home hold 后，CPU 的 max `|q-home|` 为 `0.006442 rad`，低于 `0.02 rad`；
- banana/lemon/plum/bowl 的 AABB bottom 支撑误差分别约为
  `0.000060/0.000043/0.000054/0.000114 m`，均低于 `0.005 m`；
- 四个对象的 xy drift 分别约为 `0.000608/0.001864/0.000956/0.000044 m`，均低于
  `0.01 m`；position `(3,)`、AABB `(2,3)` 与全部状态值均 finite；
- 默认 banana candidate `(0.30,0.18)` 位于 working region，保守 footprint 留在桌面内，
  对 lemon/plum/bowl 的 margin 分别为 `0.116010/0.028966/0.125367 m`。

EN/ZH CPU 结果逐项一致。AMD+EGL 的数值只在 bowl 末位浮点上有差异：支撑误差约为
`0.000117 m`、xy drift 约为 `0.000045 m`；其余记录值和所有判据保持通过。这些数据证明
当前 base scene 在有限静置窗口中的结构、布局和数值状态，不构成抓取或放置结果。

### 18.3 World/wrist 相机与人工检查

English CPU+EGL 与 AMD+EGL 都实际进入 `render=1` 分支，并得到：

- world RGB `(720,1280,3)` `uint8`，depth `(720,1280)` floating；
- wrist RGB `(720,1280,3)` `uint8`，depth `(720,1280)` floating；
- 两路数组 shape、dtype、全部像素 finite、RGB variation 和 positive depth pixel 检查通过；
- CPU 与 AMD 的 world positive-depth range 均约为 `[0.7151,2.9806] m`，wrist 均约为
  `[0.0100,0.6113] m`。

人工检查两条路径生成的并排 RGB 图后确认：world view 能同时识别桌面、Franka、banana、
lemon、plum 与 bowl 的全局关系；wrist view 是 hand 附着视角，能看到局部桌面、三件水果
和 bowl。两条路径均不存在空白、全黑、明显错位或损坏画面。depth 没有显示为图像，因而
这里只把它记录为数组、finite 与正距离证据，不把数值检查写成人工视觉结论。

### 18.4 已知 warning、状态边界与限制

四条路径均观察到 Genesis 1.3.3 已知的 Franka tendon approximation、neutral qpos 超出
joint limit、solver time constant 从 `0.005` 调整为 `0.01`，以及 neutral configuration
self-collision pair filtering warning。它们没有导致非有限状态、结构、布局、AABB、drift、
camera 或最终检查失败；本轮没有新增 fallback、EGL 或 OpenGL 错误。

本节证据支持 L07 的 CPU 无渲染数值路径、当前 Linux CPU+EGL 双相机路径和一张参考
R9700 的 AMD+EGL 附加路径。它不外推到其他 AMD/ROCm、NVIDIA、Apple Silicon、Windows、
viewer 模式或长时间稳定性，也不证明 IK 可达、无碰撞路径、抓取成功、放入 bowl、数据
时间对齐、真实相机等价、训练收益或闭环任务表现。

`M3.L07.5` 已于 2026-09-07 通过项目负责人验收。`M3.L07.6` 已将 manifest、双语讲义
与 notebook、README、首页和测试合同原子同步为 `cpu-verified`；更新后复验结果见
下一小节。

### 18.5 状态同步后复验与结论

状态 literal 变化后，双语 notebook 的 8 个 code-cell ID/source 仍完全一致，规范化
SHA-256 从 `.5` 执行时的
`b059f41ac40c5eeb545c8c795e01cf57ca04eadd89345bc99b3c1083550ca3be` 变为
`f12315f4d18f8ccdcea96853404bd67bc0e72cb75f862ecd90e3bbe688b1f3ff`；唯一行为语义变化是
setup 中的 manifest status 断言从 `planned` 改为 `cpu-verified`。

为确认当前源码，English notebook 又在独立 CPU、`render=0` kernel 中从头执行。8 个
code cell 全部完成、没有 error output，实际 backend 为 `cpu`，world/wrist camera 明确
`SKIP`，asset、layout、bundle、settled state 与最终汇总检查全部通过，最终输出
`L07 CHECK: PASSED`。执行副本与当前双语提交版的 code source 哈希一致，产物只位于
`/tmp`；两份提交版 notebook 继续保持空 outputs 和 `execution_count: null`。

`.5` 已验收的中文 CPU、English CPU+EGL 和 English AMD+EGL 证据继续适用，因为本步没有
改变仿真、布局或渲染逻辑。仓库课程验证、36 项测试、Python compileall、双模式文档构建
也均通过。以上证据支持 L07 的最终公开状态为 `cpu-verified`；其中 CPU 是最低兼容路径，
CPU+EGL 与参考 R9700 AMD+EGL 仍只是独立的附加能力证据。

`M3.L07.6` 已于 2026-09-07 通过项目负责人验收；L07 六个子步骤至此全部完成并验收。

## 19. L08 / M3.L08.5 脚本化专家 clean-kernel 验证

> 验证日期：2026-09-08（Asia/Shanghai）
>
> 范围：L08 双语 CPU 无渲染数值路径、English CPU+EGL world-camera 路径，以及参考
> R9700 的 English AMD+EGL 附加路径。四条要求路径和仓库门禁均已完成；
> `M3.L08.5` 已于 2026-09-08 通过项目负责人验收。随后启动的 `M3.L08.6` 已把 L08
> 同步为 `gpu-verified` 并完成更新后复验，且已于 2026-09-08 通过项目负责人验收。

### 19.1 环境与执行矩阵

本轮复用仓库 `.venv`：Python 3.12.3、Genesis 1.3.3、PyTorch
`2.9.1+rocm7.2.1.gitff65f5bc` 和 HIP `7.2.53211-e1a6bc5663`。系统可见 4 张
AMD Radeon AI PRO R9700；AMD 路径把物理 GPU 0 单独映射为进程内设备，notebook 实际
选择 `amdgpu`。四条路径均由 `jupyter nbconvert --execute --to notebook` 启动独立
kernel。

命令结构如下，其中 `<tmp>` 表示本轮隔离目录；Jupyter runtime、IPython、Matplotlib、
Numba、XDG cache 和 `ROBO_GENESIS_OUTPUTS_DIR` 也分别指向对应的隔离子目录：

```sh
ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l08-en-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/en/l08-demonstration-acquisition-and-scripted-experts.ipynb

ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=0 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l08-zh-cpu-render0.ipynb \
  --output-dir <tmp> \
  notebooks/zh/l08-demonstration-acquisition-and-scripted-experts.ipynb

PYOPENGL_PLATFORM=egl ROBO_GENESIS_BACKEND=cpu ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l08-en-cpu-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l08-demonstration-acquisition-and-scripted-experts.ipynb

PYOPENGL_PLATFORM=egl ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 \
CUDA_VISIBLE_DEVICES=0 ROBO_GENESIS_BACKEND=auto ROBO_GENESIS_RENDER=1 \
  .venv/bin/jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=1200 --output l08-en-amd-egl-render1.ipynb \
  --output-dir <tmp> \
  notebooks/en/l08-demonstration-acquisition-and-scripted-experts.ipynb
```

| Notebook / 能力路径 | 请求后端 → 实际后端 | 相机证据 | 执行时间 | 最终结果 |
| --- | --- | --- | ---: | --- |
| EN / CPU | `cpu` → `cpu` | 没有创建 camera；阶段图像为 0，明确 `SKIP` | 70.23 秒 | `L08 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 没有创建 camera；阶段图像为 0，明确 `SKIP` | 72.31 秒 | `L08 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | world RGB，start + 七阶段共 8 帧 | 85.21 秒 | `L08 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | world RGB，start + 七阶段共 8 帧 | 127.24 秒 | `L08 CHECK: PASSED` |

四份执行后 notebook 的 7 个 code cell 均取得 execution count，没有 error output。执行副本
与对应提交版 notebook 的 code-cell ID/source 规范化 SHA-256 均为
`627e260f1d34ef1b3cc18af8c1baccc0d58791857eeb7fc132c0834696ceca5a`；双语提交版代码也
逐字一致，并继续保持空 output 和 `execution_count: null`。执行后 notebook、提取的人工
检查 PNG、runtime、cache 和日志只位于 `/tmp/rg101-l085.QCL68t`；四个隔离
`ROBO_GENESIS_OUTPUTS_DIR` 没有产生文件，仓库内没有写入 rollout、图片或缓存。

### 19.2 Task、command schedule、trace 与 containment 证据

四条路径都读取固定 `011_banana → 024_bowl` 任务：容差 `0.060 m`，banana profile 的
yaw offset 为 `90°`、固定 hand height 为 `0.855 m`、closing force 为 `-10 N`。七阶段
名称与顺序断言通过。纯 NumPy rate-schedule 实验也逐条一致：`Δq∞=0.380 rad`；
`max_dq=0.006` 产生 64 个 waypoint、最大相邻 command 增量约 `0.0059 rad`；
`max_dq=0.003` 产生 127 个 waypoint、最大增量约 `0.0030 rad`，两条路径都准确到达同一
goal。

| 路径 | trace shape | 最大观测 arm command/state 差异 | horizontal containment | below-rim containment |
| --- | --- | --- | --- | --- |
| EN/ZH CPU、EN CPU+EGL | state/action 均为 `(850,9)` | joint 6，约 `2.4681 rad` | `0.0078 < 0.0600 m` | `0.7915 < 0.7973 m` |
| EN AMD+EGL | state/action 均为 `(849,9)` | joint 6，约 `2.4673 rad` | `0.0079 < 0.0600 m` | `0.7917 < 0.7973 m` |

所有 trace 都是等长、非空的 floating arrays，数值全部 finite；完整 rollout 均返回
`success=True`。CPU 的 EN/ZH 结果逐项一致，AMD 只出现上表所示的步数和末位浮点差异。
这些当次 trace 长度和数值用于记录当前运行，不作为跨 backend 固定答案。

### 19.3 World-camera 关键帧与人工检查

两条 `render=1` 路径都实际创建 world camera，并生成以下有序 tag：

```text
00_start → 01_pregrasp → 02_reach → 03_grasp
→ 04_lift → 05_above_target → 06_release → 07_done
```

8 张 RGB 均为 `(720,1280,3)` `uint8`，全部像素 finite；每帧有非零像素变化，序列中也
存在帧间变化。人工检查 CPU+EGL 与 AMD+EGL 的 2×4 montage 后确认：起点能同时辨认
Franka、banana、lemon、plum 与 bowl；后续帧依次显示 hand 到达 banana 上方、下降与闭合、
抬起 banana、移动到 bowl 上方、释放并退回；`07_done` 中 banana 位于 bowl 内。两条路径
均无空白、全黑、明显错位或损坏画面，阶段顺序与动作语义一致。

两条 containment 图也经过人工检查：俯视图的 banana center 位于允许的 bowl footprint
内，侧视图的 banana AABB bottom 低于 rim-minus-margin 阈值；图形结论与数值断言一致。
`render=0` 两条路径仍正常显示 command schedule、command/state trace 和 containment
三组 Matplotlib 数值图，但没有创建 camera 或伪装阶段画面。

### 19.4 Warning、证据范围与未运行项

四条路径均观察到 Genesis 1.3.3 已知的 Franka tendon approximation、neutral qpos 超出
joint limit、solver time constant 从 `0.005` 调整为 `0.01`，以及 neutral configuration
self-collision pair filtering warning；Quadrants 还提示 tuple 不能建立 weak reference，
因而关闭 template mapper cache。AMD kernel 另有一条第三方 `ast.Str` Python 3.14
deprecation warning。它们没有导致非有限 state/action、scene、rollout、containment、
camera 或最终检查失败；本轮没有 EGL、OpenGL 或 backend fallback 错误。

本节证据支持 L08 的双语 CPU 无相机数值路径、当前 Linux CPU+EGL world-camera 路径和
一张参考 R9700 的 AMD+EGL 附加路径，也记录了固定 banana episode 在四条路径中完成的
实例。成功率和对不同初态的可重复性需要另行运行多 seed 实验；notebook 末尾的
`motion_probe.py --compare`、lemon/plum 对照属于可选扩展，本步没有执行。其他 AMD/ROCm
组合、NVIDIA、Apple Silicon、Windows、viewer 模式和长时间运行也不在本轮矩阵中。

### 19.5 仓库门禁与当前状态

本轮在相同工作树完成：

- `.venv/bin/python -m robo_genesis.course_validation`：通过，13 lessons、32 localized
  Markdown files、26 notebooks、31 Python files；
- `.venv/bin/python -m pytest`：38 passed；
- `.venv/bin/python -m compileall -q src scripts tests`：通过；
- `npm ci`：安装并审计 190 个包；仍报告既有 Node `20.18.2` `EBADENGINE` warning 和
  13 项 advisory（6 low、1 moderate、6 high），未运行 `npm audit fix`；
- `npm run docs:build` 与 `EDGEONE=1 npm run docs:build`：通过；
- `git diff --check`：通过。

`M3.L08.5` 的要求路径和门禁均已完成，并于 2026-09-08 通过项目负责人验收。L08 公开
状态仍为 `planned`；是否同步为目标 `gpu-verified` 留给单独启动的 `M3.L08.6`。

### 19.6 M3.L08.6 状态同步后复验

项目负责人验收 `.1`–`.5` 并明确启动 `.6` 后，L08 已原子同步为 `gpu-verified`：

- `course.json`、双语导览 frontmatter 与课程状态说明；
- EN/ZH notebook metadata，以及 setup/final-check 中的 manifest status 断言；
- `README.md`、`README_en.md`、双语首页的课程表和整体进度摘要；
- notebook 与 manifest 合同测试。

硬件字段继续为 `gpu-recommended`。`gpu-verified` 表示本讲的正常视觉路径已经在参考 R9700
AMD+EGL 环境通过；第 19.1–19.4 节同时保留了 EN/ZH CPU 无相机数值路径和 CPU+EGL
路径的独立证据，不把 GPU 改写成阅读讲义或运行数值 fallback 的硬门槛。

状态 literal 更新后，双语 notebook 的 7 个 code-cell ID/source 仍完全一致，规范化
SHA-256 从 `.5` 执行时的
`627e260f1d34ef1b3cc18af8c1baccc0d58791857eeb7fc132c0834696ceca5a` 变为
`da664ce963a3e8cb1eebca5c48bef9aa16dec2a4e3455bfdf9f3d691dbef2c52`。行为逻辑没有改变；
两处 manifest status 断言由 `planned` 改为 `gpu-verified`。

为验证当前源码，English notebook 又在独立 CPU、`render=0` kernel 中从头执行，耗时
66.96 秒。7 个 code cell 全部完成、没有 error output，实际 backend 为 `cpu`，没有创建
camera，并得到 `(850,9)` state/action、`success=True`、通过的 horizontal/below-rim
containment 和最终 `L08 CHECK: PASSED`。执行副本与当前提交版 code source 哈希一致；
产物只位于 `/tmp/rg101-l086.wT3Yrk`，提交版双语 notebook 继续保持 clean output。

状态同步后的仓库门禁结果为：course validation 通过（13 lessons、32 localized Markdown、
26 notebooks、31 Python files），pytest 38 passed，compileall 通过，常规与 `EDGEONE=1`
文档构建通过，`git diff --check` 通过。`npm ci` 保留既有 Node `20.18.2` engine warning
和 13 项 advisory，没有修改依赖。

`.5` 已验收的中文 CPU、English CPU+EGL 与 English AMD+EGL 证据继续适用，因为 `.6`
没有改变任务、控制、仿真或渲染逻辑。以上证据支持 L08 当前公开状态为 `gpu-verified`，
同时明确 CPU 无相机数值路径也已验证。

`M3.L08.6` 已于 2026-09-08 通过项目负责人验收；L08 六个子步骤至此全部完成并验收。
