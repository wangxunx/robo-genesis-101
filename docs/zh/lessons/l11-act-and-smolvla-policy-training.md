---
lesson: L11
slug: act-and-smolvla-policy-training
locale: zh
title: "ACT 与 SmolVLA 策略训练"
duration_minutes: 150
hardware: gpu-required
status: planned
---

# L11 · ACT 与 SmolVLA 策略训练

> **硬件约定：**完整实验需要 GPU。已经验证的参考平台为 Linux x86_64、
> AMD Radeon AI PRO R9700 和 ROCm 7.2，但本讲的概念与命令不依赖特定平台。
> 无法进行训练的学员仍可完成数据检查和命令审计；不过，这条精简路径不能代替
> 两次真实的 GPU smoke 运行。

## 本讲在课程中的位置

[L09](/zh/lessons/l09-dataset-anatomy-and-imitation-learning) 已经介绍了数据集
schema、相机键、行为克隆（behavior cloning）和动作分块（action chunking）的基本思想。
[L10](/zh/lessons/l10-domain-randomization) 随后讨论了训练分布应该如何变化。
L11 将把一份带版本记录的演示数据集转化为两类策略 checkpoint：

```text
LeRobot dataset
  → validate one real sample
  → assemble the training command
  → ACT or SmolVLA optimization
  → checkpoint + saved preprocessing
  → reload on one real sample
  → closed-loop evaluation in L12
```

最后一个箭头尤其重要。本讲能够证明训练和加载链路可以运行，却不能证明学到的
策略能够完成抓取任务。要支持后一项结论，还需要在
[L12](/zh/lessons/l12-closed-loop-evaluation-and-capstone) 中按照规定的 seed、
成功判据和报告协议进行模拟器 rollout（回合执行）。

开始之前，你应当能够：

- 找到本地 LeRobot 数据集，并识别它的逻辑仓库 ID；
- 读取数据集的特征 schema、FPS、episode 边界和任务表；
- 解释本课程为何记录两路 RGB 画面、9 维机器人状态和 9 维指令动作；
- 区分行为克隆与闭环任务评估；
- 记录一次训练所使用的数据集版本和域随机化配置。

## 学习目标

完成 L11 后，你应当能够：

1. 在分配模型之前，用一个真实训练样本检查 state、action、image、task 和时间
   信息是否符合约定；
2. 解释 ACT 的视觉主干、条件变分自编码器（CVAE）、Transformer 和 action queries
   分别承担什么工作，以及训练和推理过程有何不同；
3. 解释 SmolVLA 的视觉—语言主干、任务文本、动作专家和流匹配目标分别承担什么工作；
4. 根据数据集 FPS、`chunk_size` 和 `n_action_steps` 计算名义预测时域与执行时域，
   并拒绝不合法的配置；
5. 审计生成的 ACT 与 SmolVLA `lerobot-train` 命令，包括初始化方式、batch size、
   device、路径和相机键重命名；
6. 分别为两种策略运行一次真实的 GPU 优化步骤，并找到解码、前向传播、有限 loss、
   反向传播、优化器更新和 checkpoint 保存的证据；
7. 检查并重新加载两个 checkpoint，要求它们针对同一个真实数据样本输出数值有限的
   9 维 `float32` 动作；
8. 准确说明为什么 dry-run、有限 loss、可加载的 checkpoint 和一次开环动作仍然不能
   证明闭环任务成功。

## 先明确证据边界

“训练成功了”过于含糊，无法用于严谨的实验报告。L11 使用下面的证据阶梯：

| 证据 | 能够证明什么 | 不能证明什么 |
|---|---|---|
| dry-run 命令审计 | wrapper 正确解析路径，并组装出预期的训练器参数 | 数据集、模型内容、GPU 或优化器确实能够运行 |
| 单步 smoke | 一个 batch 能够完成解码、前向、反向、更新和保存 | 模型已经收敛、能够泛化或策略实际可用 |
| 有限的训练 loss | 该步骤记录的标量在数值上有定义 | loss 将继续下降，或它能与另一种策略的 loss 直接比较 |
| 重新加载 checkpoint | 权重、配置和处理器能够重建 | 策略能在不断变化的环境中做出合理动作 |
| 一次开环动作 | 已加载模型返回了约定的 shape、dtype 和有限数值 | 执行该动作是安全的，或它能完成任务 |
| 闭环 rollout | 策略按照明确协议与模拟器持续交互 | 总体性能；除非报告了足够多带 seed 的 episode |

阅读日志时，应始终把这张表放在眼前。很小的数据集可能被模型记住；loss 持续下降时，
策略在新位姿或新外观下仍可能表现很差。短时间、有噪声的训练也可能出现相反情况：
loss 不单调并不自动意味着管线已经损坏。

## 共同的数据到策略合同

ACT 和 SmolVLA 使用同一份课程原始数据集，但采用不同的预处理与建模方式。

