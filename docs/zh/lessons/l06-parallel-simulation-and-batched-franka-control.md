---
lesson: L06
slug: parallel-simulation-and-batched-franka-control
locale: zh
title: "并行仿真与批量 Franka 控制"
duration_minutes: 90
hardware: cpu-ok
status: cpu-verified
---

# L06 · 并行仿真与批量 Franka 控制

> **课程状态：** L06 已达到 `cpu-verified`。双语 notebook 均已通过独立 CPU
> clean-kernel 执行；英文 notebook 还通过了 CPU+EGL 和参考 AMD R9700+EGL 的批量相机
> 路径。该状态表示 CPU 最低路径已经验证，不表示课程已经 `published`，也不把 GPU
> 变成学习本讲的必要条件。

## 本讲定位

L05 让一个目标位姿依次经过逆运动学（inverse kinematics，IK）、关节空间位置控制、
重复 `scene.step()` 和末端位姿实测。L06 保留这条链，进一步追问：当一个 Scene 中包含
一批环境时，这条链的含义会怎样变化？

> 怎样让一份声明好的拓扑产生 4 份彼此独立的仿真状态？前导环境维度如何贯穿 IK 与
> 控制？只更新部分环境时，又怎样避免混淆数组行号和环境索引？

核心实验包含两个阶段：

```text
一份 Plane + Franka 拓扑
  → 构建 4 个环境
  → 4 个目标位姿
  → 批量 IK 与逐环境验收
  → 批量 PD 目标与动态位姿测量
  → 只为环境 1 和 3 提供两个新目标位姿
  → 检查选中环境与未选环境的证据
```

这是一讲批量语义课，不会增加新的机器人任务。本讲没有桌子、物体、抓取状态机、数据集
或学习策略。L07 将加入抓取场景；L09 讨论演示数据录制时会复用这里的 batch 心智模型，
但 L06 不实现并行 recorder。

开始前，你应当能够：

- 解释 `init → declare → build → control → step → read/render` 生命周期；
- 找出 Franka 的 7 个 arm DOF、2 个 finger DOF，并识别 `(9,)` qpos；
- 区分 IK candidate、6 维 residual 与动态实测位姿；
- 通过位置控制执行已接受的 q，而不是瞬移状态；
- 比较世界坐标系中的 position 和 `wxyz` quaternion；
- 把相机图像视为观察证据，而不是数值验收测试。

### 90 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–8 分钟 | 回顾 L05 单环境控制链 | 写出非批量 q 与位姿的 shape |
| 8–20 分钟 | 一份拓扑与 4 份独立状态 | 解释为什么布局间距不是物理 target offset |
| 20–32 分钟 | 前导环境维度与 shape ledger | 预测完整批量和选择子集的 shape |
| 32–47 分钟 | 批量 IK | 逐行接受或拒绝候选 |
| 47–61 分钟 | 批量动态执行 | 测量 4 个环境各自的位姿误差 |
| 61–77 分钟 | 选择性更新环境 1 和 3 | 解释行到环境的映射与保留目标 |
| 77–84 分钟 | 正确性、吞吐、渲染与记录 | 说出每种主张所需要的证据 |
| 84–88 分钟 | 可选批量相机 | 核对 RGB/depth 前导维度，或明确报告跳过 |
| 88–90 分钟 | 检查点与练习 | 复述完整批量与选择子集的合同 |

## 学习目标

完成 L06 后，你应当能够：

1. 解释 `scene.build(n_envs=B)` 怎样把一份已声明的 entity topology 变成 B 份独立的
   仿真状态，同时说明 `env_spacing` 只改变它们的视觉排列；
2. 在 L05 的 q、目标位姿、IK candidate、residual 和 measured pose shape 前增加环境
   维度，并保持每行含义不变；
3. 用一次批量调用求解 B=4 的 IK target，再按环境检查 shape、有限值、position residual
   和 rotation residual，决定每行候选能否接受；
