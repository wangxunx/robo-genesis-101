---
lesson: L05
slug: inverse-kinematics-end-effector-poses-and-cameras
locale: zh
title: "逆运动学、末端位姿与相机"
duration_minutes: 120
hardware: cpu-ok
status: cpu-verified
---

# L05 · 逆运动学、末端位姿与相机

> **课程状态：** 中英文讲义与 notebook 均已完成；双语 CPU clean-kernel 路径已经通过，
> 英文 CPU+EGL 与参考 AMD+EGL 相机路径也已通过。L05 按最低 `cpu-ok` 合同记录为
> `cpu-verified`；附加 AMD 证据不表示学习者必须使用 GPU。本讲尚未进入 `published`
> 状态。

## 本讲定位

L04 已经说明，一个按名称解析的 joint target 如何经过控制器、执行器限制、动力学和
反复调用 `scene.step()`，最终变成可以测量的运动。L05 再加入负责选择 7 个 arm-joint
target 的上游环节：任务空间中的 Franka hand 期望位姿。同时，相机不再只是可选的场景
示意手段，而是具有明确坐标系、投影参数和数组合同的传感器。

本讲的核心问题是：

**怎样把世界坐标系中的 hand 目标位姿转换成可以接受的关节空间候选，经过动力学执行，
再用实测位姿、固定相机和 hand-attached camera 判断结果？**

完整推理链如下：

```text
世界坐标系中的目标位姿 T_WH*
          ↓  IK + mask + limit + residual 检查
候选 q_goal
          ↓  L04 controller + dynamics + scene.step()
实测 hand 位姿 T_WH(t)
          ↓  position/orientation error + Jacobian 证据
有边界的执行结论

fixed camera：T_WC 保持不变
wrist camera：T_WC(t) = T_WH(t) T_HC
scene state + T_CW + K + near/far → RGB 和 depth 数组
```

IK 调用没有抛出异常还不够。一组有限的关节向量可能只是不可达目标的 best-effort
结果；很小的 solver residual 不能证明动态机器人已经到达该位姿；一张看起来合理的
RGB 画面也不能证明前两项结论。L05 会先区分这些证据层，再明确把它们连接起来。

开始前，你应当能够：

- 解释 `gs.init → Scene → add_entity/add_camera → build → step/read/render`；
- 按 joint name 解析 Franka 的 7 个 arm DOF 和 2 个 finger DOF；
- 区分 `set_dofs_position(...)` 与 `control_dofs_position(...)`；
- 检查 shape、单位、位置限制和数值有限性；
- 使用实测状态而不是只看最终画面来解释有限控制窗口。

本讲不需要桌子、YCB 物体、抓取状态机、数据集或学习策略。IK 和控制的数值路径可以在
CPU 上完成。渲染是一项独立、显式的能力：如果请求了渲染，它就必须真正工作，不能在
失败后静默退回示意图。

### 120 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–10 分钟 | 把 target 生成环节接回 L04 controller | 预测 finite q、低 residual、低 tracking error 和 camera frame 分别能证明什么 |
| 10–27 分钟 | world、base、hand 和 camera frame；pose 与 quaternion 约定 | 判断两个量能否在共同坐标系中比较 |
| 27–43 分钟 | 正运动学、6×7 arm Jacobian、冗余与奇异性 | 解释局部速度映射和 IK 解为何可能不唯一 |
| 43–56 分钟 | 阻尼 IK、mask、初值、limit 与 tolerance | 写出不会把 finite q 误判为成功的 acceptance rule |
| 56–78 分钟 | 可达目标：IK、FK、动态控制与实测位姿 | 建立 target→candidate→execution 证据链 |
| 78–94 分钟 | fixed/attached camera、K、extrinsics、RGB 与 depth | 验证传感器坐标系与数组语义 |
| 94–107 分钟 | 不可达目标和显式 diagnostic execution | 区分 rejection、best effort 和 task success |
| 107–116 分钟 | 四环境 IK 与 selective update | 跟踪 batch 维度并检查每个环境 |
| 116–120 分钟 | checkpoint、证据边界与后续衔接 | 说明 L06、L07 和 L08 可以安全复用什么 |

## 学习目标

完成 L05 后，你应当能够：

1. 区分 world、robot-base、hand-link 和 camera frame，并在一个明确声明的约定下组合一条
   简短的齐次变换链；
2. 用 position 和 orientation 表示 pose，验证 Genesis 的 w-x-y-z 四元数约定，并计算
   正确处理 `q`/`-q` 双覆盖的角度误差；
3. 解释正运动学、局部空间 Jacobian、冗余、机械臂奇异性和阻尼最小二乘 IK，同时不把
   它们与路径规划或欧拉角万向节锁混为一谈；
4. 对 arm DOF 调用 `inverse_kinematics(..., return_error=True)`，并检查返回结果的 shape、
   有限性、joint limit、finger 保持以及启用的 position/rotation residual；
5. 区分 solver residual、FK prediction error 和 dynamic execution error，再用 L04
   controller 检验一个已接受候选是否在有限时窗中实际到达；
6. 解释为什么不可达目标仍可能产生有限的 best-effort joint vector，以及为什么
   diagnostic override 不是生产控制策略；
7. 解释 camera resolution、vertical FOV、intrinsic matrix、world-to-camera extrinsics、
   clipping plane、RGB shape 和 metric depth validity；
8. 管理 fixed camera 和 hand-attached camera 的生命周期，包括 `add_camera(...)`、
   `attach(...)` 和 `move_to_attach()`；
9. 在四环境 IK/control 实验中分析 `(B, ...)` 数组，并逐环境验证
   `envs_idx=[1, 3]` selective update；
10. 按依赖关系排查 frame、quaternion、reachability、control 和 camera 问题。

