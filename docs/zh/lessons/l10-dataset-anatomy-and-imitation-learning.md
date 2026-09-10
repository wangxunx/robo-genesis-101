---
lesson: L10
slug: dataset-anatomy-and-imitation-learning
locale: zh
title: "数据集解剖与模仿学习 101"
duration_minutes: 90
hardware: gpu-recommended
status: cpu-verified
---

# L10 · 数据集解剖与模仿学习 101

> **课程状态：** 双语讲义和 notebook 均已完成；英文和中文 notebook 已使用 L09 生成的同一份
> 包含两个 episode 的数据集通过 CPU-only readback，因此 L10 当前为 `cpu-verified`。本实验
> 打开本地数据，解码少量已保存帧并构造训练目标，不初始化 Genesis、不分配模型，也不启动
> 训练。课程不会隐式下载示例数据集；若本地缺少输入，请先运行 L09，或将
> `RG101_L10_DATASET_ROOT` 指向一份兼容副本。本实验不要求 GPU；`gpu-recommended` 仍作为
> 本讲在完整数据到策略工作流中的硬件标签保留。

## 本讲在课程中的位置

[L09](./l09-synthetic-data-recording-and-throughput.md) 已经把脚本化专家产生的对齐 episode
持久化到磁盘。数据集可读是必要条件，却还不足以成为一份可靠的训练输入。在选择 policy 之前，
我们还需要弄清文件各自表达什么、一条读取后的 sample 包含什么、episode 边界在哪里，以及未来
action target 如何始终留在同一个 episode 内。

```text
L09：对齐帧 + 已提交 episode + H.264/PyAV 持久化
  ↓
L10：数据集解剖 + decoded sample + statistics + episode split
     + 行为克隆目标 + action chunk
  ↓
L11：受控改变数据分布
  ↓
L12：ACT / SmolVLA 训练与 checkpoint 重载
  ↓
L13：闭环任务评估
```

L10 的输出不是训练好的模型，而是一份可审计的数据报告、一组互不重叠的 train/eval episode
ID、一条真实的行为克隆 sample，以及一个带有明确边界 mask 的未来 action chunk。

开始之前，你应该已经能够：

- 解释为什么 L09 要在仿真前进一步记录 `(observation_t, action_t)`；
- 区分 9 维关节指令目标与机器人实测状态；
- 识别固定的 `world` 视角和眼在手上的 `wrist` 视角；
- 找到 L09 创建的数据集精确目录。

### 一条聚焦的 90 分钟路线

| 时间 | 主题 | 学习产出 |
|---:|---|---|
| 0–10 分钟 | 输入身份与证据边界 | 解析唯一明确的本地数据集，并说明 L10 能证明什么 |
| 10–25 分钟 | metadata、表格数据与媒体 | 解释三层存储结构并定位逻辑 episode 边界 |
| 25–40 分钟 | raw row 与 decoded sample | 读取一条多模态 sample，区分 HWC metadata 与 CHW tensor |
| 40–52 分钟 | statistics、单位与 normalization | 诊断通道范围，不把统计量当成覆盖度证明 |
| 52–64 分钟 | episode-level train/eval split | 产出互斥 episode ID 并识别 trajectory leakage |
| 64–78 分钟 | 行为克隆与 action chunk | 构造同一 episode 内、带 padding mask 的 `(H, 9)` target |
| 78–86 分钟 | ACT 与 SmolVLA 数据合同 | 解释 task 条件和 camera-key adapter |
| 86–90 分钟 | 诊断与单变量练习 | 区分数据检查、offline loss 与 closed-loop success |

## 学习目标

完成 L10 后，你应该能够：

1. 说明录制的机器人演示如何组织成可用于模仿学习的数据集；
2. 检查一份真实数据集，并总结训练前已经验证了什么、还有哪些问题尚不能回答；
3. 解释行为克隆如何把专家演示转化为学习目标，以及为什么需要保留轨迹结构；
4. 区分离线 action 预测质量与闭环任务成功。