4. 把已接受的 `(4, 9)` q 数组设为 PD position target，通过重复 `scene.step()` 推进全部
   环境，并测量各环境的最终位姿；
5. 用 `envs_idx=[1, 3]` 配合恰好两行 target 和 command，并说清每一行对应哪个环境；
6. 解释为什么环境 0 和 2 会保留仍然有效的 PD target，而不是变成冻结状态，再检查它们
   的运动量和 retained-target error change；
7. 区分 batching correctness、simulation throughput、batched rendering 和完整 parallel
   data recording；
8. 验证可选批量 RGB/depth 的 shape，同时不拿图像代替 IK 与控制证据。

## 一份拓扑，B 份独立状态

### 声明一次，在 build 时复制

和前几讲一样，entity 与可选 camera 都必须在 Scene build 之前声明。区别出现在 build
边界：

```python
B = 4

scene = gs.Scene(...)
scene.add_entity(gs.morphs.Plane())
franka = scene.add_entity(
    gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml")
)

scene.build(
    n_envs=B,
    env_spacing=(1.1, 1.1),
    n_envs_per_row=2,
)
```

这些声明描述了一份 Plane-and-Franka 拓扑：所有副本共享 entity 类型、Link、DOF 名称和
控制器配置。`build(n_envs=4)` 会创建 4 份仿真状态；每一份都有自己的 q、qdot、控制
目标、接触与持续演化的动力学状态。

关键区别可以写成：

```text
共享的拓扑与参数
          │
          └── build(n_envs=4)
                ├── 环境 0 的状态
                ├── 环境 1 的状态
                ├── 环境 2 的状态
                └── 环境 3 的状态
```

这些环境是状态彼此独立的副本，不是分别声明的 4 台不同机器人。一条命令可以只点名其中
一部分状态，但一次 `scene.step()` 仍会推进全部 4 个环境。

### `n_envs=0` 与 `n_envs>0` 的 shape 合同不同

在 Genesis 1.3.3 中，`n_envs=0` 表示非批量 Scene，并不表示 Scene 里没有物理环境。
此时 state 和 command array 都没有前导环境维度：Franka qpos 是 `(9,)`，hand position
是 `(3,)`。

当 `n_envs>0` 时，第一维就是环境维度。`n_envs=4` 会把上述 shape 变为 `(4, 9)` 和
`(4, 3)`。即使 `n_envs=1`，接口也已经进入批量模式，因此仍保留长度为 1 的前导维度，
例如 `(1, 9)`。不要让代码把 `n_envs=1` 当成 `n_envs=0`。

### 布局 offset 不是仿真坐标

`env_spacing`、`n_envs_per_row` 和 `center_envs_at_origin` 用来排列可视化副本，方便 viewer
或总览相机同时显示多个机器人而不让画面互相重叠。Genesis 明确把这些 offset 限定为
可视化用途；它们不会改变仿真相关的位姿。

假设 2×2 可视化网格中的环境 3 被画在环境 1 的右侧，世界坐标系 IK target
`[0.45, 0.10, 0.35]` 在两个环境中仍然具有相同的物理含义。不要把画面上的网格 offset
加到目标位置上。

::: warning 不要把可视化布局当成控制目标
把 `env_spacing` 加进 IK target，会重复计算 Genesis 只在绘制副本时使用的 offset。
这样既可能让目标变得不可达，也会让数值状态不再表达画面暗示的含义。
:::

## 前导环境维度

L05 使用一行 q 和一个目标位姿。L06 改变的是前导维度，而不是每一行的含义。

令：

- `B=4` 表示 build 后的环境数量；
- `D=9` 表示 Franka 的 DOF 数量；
- `K=2` 表示选择性寻址的环境数量。

### Shape ledger