| 字段 | 在本课程中的含义 | 必须检查的内容 |
|---|---|---|
| `observation.state` | 9 个关节位置：7 个机械臂关节与 2 个夹爪关节 | shape 为 `(9,)`、`float32`、数值有限，并符合预期关节名称 |
| `action` | 按相同关节顺序记录的 9 个目标关节位置指令 | shape 为 `(9,)`、`float32`、数值有限 |
| `observation.images.world` | 固定的全局视角 | 字段存在、RGB 可解码、分辨率一致 |
| `observation.images.wrist` | 眼在手上的局部视角 | 字段存在、RGB 可解码、分辨率一致 |
| `task` | 非空的 episode 语言描述 | 解析并打印一条真实 task，不要自行编造占位文本 |
| FPS | observation 与 action 共用的采样率 | 数值为正，并与视频元数据一致 |
| episode 边界 | 防止未来动作目标跨入另一个 episode | 元数据和 padding 行为可读取 |

逻辑仓库 ID 和本地 root 是两个独立输入。例如，`genesis/fruit_pick` 可以标识
数据集，而 `datasets/fruit_pick` 指向本地副本。即使 ID 正确，配上错误目录仍然
会得到一个无效实验。

### 同一张图像的三层表示

比较 shape 之前，先弄清它描述的是哪一层：

1. 数据集元数据按高 × 宽 × 通道描述存储的视频帧；
2. 解码后的 LeRobot 样本通常以通道优先的 tensor 暴露图像；
3. 图像进入模型前，策略预处理器可能对 tensor 重命名、缩放、归一化、padding 或组 batch。

SmolVLA 还会对 `task` 分词，并且可能在内部对较短的 state/action 向量进行 padding。
因此，原始元数据中的键与模型内部特征不必拥有完全相同的名称或 shape。正确的检查方法
是沿完整预处理器走通真实的训练和加载链路，而不是对比两段孤立 JSON 后凭空猜测。

### 这里的行为克隆预测一个序列

单步行为克隆可以概括为 `policy(observation_t) → action_t`。本讲中的两个策略则会
学习未来的一段动作序列：

```text
policy(images_t, state_t, optional_task)
  → [action_t, action_t+1, ..., action_t+chunk_size-1]
```

因此，数据加载器需要取得同一个 episode 内的未来动作目标。靠近 episode 末尾时，
它会标记 padding 位置，让模型 loss 忽略或 mask 掉这些位置。动作块是在时间上协调的
一组预测，并不意味着其中每个动作都应在不再观察环境的情况下连续执行。

## ACT：预测动作块的 CVAE

ACT 是 **Action Chunking with Transformers** 的缩写。在本课程锁定的 LeRobot
实现中，图像和机器人状态共同为 Transformer 提供条件，模型输出固定长度的动作块。

### 训练路径

ACT 包含两条基于 Transformer 的路径，它们的名称很容易混淆：

- **CVAE encoder** 只在训练时读取机器人状态和真实动作块，并输出潜变量分布的
  mean 与 log variance；
- 主 **Transformer encoder/decoder** 接收视觉特征、机器人状态、采样得到的潜变量
  和学习得到的 action queries，预测完整动作块，也是推理时保留的路径。

信息流如下：

```text
ground-truth action chunk + state
  → CVAE encoder → mean/log-variance → sampled latent

camera features + state + sampled latent + action queries
  → Transformer encoder/decoder → predicted action chunk
```

当前 loss 由两部分相加：一是仅对有效、非 padding 目标计算的平均绝对动作重建误差；
二是 `kl_weight` 乘以学习到的潜变量分布与标准正态先验之间的 KL divergence。
重建项要求预测动作块模仿演示数据，KL 项则约束潜空间。二者之和为有限值，只能证明
这一次计算成功，不能证明模型已经具备完成任务的能力。

### 推理路径

推理时没有真实的未来动作可供 CVAE encoder 读取。本课程锁定的 LeRobot 实现会使用
全零潜变量，运行主 Transformer 并返回一个动作块。`ACTPolicy.select_action()` 最多将
`n_action_steps` 个动作放入队列，等队列耗尽后再查询模型。

由此产生两个不同的时域：

- `chunk_size`：模型一次预测多少个未来动作，同时也是数据加载器准备的训练目标长度；
- `n_action_steps`：运行时在重新请求动作块之前实际消费多少个预测动作。

改变 `n_action_steps` 不会缩短训练目标，而是改变部署时策略吸收新 observation 的频率。
时间集成（temporal ensembling）是 ACT 的另一种执行模式，但本课程所用 LeRobot 配置
默认关闭它，最小实验也不涵盖这种模式。

### “根据配置创建”不等于“所有权重都随机初始化”

项目的 ACT preset 会生成 `--policy.type=act`，因此策略结构根据配置创建，并适配数据集
特征。不过，LeRobot 0.6.0 的 ACT 默认配置允许视觉主干使用 ImageNet 预训练的
ResNet18 权重，所以声称默认 ACT 的每个权重都随机初始化并不准确。

单步 smoke 会特意设置 `--policy.pretrained_backbone_weights=null`。这样既能避免网络
下载，又能配合大幅缩小的 Transformer/CVAE，形成一条可重复的管线探针。得到的
checkpoint 是一个 **smoke 模型**，并不是有代表性的 ACT 训练配置。

## SmolVLA：以语言为条件的流匹配