## 先确定坐标系，再讨论坐标

### 名称说明一个量属于哪里

坐标只有和参考坐标系放在一起才有意义。L05 使用 4 个坐标系：

| 坐标系 | 符号 | 在本讲中的作用 |
|---|---|---|
| 世界坐标系 | W | target、实测 hand pose 和 fixed camera 的共同坐标系 |
| 机器人基座坐标系 | B | 导入的 Franka 模型的根坐标系 |
| Hand Link 坐标系 | H | FK、Jacobian 和 IK 使用的末端 Link 坐标系 |
| 相机坐标系 | C | 与 camera intrinsics 和 extrinsics 一起使用的光学坐标系 |

在本讲的固定基座场景中，base 恰好与 world 重合。这是当前场景配置，不是通用恒等关系。
机器人安装到桌面、移动底盘或复制环境以后，world-to-base transform 都可能不是单位变换。

Genesis 1.3.3 明确说明，传给 `inverse_kinematics(...)` 的 `pos` 和 `quat` target 都是
world-frame 量。可以这样读取 hand 的世界坐标系位姿：

```python
hand_position = hand.get_pos(relative=False)
hand_quaternion = hand.get_quat(relative=False)
```

直接用 camera-frame point 减去 `hand_position` 是无效的。必须先把其中一个变换到另一方
所在的坐标系，使两个量位于同一个 frame 中。

### 统一使用一种变换约定

本讲用 `T_AB` 表示把 B frame 中的坐标转换到 A frame 的齐次变换。对于写成齐次坐标的
点 `p_B`：

```text
p_A = T_AB p_B
```

变换链按下标首尾衔接：

```text
T_AC = T_AB T_BC
T_CA = inverse(T_AC)
```

对于刚性安装在 hand 上的相机，`T_HC` 是固定的安装 offset。相机的世界位姿会随 hand
变化：

```text
T_WC(t) = T_WH(t) T_HC
```

fixed camera 则有一个配置后保持不变的 `T_WC`。Genesis 暴露的 camera extrinsics 是
world-to-camera transform，在本约定中写作 `T_CW`，而不是 `T_WC`。把一个 pose 和它的
逆变换混淆，很容易产生看起来合理、实际却发生镜像或偏移的几何结果。

一个 4×4 transform 的形式是：

```text
T_AB = [ R_AB  p_AB ]
       [  0       1 ]
```

其中，`R_AB` 是 3×3 rotation，`p_AB` 是用 A frame 表达的 B frame 原点。本讲需要理解
变换的组合和求逆，但不要求完整推导刚体变换理论。

## Pose 由 position 和 orientation 共同组成

三维 position 本身不能说明 hand 朝向哪里。目标位姿同时包含：

```text
position:     [x, y, z]，单位为 m
orientation:  单位四元数 [w, x, y, z]
```

四元数顺序是一项 API 合同。Genesis 使用 **w-x-y-z**。从返回 x-y-z-w 的其他库取得
数值后，不能不重排就直接复制。

### 比较前先归一化

旋转四元数必须具有单位范数。严格的输入检查可以归一化很小的浮点漂移，同时拒绝无效或
接近零的向量：

```python
import numpy as np


def normalize_wxyz(quaternion):
    quaternion = np.asarray(quaternion, dtype=float)
    if quaternion.shape != (4,) or not np.isfinite(quaternion).all():
        raise ValueError("quaternion must be a finite wxyz vector of shape (4,)")
    norm = np.linalg.norm(quaternion)
    if norm < 1e-12:
        raise ValueError("a zero quaternion does not define an orientation")
    return quaternion / norm
```

归一化只能修正表示尺度；它不能修正错误的分量顺序，也不能修正用错坐标系的 target。

### `q` 与 `-q` 表示同一个旋转

单位四元数是旋转群的双覆盖：`q` 和 `-q` 表示同一个物理姿态。因此，逐分量相减可能会
为完全相同的姿态给出虚假的大误差。

对于已归一化的 measured quaternion 和 target quaternion，应使用最短角距离：

```python
def quaternion_angle_error(measured_wxyz, target_wxyz):
    measured = normalize_wxyz(measured_wxyz)
    target = normalize_wxyz(target_wxyz)
    cosine_half_angle = np.clip(abs(np.dot(measured, target)), 0.0, 1.0)
    return 2.0 * np.arccos(cosine_half_angle)
```

绝对值处理双覆盖，clip 防止浮点误差让输入越过 `arccos` 的定义域，结果位于 0 到 pi rad
之间。这就是实验计算动态 orientation error 时使用的指标。

四元数能够避免欧拉角参数化中的万向节锁，但不会消除单位范数约束、双覆盖或机械臂的
运动学奇异性。这些是不同的问题。

## 正运动学与 Jacobian

### 正运动学回答一个位形会产生什么位姿

正运动学（forward kinematics，FK）是确定性映射：

```text
q → T_WH(q)
```

在锁定的 Genesis API 中，`forward_kinematics(...)` 接收 joint configuration，并返回
world-frame link position 和 quaternion。它是针对给定 configuration 的预测，不会发送
controller command、推进 dynamics 或移动当前 scene。

这种区别对应两种不同的检查：

```text
FK prediction：      q_goal → predicted hand pose
dynamic execution：  command q_goal → scene.step() → measured hand pose
```

候选 q 的 FK pose 可能很好，但由于控制时窗太短、actuator effort 有限、机器人仍在运动，
或动态模型产生误差，实际 tracking 仍然可能很差。

### Jacobian 是局部速度映射

在位形 `q` 附近，空间 Jacobian 把 joint velocity 映射为 hand 的 linear/angular velocity：

```text
[v]
[ω] ≈ J(q) qdot
```

