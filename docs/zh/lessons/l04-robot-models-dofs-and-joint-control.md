---
lesson: L04
slug: robot-models-dofs-and-joint-control
locale: zh
title: "机器人模型、DOF 与关节控制"
duration_minutes: 90
hardware: cpu-ok
status: cpu-verified
---

# L04 · 机器人模型、DOF 与关节控制

> **课程状态：** 讲义和可执行 notebook 均已提供。notebook 已在 CPU 和参考 AMD
> ROCm 平台上通过干净 kernel 验证，其中包括 Genesis camera 路径；由于 CPU 仍是本讲
> 的最低硬件要求，L04 状态为 `cpu-verified`。

## 本讲定位

L02 介绍了 Genesis 生命周期，以及从 Scene 到刚体 Entity 和 Link 的层级。L03 进一步
说明，每调用一次 `scene.step()`，仿真就会推进一个外层时间步 `dt`，而且仅凭一张最终
画面不足以支持物理结论。L04 将这两个认识应用到课程中的第一个关节机器人：Franka
Emika Panda。

本讲的核心问题是：

**机器人模型中的一个名称怎样变成正确的控制维度？一个位置目标又怎样经过控制器、
执行器限幅和仿真动力学，最终成为可测量的运动？**

答案并不是“写入目标后再把它读出来”。一条有用的追踪链是：

```text
MJCF 中的 link 和 joint 名称
             ↓
运行时 entity-local DOF 索引
             ↓
初始 q + 目标 q + KP/KV + force range
             ↓
目标命令 → 控制器 → 动力学 → scene.step()
             ↓
实测 q(t)、qdot(t)、control force(t) 和机器人姿态
             ↓
rise、overshoot、settling、final error 和 saturation 证据
```

开始前，你应当能够：

- 解释 `gs.init → Scene → add_entity/add_camera → build → step/read/render`；
- 区分 Entity 和其中的某一个刚体 Link；
- 根据外层 `dt` 计算 step 数和仿真时长；
- 检查 NumPy 数组的 shape、单位和数值有限性；
- 只改变一个因素、保持其他条件不变来比较实验 case。

本讲不要求你已经掌握正运动学或逆运动学、末端坐标系、相机标定、抓取或策略学习。
L05 会在本讲建立关节目标的执行方式之后再引入这些主题。

## 学习目标

完成 L04 后，你应当能够：

1. 解释 MJCF 模型、Entity、Link、Joint、自由度（degree of freedom，DOF）和广义位置
   （`qpos`）之间的运行时关系；
2. 解释本讲使用的固定基座 Franka 为什么有 7 个臂关节、却有 9 个受控维度，并判断
   它们各自的单位和限制；
3. 按 joint name 解析 entity-local DOF index，并验证命令、状态、增益和 limit 数组的
   shape 是否兼容；
4. 区分作为状态重置的 `set_dofs_position(...)` 和作为动态控制目标的
   `control_dofs_position(...)`，并把二者放在正确的 build 边界之后；
5. 使用有适用边界的 PD 模型分析 KP、KV、有效惯量、重力、离散时间和 force-range
   saturation，而不声称存在一套普适调参配方；
6. 使用姿态、位置、速度、控制力和阶跃响应指标设计并解释一次 joint4 阶跃实验；
7. 按系统化顺序排查名称、索引、shape、单位、limit、非有限状态、饱和、settling 和
   渲染问题。

## 从 MJCF 文件到可控系统

### 模型提供了什么

实验通过下面的代码加载 Genesis 内置的 Franka 模型：

```python
from robo_genesis.scene_config import FRANKA_MJCF

franka = scene.add_entity(
    gs.morphs.MJCF(file=FRANKA_MJCF),
)
```

MJCF 是 MuJoCo 基于 XML 的模型定义格式。在这个模型中，它描述的内容包括：

- 刚体树及其视觉几何体和碰撞几何体；
- 刚体的惯性属性；
- joint、joint axis 和位置范围；
- actuator 及其 gain、bias 和 force range；
- 两个夹爪手指之间的 equality 和 tendon 关系。

XML 是声明，还不是仿真轨迹。`add_entity(...)` 在场景声明阶段返回 Franka Entity 的
handle；随后，`scene.build()` 导入模型并创建求解器状态。关节状态 getter 和控制调用
属于运行时操作，因此必须位于 build 之后。

Genesis 当前会把这个内置 MJCF 作为一个刚体 Entity 处理。该 Entity 内部包含多个 Link，
模型中的可动关系把这些 Link 连接起来。这扩展了 L02 的层级：

```text
Scene
└── Franka RigidEntity
    ├── 刚体 Links：link0、link1、...、hand、fingers
    ├── Joints：joint1、...、joint7、finger joints
    └── 由这些 joint 拥有的 DOF 和 qpos 坐标
```

Link 是具有位姿、惯量和几何体的刚体。Joint 约束子 Link 和父 Link 之间的相对运动。
DOF 是这种约束允许的一个独立标量运动轴。三者是不同类别的对象；Link 编号、Joint
编号和 DOF index 不能互换。

### 固定、旋转和平移关系

理解本讲只需要三类关系：