SmolVLA 是一种紧凑的**视觉—语言—动作（vision-language-action，VLA）**策略。
本课程微调 `lerobot/smolvla_base`，不会从头训练完整模型。

### 前缀上下文与动作专家

模型在概念上分成两条信息流：

- 视觉—语言主干对相机图像和 task token 进行嵌入；
- 动作专家将这些上下文与机器人状态、带噪动作块以及连续时间值结合起来。

图像、语言和状态构成上下文前缀，带噪动作及其时间嵌入构成动作后缀。通过 attention，
动作专家可以让预测以任务上下文为条件，而不会把 task 字符串误当成动作标签。

锁定的 base 配置会冻结 vision encoder，主要训练动作专家，并训练 state projection。
这些选择定义了微调边界，也会影响可训练参数量、显存占用和学习率。改变其中任意一项
都会形成不同实验，必须留下记录。

### 流匹配目标

训练时，SmolVLA 会采样噪声和一个时间值。它在演示动作块与噪声之间插值，再要求
动作专家预测沿这条路径前进的速度。用紧凑的记法表示：

```text
noisy point x_t = t × noise + (1 - t) × demonstrated_actions
target velocity = noise - demonstrated_actions
loss = mean squared error(predicted_velocity, target_velocity)
```

推理时，模型从噪声出发，将学习到的速度场积分回一个动作块。LeRobot 0.6.0 默认使用
十个采样步骤。因此，SmolVLA 的一次策略查询并不是从像素到关节的一次直接线性回归。

上面的说明已经足以支撑本讲实验中的推理。完整推导流匹配理论、tokenizer 内部机制或
每一层 attention，超出了本讲范围。

### 语言是真实输入，不是装饰

task 必须来自数据集样本，例如描述要拿起哪个物体并放到哪里。用一条不相关的硬编码
句子替换它，会改变模型的条件信号。ACT 可以使用同一份数据集而不消费语言；但在
SmolVLA 的训练与重新加载探针中，必须验证非空 task 文本确实进入了预处理器。

预训练可能提供可复用的视觉、语言和动作先验。至于这些先验能否改善当前水果抓取任务，
仍然是需要闭环实验验证的问题；模型名称、参数量或单步 loss 都无法回答它。

## 相机键是 checkpoint 合同的一部分

课程数据集根据相机的物理角色命名视角：

```text
observation.images.world
observation.images.wrist
```

SmolVLA base 使用预训练时的规范名称，因此项目 preset 会加入以下映射：

```json
{
  "observation.images.world": "observation.images.camera1",
  "observation.images.wrist": "observation.images.camera2"
}
```

LeRobot 会把该映射写入 `train_config.json` 和保存下来的
`rename_observations_processor`。`robo_genesis.eval_policy.load_policy()` 中的
加载器会重新读出这份映射，因此调用方仍可提供含义清楚的原始键 `world` 和 `wrist`。

从当前数据集新建的 ACT 会适配原始特征键，不需要 preset 中的重命名。这只是对当前
ACT 初始化路径的说明，不能推导成“任何预训练 ACT checkpoint 都能接受任意相机名”。

不要为了“修复”特征不匹配而临时编造另一份评估映射。训练、checkpoint 元数据和评估
必须使用同一个转换关系。

## ACT 与 SmolVLA：比较合同，不要直接比较原始 loss

| 问题 | ACT preset | SmolVLA preset |
|---|---|---|
| 训练器选择 | `--policy.type=act` | `--policy.path=lerobot/smolvla_base` 或锁定版本的本地 snapshot |
| 初始化 | 新建 ACT 策略；除非覆盖配置，否则视觉主干可能使用 ImageNet 权重 | 微调预训练 SmolVLA base |
| 条件输入 | 两路图像和机器人状态 | 两路图像、机器人状态和 task 文本 |
| 训练目标 | 有效动作的 L1 重建误差加权重后的 KL | 流匹配速度 MSE |
| 当前默认 chunk / 执行步数 | 100 / 100 | 50 / 50 |
| wrapper 默认 batch size | 8 | 4 |
| 本课程中的相机键重命名 | 无 | `world/wrist → camera1/camera2` |
| 重新加载路径 | 项目通用加载器和保存的处理器 | 同一个加载器，并恢复相机重命名与语言处理 |

两种原始 loss 的定义和尺度不同，用 `ACT loss < SmolVLA loss` 判断策略优劣没有意义。
即使在同一种策略内部，也只有先确认数据集、预处理、初始化、训练预算和 reduction 均
相同，才能比较不同运行。

## 理解关键训练旋钮

### `chunk_size` 与数据集 FPS

`chunk_size` 计算的是动作样本数，而不是秒。其名义时间跨度为：

```text
prediction horizon in seconds = chunk_size / dataset_fps
```

若数据集为 10 FPS 且 `chunk_size=40`，一次预测包含 4 秒的动作目标，但这并不表示
必须把这 4 秒全部开环执行。

更长的动作块可以表达更长时间的协调行为，但也会扩大输出目标，并增加 episode 末尾
附近的 padding。缩短动作块会缩小这个时域，却不会自动让动作更平滑或更容易成功。