## 先明确证据边界

“数据集可用”这句话可能混合多种不同结论。L10 将它们逐层拆开：

| 证据 | 它能证明什么 | 它不能证明什么 |
|---|---|---|
| metadata 可以打开 | schema、计数、路径模板、task 和 episode 记录可读 | Parquet row 或视频存在且可解码 |
| 数值 row 可以打开 | state、action、timestamp 和 index 可读 | 相机流与这些 row 正确对应 |
| 两路视频可以解码 | 选中的 `world` 与 `wrist` 帧可见 | 每一帧都正确，或视角足够支持学习 |
| statistics 全部有限 | 已保存的聚合量可用于诊断和预处理 | 数据覆盖广、没有偏差或能够泛化 |
| train/eval ID 互斥 | 两侧没有共享完整 episode | 数据量足以稳定选择模型 |
| 一条 action chunk 合法 | reader 遵守目标 shape 和 episode 边界 | policy 能够学会或成功执行该 chunk |

因此，正常路径先检查 metadata，再承担视频解码成本；绘制数值 feature 时只抽取少量视觉证据，
不会为了 state/action 曲线而解码整份数据集。

## 机器人数据集不是一袋彼此独立的图像

图像分类数据通常可以把样本近似看成可交换的独立条目。这里，相邻 row 属于一次按时间排序的
物理 rollout：

```text
episode e：
  (observation_0, action_0),
  (observation_1, action_1),
  ...,
  (observation_T-1, action_T-1)
```

每条 observation 同时包含机器人实测状态、两路同步相机视角和 task 上下文，action 则是与该
决策时刻配对的专家指令。相邻帧共享场景几何、物体位置、相机内容和绝大部分轨迹历史。若把它们
当成相互独立的 row，就会丢失可靠划分和构造未来 action target 所需的结构。

## 一份 LeRobot 数据集的三层结构

把磁盘上的数据集理解为三个相互关联的层次最清楚：

| 层 | 典型内容 | 它回答的问题 |
|---|---|---|
| Metadata | `info.json`、`stats.json`、task row、episode row、路径模板 | 这是什么数据集、有哪些字段、episode 在哪里？ |
| 表格数据 | 包含 state、action、timestamp 和 index 的 Parquet 列 | 每个决策时刻有哪些数值？ |
| 媒体 | `world` 和 `wrist` 对应的 MP4 文件 | 两台相机在该时刻看到了什么？ |

精简后的目录形态如下：

```text
<dataset-root>/
├── meta/
│   ├── info.json
│   ├── stats.json
│   ├── tasks.parquet
│   └── episodes/.../*.parquet
├── data/.../*.parquet
└── videos/
    ├── observation.images.world/.../*.mp4
    └── observation.images.wrist/.../*.mp4
```

这里的省略号很重要。LeRobot 可以把多个逻辑 episode 分片保存到存储 chunk 中。Parquet 或
MP4 的 **file chunk 是存储单元**，而 **episode 是具有 index 和 timestamp 边界的任务轨迹**。
不能只看文件名推断 episode 身份，应该使用 episode metadata 和 row 中的 `episode_index`。

`LeRobotDatasetMetadata` 可以在不解码视频的情况下检查第一层；随后，`LeRobotDataset`
才会把一条表格 row、task lookup 和指定 timestamp 的视频帧组合成一条 sample。

![Metadata、Parquet row 和两路视频流在 LeRobot reader 中组合为一条解码后的行为克隆 sample；独立的 policy adapter 再执行模型特定的重命名、归一化和组 batch。](/diagrams/l10-dataset-to-sample-zh.svg)

*课程自制图。图中把持久化存储、公开 decoded sample 和模型特定预处理明确分开，而不是把它们
视作同一种表示。*

## 先确认身份与 schema，再查看数值

### 解析唯一明确的本地 root

逻辑 repository ID 和本地文件系统 root 是两个不同的身份要素。例如，
`local/l09_banana_demo` 可以描述数据集，而 `DATASETS_DIR / "l09_banana_demo"` 选择本地
哪一份副本。