| 数量 | 非批量 L05 | 完整批量 B=4 | 选择 `envs_idx=[1, 3]` | 一行的含义 |
|---|---:|---:|---:|---|
| qpos / joint command | `(9,)` | `(4, 9)` | `(2, 9)` | 9 个 Franka 关节值 |
| Target position | `(3,)` | `(4, 3)` | `(2, 3)` | 一个世界坐标系 xyz target |
| Target quaternion | `(4,)` | `(4, 4)` | `(2, 4)` | 一个单位 `wxyz` orientation |
| IK residual | `(6,)` | `(4, 6)` | `(2, 6)` | xyz 与 rotation-vector residual |
| Measured hand position | `(3,)` | `(4, 3)` | 读取全部再选行 | 一个世界坐标系 xyz 测量值 |
| Measured hand quaternion | `(4,)` | `(4, 4)` | 读取全部再选行 | 一个实测 `wxyz` orientation |

完整批量调用中，第 `i` 行属于环境 `i`。选择性调用中，数组行号和环境索引属于两个不同
的命名空间：

```text
envs_idx = [1, 3]

输入/输出第 0 行  ↔  环境 1
输入/输出第 1 行  ↔  环境 3
```

因此，每个选择性输入的前导维度必须等于 `len(envs_idx)`，而不是 B。把 `(4, 9)` command
和两个 index 放在一起，不会构成正确的选择性命令；省略 `envs_idx` 时传入 `(2, 9)` command
也不正确，因为 Genesis 此时需要每个环境各有一行。

不要依赖 broadcasting 修补缺失的批量维度。显式写出每一行，才能看清 target 属于哪个
环境，让环境接收不同位姿，并在控制前暴露映射错误。

## Baseline：为 4 个环境执行批量 IK

Baseline 为每个环境分配一个可达的世界坐标系 hand pose。四个 position 不同，但所有行
使用相同的归一化 `wxyz` orientation：

```python
target_positions = np.array([
    [0.42, -0.12, 0.35],  # environment 0
    [0.48, -0.04, 0.40],  # environment 1
    [0.48,  0.06, 0.32],  # environment 2
    [0.40,  0.14, 0.38],  # environment 3
])
target_quaternions = np.tile(
    np.array([0.0, 1.0, 0.0, 0.0]),  # w, x, y, z
    (B, 1),
)
```

它们的 shape 分别为 `(4, 3)` 和 `(4, 4)`。这些都是仿真世界坐标系 target，没有任何一行
包含 `env_spacing` offset。

批量求解沿用 L05 的 IK 合同。

`hand` 与 `arm_dofs` 仍像 L04/L05 那样按 Link 和 joint 名称解析，不要用臆测的 scene-global
index 代替它们。

```python
q_start = franka.get_qpos()
q_goal_raw, ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=target_positions,
    quat=target_quaternions,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=5e-4,
    rot_tol=5e-3,
    return_error=True,
)

q_goal = to_numpy(q_goal_raw)
ik_error = to_numpy(ik_error_raw)
```

期望的输出 shape 为：

```text
q_goal.shape   == (4, 9)
ik_error.shape == (4, 6)
```

虽然 IK 通过 7 个 arm DOF 求解，但返回的 entity q 每一行仍包含 Franka 的全部 9 个 DOF，
其中两个 finger 值也保留在这一行中。

### 逐行验收，不要只看平均值

对于环境 `i`，residual 包含两部分：

```text
ik_error[i, :3]  position residual vector，单位为 m
ik_error[i, 3:]  rotation-vector residual，单位为 rad
```

沿行方向分别计算 norm：

```python
position_residuals = np.linalg.norm(ik_error[:, :3], axis=1)
rotation_residuals = np.linalg.norm(ik_error[:, 3:], axis=1)

candidate_valid = (
    np.isfinite(q_goal).all(axis=1)
    & np.isfinite(ik_error).all(axis=1)
    & (position_residuals <= 5e-4)
    & (rotation_residuals <= 5e-3)
)
```

先断言准确的 array shape 和已经归一化的 quaternion row，再要求 `candidate_valid` 中 4 个
Boolean value 全部为 true，才发送完整批量命令。