| 类型 | 允许的相对运动 | DOF 数 | 位置单位 | effort 单位 |
|---|---|---:|---|---|
| Fixed | 无 | 0 | 无 | 无 |
| Revolute | 绕一个轴旋转 | 1 | rad | N·m |
| Prismatic | 沿一个轴平移 | 1 | m | N |

固定关系不贡献控制坐标。在内置模型中，没有可动 joint 的 body 会通过模型树保持刚性
连接，机器人基座则固定在世界中。7 个臂关节都是 revolute joint；两个 finger joint
都是 prismatic joint，各自在模型给出的 `0` 到 `0.04 m` 范围内移动。

不要把“一个 joint 等于一个 DOF”推广成通用规则。spherical joint 可以有 3 个旋转
DOF，free joint 有 6 个速度 DOF；相反，fixed 关系没有 DOF。

### DOF 和 `qpos` 回答不同的问题

DOF 统计相互独立的瞬时运动轴；`qpos` 保存描述系统位形的广义坐标。二者的维数不一定
相同：

- 单轴 revolute 或 prismatic joint 通常有 1 个 DOF 和 1 个 `qpos`；
- 球面姿态有 3 个 DOF，但常用 4 个分量的单位四元数表示；
- 自由刚体有 6 个 DOF，却可以使用 7 个位置坐标：3 个平移分量和 4 个四元数分量。

本讲的固定基座 Franka 恰好是一个简单特例。每个可动 joint 都只有一个轴，因此运行时
模型有 9 个 DOF 和 9 个 `qpos` 坐标。二者相等是当前模型的属性，不是 API 不变量。
在 Genesis 1.3.3 中，这个固定导入模型的预期运行时汇总为 11 个 Link、9 个可动
Joint、9 个 DOF 和 9 个 `qpos` 坐标；notebook 会实际检查这些数量，而不是只相信这句
说明。

Genesis 在每个 `RigidJoint` 上明确暴露了这种区别：

```python
joint = franka.get_joint("joint4")
print(joint.n_dofs)
print(joint.n_qs)
print(joint.dofs_idx_local)
print(joint.qs_idx_local)
```

代码应当检查这些属性，而不是根据 joint 在 `franka.joints` 中的位置进行推断。

## Franka 的 7 个臂 DOF 和 2 个手指 DOF

当前模型的控制映射如下：

| Joint 名称 | 数量 | Joint 类型 | 位置 / 速度 | 控制 effort |
|---|---:|---|---|---|
| `joint1`–`joint7` | 7 | revolute | rad / rad·s⁻¹ | N·m |
| `finger_joint1`、`finger_joint2` | 2 | prismatic | m / m·s⁻¹ | N |

“7-DOF Franka arm”说的是机械臂链，不包括两个独立表示的手指 DOF。因此，本课程中的
整机数组长度为 9，而只包含机械臂的数组长度为 7。

内置模型给出了以下位置范围：

| Local DOF | Joint | 位置范围 | 单位 |
|---:|---|---:|---|
| 0 | `joint1` | `[-2.8973, 2.8973]` | rad |
| 1 | `joint2` | `[-1.7628, 1.7628]` | rad |
| 2 | `joint3` | `[-2.8973, 2.8973]` | rad |
| 3 | `joint4` | `[-3.0718, -0.0698]` | rad |
| 4 | `joint5` | `[-2.8973, 2.8973]` | rad |
| 5 | `joint6` | `[-0.0175, 3.7525]` | rad |
| 6 | `joint7` | `[-2.8973, 2.8973]` | rad |
| 7 | `finger_joint1` | `[0, 0.04]` | m |
| 8 | `finger_joint2` | `[0, 0.04]` | m |

这些数值是带版本的模型数据，不是所有 Franka 资产通用的机械规格。执行代码应从运行时
对象中读取它们：

```python
lower, upper = franka.get_dofs_limit(dofs_idx_local=all_dofs)
```

这项检查能够发现模型变化，也能避免一个表面上长度正确的 9 维 target 发出越界位置。

## 按名称解析索引

### 为什么裸索引很脆弱

对当前这份导入模型而言，“joint4 位于 index 3”确实成立，但它不应成为发现映射的方法。
另一份资产可能增加 floating base、重新排列 joint，或使用不同方式表示 gripper。更稳健
的程序应先按名称解析映射，再验证结果。

```python
import numpy as np

joint_names = [f"joint{i}" for i in range(1, 8)] + [
    "finger_joint1",
    "finger_joint2",
]

dof_indices = []
for name in joint_names:
    joint = franka.get_joint(name)
    if joint.n_dofs != 1 or joint.n_qs != 1:
        raise ValueError(
            f"{name} must be one-DOF/one-qpos in this lab, got "
            f"n_dofs={joint.n_dofs}, n_qs={joint.n_qs}"
        )
    dof_indices.extend(joint.dofs_idx_local)

all_dofs = np.asarray(dof_indices, dtype=int)
arm_dofs = all_dofs[:7]
finger_dofs = all_dofs[7:]

assert all_dofs.shape == (9,)
assert np.unique(all_dofs).size == 9
```