### `n_action_steps` 与重新规划

名义上的执行间隔为：

```text
replan interval in seconds = n_action_steps / dataset_fps
```

它必须满足 `1 <= n_action_steps <= chunk_size`。值越小，策略越频繁地吸收新 observation，
但推理频率也越高；值越大，查询频率越低，却要在重新观察前连续执行更多动作。延迟与
反馈之间的取舍最终要在 L12 中测量。

### batch size 与显存

batch size 决定有多少样本共同参与一次优化器更新。更大的 batch 通常需要更多激活
显存，并可能提高吞吐量；它也会改变梯度噪声。准确的显存需求取决于策略、图像数量与
分辨率、可训练模块、精度以及 GPU 上的其他进程。

如果其他配置都有效但运行超出显存，先确认实际使用的 device 和当前 GPU 占用，再减小
`--batch-size`。不要悄悄修改策略架构或动作时域后，仍把它称为同一个实验。

### steps 不等于 episode 数，也不等于收敛

`--steps` 计算优化器更新次数。它不是演示数据条数，不是 epoch 数，更不能作为收敛
证据。数据集 frame/episode 数、batch size、steps、seed 和 checkpoint 保存频率应当
一起记录。20,000 或 200,000 之类的值只是需要针对具体运行给出理由的预算，并不是
能够保证质量的“论文级参数”。

### seed 与确定性

wrapper 会记录一个 seed，供训练器管理的模型初始化和采样路径使用。复用 seed 有助于
追溯实验，但不保证在不同硬件、kernel 或依赖版本之间得到逐 bit 相同的结果。

## 项目 wrapper 保持轻量

`python -m robo_genesis.train_policy` 不会重新实现优化过程。它只负责解析课程路径，
再将一组精简、可审查的接口翻译为 LeRobot 训练器参数。

wrapper 当前控制：

- `act` 或 `smolvla` preset；
- 逻辑 repo ID 与本地 dataset root；
- job name 与 output directory；
- steps、batch size、checkpoint/log frequency、workers、seed 和 device；
- 默认使用 PyAV 作为视频后端；
- 可选的 W&B 与 Hub 发布，两者默认关闭；
- SmolVLA 的相机键重命名，以及可选的固定版本本地 base/VLM snapshot。

独立的 `--` 之后的参数会被继续传给 `lerobot-train`，例如：

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id genesis/fruit_pick \
  --dataset-root datasets/fruit_pick \
  --dry-run -- \
  --policy.chunk_size=40 \
  --policy.n_action_steps=10 \
  --policy.optimizer_lr=1e-5
```

参数转发很强大，也很容易被误用。每一项覆盖都必须写入运行记录；藏在命令行里的改动
同样意味着实验已经改变。

## 分配 GPU 之前

### 安装并识别真实运行环境

完整课程环境从锁文件安装：

```sh
uv sync --locked --all-extras
```

这份跨平台依赖解析本身并不会安装或验证课程使用的 AMD ROCm wheels。参考 AMD 环境
应遵循[兼容性矩阵](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)。

至少记录：

- Python、LeRobot 和 PyTorch 版本；
- 适用时记录 `torch.version.hip` 与 `torch.version.cuda`；
- `torch.cuda.is_available()`、可见 device 数量和实际 device 名称；
- 模型内容来自已有 cache 还是网络下载。

PyTorch 有意通过 `torch.cuda` API 暴露 ROCm device。因此在已验证的 AMD 环境中，
LeRobot 正确的 device 值仍是 `--device cuda`，而不是 `rocm`。实际 device 名称和 HIP
runtime 才是底层平台为 AMD 的证据。如果 LeRobot 回退到 CPU，这次 GPU smoke 就失败了。

### 先验证数据集，再分配模型

以下任意一项检查失败，都应在训练前停止：

- 解析后的数据集目录与 `meta/info.json` 存在；
- 能够用 `video_backend="pyav"` 读取元数据和一个样本；
- state/action 均为数值有限的 9 维 `float32`，且关节顺序一致；
- 两个预期图像键都能解码，并具有一致的尺寸；
- FPS、episode 数和 frame 数均为正；
- 样本能够解析出非空 task 文本。

这个顺序可以把数据问题与模型或 GPU 问题分开，也避免在发现相机字段缺失之前就进行
昂贵的模型下载。

### 锁定 SmolVLA 模型内容

Hub 仓库名指向的内容可能变化。已验证的参考内容为：

| 仓库 | 已验证 revision |
|---|---|
| `lerobot/smolvla_base` | `c83c3163b8ca9b7e67c509fffd9121e66cb96205` |
| `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` | `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |

在需要复现的运行开始前，应把两个仓库都解析到上述 commit，或使用一份记录了这些来源
的预先准备好的本地 snapshot。当前 wrapper 默认的裸 `lerobot/smolvla_base` 便于探索
命令，却不能单独冻结模型内容。命中 cache 也不能证明全新 cache 下的下载路径经过验证。

