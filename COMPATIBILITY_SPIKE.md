# M0.6 兼容性 spike 记录

> 状态：M0.6 已由项目负责人验收
>
> 验证日期：2026-08-28（Asia/Shanghai）
>
> 范围：候选版本与最小端到端链路的可行性验证；本文保留 M0.6 原始证据，M0.7 的最终结论见 `COMPATIBILITY.md`。本文不是正式 lockfile。

## 1. 结论

`genesis-world==1.3.3` 在当前 AMD ROCm 主机上通过了 M0.6 规定的最小链路：

1. ROCm GPU 张量运算；
2. 使用 Genesis 内置 Franka 资产进行场景构建、位置控制、IK 和离屏相机渲染；
3. 使用抓取源课程的七阶段脚本专家完成香蕉放入碗中的任务；
4. 录制一个临时 LeRobot 数据集，并读回元数据、Parquet 样本和两路 H.264 视频；
5. 在 ROCm GPU 上分别执行 1 step ACT 和 SmolVLA smoke 训练并保存 checkpoint；
6. 通过课程现有的通用 policy 加载路径重新加载两种 checkpoint，对真实数据样本完成一次推理。

因为首选候选 1.3.3 已通过全部最小链路，本次未触发 `genesis-world==1.3.1` 的回退验证。M0.7 可以把 1.3.3 作为当前拟锁定的 Genesis 版本，但仍需在干净环境中重建依赖后再生成正式锁定结果。

## 2. 验证输入与边界

### 源基线

- `hello-genesis-world/main`: `03af81cbe6d4d2b3ef658ae1ab3e85f028bff9c6`
- `franka_fruit_pick_demo/course`: `0de3ae0df2a91acbda7f4fb537c65d9e54190527`
- 当前课程仓库 HEAD: `5de7d9a45505415edd64b429c40586a6ddc0319b`

两个源仓库的已跟踪文件在验证时没有未提交差异。抓取源仓库中已有的未跟踪数据集、输出、日志和工具不是本次验证的修改对象。本次新产生的数据集、checkpoint 和缓存均写入 `/tmp/rg101-m06.n7DcFk/`，未写入源仓库。

### 验证方式

现有 `franka_fruit_pick_demo/.venv` 安装的是 Genesis 1.3.1。为了不修改源环境，本次仅将 `genesis-world==1.3.3` 使用 `--no-deps --target` 安装到 `/tmp`，然后用 `PYTHONPATH` 使 1.3.3 覆盖虚拟环境中的 1.3.1。1.3.3 因此是与该环境中已安装的其余依赖组合验证的。

由于仓库工作沙箱不暴露 `/dev/kfd`，GPU 测试在获授权的主机环境中运行。Genesis 和 ACT 使用 GPU 0，SmolVLA 在 GPU 0 被其他任务占用后改用空闲的 GPU 1。Numba、Torch、XDG 和 Matplotlib 的本次新增缓存均定向到 `/tmp`；SmolVLA 在断网模式下读取主机上已有的 Hugging Face 模型缓存。

## 3. 实测环境

| 项目 | 实测值 |
| --- | --- |
| OS / kernel | Linux `7.0.0-28-generic` x86_64 |
| Python | `3.12.3` |
| GPU | 4 × AMD Radeon AI PRO R9700，单卡可见显存 `30576 MB` |
| 本次使用设备 | GPU 0（Genesis / ACT）、GPU 1（SmolVLA） |
| ROCm（系统） | `7.2.0` |
| PyTorch | `2.9.1+rocm7.2.1.lw.gitff65f5bc` |
| PyTorch HIP runtime | `7.2.53211-e1a6bc5663` |
| torchvision | `0.24.0+rocm7.2.1.gitb919bd0c` |
| torchaudio | `2.9.0+rocm7.2.1.gite3c6ee2b` |
| Genesis | `1.3.3` |
| LeRobot | `0.6.0` |
| Transformers | `5.5.4` |
| Tokenizers | `0.22.2` |
| Accelerate | `1.14.0` |
| Safetensors | `0.8.0` |
| num2words | `0.5.14` |
| PyAV | `15.1.0` |
| NumPy | `2.2.6` |
| Numba / llvmlite | `0.66.0` / `0.48.0` |
| trimesh | `5.0.0` |
| quadrants | `1.2.0` |
| OpenCV | `5.0.0.93` |
| PyArrow | `25.0.0` |