`dofs_idx_local` 明确属于 Franka Entity 的局部索引。Genesis 还存在求解器级索引，
Joint 也有自己在列表中的位置。把一个索引空间误当成另一个传入，可能会控制错误的维度，
也可能直到场景变复杂后才报错。

### 数组形状是接口的一部分

对于没有 batch 的场景，下面每次调用都应为每个请求的 DOF 返回一个值：

```python
q = franka.get_dofs_position(dofs_idx_local=all_dofs)
qdot = franka.get_dofs_velocity(dofs_idx_local=all_dofs)
lower, upper = franka.get_dofs_limit(dofs_idx_local=all_dofs)

assert tuple(q.shape) == (9,)
assert tuple(qdot.shape) == (9,)
assert tuple(lower.shape) == (9,)
assert tuple(upper.shape) == (9,)
```

课程 notebook 会先把 tensor 转换成 NumPy，再检查每个数值是否有限。即使一个向量有
9 个元素，单位错误时仍然是错误的，因此结构表必须把 joint 类型和单位放在每个 index
旁边。

批处理场景还会增加一个 environment 维度。L04 刻意只使用一个未批处理的机器人，让
模型映射和控制证据保持清楚；并行环境的 shape 将在学习流水线后续部分出现。

## 状态重置不等于动态控制

下面两个 API 都接收位置，但含义不同。

### `set_dofs_position(...)` 用于建立状态

```python
franka.set_dofs_position(
    q_start,
    dofs_idx_local=all_dofs,
    zero_velocity=True,
)
```

这段代码会直接指定所选广义位置；使用 `zero_velocity=True` 时，还会把对应速度清零。
它适合让每组实验回到相同的初始条件。

但它不能证明控制器让机器人发生了运动。如果在期望轨迹的每个点都调用这个接口，实际
做的是覆盖状态，而不是展示机器人经过动力学产生的、受到执行器限幅的运动。

### `control_dofs_position(...)` 用于建立目标

```python
franka.control_dofs_position(
    q_target,
    dofs_idx_local=all_dofs,
)
scene.step()
q_measured = franka.get_dofs_position(dofs_idx_local=all_dofs)
```

这段代码设置位置控制器的 target。实测 state 通常不会瞬间跳到 target：控制器先计算
effort，仿真器再推进一个外层时间步，程序随后才能观测到新的位置和速度。

这个区别是一组公平增益实验的基础：

1. 把每组 case 重置到相同的 `q_start` 和零速度；
2. 配置增益和 force limit；
3. 发送 target；
4. 推进动力学；
5. 测量响应。

## 三种控制模式，一个主实验

Genesis 1.3.3 提供了三个与本讲相关的控制调用：

| 调用 | 命令含义 | 所选 DOF 的典型单位 | 它不是什么 |
|---|---|---|---|
| `control_dofs_position` | 目标广义位置 | rad 或 m | 直接状态赋值 |
| `control_dofs_velocity` | 目标广义速度 | rad/s 或 m/s | 位置目标 |
| `control_dofs_force` | 命令的广义 effort | N·m 或 N | 能保证到达位姿的目标 |

position 模式使用配置的位置增益和速度阻尼；velocity 模式使用对应的速度控制设置。
force 模式直接发送广义 effort，因此调用方需要承担更多动力学和安全方面的判断。

L04 解释这三种模式的接口边界，但可执行实验只使用 position control。要比较 KP/KV，
就必须保持控制模式不变；velocity 和 force control 实验会引入不同问题，本讲不会把它们
藏成额外的对照组。

## 外层步控制循环

L03 已经把 `dt` 定义为一次 `scene.step()` 推进的时间。现在，它还成为最直接的 Python
命令和观测更新周期：

```text
在 t[k]：选择或重复 q_target[k]
             ↓
控制器根据 target 和 state 计算有界 effort
             ↓
scene.step() 将动力学推进 dt
             ↓
在 t[k+1]：读取 q、qdot 和 control effort
```

实验使用 `dt = 0.01 s`。因此，1.2 秒观测窗口包含 120 个外层 step。第一次 step 前先在
`t = 0` 记录初始位置，之后再在每次 step 后记录新状态，这会得到包含两个端点的 121 个
位置样本。只在 step 后读取的量对应 `dt, 2dt, ..., 1.2 s`。

明确的时间对齐非常重要。如果把第一个 step 后的状态误标为 `t = 0`，报告的 rise 和
settling time 都会偏移一个样本。

每个 step 前重复发送同一个 target，也会让 action cadence 在代码中保持可见。target
可能会在内部持续生效，但显式循环与后续课程中随时间更新 target 的代码具有相同结构：

```python
q_history = [read_q()]
for _ in range(n_steps):
    franka.control_dofs_position(q_target, all_dofs)
    scene.step()
    q_history.append(read_q())
    qdot_history.append(read_qdot())
    control_history.append(read_control_force())
```

## 有适用边界的 PD 心智模型

### 位置误差与速度阻尼

对目标速度为零的某个 revolute DOF，可以使用下面这个简化模型：

```text
tau_control ≈ KP × (q_target - q) - KV × qdot
```