若要进行可审计的本地运行，通过 `--policy-path` 传入 base snapshot，并通过
`--smolvla-vlm-path` 传入 VLM snapshot。wrapper 接受 Hugging Face 中精确的
`snapshots/<40 位十六进制 commit>` 目录，或带 `robo_genesis_snapshot.json` 来源记录的
复制目录。它会在本地核验两个 revision 和必要文件，再把 VLM 目录作为
`policy.vlm_model_name` 传给 LeRobot；审计过程不会下载模型。

## 第一级实验：审计两个 dry-run 命令

选择你在前面课程中生成并检查过的数据集：

```sh
RG101_REPO_ID=genesis/fruit_pick
RG101_DATASET_ROOT=datasets/fruit_pick
```

先让 wrapper 打印 ACT 命令：

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-act-dry-run \
  --output-dir outputs/train/l11-act-dry-run \
  --steps 1 --save-freq 1 --log-freq 1 --num-workers 0 \
  --seed 1000 --device cuda --video-backend pyav \
  --dry-run
```

再打印 SmolVLA 命令：

```sh
uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-smolvla-dry-run \
  --output-dir outputs/train/l11-smolvla-dry-run \
  --steps 1 --save-freq 1 --log-freq 1 --num-workers 0 \
  --seed 1000 --device cuda --video-backend pyav \
  --dry-run
```

不要只看退出码是否为零，还要审计最终生成的命令：

| 检查项 | ACT | SmolVLA |
|---|---|---|
| 策略选择器 | `--policy.type=act` | `--policy.path=lerobot/smolvla_base` |
| wrapper 默认 batch | `--batch_size=8` | `--batch_size=4` |
| 数据 | 解析后的 ID/root 与 PyAV | 相同 |
| device | `--policy.device=cuda` | 相同 |
| 外部发布 | Hub 和 W&B 均为 false | 相同 |
| 相机映射 | 无 | 将 `world/wrist` 映射为 `camera1/camera2` 的 JSON |

dry-run 不会打开数据集、加载策略、分配 GPU tensor 或写入 checkpoint。在这个证据
等级上，不要把结果称为“training smoke”。

## 第二级实验：每种策略真实运行一步

只有环境、数据和模型内容门禁全部通过后，才能运行以下命令。两个策略应使用不同的
输出目录，避免相互覆盖。

### 仅验证 ACT 管线的 smoke

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-act-smoke \
  --output-dir outputs/train/l11-act-smoke \
  --steps 1 --batch-size 1 --save-freq 1 --log-freq 1 \
  --num-workers 0 --seed 1000 --device cuda --video-backend pyav -- \
  --policy.pretrained_backbone_weights=null \
  --policy.chunk_size=10 \
  --policy.n_action_steps=10 \
  --policy.dim_model=64 \
  --policy.n_heads=4 \
  --policy.dim_feedforward=128 \
  --policy.n_encoder_layers=1 \
  --policy.n_decoder_layers=1 \
  --policy.n_vae_encoder_layers=1 \
  --policy.latent_dim=8
```

这些架构缩减只用于以较低成本验证整条管线。该 checkpoint 必须标记为
`pipeline-only`，不能作为任务评估中的 ACT baseline。

### SmolVLA 微调 smoke

让两个策略组件分别指向 revision 门禁阶段准备好的本地 snapshot。请把
`/path/to/huggingface/hub` 替换为你机器上的 cache 根目录：

```sh
RG101_SMOLVLA_BASE_SNAPSHOT=/path/to/huggingface/hub/models--lerobot--smolvla_base/snapshots/c83c3163b8ca9b7e67c509fffd9121e66cb96205
RG101_SMOLVLA_VLM_SNAPSHOT=/path/to/huggingface/hub/models--HuggingFaceTB--SmolVLM2-500M-Video-Instruct/snapshots/7b375e1b73b11138ff12fe22c8f2822d8fe03467

uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --policy-path "$RG101_SMOLVLA_BASE_SNAPSHOT" \
  --smolvla-vlm-path "$RG101_SMOLVLA_VLM_SNAPSHOT" \
  --name l11-smolvla-smoke \
  --output-dir outputs/train/l11-smolvla-smoke \
  --steps 1 --batch-size 1 --save-freq 1 --log-freq 1 \
  --num-workers 0 --seed 1000 --device cuda --video-backend pyav
```

模型 snapshot 属于本地生成内容，不得提交。wrapper 不会接受一个仅仅看起来像 revision
的目录名：它要求精确 cache 路径或匹配的来源记录，并核验两个完整 commit ID。使用
`--policy-path` 不会关闭 SmolVLA preset 中的相机键重命名。

### 通过单步 smoke 应包含哪些证据

两种策略都应记录以下内容，不要把它们硬编码成固定结果：

- 完整命令和返回码；
- 实际 GPU 身份和软件版本；
- 数据集 episode/frame/FPS，以及一个样本的特征检查；
- 适用时记录解析后的模型 revision；
- 有限的 loss 与有限的 gradient norm；
- 一个优化器步骤已经完成的证据；
- 数字命名的 checkpoint 目录以及 `last` 指向；
- 本次运行观察到的耗时和峰值显存；
- 所有未运行项，尤其是长时间训练与闭环评估。

不要要求一个固定的 loss、gradient norm、耗时或显存数值。这些量会随环境和样本变化。
只有一个日志点时，也没有 loss 趋势可画。