配套 notebook 按以下顺序解析输入：

1. 若显式设置了 `RG101_L10_DATASET_ROOT`，优先使用它；
2. 否则使用 `DATASETS_DIR / "l09_banana_demo"`；
3. 不递归搜索其他数据集；
4. 不从 Hub 隐式下载，也不伪造 fallback 数据集。

notebook 会在构造 LeRobot reader 之前检查 `meta/info.json`，因为库本身可能在本地内容缺失时
尝试下载。提前失败可以让“路径写错”和“网络 artifact 不可用”成为两种明确不同的问题。

完成显式前置检查后，只读 metadata 的代码很简洁：

```python
from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata

metadata = LeRobotDatasetMetadata(repo_id, root=dataset_root)
print(metadata.total_episodes, metadata.total_frames, metadata.fps)
print(metadata.features)
```

第一份报告应包含解析后的 root、逻辑 repo ID、`codebase_version`、FPS、episode/frame/task
数量和 feature keys。缺少这些身份信息的结果难以复现，也很容易被错归到另一份数据集。

### 四个 user feature、五个自动字段与 task lookup

L09 声明了四个 user feature：

| Key | 存储 schema | 课程语义 |
|---|---|---|
| `observation.state` | `float32`、`(9,)` | 7 个手臂关节和 2 个手指关节的实测位置 |
| `action` | `float32`、`(9,)` | 以相同名称顺序排列的关节位置指令目标 |
| `observation.images.world` | video、`(H, W, 3)` | 固定全局视角 |
| `observation.images.wrist` | video、`(H, W, 3)` | 随手运动的眼在手上视角 |

LeRobot 负责五个 bookkeeping 字段：

| Key | 含义 |
|---|---|
| `timestamp` | episode 内的逻辑时间 |
| `frame_index` | episode 内从零开始的位置 |
| `episode_index` | 逻辑 episode 身份 |
| `index` | 跨越整份数据集的全局 row 身份 |
| `task_index` | 指向 task 表的整数引用 |

writer 在写每一帧时接收 task 文本，但表格 row 存储的是 `task_index`。读取时，LeRobot 用这个
整数查询 `meta/tasks.parquet`，再把 Python `task` 字符串加入 sample。因此，`task` 是学习者
可见 sample 的一部分，但不是第五个由用户声明的 tensor feature。

本课程的 state/action names 必须与共享的 `robo_genesis.record_dataset.JOINT_NAMES` 顺序
一致。只有 `(9,)` shape 还不够：交换两个关节仍会得到 shape 正确、语义却错误的训练目标。

## Raw row、decoded sample 与 policy input 是不同表示

同一条相机 observation 至少有三种有用表示：

| 边界 | 表示示例 | 用途 |
|---|---|---|
| Metadata | HWC 顺序的视频 shape `(120, 160, 3)` | 描述存储帧的几何形状 |
| Decoded sample | CHW 顺序的 `torch.float32` tensor `(3, 120, 160)` | 检查数据或送入数据管线 |
| Policy adapter | 已重命名/resize/normalize/组 batch 的 tensor | 满足某个 policy 的内部合同 |

HWC 与 CHW 并不矛盾，它们描述的是不同层。为了显示图像，可以先把 decoded CHW tensor
移到 CPU，再转置回 HWC；这种显示转换不能替代 policy 保存的正式 preprocessor。

这种区分也决定了高效读取方式：

- 绘制整段 episode 的 state/action 曲线时，直接读取 Parquet-backed table；
- 只有确实需要视频帧的 sample 才调用 `ds[i]`；
- 从 Hugging Face column 构造 NumPy 数组前先使用 `with_format(None)`；
- 如果返回值已经是 tensor，则使用 `value.detach().cpu().numpy()`，不要假定它位于 CPU。