对 prismatic DOF，同样的结构仍然成立，但输出是力而不是力矩。KP 根据位置误差提供
effort；KV 与运动方向相反，起到速度阻尼作用。

这个公式只是分析局部响应的工具，不是完整的 Franka 动力学。它可以帮助我们提出可检验
的预测：

- 提高 KP 可能更积极地纠正相同的位置误差；
- 提高 KP 却没有足够阻尼，可能增大速度或过冲；
- 提高 KV 可能减小速度和过冲；
- 阻尼过大也可能减慢响应。

这些表述都使用“可能”，而不是“必然”。force clipping、关节耦合、重力、初始位姿和
离散积分都可能改变实测关系。

### 理想临界阻尼及其边界

对于具有常量有效惯量 `I_eff` 的理想线性、解耦单 DOF 系统，误差动力学可以近似写成：

```text
I_eff × error_ddot + KV × error_dot + KP × error = 0
```

它的阻尼比为：

```text
zeta = KV / (2 × sqrt(KP × I_eff))
```

在这个理想模型中，`zeta = 1` 表示临界阻尼，`zeta < 1` 表示欠阻尼，`zeta > 1`
表示过阻尼。

这个公式说明了为什么改变 KP 后应当重新考虑 KV：当 KV 保持不变而 KP 增大时，理想化
阻尼比会降低。但它不能证明某组数值 KP/KV 在 Franka 上构成临界阻尼，因为机器人还
具有：

- 随位形变化的有效惯量；
- joint 之间的动力学耦合；
- 重力和其他模型力；
- 离散时间积分和外层命令周期；
- joint limit 与约束效应；
- 有限的执行器力或力矩范围。

如果把某个实测 case 称为“临界阻尼”，就需要比本讲更完整的辨识模型和证据。这里应当
描述实际观测到的瞬态，例如“在本观测窗口内没有观测到过冲”。

### 重力、负载与有限窗口误差

假设一个 joint 静止时需要抵抗非零重力力矩。在简化比例控制器中，系统可能需要保留
非零位置误差，才能产生对应的平衡力矩：

```text
support torque ≈ KP × steady position error
```

如果没有积分项或精确的重力前馈，少量非零误差可能与控制器的物理行为一致。但是，
1.2 秒轨迹的最后一个样本并不会自动成为稳态。它的误差还可能来自：

- 尚未结束的瞬态；
- 残余速度或振荡；
- 执行器饱和；
- 其他 joint 的耦合；
- 离散化效应。

在把全部 final error 归因于重力之前，必须同时检查最终速度、轨迹尾部和有限窗口
settling 规则。

## 力范围与饱和

### 控制器是有界的

项目为 Franka 的 9 个 DOF 定义了明确的 effort 上下限。在内置模型和课程配置中：

| DOF | Effort 范围 | 单位 |
|---|---:|---|
| `joint1`–`joint4` | `[-87, 87]` | N·m |
| `joint5`–`joint7` | `[-12, 12]` | N·m |
| 两个 finger DOF | `[-100, 100]` | N |

notebook 会先设置这些范围，再将其读回：

```python
franka.set_dofs_force_range(
    lower=force_lower,
    upper=force_upper,
    dofs_idx_local=all_dofs,
)
measured_lower, measured_upper = franka.get_dofs_force_range(
    dofs_idx_local=all_dofs,
)
```

当不受约束的 PD 表达式请求超过配置范围的 effort 时，控制贡献会被截断。此时继续增大
KP，也无法按比例得到更大的控制输出；响应已经不再是一个不受限制的理想二阶对照。

joint4 可以使用下面的条件检测 saturation：

```text
abs(control_force) >= 0.99 × joint4_force_limit
```

其中 `0.99` 是声明过的数值检测阈值，不是新的 force limit。应当报告满足条件的样本数
或持续时间，因为单个 peak 值无法说明 clipping 主导了多长时间的瞬态。

### 控制作用力不等于总内部作用力

Genesis 提供了两个名称相近的观测接口：

- `get_dofs_control_force()` 返回由位置或速度控制命令计算得到的内部控制贡献；
- `get_dofs_force()` 返回当前时间步中 DOF 实际承受的内部力。

二者回答的问题不同。前者适合检查命令控制器是否达到配置的 effort range；后者还反映
仿真系统的内部动力学，不能重新标成 PD command。

绘图时必须记录数据来自哪个 API。仅把 y 轴写成“torque”会丢失这个区别，并可能产生
错误的 saturation 结论。

## 实验设计：一个机器人，两组实验

配套实验只使用一个 Plane、内置 Franka MJCF 和一个可选的 Genesis camera。它不会
使用后续的抓取场景构建器、YCB 物体、逆运动学或外部下载。

数值路径可以在 CPU 上运行，不依赖渲染。可选 camera 路径回答关于机器人姿态的视觉
问题；状态和控制数组则回答有关瞬态的定量问题。

### 在 build 前声明场景

notebook 会让关键场景逻辑直接可读：

