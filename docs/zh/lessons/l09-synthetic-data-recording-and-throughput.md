---
lesson: L09
slug: synthetic-data-recording-and-throughput
locale: zh
title: "合成数据录制与采数吞吐"
duration_minutes: 120
hardware: gpu-recommended
status: planned
---

# L09 · 合成数据录制与采数吞吐

> **课程状态：** L09 目前仍为 `planned`。中文讲义正在 review；双语 notebook 与约定的
> 运行矩阵尚未完成验证。

## 从一次成功 rollout 到一份可信数据集

[L08](./l08-demonstration-acquisition-and-scripted-experts.md) 已经构建了七阶段
banana-to-bowl 专家，并接入能够观察 commanded action 与 measured robot state 的 per-step
hook。到目前为止，这些值只存在于内存中。L09 要回答四个问题，把同一条 rollout 转换成
可持久化的数据集：

1. 每个 action 应该与哪一时刻的 observation 配对？
2. 100 Hz 控制循环中的哪些 step 应该成为 dataset frame？
3. 一次尝试在什么条件下才能成为已提交的 episode？
4. 怎样证明结果可以重新读取，同时不夸大采数吞吐或策略质量？

核心管线如下：

```text
L08 task + expert + per-step hook + success predicate
  → 对齐 observation_t 与 action_t
  → 按 dataset FPS 对 100 Hz 控制循环采样
  → 缓存一次完整 attempt
  → 只提交通过验收的 episode
  → finalize 并重新打开 LeRobot dataset
  → 检查 boundary、数值和同步相机帧
```

这是一节数据录制课，不是策略训练课。[L10](./l10-dataset-anatomy-and-imitation-learning.md)
会进一步拆解数据表示，并介绍模仿学习中的 sample 语义；L11 会通过域随机化改变数据分布，
L12 则会训练策略。本讲的目标更聚焦：得到一份规模很小、但时间语义和事务语义都经得起
检查的录制结果。

开始之前，你应该能够：

- 运行 L08 的 `TaskSpec("011_banana", "024_bowl")` 脚本化专家；
- 区分脚本化专家发出的 9 维关节目标（commanded action）与机器人实际测得的关节位置
  （`qpos`）；
- 解释为什么 world/wrist camera 是 observation，而不是任务成功判据；
- 在 release 和 settle 后使用 banana-in-bowl success predicate；
- 区分 unbatched scene 与 L06 引入的 leading environment dimension。

### 精简的 120 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–15 分钟 | Frame、attempt 与 episode boundary | 指出记录从何时开始、何时可以提交 |
| 15–35 分钟 | `observation_t`、`action_t` 与 transition | 标出 capture、command 和 step 的准确顺序 |
| 35–50 分钟 | 从 100 Hz control 到 5/30 FPS | 推导 capture index，并区分物理间隔与逻辑 timestamp |
| 50–65 分钟 | User feature、自动字段与 action 语义 | 说明每个 shape、名称顺序和字段所有权 |
| 65–90 分钟 | 录制两个通过验收的 episode | 保存两条完整 episode，并丢弃失败 attempt |
| 90–105 分钟 | Finalize 并用 PyAV 回读 | 检查 index、timestamp、tensor、task text 与两路视频 |
| 105–115 分钟 | Timeline、command/state 曲线与同步 montage | 用数值和视觉证据解释一条已持久化 episode |
| 115–120 分钟 | 吞吐边界与单变量练习 | 区分 dataset FPS、batching 与实测 wall-clock throughput |

## 学习目标

完成 L09 后，你应该能够：

1. 说清机器人学习数据集记录了哪些信息——机器人状态、专家动作、任务和相机观测——以及
   为什么观测与动作必须来自同一时刻；
2. 把 L08 的成功专家示范录制成一份小型、完整的 LeRobot 数据集；
3. 重新打开已保存的数据集，借助磁盘文件、曲线和相机画面检查各个回合是否按预期记录；
4. 说明记录频率和采集方式会怎样影响数据量，以及收集更多示范所需的时间。

## 一个对齐 frame 与一个 episode transaction