平均 residual 可能掩盖失败行。例如 3 个很小的数值可能把 mean 拉到 tolerance 以下，
即使第 4 个环境没有收敛。最大值可以辅助汇总，但逐行数值及其标签必须保留：

```text
环境 0：position residual ...，rotation residual ...，accepted ...
环境 1：position residual ...，rotation residual ...，accepted ...
环境 2：position residual ...，rotation residual ...，accepted ...
环境 3：position residual ...，rotation residual ...，accepted ...
```

和 L05 一样，有限的 q 只是 candidate。IK 不会移动机器人，也不会生成 collision-free path。
本讲中只要任意 baseline row 失败，就应停止这一阶段并诊断，而不是把接受和拒绝的候选
混在一起发送。

## 批量动态执行

4 行 candidate 全部通过后，把它们设为 position controller target：

```python
franka.control_dofs_position(q_goal)

for _ in range(180):
    scene.step()
```

由于省略了 `envs_idx` 且 command 有 4 行，第一个调用会更新全部 4 个 PD target。随后每次
`scene.step()` 都推进 4 份环境状态。增大 B 不会增大仿真的 `dt`，而是让更多状态副本参与
同一步仿真。

固定观察窗口结束后，读取与 IK target 相同的世界坐标系 hand pose：

```python
measured_positions = to_numpy(hand.get_pos(relative=False))
measured_quaternions = to_numpy(hand.get_quat(relative=False))

position_errors = np.linalg.norm(
    measured_positions - target_positions,
    axis=1,
)

def quaternion_angle_error_rows(measured_wxyz, target_wxyz):
    measured_wxyz = np.asarray(measured_wxyz, dtype=float)
    target_wxyz = np.asarray(target_wxyz, dtype=float)
    measured = measured_wxyz / np.linalg.norm(
        measured_wxyz,
        axis=1,
        keepdims=True,
    )
    target = target_wxyz / np.linalg.norm(
        target_wxyz,
        axis=1,
        keepdims=True,
    )
    cosine_half_angle = np.clip(
        np.abs(np.sum(measured * target, axis=1)),
        0.0,
        1.0,
    )
    return 2.0 * np.arccos(cosine_half_angle)

orientation_errors = quaternion_angle_error_rows(
    measured_quaternions,
    target_quaternions,
)
```

`quaternion_angle_error_rows()` 对每组已经归一化的 quaternion pair 应用 L05 的最短角计算。
四元数 dot product 的绝对值让计算不受等价表示 `q` 与 `-q` 的影响。它的结果和
`position_errors` 一样，shape 都是 `(4,)`。

对于这个 Plane-and-Franka 实验及有限控制窗口，采用以下操作性动态检查：

| 检查 | 逐环境要求 |
|---|---:|
| 最终 position error | `<0.02 m` |
| 最终 orientation error | `<0.05 rad` |
| 相对初始位姿的 position error | 减小 |

这些阈值只适用于当前实验，不代表真实 Franka 的精度、任意目标或长期控制精度。未来的
配套 notebook 必须逐行验证它们，之后才能把结果作为运行证据。

### Solver 证据与 dynamics 证据仍须分开

| 证据 | 回答的问题 | 不能证明什么 |
|---|---|---|
| 逐环境 IK residual | 每个数值候选是否满足位姿 tolerance？ | 机器人是否运动？ |
| 批量 command shape 与 mapping | 每个候选行是否发给预期环境？ | 控制器是否跟踪到它？ |
| 逐环境 measured pose error | 动态执行后每个 hand 最终在哪里？ | 路径是否无碰撞？ |

不要用 `set_dofs_position()` 替换控制器。状态重置虽然能让最终位姿看起来正确，却会移除
本阶段本应检验的 PD controller 和 dynamics。

## 选择性更新：环境 1 和 3

第二阶段只改变两个 target：

```python
selected_envs = [1, 3]
untouched_envs = [0, 2]

selected_target_positions = np.array([
    [0.44, -0.16, 0.32],  # row 0 → environment 1
    [0.50,  0.12, 0.40],  # row 1 → environment 3
])
selected_target_quaternions = np.tile(
    np.array([0.0, 1.0, 0.0, 0.0]),
    (len(selected_envs), 1),
)
```