`amd-smi` 可读取 ROCm 和显存状态，但返回的 amdgpu 内核模块版本字段为 `AMDSMI_STATUS_FILE_ERROR - Error opening file`，因此本文不填写无法确认的驱动版本。

## 4. 分项证据

### 4.1 ROCm 基础计算

- `torch.cuda.is_available()` 为 `True`。
- 设备名为 `AMD Radeon AI PRO R9700`。
- 单卡过滤后张量乘加和同步成功，结果为 `[1.0, 2.0, 5.0, 10.0, 17.0, 26.0, 37.0, 50.0]`。

### 4.2 Genesis 场景、控制、IK 和渲染

最小场景直接使用 Genesis 1.3.3 内置资产 `xml/franka_emika_panda/panda.xml`，而不是源项目复制的 Franka 目录。

- `scene.build()` 成功。
- Franka 状态和 IK 解的维度均为 9。
- IK 解全部为有限值，返回的最大位姿误差为 `0.0002107024`。
- 位置控制后关节状态发生可观测变化，与初始状态的 L2 差为 `0.0311287`。
- 离屏渲染返回 `(120, 160, 3)` 的 `uint8` RGB 图像，像素范围为 `[10, 255]`。

### 4.3 脚本专家

使用抓取源课程的 `grasp_demo.py`，在 Genesis 1.3.3 / GPU 0 上运行默认七阶段流程：

```text
[grasp_demo] task: pick=011_banana place=024_bowl -> success = True
```

这一项使用了源课程现有的 Franka 副本，因为当前尚处于 M0，还没有在 M1.4 将其路径改为 Genesis 内置资产。内置 Franka 资产的加载和基本控制已在 4.2 独立通过；M1.4 完成路径切换后需重跑抓放 smoke。

### 4.4 LeRobot 录制与读取

用 `record_dataset.py` 记录了一个成功 episode，为了缩短 spike 将采样参数设为 5 FPS、`160×120`、两路 RGB：

```text
[record] episode 1/1 saved (attempt 1, seed 0, pick=011_banana, 42 frames)
[record] done: 1 success in 1 attempts -> /tmp/rg101-m06.n7DcFk/dataset-g133
```

使用 `LeRobotDatasetMetadata` 和 `LeRobotDataset(..., video_backend="pyav")` 独立读取的结果：

- 1 episode，42 frames，5 FPS；
- `observation.state`: `(9,) float32`；
- `action`: `(9,) float32`；
- `observation.images.world`: `(3, 120, 160) float32`；
- `observation.images.wrist`: `(3, 120, 160) float32`；
- 任务文本、episode/frame/index 字段存在。

首次命令使用 `--vcodec libx264` 被 LeRobot 0.6.0 在建立数据集前拒绝。LeRobot 的配置名应为 `h264`，底层 FFmpeg 实际编码器仍为 libx264。更正为 `--vcodec h264` 后录制和读取均通过。

### 4.5 ACT smoke 训练

训练使用 LeRobot 0.6.0 的 ACT 实现，对 spike 缩小模型并关闭预训练视觉权重下载：

- batch size: 1；
- steps: 1；
- chunk/action steps: 10 / 10；
- transformer: `dim_model=64`、`n_heads=4`、编码器/解码器/VAE 编码器各 1 层；
- 可训练参数：`11,322,009`；
- 该 step loss: `20.499`；
- GPU 峰值显存（训练日志）：`0.36 GB`；
- checkpoint: `/tmp/rg101-m06.n7DcFk/act-smoke/checkpoints/000001/pretrained_model`；
- `model.safetensors` 大小：`45,384,956` bytes。