```python
scene = gs.Scene(
    sim_options=gs.options.SimOptions(dt=0.01, substeps=2),
    show_viewer=False,
)
scene.add_entity(gs.morphs.Plane())
franka = scene.add_entity(gs.morphs.MJCF(file=FRANKA_MJCF))

if render_enabled:
    camera = scene.add_camera(
        res=(720, 540),
        pos=(1.8, -1.8, 1.4),
        lookat=(0.0, 0.0, 0.55),
        fov=42,
        GUI=False,
    )

scene.build()
```

camera 必须在 `scene.build()` 前添加。`gs.init()` 执行后，如果要改变 backend、render
模式或 build-time topology，应当从干净 kernel 重新启动。

实验采用明确的环境变量合同：

- `ROBO_GENESIS_BACKEND=auto` 或 `cpu` 选择请求的计算路径；
- `ROBO_GENESIS_RENDER=0` 跳过 camera 创建和渲染；
- `ROBO_GENESIS_RENDER=1` 要求创建 camera，并得到有效、有限的 RGB 数组；
- 输出文件只能写入 `ROBO_GENESIS_OUTPUTS_DIR`。

如果明确启用了渲染，那么渲染失败就是该路径失败，不能静默替换成示意图后仍声称得到
了 Genesis camera 证据。

## Part A：joint4 基准运动

### 建立初始状态

项目已经提供一个 9 维起始位形和一组基础增益。发送 target 前，实验必须：

1. 按名称解析全部 9 个 DOF；
2. 断言 `q_start`、KP、KV 和 force-range 的 shape；
3. 验证 `q_start` 位于每个位置限制以内；
4. 使用 `zero_velocity=True` 重置 9 个位置；
5. 读回位置和速度；
6. 捕获初始 camera 帧，或读取各 Link 的实测位置。

joint4 target 是从起始值出发的正向 `0.25 rad` 阶跃，其他位置 target 保持不变：

```python
q_target = q_start.copy()
q_target[3] += 0.25

if not np.all((lower <= q_target) & (q_target <= upper)):
    raise ValueError("position target exceeds the model limits")
```

名称映射证明了数组元素 3 在当前运行时模型中对应 joint4。代码不会在解析和检查之前就
依赖这一事实。

### 测量运动，而不是假定运动

控制循环会记录：

- 以 rad 为单位的 joint4 target position；
- 以 rad 为单位的实测 joint4 position `q(t)`；
- 以 rad/s 为单位的实测 joint4 velocity `qdot(t)`；
- 以 N·m 为单位的 joint4 control contribution；
- 机器人的初始和最终姿态。

至少应当满足：最终绝对位置误差小于初始误差，所有记录值都有限，数组长度与声明的
时间戳一致。这些检查能够证明机器人向 target 运动，却不能单独证明瞬态表现良好。

一组 camera 图可以让模型和姿态变化可见，但无法揭示两帧之间短暂的过冲或 peak control
torque。相反，折线图可以量化响应，却无法证明所需机器人资产和 camera 取景正确。这两
类证据相互补充。

## 在查看结果前定义阶跃响应指标

主对照使用从 `q0` 到 `q_target` 的正向阶跃，以及有限的 1.2 秒观测窗口。以下指标是
针对本实验给出的操作性定义。

### 上升时间（rise time）

Rise time 是实测 joint 第一次到达命令正向阶跃 90% 的采样时刻：

```text
q(t) >= q0 + 0.9 × (q_target - q0)
```

如果没有任何样本达到阈值，应报告 `not observed`，不能用观测窗口末端代替。

### 过冲（overshoot）

对本实验的正向阶跃：

```text
overshoot = max(0, max_t(q(t) - q_target))
```

如果改成负向阶跃，这个单侧定义也需要反向。报告 overshoot 为零，表示外层采样时刻没有
观测到过冲；它不能证明连续轨迹从未在两个样本之间越过 target。

### 有限窗口调节时间（settling time）

本实验的 settling band 为 `±0.01 rad`。Settling time 是误差第一次进入该范围，并在
记录窗口的所有后续样本中始终保持在该范围内的时刻：

```text
abs(q(t:) - q_target) <= 0.01 rad for the rest of the array
```

如果不存在这样的后缀，应报告 `not observed`。如果存在，也应称为有限窗口 settling。
一段 1.2 秒记录不能证明无限时域稳定，也不能排除之后的扰动。

### 最终误差、峰值速度与峰值控制力

其余三个指标为：

```text
final error  = abs(q_target - q at the final sample)
peak speed   = max(abs(qdot))
peak control = max(abs(control force))
```

Final error 描述一个端点，不是完整响应。Peak speed 和 peak control 必须注明单位。
Peak control 还必须与模型的 joint4 force range 比较，并通过完整 control trace 判断
saturation 只发生在一个样本，还是持续了一段时间。

## Part B：隔离 KP 与 KV

第二组实验让三个 case 从相同的 `q_start`、零速度、joint4 target、`dt`、substeps、
duration、force range、seed 和非 joint4 增益开始。

| Case | joint4 KP | joint4 KV | 受控对照 |
|---|---:|---:|---|
| G1 · Reference | 3500 | 100 | 低刚度参考组 |
| G2 · Higher KP only | 7000 | 100 | G1→G2 只改变 KP |
| G3 · More damping | 7000 | 300 | G2→G3 只改变 KV |