## 把 checkpoint 当作完整软件包检查

LeRobot 会写入以数字步骤命名的目录，并更新 `last`，使其指向最新 checkpoint：

```text
outputs/train/l11-act-smoke/
└── checkpoints/
    ├── 000001/
    │   └── pretrained_model/
    │       ├── config.json
    │       ├── train_config.json
    │       ├── model.safetensors
    │       ├── policy_preprocessor.json
    │       ├── policy_postprocessor.json
    │       └── processor state files required by those JSON configs
    └── last -> 000001
```

SmolVLA 中各文件承担的角色相同，但 processor state 文件名可能不同。应验证文件角色和
引用关系，而不要假设某个带编号的文件名是跨策略通用 API。

至少检查：

- `model.safetensors` 存在且非空；
- `config.json` 记录了预期的策略类型、chunk、执行步数和 9 维 action 输出；
- `train_config.json` 记录了数据集身份、seed、output 和训练选项；
- preprocessor 与 postprocessor 配置引用的必要 state 文件均存在；
- SmolVLA 在训练配置和 rename processor 中都记录了准确的相机键重命名。

数字目录是可持久保留的证据，`last` 只是一个方便访问的指针。不要只检查字符串路径
存在，还要确认它确实解析到那个数字 checkpoint。

## 在真实样本上重新加载

下一项检查使用 `robo_genesis.eval_policy.load_policy()`，并传入训练时相同的 repo ID
和本地数据集元数据。加载器会重建策略及其 pre/postprocessors；对于 SmolVLA，还会从
`train_config.json` 恢复相机映射。

两个策略都使用同一个真实数据样本。探针必须报告：

```text
policy type
actual device
raw image keys
task text present (SmolVLA)
action shape: (9,)
action dtype: float32
all action values finite: true
```

数据集样本中解码后的图像可能需要转换回项目推理 helper 所期望的原始 HWC observation
格式。请在配套 notebook 中明确完成并断言这项转换。不要为了让调用返回就用随机 tensor
替代真实样本。

这仍然只是一个**开环单样本探针（open-loop single-sample probe）**：它不会构建
Genesis 场景、应用动作、观察下一时刻状态或检查任务是否成功。

## 第三级实验：先设计完整运行，再开始训练

完整训练是课后作业，需要学员主动选择执行，不能因为 notebook 从头运行到尾就自动
启动。开始前先填写运行记录：

| 决策 | 启动前记录 |
|---|---|
| 数据 | repo ID、本地 root、产物/版本、episodes、frames、FPS、域随机化来源 |
| 初始化 | 策略类型或锁定的 base/VLM revisions；ACT backbone weight 选择 |
| 时域 | 明确的 `chunk_size` 与 `n_action_steps`，以及按数据集 FPS 换算的时长 |
| 优化 | steps、batch、学习率覆盖、seed、workers、log/save frequency |
| 资源 | 实际 GPU/软件、空闲显存、模型 cache、输出存储空间 |
| 评估交接 | 数字 checkpoint 路径，以及接收它的 L12 协议 |

选定数值后，一条完整 ACT 命令具有以下形式：

```sh
# Set every ALL_CAPS value from the run record before executing.
RG101_ACT_STEPS=CHOOSE_INTEGER
RG101_ACT_BATCH=CHOOSE_INTEGER
RG101_ACT_CHUNK=CHOOSE_INTEGER
RG101_ACT_EXECUTION_STEPS=CHOOSE_INTEGER
RG101_ACT_LR=CHOOSE_FLOAT
RG101_ACT_BACKBONE_WEIGHTS=CHOOSE_IMAGENET_IDENTIFIER_OR_NULL
RG101_SAVE_FREQ=CHOOSE_INTEGER
RG101_LOG_FREQ=CHOOSE_INTEGER
RG101_SEED=CHOOSE_INTEGER

uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name act-fruit-pick \
  --output-dir outputs/train/act-fruit-pick \
  --steps "$RG101_ACT_STEPS" \
  --batch-size "$RG101_ACT_BATCH" \
  --save-freq "$RG101_SAVE_FREQ" \
  --log-freq "$RG101_LOG_FREQ" \
  --num-workers 4 --seed "$RG101_SEED" \
  --device cuda --video-backend pyav -- \
  --policy.pretrained_backbone_weights="$RG101_ACT_BACKBONE_WEIGHTS" \
  --policy.chunk_size="$RG101_ACT_CHUNK" \
  --policy.n_action_steps="$RG101_ACT_EXECUTION_STEPS" \
  --policy.optimizer_lr="$RG101_ACT_LR"
```

对应的 SmolVLA 模板使用锁定的 snapshot，并记录其微调边界：