这里有两个发生在不同尺度上的正确性边界。在一个 control step 内，state、camera 与 action
必须描述同一个决策时刻；在一次 attempt 内，任务结果尚未确定之前，任何 frame 都不应成为
正式训练 episode。

![在每个控制 step 内，当前状态与两路相机画面在仿真推进前同当前动作配对；在一次尝试内，episode-local buffer 只有成功后才会提交，失败则整体丢弃，最终通过 finalize 关闭数据集。](/diagrams/l09-alignment-and-episode-transaction-zh.svg)

*课程自制示意图。上半部分定义时间对齐，下半部分定义本课程使用的 success-gated episode
transaction。*

混淆这两个边界会造成不同的错误。即使每个 episode 文件都合法，错开一帧也可能让模型
悄悄学习“错误状态下的动作”；缺少事务边界，则可能让半次 attempt 混入一份原本对齐的
数据集。

## 在推进模拟器前对齐 observation 与 action

### Recorder 在模拟器推进前运行

本讲把“应用 action 后，模拟器从当前 state 变到下一个 state 的过程”称为
**transition（状态转移）**。L08 的脚本化专家先计算 command，再调用
`recorder.on_step(action)`，随后发送 command、推进模拟器，并更新 wrist camera pose：

```text
当前 simulator state 与当前 camera pose
  → 计算 action_t
  → recorder.on_step(action_t)
      ├── 读取 measured q_t
      ├── 渲染 world_t
      ├── 渲染 wrist_t
      └── 保留 commanded target a_t
  → 向 arm 和 fingers 发送 a_t
  → scene.step()
  → update_wrist_cam()
  → 为下一次 callback 准备好 observation_{t+1}
```

因此监督学习中的配对是

```text
(observation_t, action_t),
```

而不是 `(observation_{t+1}, action_t)`。Observation 表示专家选择或暴露 `action_t` 时能够
看到的信息；该 command 引发的 transition 才产生下一条 observation。

这项约定与 L08 的 trace 一致。持久化 recorder 会增加两路 camera image 和一次采样决定，
但不能把 hook 移到 `scene.step()` 的另一侧。

### 所有记录字段共用一次采样决定

当一个 control step 被保留时，recorder 应同时保留：

```text
measured q_t
commanded target a_t
world RGB_t
wrist RGB_t
task text
```

整组数据只使用一次“保留或跳过”的决定。如果保留一个 control step，就同时保存它的
state、action 和两路相机图像；如果跳过，就全部不保存。不要让每个字段使用自己的采样
计数器，也不要在渲染 world 与 wrist 之间推进 scene。数组长度相同，并不能证明分别采样的
值已经对齐；它只能说明各字段的样本数量相同，不能说明相同行号的数据来自同一个
control step。

::: warning Shape 正确的数据集仍可能错开一帧
把 `state_{t+1}` 与 `action_t` 配对，往往仍能得到 shape 完美、数值 finite、曲线看似合理的
数组。只有检查 control-loop 顺序，才能发现这类语义错误。请记录 callback index，并把
capture、state、action 和两路 image 放在同一个分支中。
:::

## 在不虚构时间的前提下采样 100 Hz 控制器

### Control rate 与 dataset rate 职责不同

当前 scene 使用 `dt = 0.01 s`，因此专家按 100 Hz 的频率向 recorder 暴露 control-step
callback。数据集不需要保留每一次 callback。若目标速率为 `f` FPS，则理想间隔为：

```text
control_steps_per_frame = 100 / f.
```

5 FPS 恰好对应 20 个 control steps；30 FPS 则约为 3.333，无法直接成为一个可执行的整数
step 间隔。始终每 3 步采一次会得到约 33.3 FPS，始终每 4 步采一次则只有 25 FPS。

### 使用 recorder 的分数累加器

`EpisodeRecorder` 用一个持续累加的数值，把非整数间隔转换成整数 step 上的采样决定。
它先预载一个完整间隔以保留第一次 callback，之后每次 callback 都加 `1`：