这些数值用于让当前模型和位姿中的差异清晰可见，不是任意 Franka 任务或真实硬件上的
推荐控制器。

查看数组前，先提出两个假设：

1. G2 到达 90% 的时间可能不晚于 G1；但由于 KP 增大而 KV 不变，它也可能出现更大的
   speed、overshoot 或更长的 force-limit 持续时间。
2. G3 与 G2 的 KP 相同，额外阻尼可能减小 peak speed 和 overshoot，但也可能让 rise
   变慢。

这些是需要检验的预测，不能无条件打印成结果。notebook 必须从本次运行得到的数组动态
生成每句解释。如果某个关系没有出现，应报告实际顺序，并检查 saturation、时间对齐、
初始状态一致性和观测窗口。

### 完整重置每个 case

只改变增益却不重置状态，无法形成受控对照，因为第二组会继承第一组的位置和速度。
因此，每个 case 都从下面的操作开始：

```python
franka.set_dofs_position(
    q_start,
    dofs_idx_local=all_dofs,
    zero_velocity=True,
)
```

随后，实验应用该 case 的增益向量，验证 target 和 force range，记录 `t = 0`，再运行
相同数量的外层 step。代码应逐字段比较 case 配置，并断言 G1→G2 只改变 joint4 KP，
G2→G3 只改变 joint4 KV。

### 引导式解读包含四段证据

应按以下顺序阅读结果表和轨迹：

1. **G1→G2 隔离 KP。** 在确认 KV 和其他输入完全相同后，比较 rise、peak speed、
   overshoot 和 settling。报告实测变化方向，不能声称更高 KP 总是更好。
2. **G2→G3 隔离 KV。** 在 KP 固定时比较 rise、peak speed、overshoot 和 settling。
   说明增加阻尼是否减小了实测瞬态，以及付出了怎样的响应时间代价。
3. **Final error 有证据边界。** 把 final error 与最终速度和 settling 状态一起比较。
   不能从最终值推断完整瞬态质量，也不能把全部剩余误差归因于重力。
4. **执行器 limit 限定了模型。** 把每条 control trace 与 joint4 limit 对照，报告检测
   到的饱和样本数或持续时间。如果发生 clipping，应明确说明无约束理想 PD 已无法解释
   完整响应。

这段解释必须根据当前结果数组动态生成，能够处理 rise 或 settling 为 `not observed` 的
情况，也不能嵌入从另一台机器或另一个 backend 复制来的数值。

## 视觉证据与定量证据各有职责

L04 会同时保留 Genesis 原生图像和 Matplotlib 图表。

| 证据 | 来源 | 能回答的问题 | 无法单独回答的问题 |
|---|---|---|---|
| 初始/最终 RGB | Genesis `add_camera` 和 `camera.render` | Franka 场景是否真正完成渲染，可见姿态发生了怎样的变化？ | Rise time、overshoot 或 peak torque 是多少？ |
| 初始/最终状态示意图 | 明确关闭渲染时读取的 Link 位置 | 在 headless 路径上，实测机器人几何是否发生变化？ | Genesis RGB renderer 是否经过验证？ |
| `q(t)` 图 | 实测 DOF 位置 | target 是否被逐步跟踪，是否 overshoot，是否仍在 band 以外？ | 视觉资产和 camera 是否正确？ |
| `qdot(t)` 图 | 实测 DOF 速度 | joint 运动有多快，是否仍有残余运动？ | 是哪种 effort 产生了运动？ |
| control-force 图 | `get_dofs_control_force()` 与 limit 线 | 控制器是否达到配置的 effort range？ | 总 internal force 是多少？ |
| 动态指标表 | 当前数组和声明的定义 | 受控 case 在当前窗口内有什么差异？ | 这种关系是否适用于所有位姿和机器人？ |

当 `ROBO_GENESIS_RENDER=1` 时，两张 RGB 都必须是非空、数值有限且通道 shape 符合
预期的数组；渲染错误会终止该路径。当 `ROBO_GENESIS_RENDER=0` 时，notebook 会明确
打印 render `SKIP`，并可以绘制基于实测 Link 的示意图，但标题必须说明它不是 camera
frame。

源实验使用初始和最终图像，而不是视频。L04 保留这种证据形式：短时瞬态由时间序列图
测量得更准确，因此本讲不要求视频。

## 配套 notebook 工作流

可执行实验按以下顺序组织，使每项结果都能追溯到它的配置：

1. 打印课程 metadata、Genesis 版本、请求与实际 backend、render 模式、seed 和输出
   目录；
2. 调用一次 `gs.init()`，声明 Plane、Franka 和可选 camera，然后调用
   `scene.build()`；
3. 检查 Link 和 Joint，解析 9 个具名 local DOF，并打印名称、类型、index、单位和
   limit 表；
4. 验证所有配置的 shape、位置限制、effort range 和数值有限性；
5. 运行 joint4 基准阶跃，并保留初始样本；
6. 显示初末姿态证据，绘制带单位和 limit 线的 `q`、`qdot` 和 control force；
7. 从完全相同的重置状态运行 G1–G3，并验证单变量修改；
8. 计算指标，并根据实测数组生成四段式解释；
9. 执行最终检查：成功时打印 `L04 CHECK: PASSED`，否则指出具体违反的 invariant。