Genesis 返回结果的前 3 行对应平移，后 3 行对应转动。对于完整的固定基座 Franka
Entity，`get_jacobian(hand)` 的 shape 是 `(6, 9)`；选择按名称解析出的 7 个 arm column，
就得到本讲 IK 推理所用的 `(6, 7)` arm Jacobian。

这个近似是局部的。`q` 发生明显变化时，`J(q)` 也会变化。初始 pose 处测得的 Jacobian
不是整个 workspace 的全局映射。

### 用 7 个机械臂变量满足 6 维位姿

hand pose 有 3 个 position 维度和 3 个 orientation 维度，Franka arm 有 7 个 joint
variable。在不受 constraint 和 singularity 影响时，多出的一个变量使机械臂对于 6 维
pose task 具有运动学冗余。

冗余既有用，也有明确边界：

- 多个 configuration 可能产生相同的 hand pose；
- 返回的解可能受 initial guess 影响；
- joint limit 可能排除原本有效的解分支；
- mask 可以减少受到约束的 task dimension；
- secondary objective 可以偏好某一种姿态，但 L05 不设计这类目标。

因此，IK 返回的是**一个**候选，而不是**唯一的** configuration。

### 机械臂奇异性不是万向节锁

arm Jacobian 的 singular value 描述局部运动能力。如果某个 singular value 很小，对应的
task-space 方向就可能需要很大的 joint-space 变化；发生秩亏时，机器人在该 configuration
下无法由现有 joint velocity 产生某个瞬时方向。

这是 manipulator singularity，属于机器人及其 pose 的属性。gimbal lock 则是某种
Euler-angle 参数化的坐标奇异性。使用 quaternion 能避免后者，却不能避免前者。

notebook 会报告实测 configuration 对应的有限 Jacobian singular values，但不会设置一个
通用 condition-number threshold，也不会用一次采样宣称整个 workspace 都不存在奇异性。

## 逆运动学是一种带约束的数值搜索

IK 把 FK 的问题反过来：

```text
期望 T_WH* → 一个 FK pose 近似 T_WH* 的 q candidate
```

在 Genesis 1.3.3 中，针对 arm-only 求解的教学调用具有下面的结构：

```python
q_candidate, residual = franka.inverse_kinematics(
    link=hand,
    pos=target_position,
    quat=target_quaternion,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    damping=0.01,
    pos_tol=position_tolerance,
    rot_tol=rotation_tolerance,
    pos_mask=[True, True, True],
    rot_mask=[True, True, True],
    return_error=True,
)
```

对于当前非批量 Franka，返回的 whole-entity candidate shape 为 `(9,)`，residual shape
为 `(6,)`。residual 顺序是：

```text
[position error x, position error y, position error z,
 rotation-vector error x, rotation-vector error y, rotation-vector error z]
```

锁定版本签名中的默认 tolerance 是 position `5e-4 m`、rotation `5e-3 rad`。实验可以
显式传入这些值，让 acceptance contract 清晰可见，而不是隐式继承默认值。

### 阻尼最小二乘

IK 会在当前 configuration 附近反复利用 Jacobian 线性化 pose error。阻尼最小二乘更新
具有下面的形式：

```text
delta_q = J^T (J J^T + lambda^2 I)^-1 error
```

阻尼项 `lambda` 会对求逆进行正则化，减小 singular value 很小时的极端 update，但它不能
凭空补出缺少的自由度，也不能让不可达 target 变得可达。阻尼太小会让奇异位形附近的
update 更敏感，太大则可能让前进速度过于保守。

### 初值、mask 和 limit 会改变问题

有 4 组参数需要明确解释：

- `init_qpos` 决定数值搜索从哪里开始。存在冗余时，不同起始姿态可能得到不同 candidate。
- `dofs_idx_local=arm_dofs` 防止 solver 把 finger 当作 pose variable。返回的 finger
  coordinate 应当保持为预期的夹爪状态。
- `pos_mask` 和 `rot_mask` 决定哪些 task-space component 需要满足。一个被关闭的
  component 之后不能被描述成已经解出的 constraint。
- `respect_joint_limit=True` 使用模型 limit 约束搜索。candidate 位于 limit 内仍可能有
  过大的 residual，因此 limit valid 是必要条件，不是充分条件。

如果省略 `init_qpos`，当前 solver 会从 scene qpos 开始，并在求解完成后恢复原有 scene
qpos/link state。因此，仅调用 IK 不会让机器人产生动态运动。这也是为什么只有发送 control
target 并步进后，才能读取 measured state。

### 不可达目标同样会产生返回路径

数值 solver 在耗尽 sample 或 iteration 后通常仍会返回搜索到的最佳 candidate。对于
`[2, 0, 2] m` 这样明显不可达的 world target，这个 candidate 仍可能是 finite、shape
正确且符合 joint limit，但 residual 远大于声明的 tolerance。

如果把 `np.isfinite(q_candidate).all()` 当作收敛，就会接受 residual 原本应当拒绝的
case。L05 把它称为**有限的 best-effort candidate**，而不是成功的 IK solution。

IK 也不会生成 collision-free path。即便 endpoint residual 很小，到达它的运动仍可能与
机器人自身、桌子或障碍物相交。L05 不包含障碍物或抓取物体；collision-aware planning
不属于本讲范围。

## 进入控制器前先验收候选

### 分层 acceptance rule

在本实验中，candidate 只有同时满足所有启用条件，才有资格进入动态执行：

1. q 具有预期 `(9,)` shape，且 q/residual 中的所有数值都有限；
2. 返回的 residual shape 为 `(6,)`；
3. 每个参与求解的 joint 都位于运行时 position limit 内；
4. 两个 finger coordinate 保持为预期值；
5. 启用的 position residual 范数不大于显式 position tolerance；
6. 启用的 rotation-vector residual 范数不大于显式 rotation tolerance。