```python
control_fps = 100  # Example: 100 control steps per simulated second
dataset_fps = 30   # Example: retain 30 dataset frames per simulated second
steps_per_frame = control_fps / dataset_fps
accum = steps_per_frame

for control_step in range(total_control_steps):
    accum += 1.0
    if accum < steps_per_frame:
        continue
    accum -= steps_per_frame
    capture(control_step)
```

这与源码中 recorder 的更新顺序相同。对于 100 次 callback，它会得到：

| Dataset rate | 起始 capture index | Gap pattern | 保留数量 |
|---:|---|---|---:|
| 5 FPS | `0, 19, 39, 59, 79, 99` | 第一次为 `19`，之后为 `20` | 6 |
| 30 FPS | `0, 3, 6, 10, 13, ...` | `3` 和 `4` | 30 |

5 FPS 多出的一个样本来自两点：第一次 callback 被保留，最后又恰好在 callback 99 达到
阈值。Episode 越长，平均采样率越接近目标值。每次 attempt 开始时，
`EpisodeRecorder.reset()` 都会恢复预载的累加器，不会沿用上一次 attempt 的采样进度。

### Logical timestamp 不等于准确的物理 step 时间

LeRobot 0.6.0 会分配 episode-local `frame_index`，并计算：

```text
timestamp = frame_index / dataset_fps.
```

在 30 FPS 下，logical timestamp 依次为 `0`、`0.0333...`、`0.0666...`。对应的 simulator
callback 可能位于 index `0`、`3`、`6`、`10`，实际物理间隔依次为 30、30、40 ms。
Logical timeline 是均匀的，而整数 step 上的采样间隔会交替变化。

这些时间量都有用，但回答的问题不同：

| 时间量 | 含义 | 默认 schema 是否存储？ |
|---|---|---|
| Control-step index | 哪个 simulator callback 会被保留 | 只在采样练习中计算 |
| 物理仿真时间 | `control_step / control_fps` | 可由计算出的 index 推导 |
| LeRobot timestamp | 均匀的 episode 时间，即 `frame_index / dataset_fps` | 是 |
| Wall-clock time | 机器完成模拟、渲染、编码与写入所花的时间 | 单独测量 |

Notebook 会用相同的累加逻辑计算预期 capture index，但不会把它写入数据集或作为 policy
input。不要把 LeRobot logical timestamp 称为 wall-clock measurement，也不要把平均
`3.333` gap 当成一个固定的 simulator step 数。

## 写入前先定义 frame schema

### 四项声明的 feature 与一个必需 task 字符串

录制 schema 包含四项 user-declared feature：

| Key | Writer 输入 | 含义 |
|---|---|---|
| `observation.state` | `float32`，shape `(9,)` | Callback 时实测的 7 arm + 2 finger qpos |
| `action` | `float32`，shape `(9,)` | 与该 observation 配对的 7 arm + 2 finger commanded position target |
| `observation.images.world` | `uint8`，shape `(120, 160, 3)`，声明为 `video` | HWC 顺序的固定 world-camera RGB |
| `observation.images.wrist` | `uint8`，shape `(120, 160, 3)`，声明为 `video` | HWC 顺序的 eye-in-hand RGB |

每次 `add_frame()` 还必须包含 `task` 字符串：

```text
pick the banana and place it in the bowl
```

在 LeRobot 0.6.0 中，`task` 是用于构建 task table 的特殊输入，并不是调用方在
`build_features()` 中声明的另一个 feature。回读时，reader 会把存储的 `task_index` 重新
解析成 task text。

Writer 接收 HWC `uint8` image。默认 reader 路径把解码后的视频返回为 channel-first
`torch.float32`，所以 `(120,160,3)` 写入合同与 `(3,120,160)` 回读合同并不矛盾。L10 会
进一步解释 reader representation 与 training sample。

### 五个 bookkeeping 字段归 LeRobot 所有

调用方不能提供以下字段：

| 自动字段 | 边界 |
|---|---|
| `frame_index` | 在每条 episode 内从零开始 |
| `timestamp` | 在每条 episode 内等于 `frame_index / fps` |
| `episode_index` | 标识已提交的 episode |
| `index` | 在所有已提交 frame 间保持全局连续 |
| `task_index` | 指向 task metadata table |