该 loss 只证明前向、反向、优化器更新和保存链路可运行，不代表模型已学会任务。

### 4.6 ACT checkpoint 加载与推理

通过源课程 `eval_policy.py` 中的 `load_policy()` 和 `PolicyBundle.select_action()` 加载刚生成的 checkpoint，并对临时数据集的第一个真实样本执行推理：

```text
policy_type act
device cuda
action_shape (9,)
action_dtype float32
action_finite True
action_minmax -2.395956039428711 2.5108227729797363
gpu_peak_mb 124.91
```

### 4.7 SmolVLA smoke 训练

`train_policy.py smolvla --dry-run` 首先确认实际命令使用 `--policy.path=lerobot/smolvla_base`，并自动注入以下相机键映射：

```json
{
  "observation.images.world": "observation.images.camera1",
  "observation.images.wrist": "observation.images.camera2"
}
```

实际 smoke 在 `HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1` 下使用主机已有缓存，没有从网络获取模型。本次读取的缓存 revision 为：

- `lerobot/smolvla_base`: `c83c3163b8ca9b7e67c509fffd9121e66cb96205`；
- `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`: `7b375e1b73b11138ff12fe22c8f2822d8fe03467`。

有效的 GPU 1 smoke 结果：

- batch size: 1；
- steps: 1；
- 输入：临时数据集的两路 RGB、9 维状态和任务文本；
- 相机键：`world/wrist` 映射为 `camera1/camera2`；
- 总参数：`450,046,176`；
- 可训练参数：`99,880,992`；
- 该 step loss: `6.305`；
- gradient norm: `42.467`；
- GPU 峰值显存（训练日志）：`1.81 GB`；
- checkpoint: `/tmp/rg101-m06.n7DcFk/smolvla-smoke-gpu1/checkpoints/000001/pretrained_model`；
- `model.safetensors` 大小：`906,712,520` bytes。

该 1 step loss 同样只用于证明微调链路可运行，不表示 SmolVLA 已在该数据集上收敛。

### 4.8 SmolVLA checkpoint 加载与推理

通过与 ACT 相同的 `load_policy()` 和 `PolicyBundle.select_action()` 通用路径加载新 checkpoint。输入来自真实数据样本，包含两路图像、9 维状态和任务文本 `pick the banana and place it in the bowl`：

```text
policy_type smolvla
device cuda
image_keys ['observation.images.world', 'observation.images.wrist']
action_shape (9,)
action_dtype float32
action_finite True
action_minmax -2.147381544113159 3.5599122047424316
gpu_peak_mb 986.19
```

加载时成功从 checkpoint 恢复了 `world/wrist → camera1/camera2` 映射。

## 5. 关键命令

Genesis 1.3.3 临时覆盖安装：

```sh
UV_CACHE_DIR=/tmp/rg101-m06.n7DcFk/uv-cache \
uv pip install \
  --python /home/xunwang2/project/franka_fruit_pick_demo/.venv/bin/python \
  --target /tmp/rg101-m06.n7DcFk/genesis-1.3.3 \
  --no-deps 'genesis-world==1.3.3'
```

临时数据录制的有效参数：

```sh
python franka_fruit_pick/record_dataset.py \
  --episodes 1 --max-attempts 1 \
  --fps 5 --img-width 160 --img-height 120 \
  --pick 011_banana --repo-id local/m06_g133 \
  --root /tmp/rg101-m06.n7DcFk/dataset-g133 \
  --vcodec h264
```

ACT smoke 训练的有效参数：