一个说明性的纯逻辑检查如下：

```python
position_norm = np.linalg.norm(residual[:3][position_mask])
rotation_norm = np.linalg.norm(residual[3:][rotation_mask])

candidate_valid = bool(
    q_candidate.shape == (9,)
    and residual.shape == (6,)
    and np.isfinite(q_candidate).all()
    and np.isfinite(residual).all()
    and np.all(q_candidate >= lower_limits)
    and np.all(q_candidate <= upper_limits)
    and np.allclose(q_candidate[finger_dofs], q_start[finger_dofs])
    and position_norm <= position_tolerance
    and rotation_norm <= rotation_tolerance
)
```

代码还应当显式处理空 mask，而不是依赖偶然的数组 reduction 行为。主实验会启用全部 6 个
task dimension。

### 三种误差回答三个不同问题

如果不说明所处阶段，“pose error”这个词过于含糊。

| 证据 | 获得方式 | 回答的问题 | 不能证明什么 |
|---|---|---|---|
| IK solver residual | 由 `inverse_kinematics(..., return_error=True)` 返回 | 数值 candidate 是否满足启用的 kinematic tolerance？ | 动态机器人是否真正运动到那里？ |
| FK prediction error | 比较 `q_candidate` 的 FK 与 target | 独立的运动学 readback 是否与 candidate 一致？ | controller execution 是否充分？ |
| Dynamic tracking error | control 和 `scene.step()` 后的实测 hand pose | 仿真机器人在当前有限时窗中是否接近 target？ | 路径是否无碰撞，或任务是否成功？ |

前两者可能非常接近，但仍应作为名称不同的证据保留下来。第三种误差包含 controller 和
dynamics 的影响，预期不会与理想运动学结果完全相同。

### L04 controller 仍然位于执行链中

candidate 通过验收后，L05 不会把机器人瞬移到该位形，而是沿用 L04 的 position-controller
路径：

```python
position_history = [hand.get_pos(relative=False)]
quaternion_history = [hand.get_quat(relative=False)]

for _ in range(180):
    franka.control_dofs_position(q_candidate, dofs_idx_local=all_dofs)
    scene.step()
    if render_enabled:
        wrist_camera.move_to_attach()
    position_history.append(hand.get_pos(relative=False))
    quaternion_history.append(hand.get_quat(relative=False))
```

教学实验要求最终 position error 小于 `0.02 m`，最终 orientation error 小于 `0.05 rad`，
并且两种误差都小于各自初值。这些是当前场景和控制时窗的操作性阈值，不是 Franka 机器人的
机械精度，也不是 IK 的普遍保证。

完整 trajectory 仍是主要证据。一个 final value 可能掩盖 overshoot、后期漂移，或长时间
停留在远离 target 的位置。

### Diagnostic execution 必须保持显式

不可达 case 在正常流程中会于 control 前被拒绝。随后，notebook 会提供一个标注明确的
**diagnostic override**，它只允许执行 finite、in-limit 的 best-effort candidate，用于
测量这个 rejected candidate 实际会做什么：

- hand 实际移动了多远；
- 请求的 position error 还剩多少；
- target 是否仍位于可达 workspace 之外；
- 为什么 finite output 不等于 task success。

override 永远不会把 `ik_valid` 改成 true，也不会进入正常 control path。warning 和原始
rejection reason 必须始终与生成的 trace 或 image 放在一起。

## 相机是带坐标系的测量

### 固定相机与附着相机回答不同问题

实验使用两种相机关系：

| 相机 | 位姿关系 | 主要用途 |
|---|---|---|
| 固定世界相机 | 配置后的 `T_WC` 保持不变 | 观察完整机器人、target marker 和姿态变化 |
| 手腕相机 | `T_WC(t) = T_WH(t) T_HC` | 观察 eye-in-hand 视角如何随末端变化 |

fixed camera frame 可以展示场景和最终姿态，wrist frame 可以展示传感器视角确实随 hand
运动。但仅凭其中任何一张图像，都不能测量 IK residual 或 task-space tracking error。

### 生命周期：declare、build、attach、update、render

两个 camera 都必须在 `scene.build()` 前通过 `scene.add_camera(...)` 创建。attachment 需要
已经 build 的 hand link，因此发生在 build 之后：

```python
fixed_camera = scene.add_camera(
    res=(640, 360),
    pos=(1.4, -1.4, 1.2),
    lookat=(0.35, 0.0, 0.45),
    fov=42,
    GUI=False,
)
wrist_camera = scene.add_camera(
    res=(640, 360),
    pos=(0.0, 0.0, 1.0),
    lookat=(0.0, 0.0, 0.0),
    fov=42,
    near=0.01,
    far=20.0,
    GUI=False,
)

scene.build()
wrist_camera.attach(hand, offset_T=hand_to_camera_transform)
wrist_camera.move_to_attach()
```

`attach(...)` 保存 link 与 `T_HC` 的关系。在 Genesis 1.3.3 中，它不会在机器人每次 step
后自动刷新相机。hand 移动后、读取新 camera pose 或 render observation 前，都要调用
`move_to_attach()`。

初始化后改变 camera topology、render mode 或 backend，不是 notebook 中可用的捷径。
这类修改需要重启 kernel 并重新 build scene。

### 分辨率与竖直视场角

Genesis 的 camera resolution 声明方式为：

```text
res = (width, height)
```

对应的单相机数组使用图像轴顺序：

```text
RGB shape    = (height, width, 3)
depth shape  = (height, width)
```

如果图像恰好是正方形，交换两种约定可能不易被发现，换成非正方形 sensor 才会失败。
因此，实验会明确把 `res` tuple 与返回数组逐项核对。