若为了收集 state vector 而逐帧调用 `ds[i]`，两路视频也会在每个 index 被解码。数值结果可能
仍然正确，但这种做法隐藏了不必要的成本，也混淆了表格读取与多模态 sample 组装。

只有需要 task lookup 或图像时，才使用完整 reader：

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset(
    repo_id,
    root=dataset_root,
    episodes=[0],
    video_backend="pyav",
)
sample = dataset[0]  # joins the row, task text, and requested camera frames
```

### 读取同一时刻的两种视角

相机名称表达了各自的物理角色：

- `world` 固定不动，因此保留机器人、物体和碗之间的全局布局；
- `wrist` 随手运动，因此在接近、抓取、抬升和释放时提供局部证据。

实验会从同一个 episode 解码 start、middle 和 end 三条 sample，并组成 2×3 montage。每一列的
两台相机必须对应相同 episode、frame 和 timestamp。相比一张没有时间信息的截图，这种检查能
更好地验证同步关系和视角身份。

montage 中能看出任务进展，只能证明这些存储帧可以读取和解释；它不能证明 policy 会关注正确
视角、相机覆盖了所有失败模式，或一条 episode 已经足以训练。

::: warning 应读取实际 codec 与 backend metadata
已验证的 L09 数据集使用 H.264 视频，并通过 PyAV 重新打开。不要复制旧 slides 中的 AV1
说法，也不要混淆 codec 和 decoder backend。先检查当前数据集，再在本课程的显式读取路径上
传入 `video_backend="pyav"`。
:::

## Statistics 连接物理单位与模型坐标

`meta/stats.json` 保存 per-feature 聚合量。对于 state/action 的每个通道，当前数据格式可以
提供 `min`、`max`、`mean`、`std`、`count`，以及 `q01`、`q10`、`q50`、`q90`、
`q99` 等分位数。

这些 shape 是聚合后的 shape，不是 sample shape：

| Feature | Sample shape | 典型 statistics shape | 含义 |
|---|---:|---:|---|
| state 或 action | `(9,)` | `(9,)` | 每个关节通道一个值 |
| RGB 图像 | 解码后为 `(3,H,W)` | `(3,1,1)` | 可以沿空间维广播的 per-channel 值 |
| `count` | 不是 feature value | 聚合样本数 | 有多少数据参与了聚合 |

state/action 的前 7 个通道是以 rad 为单位的旋转手臂关节，最后 2 个是以 m 为单位的移动手指
关节。若把九个通道都画在一条没有单位说明的坐标轴上，物理上重要的手指变化可能看起来微不足道，
也会让人误以为不可比较的数值拥有相同单位。实验会把手臂与手指拆成不同 panel。

### 在训练前用 statistics 做诊断

statistics 可以暴露值得继续调查的问题：

- 非有限值意味着数值路径可能已经损坏；
- 不合理的最小值或最大值可能来自单位、顺序或录制错误；
- 接近零的标准差可能暴露静止通道或不足的任务覆盖；
- 极值与 `q01`/`q99` 相距很远，可能说明存在 outlier；
- `count` 与预期数据范围不一致，说明聚合量可能描述了另一批数据。

它们不能证明数据多样、没有偏差、与任务相关或能够泛化。一份所有数值都有限的数据集，也可能
只包含两条几乎相同的轨迹。

### Normalization 是可逆接口

不同单位会形成不同数值尺度。常见的教学示例是按通道标准化：

```text
x_norm = (x - mean) / max(std, epsilon)
x      = x_norm * std + mean
```

正向变换可以避免任意物理单位悄悄决定优化器看到的相对尺度；逆向变换同样重要，因为预测 action
最终必须恢复为控制器所需的关节目标坐标。

notebook 只会对一个手臂通道应用这条公式进行 sanity check，不会另写一套生产级 preprocessor。
在 LeRobot 0.6.0 中，policy 配置选择 normalization mode，dataset statistics 传给 policy
processor，输出 processor 再对 action 做 unnormalization。训练、checkpoint 重载和评估必须
保留同一套 processor state。

::: warning 不要直接除以极小的标准差
恒定或近似恒定的通道会让朴素 z-score 变得不稳定。应先检查该通道，并遵循 policy 的正式
processor 行为。`epsilon` 只能让课堂计算保持有限，不能补回缺失运动或修复错误数据。
:::

## 按完整 episode 划分，而不是拆分相邻 frame

假设一条 trajectory 包含 100 个相邻 frame。随机进行 80/20 row split 时，frame 40 可能进入
训练集，而 frame 41 进入评估集。这两条 sample 几乎共享相同的场景、物体位置、相机图像和历史。
此时较低的 held-out loss 部分衡量的是近重复样本上的插值，而不是在独立轨迹上的表现。这就是
**trajectory leakage**。

因此，L10 只划分完整 episode ID。在锁定的 LeRobot 0.6.0 factory 中，相关过程是：

```text
选中的 episode ID
  → 按 task 对 episode 分组
  → 每个 task 留出最后 ceil(n_task × eval_split) 个 episode
  → 使用同一 temporal-window 合同构造 train 和 eval reader