```sh
python franka_fruit_pick/train_policy.py act \
  --repo-id local/m06_g133 \
  --dataset-root /tmp/rg101-m06.n7DcFk/dataset-g133 \
  --output-dir /tmp/rg101-m06.n7DcFk/act-smoke \
  --name m06-act-smoke --steps 1 --batch-size 1 \
  --save-freq 1 --log-freq 1 --num-workers 0 --device cuda -- \
  --policy.pretrained_backbone_weights=null \
  --policy.chunk_size=10 --policy.n_action_steps=10 \
  --policy.dim_model=64 --policy.n_heads=4 \
  --policy.dim_feedforward=128 \
  --policy.n_encoder_layers=1 --policy.n_decoder_layers=1 \
  --policy.n_vae_encoder_layers=1 --policy.latent_dim=8
```

SmolVLA GPU smoke 训练的有效参数：

```sh
ROCR_VISIBLE_DEVICES=1 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python franka_fruit_pick/train_policy.py smolvla \
  --repo-id local/m06_g133 \
  --dataset-root /tmp/rg101-m06.n7DcFk/dataset-g133 \
  --output-dir /tmp/rg101-m06.n7DcFk/smolvla-smoke-gpu1 \
  --name m06-smolvla-smoke-gpu1 \
  --steps 1 --batch-size 1 --save-freq 1 \
  --log-freq 1 --num-workers 0 --device cuda
```

上述 Python 命令在实际验证时还使用了第 2 节说明的 GPU 限定和临时缓存环境变量。

## 6. 警告与已知限制

- Genesis 加载 Franka 时报告 tendon 被近似为 joint actuator、中性位形超出关节限制、constraint solver `timeconst` 被调整、以及中性位形自碰撞对被过滤。这些警告未阻断本次 smoke，但 M1.4 切换内置模型时应复核关节名、tendon 行为、控制参数和自碰撞设置。
- 此次 1.3.3 是覆盖在一个现有 1.3.1 环境上的定向 spike，不等同于已验证干净安装。
- 抓取源课程的 `uv.lock` 与实际可运行虚拟环境不一致：lock 当前解析到通用 PyTorch 2.11.0 和 LeRobot 0.6.1，而本次实测为 ROCm PyTorch 2.9.1 和 LeRobot 0.6.0。不应将源 lockfile 直接当作当前已验证环境。
- ACT 和 SmolVLA 都只执行了 1 step 训练和单次推理，没有执行长训练、收敛检查或学习策略的闭环任务成功率评估。
- 在选择物理 GPU 1 时，同时把 `ROCR_VISIBLE_DEVICES`、`HIP_VISIBLE_DEVICES` 和 `CUDA_VISIBLE_DEVICES` 都设为 `1` 会使当前 PyTorch 看不到 GPU，LeRobot 会明确警告并回退到 CPU。只设置 `ROCR_VISIBLE_DEVICES=1` 时，物理 GPU 1 被正确重映射为进程内的 `cuda:0`，GPU 训练通过。正式环境文档应避免同时使用多套可见设备变量。
- SmolVLA 本次使用已有 Hugging Face 缓存完成断网验证；尚未验证从空缓存下载模型的网络流程。
- 本次未验证 CPU-only、NVIDIA CUDA、Apple Silicon、Windows 或其他 AMD GPU/ROCm 组合。
- 因为没有触发回退条件，Genesis 1.3.1 仅是已有环境中的原始版本，不是本次独立对照验证的候选。

## 7. M0.7 输入

M0.7 应在本记录基础上：

1. 以 Genesis 1.3.3 作为拟锁定版本；
2. 明确区分系统 ROCm 7.2.0、PyTorch wheel 的 HIP runtime 7.2.53211 和 PyTorch 本身版本；
3. 将 PyTorch ROCm wheel 的来源与安装方法写入正式环境说明；
4. 锁定 LeRobot 0.6.0 与 PyAV 15.x，避免源 lockfile 中的未验证升级；
5. 在干净临时环境中重建依赖，至少重跑 import、GPU 张量、Genesis 最小场景与 ACT/SmolVLA smoke；
6. 生成最终兼容矩阵、精确版本策略和未验证平台声明。