对于本讲使用的 pinhole camera，`fov` 指**竖直**视场角。设宽度为 `W`、高度为 `H`、
vertical FOV 为 `theta_v`，Genesis 的居中 intrinsic model 为：

```text
f_x = f_y = 0.5 H / tan(theta_v / 2)
c_x = W / 2
c_y = H / 2

K = [f_x   0   c_x]
    [ 0   f_y  c_y]
    [ 0    0    1 ]
```

`camera.intrinsics` 暴露这个 3×3 matrix。这些仿真 pinhole 参数不代表相机已经针对真实
设备做过标定。lens distortion 和真实 hand-eye calibration 不属于 L05。

### 外参把世界坐标变换到相机坐标

`camera.extrinsics` 暴露 Genesis camera convention 下的 4×4 world-to-camera
transform。应当把它和引擎的 intrinsic/projection convention 配套使用，而不是根据 `pos`
和 `lookat` 猜测坐标轴后自行重建。

对于运动中的 attached camera，可以通过 `camera.transform` 获得实时 camera pose。
Genesis 1.3.3 把 `intrinsics` 和 `extrinsics` 暴露为 cached property，因此，如果在 pose
update 前后读取同一个相机对象的 extrinsics，代码应使用当前 transform 和相同的版本锁定
坐标轴约定重新计算 fresh world-to-camera matrix：

```python
def live_world_to_camera(camera):
    world_from_graphics_camera = np.asarray(camera.transform, dtype=float)
    graphics_to_camera_axes = np.diag([1.0, -1.0, -1.0, 1.0])
    world_from_camera = world_from_graphics_camera @ graphics_to_camera_axes
    return np.linalg.inv(world_from_camera)
```

这段代码复现锁定版本的 `extrinsics` 计算，但不会重复使用 `move_to_attach()` 之前缓存的
结果。notebook 将比较初末两个 fresh world-to-camera matrix；陈旧的 cached property 不能
作为 wrist camera 保持不动的证据。升级 Genesis 时，应重新核对此处的版本特定处理。

预期关系是定性的结构关系：

- 机器人运动时，fixed camera 的 transform 和 extrinsics 保持不变；
- 调用 `move_to_attach()` 后，wrist camera 的 transform 和 fresh extrinsics 发生变化；
- `T_WC(t)` 始终与实测 hand transform 和固定安装 offset 一致。

### RGB 与 depth 具有不同语义

同时启用 RGB 和 depth 时：

```python
rgb, depth, _, _ = fixed_camera.render(
    rgb=True,
    depth=True,
    segmentation=False,
    normal=False,
)
```

对于当前 rasterizer 路径，depth 输出是以 m 为单位的线性深度。即便 depth array 中所有
值都是 finite，其中仍可能包含 far plane 的背景值。实验用下面的条件定义有效表面像素：

```python
valid_depth = (
    (depth > fixed_camera.near)
    & (depth < fixed_camera.far * (1.0 - 1e-3))
)
```

因此，有效 observation 不只是检查 `np.isfinite(depth).all()`，还要求：

- RGB 是非空 `uint8`，shape 为 `(H, W, 3)`；
- depth 是 floating-point array，shape 为 `(H, W)`；
- 在当前 renderer path 上，两个数组中的所有值都 finite；
- 至少一个 depth pixel 严格位于声明的 clip interval 内。

本讲不引入 segmentation 或 point-cloud processing。这些输出需要各自的 label 和 coordinate
contract，不能被当作 RGB 的无成本扩展。

### 渲染是一条显式分支

`ROBO_GENESIS_RENDER=0` 是 CPU 最小路径。它会打印清晰的 render `SKIP`，不会创建假的
RGB/depth array，并且可以根据实测 hand/link state 绘制示意图。图题必须写明
**measured-state schematic, not a camera frame**。

`ROBO_GENESIS_RENDER=1` 则要求真正执行 Genesis camera path。camera 创建、render、
K/extrinsics 检查、array validation 或 valid-depth 任一失败，都应当让这条路径失败。捕获
错误后画一张 Matplotlib 替代图，却继续声称 camera 已验证，会抹掉本实验要教授的区别。

Matplotlib 仍适合显示 Genesis 返回的 pixel，以及绘制 pose/error trajectory。它与原生
仿真画面互补，而不是替代后者。

## 配套实验：可达与不可达位姿

实验会保留源课程中的重要结构：运行前预测、Plane、Franka、target marker、fixed camera、
reachable/unreachable target、动态对照、checkpoint 和 summary；同时加入更严格的 frame、
quaternion、Jacobian 和 camera 证据。实验只使用内置 primitive，不调用后续的 tabletop/YCB
scene builder。

### 运行前先做预测

查看任何输出前，先写下答案：

1. 如果 IK 返回 finite `(9,)` vector，它是否必然已经收敛？
2. 如果 IK residual 低于 tolerance，动态 hand 是否必然已经到达 target？
3. 对 `q_target` 和 `-q_target` 应当报告多大的 orientation error？
4. 哪一个 camera transform 应保持不变，哪一个应发生变化？
5. 如果 `res=(640, 360)`，RGB 和 depth 的 shape 分别应当是什么？
6. 一张看起来合理的 final image 能否证明 position 和 orientation error 都很低？

重点不是猜出精确输出，而是在结果影响判断之前先明确证据合同。

### Scene 与 frame 检查

场景包含 Plane、内置 Franka、reachable-target marker，以及一个便于从画面中识别 camera
motion 的小型 reference primitive。启用渲染时，fixed/wrist camera 都在 build 前声明。

build 后，notebook 会：

- 按名称解析全部 9 个 local DOF，并分开 7 个 arm index 和 2 个 finger index；
- 获取 `hand` link 并读取它的 world-frame pose；
- 读取 q、qdot、joint limit、gain 和 force range；
- 明确 W 和 B 只在本 scene 中重合；
- attach wrist camera 并进行首次 update。