```sh
# Set every ALL_CAPS value from the run record before executing.
RG101_SMOLVLA_BASE_SNAPSHOT=CHOOSE_PINNED_BASE_SNAPSHOT
RG101_SMOLVLA_VLM_SNAPSHOT=CHOOSE_PINNED_VLM_SNAPSHOT
RG101_SMOLVLA_STEPS=CHOOSE_INTEGER
RG101_SMOLVLA_BATCH=CHOOSE_INTEGER
RG101_SMOLVLA_CHUNK=CHOOSE_INTEGER
RG101_SMOLVLA_EXECUTION_STEPS=CHOOSE_INTEGER
RG101_SMOLVLA_LR=CHOOSE_FLOAT
RG101_SMOLVLA_FREEZE_VISION=CHOOSE_TRUE_OR_FALSE
RG101_SMOLVLA_TRAIN_EXPERT_ONLY=CHOOSE_TRUE_OR_FALSE
RG101_SMOLVLA_TRAIN_STATE_PROJ=CHOOSE_TRUE_OR_FALSE
RG101_SAVE_FREQ=CHOOSE_INTEGER
RG101_LOG_FREQ=CHOOSE_INTEGER
RG101_SEED=CHOOSE_INTEGER

uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --policy-path "$RG101_SMOLVLA_BASE_SNAPSHOT" \
  --smolvla-vlm-path "$RG101_SMOLVLA_VLM_SNAPSHOT" \
  --name smolvla-fruit-pick \
  --output-dir outputs/train/smolvla-fruit-pick \
  --steps "$RG101_SMOLVLA_STEPS" \
  --batch-size "$RG101_SMOLVLA_BATCH" \
  --save-freq "$RG101_SAVE_FREQ" \
  --log-freq "$RG101_LOG_FREQ" \
  --num-workers 4 --seed "$RG101_SEED" \
  --device cuda --video-backend pyav -- \
  --policy.chunk_size="$RG101_SMOLVLA_CHUNK" \
  --policy.n_action_steps="$RG101_SMOLVLA_EXECUTION_STEPS" \
  --policy.optimizer_lr="$RG101_SMOLVLA_LR" \
  --policy.freeze_vision_encoder="$RG101_SMOLVLA_FREEZE_VISION" \
  --policy.train_expert_only="$RG101_SMOLVLA_TRAIN_EXPERT_ONLY" \
  --policy.train_state_proj="$RG101_SMOLVLA_TRAIN_STATE_PROJ"
```

`CHOOSE_...` 值是有意设置的停止标记，不是推荐参数；只有替换它们之后训练 CLI 才会
接受命令。对于 ACT backbone，应记录准确的 torchvision weight 标识符或 `null`；
对于三个 SmolVLA 布尔量，应明确记录预期的微调边界。这样可以防止把全课程通用常量
或隐藏默认值误当成在所有情形下都充分的配置。若长时间任务没有运行，就写明
**未运行**；不要编造曲线、耗时、显存用量或 checkpoint 质量。

没有训练硬件的学员仍可完成概念检查、数据门禁和 dry-run。如果课程将来发布带版本的
checkpoint，它可以作为 L12 的输入，但在对应元数据和下载说明可用之前，不能假设该
产物存在。使用课程提供的产物时，必须报告为“使用提供的产物”，不能声称自己完成了
L11 GPU 训练实验。

## 分层诊断故障

### 运行意外使用了 CPU

在检查模型代码之前，先检查 PyTorch 与 LeRobot 版本、`torch.cuda.is_available()`、
可见 device 数、实际 device 名称和 HIP/CUDA runtime。在多 GPU AMD 主机上，应遵循
兼容性矩阵中的可见性规则。如果 LeRobot 先给出警告、随后转到 CPU 执行，这次 GPU
smoke 应判为失败，而不是“成功回退”。

### SmolVLA 无法离线加载

确认两个模型 revision，并检查当前进程可见的 Hugging Face cache 是否包含对应内容。
修改 `XDG_CACHE_HOME` 可能会隐藏原本有效的模型 cache；反过来，在旧 cache 中找到文件
也不能证明记录的 revision 正确，或全新下载路径可用。

### 数据集无法解码视频

检查本地 root、`meta/info.json`、视频元数据和 `--video-backend pyav`。
`torchcodec`/FFmpeg 共享库错误属于另一条解码路径，不要把它误诊为策略架构问题。

### SmolVLA 报告缺少相机特征

先在生成的命令中检查 `--rename_map`，再检查保存的 `train_config.json` 和 rename
processor。原始数据集键应保持为 `world/wrist`；不要重命名文件，也不要另加一份与
训练冲突的评估专用映射。

### 训练超出显存

先确认使用了预期 GPU 且没有其他竞争进程，再减小 batch size。如果 ACT smoke 失败，
还要确认缩小模型的全部覆盖项确实在 `--` 之后被转发。悄悄改变架构、精度或可训练模块
后，不能再声称两个实验等价。

### loss 或梯度出现非有限值

回到第一个真实样本和数据集统计，检查数值有限性、归一化、task/image 对齐、学习率
覆盖以及可选的混合精度。保留首次失败的步骤和真实日志，不要用编造的预期值替换它们。

### 没有生成 checkpoint

检查子进程返回码、输出目录、`steps`、`save_freq` 和可用存储空间。仅仅创建了运行目录，
不能证明 `model.safetensors` 已经写入。

### 重新加载时报告特征不匹配

同时使用训练数据集元数据、数字 checkpoint 目录和保存的 processors。对于 SmolVLA，
还要验证持久化保存的相机键重命名。对两种模型，都应先检查 9 维 action 合同，再怀疑 GPU。