`add_frame()` 会在当前 episode buffer 中生成 `frame_index` 与 `timestamp`；`save_episode()`
分配 global `index`、填入 `episode_index`，并把 task string 映射为 `task_index`。手动提供
这些字段会混淆调用方与 writer 的所有权，因此 LeRobot frame validation 会拒绝它们。

### 保持九维关节顺序

State 与 action 都使用 `robo_genesis.record_dataset` 中的 `JOINT_NAMES`：

```text
panda_joint1 ... panda_joint7,
panda_finger_joint1, panda_finger_joint2
```

名称明确了每个维度的归属。只检查 `shape == (9,)`，无法发现两个 finger 对调或 arm/finger
顺序发生变化。

在 grasp、lift 与 transport 阶段，arm 接收 position target，两个 fingers 则通过闭合力控制。
数据集仍保存统一的 9 维 position-target action：前 7 项是 arm target，最后 2 项都是 `0.0`。
这里的 `0.0` 只是“闭合夹爪”的替代表示，既不是实际下发的 force command，也不是实测
finger position。这样可以让 action 格式与后续输出 9 维关节位置目标的 policy 保持一致。

## 把每条 episode 当作一次事务

### 先完成 attempt，再决定是否提交

在 release、retreat 与 settle 完成前，一次 attempt 的结果仍未知。因此，课程 recorder 会
先在 LeRobot writer 外部缓存采样数组：

```text
reset scene 与 EpisodeRecorder
  → 运行完整 scripted attempt
  → 执行 check_success()
      ├── success + 非空 buffer
      │     → 对每个 buffered frame 调用 dataset.add_frame(...)
      │     → dataset.save_episode()
      └── failure
            → 丢弃 episode-local arrays
```

这一顺序很重要，因为 LeRobot 自己的 `add_frame()` 可能在 `save_episode()` 之前写入临时
camera image。课程的正常 success-only 路径会一直等到 success 成立才调用 `add_frame()`，
因此 failed attempt 根本不会进入 writer。

目标是得到两条 accepted banana-to-bowl episode，最多执行十次 attempt。如果没有得到两次
success，最终检查失败。

### Success 是 episode-level gate

在这份数据集中，`success` 表示释放后的香蕉在 settle 后满足 L08 的水平与 below-rim 两项
containment 检查。它决定整条 attempt 是否进入主数据集。

因此，success-only 数据集不会增加一个在每个已保存 row 中都为 true 的逐帧 `success`
feature。这样的字段既冗余，也无法保留 rejected attempt 在哪里、为什么失败。

### `save_episode()` 与 `finalize()` 关闭不同边界

`save_episode()` 提交当前 episode：它写入 tabular data、编码视频、更新 metadata，并重置
writer 的 episode buffer。下一条 episode 的 `frame_index=0`、`timestamp=0`，
`episode_index` 递增，而 global `index` 继续累计。

`finalize()` 则在所有 accepted episode 完成后关闭整份数据集。在 LeRobot 0.6.0 中，它会
等待尚未完成的 image/video 工作、关闭 Parquet writer 并 finalize metadata。若没有调用，
必要的 footer metadata 可能缺失，数据集也可能无效。垃圾回收提供的 safety net 不能代替
显式生命周期调用。

## 最小录制实验

### 有意缩小的参数

配套 notebook 使用：

| 设置 | 核心值 | 原因 |
|---|---:|---|
| Task | banana → bowl | 复用已经验收的 L08 task 与 predicate |
| Accepted episodes | 2 | 让 episode boundary 可观察，但不暗示足以训练 |
| Maximum attempts | 10 | 防止采集循环无限运行 |
| Dataset FPS | 5 | 在保留任务进展的同时控制编码成本 |
| Image size | `160×120` | 让双相机视频足够小，可以执行四路径验证矩阵 |
| Camera keys | world + wrist | 同时提供场景上下文与 eye-in-hand 视角 |
| RGB codec | H.264 | 当前验证路径显式使用的 codec |
| Scene batch size | `n_envs=1` | 使用已经支持的串行 recorder |