关键的 Scene、entity、camera、build、attachment、IK、control、sampling 和 validation 逻辑
都会在 notebook 中直接呈现。可复用常量可以来自 `robo_genesis`，但实验不能成为某个
experiment runner 的黑盒包装。

### 可达目标的证据

主 target 是一个可达的 world-frame hand pose。求解前先验证 target quaternion 使用
w-x-y-z 并完成归一化。随后，notebook 会：

1. 读取 initial hand pose，计算 initial position/orientation error；
2. 获取完整 `(6, 9)` Jacobian 和 `(6, 7)` arm slice；
3. 使用 `return_error=True` 执行 arm-only IK；
4. 验证完整 candidate、residual、limit、mask 和 finger；
5. 用 FK 预测 candidate 对应的 hand pose；
6. 在 180 个 outer step 中发送已接受的 whole-robot q target；
7. 每步后记录实测 hand position、quaternion 和 joint state；
8. 验证 final error 和完整 finite trajectory。

启用渲染时，实验还会采集 fixed-camera initial/reached frame、reached RGB/depth，以及
wrist initial/final frame，并比较 fixed 与 fresh wrist extrinsics。关闭渲染时，只使用
明确标注的 measured-state fallback 和数值形式的 camera planning 信息。

### Guided reachable interpretation

notebook 会根据当前运行产生的数组动态生成 4 段解释，而不是嵌入预期数值：

1. **坐标系与表示：** 明确 target/measured frame，检查 w-x-y-z normalization 和
   `q`/`-q`，说明哪些量可以直接比较。
2. **Solver 与 FK：** 报告启用的 residual norm、acceptance condition、FK prediction 和
   finger/limit 检查，但不把 candidate 描述成已经执行。
3. **动态执行与 Jacobian：** 比较初末 position/orientation error，描述其 trajectory，并
   把 singular value 结论限制在实测 configuration。
4. **Camera 证据：** 区分 fixed 与 attached observation、array/depth validity，以及 fresh
   extrinsics 是否按预期变化；若关闭渲染，则明确说明没有测试 camera result。

这种顺序可以避免让一张好看的图像成为对本次运行的第一个、也是唯一的解释。

### 不可达目标的证据

第二个 target 被刻意放在工作区域以外较远的位置。它会经过相同的 IK 与 candidate
validation pipeline。预期的**结果类型**是因为 residual 被拒绝，但 notebook 会从当前
array 动态生成实际原因，不会打印写死的 residual。

当 `ik_valid` 为 false 时，正常 control 会被跳过。随后，可选 diagnostic override 会在
明确 warning 下执行 finite best-effort candidate，记录 hand before/after pose，并计算它到
原始 requested target 的 remaining error。fixed-camera final frame 可以展示机器人，但
requested marker 可能位于画面以外；这样的构图不能充当 acceptance test。

四段式 guided interpretation 会追问：

1. 究竟哪些 acceptance condition 失败，哪些只是通过？
2. reachable 与 unreachable solver residual 在各 component 和启用 norm 上有何差异？
3. 如果执行了 diagnostic，hand 实际移动多远，请求的 error 还剩多少？
4. 为什么 finite q、可见运动和没有异常仍不能证明 reachability、path safety 或 task
   success？

## 四个环境与 selective update

最后一个扩展把同样的思路应用到 `B=4` 的复制环境。这里引入的是 batch shape 和
per-environment validation，而不是 throughput benchmark。加速比、采样吞吐和数据记录的
并行性留到 L08。

### 保留 leading dimension

对于 4 个环境，预期 shape 为：

| Quantity | Shape |
|---|---:|
| 当前 whole-robot qpos | `(4, 9)` |
| Target position | `(4, 3)` |
| Target quaternion | `(4, 4)` |
| IK q candidate | `(4, 9)` |
| IK pose residual | `(4, 6)` |
| 实测 hand position | `(4, 3)` |

solver 和 controller check 都应当逐行执行。很小的 mean error 可能掩盖某个失败环境，
因此不能作为 acceptance rule。

baseline 使用 4 个 reachable target 和共享 initial state。经过 220 step 后，每个环境都
必须具有 finite state、accepted IK candidate、低于实验 `0.08 m` threshold 的 position
error，并且 error 小于各自 initial value。较宽松的 batch threshold 是这个 extension 的
操作性合同，不是对 single-environment pose-quality 结论的修改。

### `envs_idx` 选择行，不会创建新的坐标系

selective update 会给 environment 1 和 3 发送两个新 target：

```python
selected_envs = np.asarray([1, 3], dtype=int)
selected_targets = target_positions[selected_envs]

selected_q, selected_residual = franka.inverse_kinematics(
    link=hand,
    pos=selected_targets,
    quat=target_quaternions[selected_envs],
    dofs_idx_local=arm_dofs,
    return_error=True,
    envs_idx=selected_envs,
)
```

这里的 `selected_targets` shape 为 `(2, 3)`，selected candidate shape 为 `(2, 9)`。
行数和行顺序都必须与 `envs_idx` 匹配。environment 0 和 2 保留旧 target，environment 1
和 3 接收新 target。

“没有收到新 command”不等于“被冻结”。untouched environment 仍会在旧 controller target
和 dynamics 作用下继续演化。因此，extension 会检查：

- selected environment 与各自新 target 的最终距离小于 `0.08 m`；
- untouched hand displacement 小于 `0.005 m`；
- untouched retained-target error 的恶化不超过 `0.002 m`。

这些 threshold 用于保留源练习的受控关系，必须在支持的路径上重新验证；它们不是 selective
control 的通用性质。

### Guided batch interpretation

应当逐行阅读 batch 输出：