最小 CPU 路径使用 `ROBO_GENESIS_RENDER=0`，但仍会执行全部模型、控制和指标检查，
同时必须把 camera 工作标记为跳过。启用渲染的路径可以增加场景证据，却不能取代数值
路径。

## 如何判断实验运行成功

一次成功执行应提供以下全部证据：

- 实际运行时报告了预期的 7 个 arm DOF 和 2 个 finger DOF 名称映射；
- `q_start`、target、gain、limit 和 force range 具有预期 shape、单位和有限数值；
- joint4 target 位于运行时位置限制以内；
- 基准实验的 final error 小于 initial error；
- 时间戳与初始样本及每个外层 step 正确对齐；
- G1、G2、G3 从相同位置和零速度开始；
- 自动检查确认了预期的单变量 gain 修改；
- 未发生的 rise 或 settling 被报告为 `not observed`；
- position、velocity 和 control-force 数组都有限，并在图中注明单位；
- saturation 与读回的 force range 完成对照；
- 输出明确说明姿态证据来自 Genesis RGB，还是明确标注的实测状态 fallback。

受支持 backend 之间出现少量数值差异，不会自动表示失败。应保留完整数组并比较已定义
的关系。如果定性顺序发生变化，应同时保留两种结果并诊断原因，而不是隐藏某一个
backend。

## 常见警告与失败

### 构建期间出现 importer 警告

在 Genesis 1.3.3 中，导入这个 MJCF 时可能出现与版本相关的 warning，例如 tendon
近似、neutral `qpos`、constraint time constant 调整或 neutral-pose self-collision
过滤。应当保留这些信息。一个已知 importer warning 本身不能证明运行失败；而屏蔽所有
warning 也会抹去有用上下文。

build 完成后，仍然必须检查具名结构、有效 shape、有限状态和合法 limit。出现未知
joint name、非有限轨迹或断言失败时，不能用“同时存在一个预期 warning”作为忽略理由。

### 找不到 joint name

先打印运行时 `franka.joints` 中的名称，再与锁定模型核对。修改 index 前，应检查
Genesis 版本和模型路径；不要用猜测出来的列表位置替代缺失名称。

### 命令长度与 index 长度不同

打印两边的 shape，确认命令是只包含 arm 的 `(7,)`，还是包含整机的 `(9,)`。value 和
index 必须一起切片，不能依赖隐式 broadcasting 发送控制命令。

### 目标越过 joint limit

读取当前 lower/upper 数组，定位具名 DOF，然后拒绝或重新设计实验。静默 clip target
会改变实际请求的阶跃，使其不能再与其他 case 公平比较。

### 实测位置立即等于 target

检查实验是否使用了 `set_dofs_position`，而不是 `control_dofs_position`，或者是否在
动态 step 前读取了状态。状态 reset 不是控制器响应。

### 响应发生振荡或过冲

先确认每个 case 都从零速度开始，再检查 KP、KV、`dt`、substeps、完整 velocity trace
和 force limit。不能只看一张最终帧就诊断“KP 过高”。

### 提高 KP 后实测上升时间没有缩短

确认只有 KP 发生变化，时间戳正确对齐，target 也完全相同。随后检查 control trace 是否
saturation；当两个 case 都被同一个 limit 截断时，KP 加倍并不会让可用 torque 加倍。

### 最终误差不为零

检查最终速度、`q(t)` 尾部、settling 状态、重力负载和 saturation。诊断时可以先延长
观测窗口，不要一次改变多个控制参数。

### 没有观测到 settling

应当原样报告。确认 `±0.01 rad` band 和 suffix rule，再检查轨迹是一直在 band 外、进入
后又离开，还是仅仅因为窗口太短而结束。不能把缺失值格式化成一个成功时间。

### 控制作用力与内部作用力不一致

确认每个数组来自哪个 getter。按 API 定义，它们就是不同的量。控制器 limit 分析应使用
`get_dofs_control_force()`；如果还检查 `get_dofs_force()`，必须单独标注。

### 请求 AMD 却报告 CPU

同时记录 requested backend 和 actual backend。一次运行只能作为 Genesis 实际选择的
backend 的证据，不能把 CPU 输出重新标成 AMD 结果。

### 渲染失败

如果请求了渲染，应保留错误并判定该路径失败。检查 camera 是否在 build 前声明，以及
进程是否具备所需图形环境。如果渲染本来就明确关闭，则打印 `SKIP`，并且只使用清楚
标注的状态派生姿态图。

### 改变 build-time 设置后没有重启

`gs.init()` 是进程级操作，camera topology 也会在 build 时固定。改变 backend、render
模式或 build-time scene content 前，应重新启动 kernel。

### 诊断顺序

每次都使用相同顺序：