这里的 `selected_target_positions[0]` 不属于环境 0，而是属于 `selected_envs[0]`，即环境 1；
第二行属于环境 3。

IK 和 control 必须使用同一个 index list：

```python
q_selected_raw, selected_ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=selected_target_positions,
    quat=selected_target_quaternions,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=5e-4,
    rot_tol=5e-3,
    return_error=True,
    envs_idx=selected_envs,
)

q_selected = to_numpy(q_selected_raw)
selected_ik_error = to_numpy(selected_ik_error_raw)
```

选择性调用的 shape 必须准确等于：

```text
selected_target_positions.shape   == (2, 3)
selected_target_quaternions.shape == (2, 4)
q_selected.shape                  == (2, 9)
selected_ik_error.shape           == (2, 6)
```

继续逐行检查有限值、position residual `<=5e-4 m` 与 rotation residual `<=5e-3 rad`。
两行都通过后，才能把它们发送给控制器：

```python
positions_before_selective = measured_positions.copy()
baseline_position_errors = position_errors.copy()

franka.control_dofs_position(q_selected, envs_idx=selected_envs)
for _ in range(180):
    scene.step()
```

这会替换环境 1 和 3 的 PD target，但不会覆写环境 0 和 2 持有的 target。

### 未选中不等于冻结

环境 0 和 2 没有收到新命令，但 `scene.step()` 仍会推进它们。原有 PD controller 会继续
跟踪 baseline q target，因此它们可能完成少量剩余收敛，也可能表现出正常的数值动力学。
如果把它们称为“冻结”，就是用错误原因预测零状态变化。

证据因此必须回答两个不同的问题：

1. 环境 1 和 3 是否到达各自的新 target？
2. 环境 0 和 2 是否保留旧 target，且没有出现实质性退化？

选择性控制窗口结束后，读取全部 4 个位姿。选中的行与两个新 target 比较，未选中的行与
原始 baseline target 比较：

```python
positions_after = to_numpy(hand.get_pos(relative=False))
quaternions_after = to_numpy(hand.get_quat(relative=False))

selected_position_errors = np.linalg.norm(
    positions_after[selected_envs] - selected_target_positions,
    axis=1,
)
retained_position_errors = np.linalg.norm(
    positions_after[untouched_envs] - target_positions[untouched_envs],
    axis=1,
)
selected_orientation_errors = quaternion_angle_error_rows(
    quaternions_after[selected_envs],
    selected_target_quaternions,
)
retained_orientation_errors = quaternion_angle_error_rows(
    quaternions_after[untouched_envs],
    target_quaternions[untouched_envs],
)
untouched_motion = np.linalg.norm(
    positions_after[untouched_envs]
    - positions_before_selective[untouched_envs],
    axis=1,
)
retained_error_change = (
    retained_position_errors
    - baseline_position_errors[untouched_envs]
)
```

还要用对应的 quaternion target row 计算 selected 和 retained orientation error，然后逐环境
应用以下检查：

| 分组 | 证据 | 要求 |
|---|---|---:|
| 选中的环境 1 和 3 | 到新 target 的 position error | `<0.02 m` |
| 选中的环境 1 和 3 | 到新 target 的 orientation error | `<0.05 rad` |
| 未选的环境 0 和 2 | 到保留 target 的 position error | `<0.02 m` |
| 未选的环境 0 和 2 | 到保留 target 的 orientation error | `<0.05 rad` |
| 未选的环境 0 和 2 | 选择性控制窗口内的运动量 | `<0.005 m` |
| 未选的环境 0 和 2 | 保留 position error 的增加量 | `<=0.002 m` |

最后两项必须配合使用。运动量很小，无法说明环境是在靠近还是远离保留目标；最终误差很
小，也可能掩盖它相对更好 baseline 出现的明显退化。一起报告运动量、旧误差、新误差与
误差变化，才能让解释可审查。