1. 验证 target、quaternion、candidate、residual 和 measured-state shape；
2. 逐个指出哪些 environment 通过或未通过 IK acceptance；
3. 比较每个 baseline environment 的 initial/final error，而不是只看 mean；
4. 把 selected-target tracking、untouched motion 和 retained-target error 分开。

单个 camera 通常只展示一个 rendered environment 或 viewpoint，不能作为 4 行共同证据。
因此，batch extension 使用 per-environment table 和 measured target-to-hand plot。

## 证据边界与成功标准

只有保持正确的证据范围，本讲实验才算成功：

| 观察 | 支持的结论 | 不支持的结论 |
|---|---|---|
| Finite q 和正确 shape | solver 返回了结构上可用的数据 | IK 已收敛 |
| Residual 低于声明的 tolerance | candidate 通过当前 kinematic acceptance rule | 机器人已经动态到达 |
| FK prediction 靠近 target | candidate 的 kinematic pose 与 target 一致 | controller 已执行该 candidate |
| 实测 error 在 180 step 中下降 | hand 在当前有限时窗中接近 target | 路径无碰撞或具有全局稳定性 |
| 有效 RGB/depth 和 K/extrinsics | 配置的 simulated camera 产生了可用 observation | 相机已经完成真实设备标定 |
| update 后 wrist extrinsics 变化 | attached viewpoint 跟随运动中的 hand | pixel 变化能证明 IK 精度 |
| 4 个 per-env check 全部通过 | 当前 batch 实验满足逐行合同 | batching 总能加速 workload |

single-environment threshold（`0.02 m`、`0.05 rad`）以及 batch/selective threshold 都是
实验验收值。它们不能描述硬件精度、任意 workspace、其他 controller gain 或所有 Genesis
backend。

## 常见 warning 与失败

### 目标与测量使用了不同坐标系

打印每个位姿所属的 frame。确认 world-frame link measurement 使用 `relative=False`，并检查
camera quantity 需要的是 `T_WC` 还是 `T_CW`。不要通过改变符号、直到图看起来合理的方式
修补 frame mismatch。

### Hand 转动不符合预期

检查 target 是否按 w-x-y-z 传入、是否已归一化，以及它的轴是否在预期 frame 中表达。
逐分量 quaternion error 也会误判 `q` 与 `-q`；应使用 shortest-angle metric。

### IK 返回 finite q，但 candidate 被拒绝

这是 solver 的预期结果之一，对 unreachable target 尤其如此。分别检查 position/rotation
residual、启用的 mask、limit 和 finger preservation。不要为了让预设 target 通过而放宽
tolerance。

### 不同 initial guess 产生不同 q

冗余允许这种情况。比较每个 candidate 的 FK pose、limit、residual，以及它到 starting
configuration 的距离。不同的 valid q 不自动等于错误。

### Jacobian 看起来病态

确认选择的是按名称解析出的 7 个 arm column，并确认 Jacobian 采样自报告的
configuration。检查 singular value；诊断时可以尝试附近 starting pose 或更大 damping。
不要把问题称为 gimbal lock，也不要从一个 matrix 推出全局 workspace 结论。

### FK 很好，但 dynamic tracking 很差

检查 candidate 是否传入 `control_dofs_position`、scene 是否按预期时长 step，以及 measured
hand pose 是否在每个 step 后读取。随后再检查 joint limit、force saturation、final joint
error、velocity 和完整 pose-error trace。FK 不包含这些执行影响。

### 不可达目标的诊断执行看起来朝 target 运动了

best-effort candidate 本来就可能减小一部分 error。应报告 actual motion 和 remaining error。
有所改善不等于满足 tolerance，也不能说明 path safety。

### RGB 的宽高似乎交换了

同时打印 `camera.res` 和两个 array shape。`res` 是 `(W, H)`，array index order 则是
`(H, W, ...)`。不要写出只在正方形 test camera 上碰巧通过的 shape assertion。

### `depth` 全部有限，却没有有效的表面 pixel

应用声明的 near/far mask。far-plane background 也可能是 finite。随后检查 camera pose、
clipping plane 和 geometry 是否位于 view 内；不要把整张 finite image 都当作已观测表面。

### 手腕相机没有移动

确认它在 build 前被添加，build 后 attach 到预期 `hand` link，并在机器人运动后调用
`move_to_attach()` 更新。应比较 fresh transform 或 fresh world-to-camera matrix，不能依赖
之前缓存的值。

### 渲染失败

如果明确请求了 rendering，就保留 error 并让 render path 失败。检查 graphics environment、
camera declaration order 和 clean-kernel setting。只有主动选择
`ROBO_GENESIS_RENDER=0` 的运行才可以使用带明确标签的 measured-state schematic。

### 选择性批量更新改变了错误的行

把 `envs_idx`、target shape、返回 q shape 和 command shape 放在一起打印。检查它们的行
顺序，并在 step 后读取每个 environment。记住，unselected environment 仍然会在旧 target
下继续演化。

### 诊断顺序

按下面的依赖顺序检查：

```text
version、clean kernel、requested/actual backend、render mode
  → build boundary 和 camera declaration/attachment
  → frame name、unit、quaternion order 和 norm
  → named arm/finger index、q shape 和 joint limit
  → IK mask、residual 和 acceptance
  → FK prediction
  → controller command、step count 和 measured pose trajectory
  → local Jacobian 证据
  → live camera pose、K/extrinsics、RGB/depth 和 clip mask
  → batch leading dimension 和 per-environment 关系
```

这样能在结构错误被误判为 IK tuning 或 renderer 行为之前找到问题。Genesis MJCF importer
warning 可以记录和解释，但不能成为错误 shape、非有限值、limit violation 或 requested
render 失败的借口。

## 检查点与练习