这些数值是 verification scale，不是推荐的生产数据集规模。两条成功 episode 无法证明专家
成功率、覆盖度、多样性或策略性能。

### 显式创建 writer

共享模块负责 schema helper；notebook 会在构建 writer 前直接展示其结果：

```python
from lerobot.configs.video import RGBEncoderConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from robo_genesis.record_dataset import build_features

dataset = LeRobotDataset.create(
    repo_id="local/l09_banana_demo",
    root=dataset_root,
    fps=5,
    features=build_features((160, 120)),
    robot_type="franka",
    use_videos=True,
    rgb_encoder=RGBEncoderConfig(vcodec="h264"),
)
```

逻辑 repository ID 与本地 root 是两个不同值。默认 root 是配置后的
`DATASETS_DIR / "l09_banana_demo"`；如需改变数据集位置，应在 notebook kernel 启动前设置
`ROBO_GENESIS_DATASETS_DIR`。

Notebook 还会在 kernel 启动前把 `HF_DATASETS_CACHE`、`XDG_CACHE_HOME` 和
`MPLCONFIGDIR` 指向可写的隔离位置。即使本地 dataset 有效，只要 library cache 指向
只读目录，打开过程仍然可能失败。

::: danger 保护已有数据集
如果准确的输出目录已经存在，notebook 默认停止。只有设置 `RG101_L09_OVERWRITE=1`，
才会允许替换解析后的 `l09_banana_demo` 目录。绝不能递归删除整个 datasets 目录、项目根
目录、home directory 或任何尚未解析并检查的路径。
:::

### 完成本课实验必须启用渲染

要完成 L09 实验，必须设置 `ROBO_GENESIS_RENDER=1`。它会创建两台相机、运行 scripted
attempt、写入并重新打开数据集，以及生成视觉证据。

`ROBO_GENESIS_RENDER=0` 只会对 sampling schedule、schema 和 throughput calculation 做
有限的诊断检查。它不会创建 camera、运行 recorder、写入或重新打开 dataset，也不会生成
视觉证据，因此不能完成本课实验。

## 不要相信 writer，重新打开结果

第二条 accepted episode 完成并调用 `finalize()` 后，新建 metadata 与 reader 对象：

```python
from lerobot.datasets.lerobot_dataset import (
    LeRobotDataset,
    LeRobotDatasetMetadata,
)

metadata = LeRobotDatasetMetadata(
    "local/l09_banana_demo",
    root=dataset_root,
)
recorded = LeRobotDataset(
    "local/l09_banana_demo",
    root=dataset_root,
    video_backend="pyav",
)
sample = recorded[0]
```

这是 persistence test，而不是内存 recorder 的另一种视图。回读必须证明：

- metadata 报告 5 FPS、两条 episode、一个 task，以及大于零的 total frame count；
- total frames 等于两条 accepted in-memory buffer 长度之和；
- global `index` 跨两条 episode 保持连续；
- 每条 episode 的 `frame_index` 与 `timestamp` 都从零重新开始；
- 每一 row 都满足 `timestamp == frame_index / 5`；
- state 与 action 解码为符合声明关节顺序、数值 finite 的 `(9,) torch.float32`；
- 两路 image 都通过 PyAV 解码为数值 finite 的 `(3,120,160) torch.float32` tensor；
- task text 准确解析为 banana-to-bowl 描述。

检查 `meta/`、`data/` 与 `videos/` 下的代表性路径，包括 `meta/info.json` 和
`meta/tasks.parquet`，但不要假定每条 episode 必须分别对应一个独立 Parquet 或 MP4 文件。
LeRobot 可以在保持逻辑 episode boundary 的同时对存储分片。

### 从三个角度查看一条已持久化 episode

Notebook 只使用回读后的数据展示证据：

1. **Episode timeline：** global `index`、`episode_index`、`frame_index` 与 `timestamp` 展示
   跨 episode 的连续关系和 episode 内部的重置；