### 动作数值有限，但抓取仍然失败

这说明重新加载探针已经通过，同时也走到了它的证据边界。接下来应进入 L12 的闭环诊断：
检查 observation 时序、执行时域、控制应用、任务判据、seed 和分布划分。

## 检查题与练习

### 概念检查

1. 为什么 ACT 的 CVAE encoder 可以在训练时使用演示数据中的未来动作，却不能在推理时
   使用它？
2. 在 10 FPS 下，`chunk_size=40`、`n_action_steps=8` 分别对应多长的预测时域和重新
   规划间隔？
3. 为什么减小 `n_action_steps` 不会把 ACT 训练目标从 40 个动作缩短？
4. 为什么更低的 ACT loss 不能证明 ACT 优于 SmolVLA？
5. 哪些文件可以证明 SmolVLA 的相机键重命名在重新加载 checkpoint 后仍然存在？
6. 为什么在 ROCm 机器上 `device=cuda` 可能是正确设置？哪些证据可以说明实际 device
   是 AMD GPU？
7. 即使策略没有学到任何有用的抓取行为，单步 smoke 中的哪些检查仍可能通过？

### 命令审计练习

使用你自己的数据集 root 生成两个 dry-run 命令。把最终训练器的每个参数标记为以下
类别之一：

- 数据集身份与解码；
- 策略初始化；
- 优化预算；
- 输出/日志；
- device/runtime；
- 预处理兼容性。

然后从复制的命令中删除 SmolVLA 相机键重命名，**不要实际运行训练**，并解释哪些原始
特征名与规范特征名将不再对应。

### 实验设计练习

编写两份只在 `n_action_steps` 上不同的运行记录，保持数据集、checkpoint、`chunk_size`、
seed 集合和 L12 协议不变。预测重新规划频率与推理成本之间的取舍，但不要预测成功率
数值；该数值必须来自后续 rollout。

### 产物审计练习

给定一个数字 checkpoint 目录，编写一份简短报告，包含：

- 策略类型与初始化来源；
- 数据集 ID/root 与 seed；
- chunk 时域与执行时域；
- 预期原始相机键及任何重命名；
- 已存在的权重文件和 processor 文件；
- 单样本 action 的 shape/dtype/有限性；
- 对该产物所能做出的最强合理结论。

## 总结并衔接 L12

- 两种策略都消费相同的双视角、9 维 state/action 课程数据集，但内部预处理与训练目标
  不同；
- ACT 使用仅在训练时出现的 CVAE encoder 和 Transformer 来重建动作块；当前 preset
  仍可能使用预训练视觉主干权重；
- SmolVLA 让动作专家以视觉、语言和状态为条件，再通过流匹配从噪声生成动作块；
- `chunk_size` 定义预测目标，`n_action_steps` 定义重新规划前会消费其中多少动作；
- dry-run、单步 smoke、重新加载 checkpoint 和一次开环动作是四个不同证据等级；
- 为了实现可复现，模型 revisions、相机键重命名、pre/postprocessors、数据身份和数字
  checkpoint 必须一起传递；
- 完整训练是一项明确记录、主动执行的课后实验，固定 steps 数并不能普遍保证质量。

L12 会把其中一个 checkpoint 加载到 Genesis 控制循环中，随时间执行它的动作，在多次
带 seed 的 episode 上评估任务判据，并报告带不确定性的成功次数。只有到那时，策略质量
才会成为一项闭环结论。

## 参考来源

- [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)
  — ACT 论文；action chunking、CVAE 建模和 temporal ensembling 的来源。
- [ACT 官方实现](https://github.com/tonyzhaozh/act) — 与论文配套的参考实现。
- [SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics](https://arxiv.org/abs/2506.01844)
  — SmolVLA 论文及其架构说明。
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) —
  SmolVLA 所用条件流匹配目标的背景资料。
- [LeRobot 0.6.0 ACT 源码](https://github.com/huggingface/lerobot/tree/v0.6.0/src/lerobot/policies/act)
  和 [SmolVLA 源码](https://github.com/huggingface/lerobot/tree/v0.6.0/src/lerobot/policies/smolvla)
  — 本讲所述配置默认值、loss、动作队列、保存的 processors 和采样行为的实现依据。
- [已验证 revision 的 `lerobot/smolvla_base`](https://huggingface.co/lerobot/smolvla_base/tree/c83c3163b8ca9b7e67c509fffd9121e66cb96205)
  和[已验证 revision 的 `SmolVLM2-500M-Video-Instruct`](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct/tree/7b375e1b73b11138ff12fe22c8f2822d8fe03467)
  — 参考兼容性运行所使用的模型内容。
- [PyTorch HIP 语义](https://docs.pytorch.org/docs/stable/notes/hip.html)
  — 关于 ROCm 共用 `torch.cuda` 接口的官方说明。
- [RoboGenesis 101 训练 wrapper](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/train_policy.py)、
  [策略加载器](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/eval_policy.py)
  和[兼容性记录](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
  — 本讲所采用的项目接口与验证边界。