### 概念检查

不回看表格，回答下面的问题：

1. `T_AB` 执行什么变换？它与 `T_BA` 有什么关系？
2. 为什么 world 和 robot-base frame 可以在本 scene 中重合，但不能在一般情况下等同？
3. 为什么 w-x-y-z 顺序、归一化和 `q`/`-q` 等价是 3 个不同检查？
4. FK 与动态执行一个 FK/IK candidate 有什么区别？
5. 为什么 Franka arm 对 6 维 hand-pose task 是冗余的？
6. 小 Jacobian singular value 在局部意味着什么？为什么它不是 Euler gimbal lock？
7. damping 在 least-squares IK update 中起什么作用？
8. 为什么一个 finite、in-limit 的 q 仍可能无法通过 IK acceptance？
9. Genesis 返回的 IK error 有哪 6 个 component？
10. 哪些证据分别对应 solver residual、FK prediction error 和 dynamic tracking error？
11. 为什么 attached camera 必须在运动后调用 `move_to_attach()`？
12. `res=(W,H)` 和 RGB `(H,W,3)` 怎样描述同一台 camera？
13. 为什么 finite far-plane depth value 不一定是实测表面？
14. 为什么 batch mean 可能掩盖一个失败环境？
15. 为什么没有收到 selective 新 command 的环境仍可能移动？

### 动手练习

从 clean kernel 运行 reachable 和 unreachable 实验，然后完成以下任务：

1. 为 W、B、H 和两个 camera 绘制 frame chain，并标注 error calculation 中每个 target 和
   measured pose；
2. 验证 target quaternion norm，并用数值说明改变其符号不会改变 shortest-angle error；
3. 报告 full/arm Jacobian shape 和实测 configuration 处的 singular value，但不设置通用
   singularity threshold；
4. 列出每个 IK acceptance condition 及其当前 pass/fail 结果；
5. 带单位比较 solver residual、FK prediction error、initial execution error 和 final
   execution error；
6. 使用 rejection reason、diagnostic motion 和 remaining error 解释 unreachable case，
   而不是只看 image；
7. 启用渲染时，验证 fixed/wrist transform behavior、K、RGB/depth shape、dtype 和 valid
   depth；否则列出所有被 skip 的 camera check；
8. 对 B=4 逐行报告 baseline 和 selective-update 结果，并说明 aggregate mean 为什么不够。

扩展练习：保持 target 不变，只把 IK initial guess 改为另一个有效 arm pose。比较 candidate
q、FK pose、residual 和它到原 q 的距离。目标是观察冗余与数值搜索，而不是把某个姿态评为
普遍最优。

不要给 scene 加入 table、YCB object、grasp action 或 collision planner。这些改动会改变
问题，应当留给后续课程。

## 小结与后续衔接

- Pose 由具名 frame 中的 position 和 orientation 共同组成。本讲使用 world-frame hand
  target 和 Genesis w-x-y-z unit quaternion。
- `q` 与 `-q` 表示同一个旋转；shortest-angle quaternion error 可以防止表示符号变成
  虚假的物理误差。
- FK 把 q 映射为 world-frame link pose；Jacobian 把 joint velocity 映射为局部 hand
  spatial velocity，其 singular value 只描述当前 configuration。
- 7-DOF arm 求解 6 维 pose task 时存在冗余。IK 可以不唯一，并受 initial guess、mask、
  damping 和 limit 影响。
- 阻尼最小二乘可以正则化局部求解，但不能让不可达 target 变得可达，也不会产生
  collision-free path。
- finite solver output 只是 candidate。只有通过 shape、finiteness、limit、finger 和启用
  residual 检查后才能接受。
- Solver residual、FK prediction 和 dynamic tracking 是不同证据。accepted target 仍需
  L04 controller 和 `scene.step()` 才能成为运动。
- Fixed camera 保持 world pose；wrist camera 把实测 hand pose 与固定安装关系组合起来，
  并且必须在运动后刷新。
- Genesis 使用 `res=(W,H)` 和按 `(H,W,...)` 排列的 image array；vertical FOV、K、
  world-to-camera extrinsics、near/far 和 valid depth 都属于 observation contract。
- Batched IK 保留 leading environment dimension。selective command 和 acceptance 必须
  逐环境检查，不能被 mean 掩盖。

L06 会把这些 frame 和 camera contract 放入包含获批物体的 tabletop task scene。L07 会把
pose target 串成 scripted expert，并添加 motion/grasp logic，而不会把 IK 当作 path
planning。L08 会为了 throughput、同步 observation 和 data recording 再次使用 batched
environment。上述后续结论都不能由 L05 的一次 pose reach 直接推出。

## 参考资料

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  — 官方用户文档和 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  — 本课程锁定的精确引擎版本。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — 版本锁定的 FK、Jacobian、inverse-kinematics、state 和 control API 行为。
- [Genesis 1.3.3 inverse-kinematics solver 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/solvers/rigid/abd/inverse_kinematics.py)
  — damped least-squares update、mask、tolerance、limit 和 best-candidate 行为。
- [Genesis 1.3.3 `Camera` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — resolution/FOV、transform、intrinsic/extrinsic、attachment、render、depth 和 clipping
  语义。
- [Genesis 1.3.3 内置 Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — 本讲使用的机器人模型、joint、range 和 actuator 配置。
- [Modern Robotics，Lynch 与 Park](https://modernrobotics.northwestern.edu/nu-gm-book-resource/)
  — frame、rigid transform、正逆运动学、Jacobian、冗余与奇异性的开放教材背景。
- [OpenCV camera calibration and 3D reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
  — pinhole intrinsic/extrinsic projection model 和 camera coordinate terminology 的参考；
  Genesis 特定约定仍以以上锁定版本 Genesis 源码为准。