这些有限窗口检查只支持一个狭义结论：本实验中的选择性命令没有实质性干扰保留目标。
它们不能证明异步 reset、任意 B 下的隔离性或长期稳定性。

## 必须分开的四种“并行”含义

“并行仿真”很容易承载过多含义。L06 把它拆成四种不同主张：

| 主张 | 本讲需要的证据 | 这些证据不能证明什么 |
|---|---|---|
| 批量正确性 | 各环境的 shape、行映射、有限值、residual 和动态误差 | wall-clock 执行更快 |
| 仿真吞吐 | 包含预热、固定 backend 与 workload、同步且排除渲染的受控计时 | target ownership 或控制正确 |
| 批量渲染 | 带前导环境维度的真实 RGB/depth array | IK、动态跟踪或数据记录正确 |
| 完整并行数据记录 | action/observation 对齐、环境与 episode identity、reset 语义、编码和 writer backpressure | 策略质量更好 |

一次 `scene.step()` 会推进 B 份状态，因此 N 次调用产生 B×N 个 environment transition。
这是 API 事实，不是实测 speedup。Wall-clock throughput 取决于 backend、B、场景复杂度、
kernel 编译、同步、渲染和数据传输。本讲不会宣称 B=4 就会“快 4 倍”，也不设置 FPS 或
transitions-per-second 验收阈值。

如果以后要 benchmark throughput，应先 warm up，在计时边界同步，固定 physics 与 rendering
workload，并同时报告 steps/s 和 environment transitions/s。不要用一次正确性实验推出性能
结论。

## 可选批量相机观测

数值 IK/control 是最低 CPU 路径。显式启用渲染时，可以在 Scene build 前配置
`VisOptions`，让 Genesis 1.3.3 Rasterizer 为每个待渲染环境返回一幅图像：

```python
vis_options = gs.options.VisOptions(
    rendered_envs_idx=[0, 1, 2, 3],
    env_separate_rigid=True,
)

scene = gs.Scene(
    ...,
    vis_options=vis_options,
)
camera = scene.add_camera(
    res=(640, 360),
    pos=(1.2, -1.2, 1.0),
    lookat=(0.35, 0.0, 0.35),
    fov=45,
    GUI=False,
)

# Add entities, then call scene.build(n_envs=4, ...).
```

使用 `rendered_envs_idx=[0, 1, 2, 3]` 和 `env_separate_rigid=True` 时，render 应具有以下
shape：

```python
rgb, depth, _, _ = camera.render(rgb=True, depth=True)

rgb.shape    == (4, 360, 640, 3)
depth.shape  == (4, 360, 640)
```

和 L05 一样，camera 配置使用 `res=(W, H)`，array 则先放 height 再放 width。新的第一维
遵循 `rendered_envs_idx`，每一行表示一个待渲染环境。检查 RGB 是非空 `uint8`，depth 是
有限的 floating array，并人工确认 4 幅图中都包含 Franka 与地面参照。2×2 mosaic 便于
展示，但原始四维 RGB array 才是 batch 证据。

如果没有设置 `env_separate_rigid=True`，Rasterizer 可以改为把多个带视觉 offset 的副本画
进同一幅 overview image。这个 `(H, W, 3)` 单张图像不是 batched image stack。

关闭渲染时，应明确报告 camera `SKIP`，不要创建占位 array，也不要用 Matplotlib 机器人
示意图替代。开启渲染时，真实 camera array 能证明批量观察可用，但仍不能代替 residual、
command mapping 或动态位姿检查。

## 配套实验

配套实验让一份 Plane-and-Franka 拓扑依次经过完整批量 baseline 与一次 selective update。
它会直接展示 target array、`envs_idx`、IK call、validity vector、controller call 和逐环境
误差计算，而不是把它们藏进黑盒 runner。

### 运行前先预测

执行实验前先写下答案：