```

这条规则是确定性的，但确定性不等于有代表性。如果采集顺序与 seed、物体位置、光照或
domain-randomization schedule 相关，“最后几个 episode”可能形成系统性不同的分组。正式实验
应在采集前冻结 split rule 和采集条件，并记录精确 episode ID。

对于只有 2 个同 task episode 的 L09 数据集，使用 20% 等非零比例时会得到 1 个 train 和
1 个 eval episode。它适合演示划分机制，却远不足以支持稳定的模型选择或泛化结论。每个 task
还必须拥有足够多 episode，才能在留出数据后仍保留训练数据。

![完整 episode 被分配给训练或评估，两侧不共享 frame；未来 action window 保持在同一 episode 内，边界复制值由 action_is_pad 标记并从有效 target 中排除。](/diagrams/l10-episode-split-and-chunk-zh.svg)

*课程自制图。上半部分保护评估身份，下半部分保护 episode 末尾的时序 target。*

## 行为克隆把对齐 row 转化为监督学习

行为克隆（behavior cloning，BC）把专家演示当作监督样本。对于单步 action：

```text
observation_t = {state_t, world_t, wrist_t, optional task_t}
expert target = action_t
policy_theta(observation_t) ≈ action_t
```

写成紧凑形式：

```text
min_theta  E_(observation_t, action_t)∼D
           [ loss(policy_theta(observation_t), action_t) ]