```text
版本、请求/实际 backend 和 render 模式
  → 模型路径和 build 边界
  → joint 名称、local DOF、类型、单位和 limit
  → 命令/index shape 和 target 合法性
  → 相同 reset state 和零速度
  → q/qdot/control-force 有限性和时间戳
  → force saturation 和有限观测窗口
  → backend 对照或 gain 调整
```

这套顺序会在把结构错误误判成控制器调参问题之前先找到它们。

## 课堂检查与练习

### 概念检查

不要回看前面的表格，独立回答：

1. Fixed 关系会贡献 DOF 吗？为什么？
2. 为什么当前 Franka 有 7 个 arm joint，却有 9 个受控维度？
3. 为什么 free joint 或 spherical joint 的 `n_qs` 可能与 `n_dofs` 不同？
4. 为什么通过 `dofs_idx_local` 解析，比复制另一份模型中的裸整数更安全？
5. arm position、finger position、arm effort 和 finger effort 分别使用什么单位？
6. 为什么 `set_dofs_position(..., zero_velocity=True)` 适合在实验前使用，却不能证明
   动态控制成功？
7. 在理想单 DOF 模型中，提高 KP 后为什么应重新考虑 KV？
8. 为什么非零 final error 可能与重力一致，却仍不能证明全部误差都来自重力？
9. 要检查 position controller 是否达到配置的 force range，应使用哪个 getter？
10. 为什么两张 camera frame 无法证明 rise time 或 overshoot？

### 动手练习

运行基准实验和 G1–G3 对照。执行前，先写下你对 rise、overshoot、peak speed 和
saturation 变化方向的预测；执行后：

1. 根据打印的 case 配置证明 G1→G2 只改变 joint4 KP，G2→G3 只改变 joint4 KV；
2. 报告所有指标及其单位，未观测到时使用 `not observed`；
3. 说明哪些 case（如果有）到达了读回的 joint4 force limit，以及持续了多少个样本；
4. 解释实测 KP/KV 关系，但不要使用“永远”或“普遍如此”这样的表述；
5. 解释为什么只看 final error 会漏掉部分瞬态信息；
6. 说明限定结论范围的 Genesis 版本、backend、位姿、target、时间步、force range 和
   观测窗口。

作为扩展，保持 G2 的其他配置不变，只把观测窗口扩大一倍。先预测哪些指标可能只是因为
观测到更多轨迹而改变。已经观测到的 rise time 和 peak 可能保持不变，但有限窗口
settling 状态和 final error 可能变化。这个练习改变的是证据窗口，而不是物理控制器。

不要增加任意更高增益的 case。练习目标是解释一组受控且受到执行器限幅的实验，不是
寻找最剧烈的运动。

## 小结与后续连接

- MJCF 文件声明关节模型，build 会把它转化成刚体 Entity 拥有的运行时状态。
- Link 是刚体，Joint 约束相对运动，DOF 统计独立运动轴，`qpos` 保存位形坐标。
- 本讲使用的固定基座 Franka 有 7 个 revolute arm DOF 和 2 个 prismatic finger DOF；
  `n_qs == n_dofs == 9` 是当前模型的特例。
- 应先按 joint name 解析 entity-local DOF index，再验证 shape、单位和位置 limit，最后
  才发送命令。
- `set_dofs_position` 重置状态；`control_dofs_position` 设置 target，后者通过控制
  effort 和 `scene.step()` 中的动力学变成运动。
- 简化 PD 模型可以解释 KP/KV 的作用，但有效惯量、耦合、重力、离散时间、约束和
  effort limit 共同限定了它的适用范围。
- 应联合阅读 `q(t)`、`qdot(t)`、control force、saturation 和有限窗口指标。一个最终
  数值或一张姿态图不能代表全部瞬态。
- Genesis camera frame 提供场景和姿态证据，实测状态图提供定量控制证据，二者不能
  相互替代。

L05 将用逆运动学从期望末端位姿计算 arm-joint target，并把 camera 当作传感器，而不再
只作为场景证据；这个 target 仍然需要 L04 的控制循环才能变成运动。L06 会把受到控制的
机器人放入抓取场景。L07 会把同一个关节控制接口组织成脚本化专家，并且仍需遵守 limit、
时间和实测状态合同。

## 资料来源

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  — 官方使用和 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  — 本课程锁定的准确引擎版本。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — 带版本的状态、gain、position/velocity/force control、force-range 和 force
  observation API 语义。
- [Genesis 1.3.3 `RigidJoint` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_joint.py)
  — 带版本的 `n_qs`、`n_dofs`、joint type 和 entity-local index 属性。
- [Genesis 1.3.3 内置 Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — 本讲使用的 joint type、range、actuator 参数、tendon 和 equality 定义。
- [Genesis 1.3.3 机器人控制教程](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/examples/tutorials/control_your_robot.py)
  — 官方 position、velocity 和 force control 示例。
- [MuJoCo Modeling 文档](https://mujoco.readthedocs.io/en/stable/modeling.html)
  — body、joint、actuator 和 constraint 背后的 MJCF 建模概念。
- [《Feedback Systems》，Åström 与 Murray](https://fbsbook.org/)
  — 二阶响应和反馈控制推理的开放教材背景；本讲先明确理想化阻尼关系的边界，再把它
  应用于耦合机器人。