2. **Command/state 曲线：** 选取一个 arm joint 和 fingers，对比 commanded target 与
   measured qpos。Arm 使用 radians、finger 使用 metres，二者放在不同 panel，避免共用纵轴
   造成误导；
3. **同步 montage：** 从同一 episode 取 start、middle、end 三个 sample，组成 2×3 的
   world/wrist 网格。每一列标题都标出相同的 episode、frame 与 timestamp。

Montage 应当非空、非全黑，能够看出任务进展，并呈现合理的 wrist viewpoint 变化。它证明
当前持久化视频能够解码并与 tabular row 对应，但不能证明演示具有足够多样性或足以训练。

## 采数吞吐是整条管线的性质

### Dataset FPS 不等于 wall-clock speed

一次串行 attempt 包含多个阶段：

```text
simulate → render two cameras → resize → buffer → encode → write metadata/data
```

降低 dataset FPS 会减少保留 frame、图像处理和编码量，却不会自动让 physics simulation
推进得更快，也不能说明每 wall-clock hour 能得到多少成功 episode。若渲染或编码成本很高，
机器生成一份 5 FPS 数据集仍可能慢于实时。

有意义的测量必须同时写清分子和分母：

```text
committed_frames / wall_clock_second
accepted_episodes / wall_clock_hour
simulated_seconds / wall_clock_second
```

记录中还要注明 backend、batch size、dataset FPS、resolution、codec、warm-up、同步方式，
以及 elapsed time 是否包含失败 attempt。

### Batched simulation 不等于完整 parallel recorder

L06 已说明 `scene.build(n_envs=B)` 会创建 B 份独立 simulator state，但这一事实不会自动
解决录制问题：

| 能力 | 必须满足什么 | 不能证明什么 |
|---|---|---|
| Serial collection | 一个环境拥有一个 sampler、buffer、success result 与 reset | 高吞吐或广覆盖 |
| Batched simulation | State/action row 保留 leading environment identity | 独立 episode commit 或已编码视频 |
| Batched rendering | Camera array 保留 environment 与 camera identity | Writer capacity 或正确的异步 reset |
| Complete parallel recording | 每个环境拥有独立 clock、buffer、outcome、reset 与 commit path；encoding queue 有界 | 在所有机器上获得固定 speedup |

对于完整 parallel recorder，environment 2 完成时不能截断 environment 0 仍在进行的 episode；
重置某一 row 时不能重置另一 row 的 sampler；camera frame 必须同时保留 camera 与 environment
identity。最后，encoder 与 storage writer 必须能够跟上 producer rate，或通过有界 queue 和
backpressure 限制生产速度，而不是无限占用内存。

V1 课程只实现单环境 recorder。`B × FPS` 是理论 frame production rate，不是实测速率提升。

## 按边界诊断失败

1. **依赖或 codec：** 确认 LeRobot 0.6.0、dataset dependencies 与 API codec 值 `h264`；
   未核对 API 合同时，不要擅自换成 `libx264` 这类 FFmpeg encoder 名称；
2. **Cache 或输出路径：** 检查准确 dataset root 与 library cache 是否可写；不要用删除无关
   数据的方式解决权限错误；
3. **Camera capture：** 确认 render 已启用、两台 camera 在 `build()` 前声明、wrist pose 在
   每个 step 后更新，并检查采集 RGB 的 shape 与 dtype；
4. **时间对齐：** 打印 callback 与 capture index，在发送配对 action 前读取 state 与两路
   image；不能靠裁掉数组首尾来掩盖 off-by-one；
5. **采样率：** 检查 control FPS、dataset FPS、初始 phase、episode reset、count 与 gap set；
   wall-clock jitter 不属于 logical frame timestamp；
6. **Episode 泄漏：** 检查 recorder reset、success gate、`save_episode()` 调用和下一条
   episode 的首帧；failed attempt 不能留下 dataset row 或 video；
7. **输出无法读取：** 确认已调用 `finalize()`，用 `video_backend="pyav"` 重新打开，并检查
   metadata、Parquet 与两个 video key，不能只确认目录存在；