```

L10 有意不固定 `loss` 的具体形式。ACT 与 SmolVLA 使用不同的模型结构和目标，相关机制留到
L12 解释。二者共同依赖的数据语义是：observation 和专家 target 必须对齐、有限、有序，并接受
一致的变换。

虽然优化形式看起来像监督学习，部署过程却是时序性的。数据集中的状态由专家产生，部署后的
policy 则通过自己的 action 产生未来状态。一个小误差就可能把机器人带到演示中很少出现、甚至
从未出现的 observation，随后误差还可能继续累积。这种 distribution shift 正是 training loss
或 open-loop prediction 不能取代 closed-loop evaluation 的原因。

### Offline evaluation 与 closed-loop evaluation 衡量不同内容

Offline evaluation 把 policy action 与 held-out expert action 比较，并报告 behavior-cloning
action loss 等指标。它不会在 simulator 中执行预测 action，因此 policy 既不能改变未来
observation，也无法证明自己能否从错误中恢复。

Closed-loop evaluation 在 Genesis 中逐步执行 policy。每个预测 action 都会改变机器人状态和
下一条 observation，因此误差可能累积，policy 也可能遇到专家演示之外的状态。此时它才有机会
作出反应并尝试恢复。最终结果使用 task-level success criterion 衡量，例如物体是否在 release
和 settling 后成功放入目标。

因此：

```text
held-out behavior-cloning loss ≠ closed-loop task success
offline evaluation             ≠ closed-loop evaluation
```

可靠的评估流程应先按完整 episode 或 trajectory 划分数据，避免 train/eval leakage，再使用
closed-loop rollout 衡量真实任务表现。

## 把单步 target 扩展成 action chunk

许多机器人 policy 会一次预测一段未来 action，而不只预测下一步。对于 chunk size `H`，L10
让 reader 按数据集 FPS 查询对齐 offset：

```python
H = 4
delta_timestamps = {
    "action": [i / fps for i in range(H)],
}
```

在 frame `t`，action 从 `(9,)` 变成 `(H, 9)`：

```text
[action_t, action_t+1, action_t+2, action_t+3]
```

在 5 FPS 下，4 个 sample 构成的名义四步 horizon 为 `H / fps = 0.8 s`；最后一个采样 target
距离当前帧 `(H - 1) / fps = 0.6 s`。两者相关，但不是同一个量。

### Chunk 必须停在 episode 边界

接近最后一帧时，未来 index 已不存在。LeRobot reader 会把它们 clamp 到 episode 边界，以保持
tensor shape 固定，同时返回 `action_is_pad`：

```text
最后一帧的 action rows：[a_last, a_last, a_last, a_last]
action_is_pad：         [ false,   true,   true,   true]
```

复制值只是 padding，不是新增的三条演示。训练 loss 必须忽略被标记的 row。若跨进下一个 episode
则问题更严重：模型会学到一段穿过环境 reset、物理上不可能成立的未来。

episode 中段应产生 `(4,9)` 且四个 mask entry 全为 false；最后一帧保持相同 shape，但只有第一
行有效。这两个 probe 分别检查正常情况和边界情况。

`chunk_size` 定义训练/预测 target 的长度；一次执行多少预测 action 后重新规划，则由
`n_action_steps` 决定。这是 L12 才会展开的 policy 与闭环取舍，不在本讲决定。

## 一份 raw dataset，两种面向 policy 的合同

ACT 与 SmolVLA 消费同一份课程数据集，但它们的 preprocessor 并没有完全相同的内部合同：

| 问题 | 本课程的 ACT 路径 | 本课程的 SmolVLA 路径 |
|---|---|---|
| Raw observation | state、`world` 和 `wrist` | state、`world`、`wrist` 和 task 文本 |
| 训练 target | 来自同一 episode 的 action chunk | 来自同一 episode 的 action chunk |
| Raw camera-key 处理 | 新建 ACT 配置适配 dataset keys | preset 把 key 改为预训练 base 所期待的名称 |
| Rename | 当前 from-configuration 路径无需 rename | `world → camera1`、`wrist → camera2` |
| L10 职责 | 验证字段、shape、task 可用性、chunk 和 adapter map | 相同 |
| 留给 L12 | CVAE、Transformer、KL/reconstruction loss、优化和 checkpoint | VLM/action expert、flow matching、微调和 checkpoint |

项目 preset 将 SmolVLA mapping 写成：

```json
{
  "observation.images.world": "observation.images.camera1",
  "observation.images.wrist": "observation.images.camera2"
}
```

这是 schema adapter，不是要求重命名磁盘文件。训练管线把 adapter 随 preprocessor 保存，评估
时仍然提供语义明确的 raw keys `world` 和 `wrist`。只在评估阶段临时发明另一套 mapping，会
破坏训练/checkpoint 合同。

统一 schema 或 adapter 都不意味着所有 policy 可以任意互换。模型特定的 resize、normalization、
language tokenization、padding 和 batching 仍然真实存在，必须与 checkpoint 一起保存和恢复。

## 配套实验：产出一份可审计的读取报告

应复用完成 L09 时的环境，其中已经包含所需 reader 栈。仓库的 `data` extra 声明了 LeRobot、
PyArrow 和视频依赖，但安装仍应遵循项目 README 与兼容性记录中的平台步骤。尤其不要在已验证的
AMD 环境上执行通用 PyPI sync，因为它可能替换已经锁定的 ROCm PyTorch wheels。

notebook 依次完成八项检查，每一步都产出可见证据：

1. **解析输入：** 打印精确 local root 和 repo ID；若必要文件缺失，给出直接恢复步骤并停止。
2. **审计 metadata：** 报告版本、FPS、计数、tasks、feature names、joint names、episode
   boundaries、路径模板和实际视频信息。
3. **读取一个 episode：** 对比 raw numeric row 与 decoded sample，再解码 start/middle/end
   的 `world`/`wrist` montage。
4. **检查数值：** 不解码视频地读取完整 state/action columns，把手臂 rad 与手指 m 分开，并与
   statistics 对照。
5. **规划 split：** 列出 train/eval episode IDs、task、length 和 frame totals；断言两侧非空、
   不相交且完整覆盖。
6. **构造 `H=4`：** 检查中段和最后一帧的 action chunk，并可视化 `action_is_pad`。
7. **比较 consumer：** 读取项目 ACT/SmolVLA preset 合同，但不创建任一模型。
8. **汇总证据：** 要求所有数据检查通过，同时明确报告没有产生训练、checkpoint、Genesis
   rollout 或 success rate。

预期的 L09 输入至少有 2 个非空 episode、1 个 task、5 FPS、9 维 state/action feature，以及
可解码的 `world`/`wrist` 视频。实际 episode length 和数值范围来自你的数据副本，不是应该从
本页抄写的常量。

## 按层诊断失败

1. **找不到数据集：** 打印解析后的精确 root 并检查 `meta/info.json`。先运行 L09 或设置
   `RG101_L10_DATASET_ROOT`；不要扫描随机目录，也不要静默下载另一份数据集。
2. **版本不匹配：** 对照存储的 `codebase_version` 和锁定的 LeRobot 0.6.0 reader。不要为了
   压掉兼容性错误而直接修改 metadata。
3. **Metadata 能打开但 row 失败：** 检查 data path template、episode records 和引用的
   Parquet 文件。metadata-only 成功不等于完整数据集可以读取。
4. **Row 能打开但视频失败：** 检查两路 MP4 引用路径、codec 信息和显式 PyAV backend。
5. **图像看起来转置或发暗：** 区分存储 HWC 与 decoded CHW，再检查 dtype 和数值范围，最后
   决定是否转置或缩放。
6. **数值图异常缓慢：** 确认代码读取的是 table columns，而不是在每帧调用 `ds[i]` 并解码
   两路视频。
7. **Statistics 看起来与 feature shape 不一致：** vector aggregate 应为 `(D,)`，RGB
   aggregate 应为 `(C,1,1)`，不应期待它们与完整 sample shape 相同。
8. **Eval 好得不可信：** 在解释 loss 之前，先检查 random frame split、相邻 trajectory
   leakage 和 collection-order correlation。
9. **最后一个 chunk 出现重复值：** 检查 `action_is_pad`。边界复制值必须被 mask，不能作为
   未来专家 target。
10. **SmolVLA 找不到 camera：** 对照 raw `world`/`wrist` keys 与保存或 preset 中的
    `camera1`/`camera2` rename；不要修改 dataset schema。

## 检查题与单变量练习

### 概念检查题

1. 为什么一个 Parquet 或 MP4 chunk 可以包含多个 episode 的数据？
2. 为什么 metadata 中的 HWC 和 `ds[i]` 返回的 CHW 都是正确的？
3. 为什么绘制整段 episode 的 state/action 时，不应该索引每一条 decoded sample？
4. 为什么手臂和手指曲线不应共用一条没有单位说明的数值轴？
5. random frame split 如何泄漏 trajectory 信息？
6. 为什么重复的边界 action 只有在 mask 被正确使用时才不会变成错误的未来 target？
7. 为什么当前 SmolVLA 路径需要 camera-key adapter，而当前 ACT 配置不需要？
8. 为什么 sample 可解码、action 有限和较低 offline loss 都不能证明 closed-loop success？

### 单变量练习：只改变 `H`

保持 dataset root、选中 episode、FPS、feature schema 和 split 不变，分别考察 `H = 2`、`4`
和 `8`。

运行之前，先预测每个取值对应的：

- action tensor shape；
- `H / fps`，即名义 sample 数对应的 horizon；
- `(H - 1) / fps`，即最后一个 target 的 offset；
- 当前 row 是 episode 最后一帧时，哪些位置会被 padding。

随后构造每个 reader window，把实际 mask 与预测对照，并且只统计未被 mask 的 target。这个练习
改变的是 data-window 语义；它不会训练三种 policy，也不能预测哪个 horizon 的任务成功率最高。

## 证据边界与 L11/L12 衔接

完成 L10 可以证明一份本地数据集具有一致的身份、schema、数值、代表性 decoded frame、
statistics、episode boundary、split ID 和 action-window 行为，但不能证明：

- 演示数量或 domain coverage 足以支持学习；
- domain randomization 带来了收益；
- training loss 有限、训练收敛或 checkpoint 质量可靠；
- open-loop policy prediction 足够准确；
- closed-loop grasp success 或 sim-to-real transfer。

[L11](./l11-domain-randomization.md) 接下来会讨论如何改变外观、物体位置、相机和动力学分布，
同时不破坏任务语义。[L12](./l12-act-and-smolvla-policy-training.md) 随后消费本讲的数据合同，
训练 ACT 和 SmolVLA，并重新加载保存的 processor。[L13](./l13-closed-loop-evaluation-and-capstone.md)
最后才把加载后的 policy 放回控制回路。

## 小结

- LeRobot 数据集包含 metadata、表格和 media 三层；存储 file chunk 不等于 episode。
- Metadata 用 HWC 描述存储视频，decoded sample 通常提供 CHW tensor；policy preprocessing
  是第三种表示。
- `world` 和 `wrist` 提供同步的全局与局部证据，应检查当前输入数据在相同时刻的两种视角。
- Per-channel statistics 支持诊断和可逆 normalization，但不能证明覆盖度或泛化能力。
- 按完整 episode 划分，避免近重复 trajectory frame 泄漏。
- 行为克隆从对齐 observation 学习专家 target，但部署时会进入 policy 自己产生的状态，并可能
  累积误差。
- Action chunk 使用与 FPS 对齐的 offset、固定 shape 和 padding mask，确保 target 不跨越
  episode reset。
- ACT 与 SmolVLA 共享 raw dataset，但保留不同的 task、camera-key 和 preprocessing 合同。

## 资料来源

- [LeRobot 0.6.0 dataset metadata 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/dataset_metadata.py)
  — 固定版本的 `info.json`、statistics、tasks、episodes 读取与文件路径解析实现。
- [LeRobot 0.6.0 dataset reader 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/dataset_reader.py)
  — 固定版本的 Parquet 读取、task lookup、按需视频解码、时序查询、边界 clamp 与 padding mask
  实现。
- [LeRobot 0.6.0 dataset factory 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/factory.py)
  — action offset 解析和按 task 分组的 episode-level train/eval split。
- [LeRobot 0.6.0 normalization processor 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/processor/normalize_processor.py)
  与 [ACT processor 源码](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/policies/act/processor_act.py)
  — 面向 policy 的 normalization 与 action unnormalization 行为。
- [A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://proceedings.mlr.press/v15/ross11a.html)
  — 对时序 distribution shift 和误差累积问题的形式化讨论，说明为何监督 BC loss 之外还需要
  closed-loop evaluation。
- [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)
  — ACT 论文，也是 action chunking 的依据。
- [SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics](https://arxiv.org/abs/2506.01844)
  — SmolVLA 架构，以及本讲 data-contract 对照所需的语言条件策略背景。
- [RoboGenesis 101 recorder](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/record_dataset.py)、
  [training wrapper](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/train_policy.py)
  与 [兼容性记录](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
  — 本课程使用的当前 9 关节 schema、policy presets 与已验证运行边界。
