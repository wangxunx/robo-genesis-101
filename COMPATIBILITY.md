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
| CPU-only 完整链路 | **部分验证** | L01–L02 的 CPU 最小实验已验证；L03–L06 尚未完成，训练全链路也未在 CPU-only 环境验证。 |
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

## 10. L11 / M2.10 GPU kernel 验证

> 验证日期：2026-09-01（Asia/Shanghai）
>
> 范围：L11 的真实数据门禁、ACT/SmolVLA 命令审计、双策略 1 step GPU
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
收敛，也没有在 Genesis 中施加动作、运行闭环 rollout 或计算抓放成功率；这些证据仍
属于 L12。执行后的 notebook、临时数据、checkpoint、训练日志和缓存均不提交到 Git。

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
0.6.0，但该项只是后续训练提示，不属于 L01–L06 的通过条件。两份提交 notebook 都只有
4 个 code cell，其源码和 ID 的规范化 SHA-256 均为
`68dfad0c9af76db3e6f904781c536833829594b72f5068f2da076515cacecf4b`；提交文件保持
`execution_count: null` 且没有 output。

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