1. `build(n_envs=4)` 之后的 qpos shape 是什么？
2. 环境 3 在画面中的位置会改变它的世界坐标系 IK target 吗？
3. 4 个 residual 中有一个失败时，及格的平均值能让整批通过吗？
4. 使用 `envs_idx=[1, 3]` 时，command row 0 属于哪个环境？
5. 选择性命令之后，`scene.step()` 还会推进环境 0 和 2 吗？
6. RGB shape `(4, H, W, 3)` 能证明 4 个 IK candidate 都收敛了吗？

### 最小数值路径

即使关闭渲染，实验也应完成本讲核心内容：

1. 初始化一个受支持的 backend，声明 Plane 与 Franka；
2. 使用 `n_envs=4` build，并确认 qpos 为 `(4, 9)`；
3. 创建 4 行显式世界坐标系 target 和归一化 `wxyz` row；
4. 求解批量 IK，逐行验收所有 residual；
5. 应用已接受的 `(4, 9)` PD target，step 整个 Scene；
6. 测量 4 个 position error 和 orientation error；
7. 通过 `envs_idx=[1, 3]` 求解并应用两行新 target；
8. 测量 selected-target error、retained-target error、untouched motion 和
   retained-error change；
9. 根据请求打印真实 camera 证据，或明确输出 render `SKIP`。

没有异常不等于通过。一次成功运行必须满足准确的 shape 合同、有限值和每一项逐环境数值
检查。

## 常见失败与诊断顺序

### qpos 是 `(9,)`，不是 `(4, 9)`

确认实际 build call 使用了 `n_envs=4`。创建名为 `B` 的变量或声明一台机器人，都不会添加
batch dimension。还要记住，所有 entity 和 camera 必须先声明，Scene 才能 build。

### 后几行的 target 发生偏移或变得不可达

删除手工加入的 `env_spacing` 或 grid offset。把数值 target row 与可视化布局设置分开打印。
IK 接收的是仿真世界坐标系位姿，不是屏幕上的摆放位置。

### IK 报告前导维度错误

在调用点打印 `target_positions.shape`、`target_quaternions.shape` 和 `len(envs_idx)`。
完整批量输入需要 4 行；`[1, 3]` 的选择性调用需要 2 行。

### 平均 residual 通过，但某台机器人没有到达

带环境标签打印 position 与 rotation residual norm，把 tolerance 应用于 Boolean vector，
而不是只应用于一个 scalar mean。只要一行失败，就不要发送完整批量命令。

### 错误的环境向新 target 运动

在 selective IK 和 control 前都打印 `(row, env_idx, target)`，并在两个调用中复用同一个
有序、无重复的 `envs_idx` list。不要把两行结果的局部行号当成全局环境索引。

### 未选环境发生少量运动

不要立刻把它判定为跨环境干扰。环境 0 和 2 仍持有有效的 baseline PD target。应同时比较
前后运动量、retained-target error 和 error change，再检查是否使用了错误的 index list 或
command array。

### IK 通过，但动态位姿误差不通过

确认接受的 q 已进入 `control_dofs_position()`，完整 step 窗口确实执行，DOF order 与 gain
符合 L04/L05 配置，而且最终位姿在执行后以 `relative=False` 读取。逐环境检查 trajectory
中是否出现非有限值，或 error 是否停止下降。不要用状态重置强行让断言通过。

### RGB 没有环境维度

确认 `VisOptions(env_separate_rigid=True)` 和目标 `rendered_envs_idx` 都在 build 前传入。
单张 overview image 是另一种渲染模式，不表示数值 batching 失败。

### B=4 比预期更慢

把首次 build 的编译、渲染、同步和 array copy 与 steady-state stepping 分开。正确的 batch
语义不要求固定 speedup。

使用以下诊断顺序：

```text
版本、backend 与 render mode
  → declare/build 边界与 B
  → 数值坐标系与可视化 spacing
  → 完整批量或子集 shape
  → row-to-environment mapping
  → 逐行 IK residual
  → PD target 与 step window
  → measured state 与逐环境 error
  → 可选 camera shape 或 throughput measurement
```