8. **吞吐过低：** 先分别测量 simulation、rendering、resize、encoding 与 writing，再改变
   多个参数或宣称 batching 已经解决瓶颈。

## 检查问题与单变量练习

### 概念检查

1. 对当前 recorder hook 而言，为什么 `(state_{t+1}, action_t)` 是错误配对？
2. 为什么不能把 100/30 四舍五入为固定的三步间隔？
3. 为什么 LeRobot timestamp 可以均匀，而实际 simulator gap 仍在 3 与 4 steps 间交替？
4. 为什么可以先缓存一条完整 failed attempt，再整体丢弃而不损坏数据集？
5. `save_episode()` 与 `finalize()` 分别关闭什么边界？
6. 为什么 state、action、world RGB 与 wrist RGB 必须共用一次采样决定？
7. 为什么 `n_envs=4` 本身不能证明已有完整 parallel recorder 或四倍吞吐提升？
8. 当前 success-only 数据集能证明什么，又遗漏了哪些 failure 或 recovery 信息？

### 单变量练习：只改变 dataset FPS

保持 `control_fps=100`、rollout 长度、schema、image size 和 codec 不变，从 10、20、30 FPS
中选择一个候选速率。

计算之前，先预测：

- 可能出现的 control-step gap 集合；
- logical timestamp 间隔；
- 给定 control-step 数下保留的 frame 数；
- 保留更少 frame 时，哪些成本可能下降。

随后运行 sampling calculation，把 capture index 与预测比较。请分别报告“每 simulated second
的数据 frame 数”和“尚未测量 wall-clock throughput”，不要重新运行 Genesis，也不要从
sampling schedule 推断机器速度。

## 证据边界与 L10 衔接

两条能够读取的成功 episode 可以建立一个范围有限但很重要的结论：当前 task、recorder、
schema、video path、transaction boundary 与 reader 能够协同工作。它们不能证明：

- 专家跨 seed 的成功概率；
- 数据集多样性或覆盖度；
- 任一相机带来的因果收益；
- 数据量足以训练 ACT 或 SmolVLA；
- policy loss、open-loop accuracy 或 closed-loop success；
- sim-to-real transfer。

L10 会从本讲验证过的持久化 row 与 metadata 出发，解释 dataset anatomy、decoded sample
semantics、statistics、temporal window，以及 behavior cloning 为什么能够从
observation/action example 学习。把这些主题留到下一讲，可以让 L09 始终聚焦于生成语义
正确的记录。

## 小结

- 在 transition 前采集 measured state、两路 image 与 commanded action，让每个 row 表示
  `(observation_t, action_t)`；
- 每条 episode 使用一个确定性 sampling clock；100 Hz 到 30 FPS 需要交替的整数 gap，不能
  四舍五入成固定间隔；
- LeRobot 均匀的 `frame_index / fps` timestamp 不同于 simulator callback time 和
  wall-clock throughput；
- 声明四项 user feature，通过 `add_frame()` 提供 task text，并让 LeRobot 管理 bookkeeping
  fields；
- 缓存完整 attempt，用 task success 作为 acceptance gate，每条 accepted episode 调用一次
  `save_episode()`，采集完成后调用一次 `finalize()`；
- 重新打开数据集并解码两路 camera，再相信写入结果；
- 把 FPS、batched simulation、complete parallel recording 与实测 throughput 视为不同主张。

## 参考资料

- [LeRobot 0.6.0 `LeRobotDataset` 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/lerobot_dataset.py)
  ——固定版本的 create、readback、episode save 与 finalization 接口。
- [LeRobot 0.6.0 `DatasetWriter` 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/dataset_writer.py)
  ——固定版本的 frame index、timestamp、task mapping、episode commit、video encoding 与
  writer lifecycle。
- [LeRobot 0.6.0 feature validation 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/feature_utils.py)
  ——user feature 与自动 bookkeeping field 的所有权。
- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  ——官方 engine、camera、simulation 与 parallel-environment API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  ——本课程锁定的准确 engine 版本。
- [PyAV 文档](https://pyav.org/docs/stable/)
  ——显式 readback 路径使用的 video container 与 frame decoding library。