## 检查点与练习

### 概念检查点

不回看前文，回答以下问题：

1. `n_envs=0` 表示什么？它与 `n_envs=1` 有什么区别？
2. 哪些属性属于共享拓扑，哪些属于逐环境状态？
3. 为什么不能把 `env_spacing` 加进世界坐标系 IK target？
4. B=4 时，q、position、quaternion 和 IK residual 的完整批量 shape 分别是什么？
5. `envs_idx=[1, 3]` 时这些 shape 是什么？两行各自映射到哪个环境？
6. 为什么平均 residual 和 camera mosaic 都不能代替逐行验收？
7. 只有环境 1 和 3 收到新命令后，为什么环境 0 和 2 仍是动态的？
8. 怎样用证据区分 batch correctness、throughput、batched rendering 与完整 data
   recording？

### 动手练习：选择环境 0 和 2

Baseline 通过后，只改变 selective stage：

```python
selected_envs = [0, 2]
untouched_envs = [1, 3]
selected_target_positions = np.array([
    [0.46, -0.08, 0.38],  # row 0 → environment 0
    [0.44,  0.10, 0.36],  # row 1 → environment 2
])
```

保持 B、orientation、controller setting、step count 与 rendering mode 不变。运行前，先预测
position、quaternion、q 和 residual 的 shape，并写出行映射。

然后逐环境报告：

1. 两组 selected IK residual；
2. selected 最终 position 与 orientation error；
3. untouched 环境相对各自原始 baseline target 的最终 error；
4. untouched motion 与 retained position-error change；
5. camera batch shape 是否发生变化。

不要增大 B、添加物体或为运行计时。这些变化会让人难以判断结果究竟来自新 index mapping，
还是来自其他变量。

## 小结与后续连接

- `build(n_envs=B)` 把一份已声明拓扑复制成 B 份独立状态。`n_envs=0` 是非批量模式；
  任意正数都会添加前导环境维度。
- `env_spacing` 与 `n_envs_per_row` 只控制可视化布局。世界坐标系 IK target 不包含这些
  offset。
- B=4 时，q/command、position、quaternion 和 IK residual shape 分别为 `(4, 9)`、
  `(4, 3)`、`(4, 4)` 和 `(4, 6)`。
- 使用 `envs_idx=[1, 3]` 时，上述 shape 的第一维变为 2：row 0 对应环境 1，row 1 对应
  环境 3。
- 每个 IK candidate 都要分别通过 shape、有限值、position residual 和 rotation residual
  检查，才能成为 PD target。
- 一次 `scene.step()` 推进全部环境。动态控制窗口结束后，要逐行测量 position 与
  orientation error。
- 未选环境保留之前的 PD target，并非冻结；需要同时用 motion 与 retained-error change
  检查选择性隔离。
- Batch correctness、throughput、batched rendering 和完整 parallel recording 是需要不同
  证据的主张。B=4 不代表 wall-clock 一定快 4 倍。

L07 会在保持控制与索引纪律的同时加入桌面抓取场景。L09 记录 action/observation 时，也
需要沿用这里的前导维度与 environment identity 规则。本讲不能证明 collision-free path、
任意 B 下的稳定性、异步 reset、长期稳定性、recorder correctness、policy benefit 或
grasp success。

## 参考资料

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  — 官方用户与 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  — 本课程锁定的准确引擎版本。
- [Genesis 1.3.3 `Scene` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/scene.py)
  — 固定版本的 `build()`、batch dimension 与 visualization offset 行为。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — 固定版本的批量 IK、状态读取与选择性位置控制行为。
- [Genesis 1.3.3 `Camera` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — 固定版本的渲染与批量图像返回行为。
- [Genesis 1.3.3 `VisOptions` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/options/vis.py)
  — 固定版本的环境选择与 separate-rigid 渲染选项。
- [Genesis 1.3.3 内置 Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — 本讲所用机器人模型、joint、limit 与 actuator configuration。
