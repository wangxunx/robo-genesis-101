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

> **课程状态：** 重构后的双语讲义和可执行 notebook 均已提供。notebook 已在 CPU 和
> 参考 AMD ROCm 平台上通过干净 kernel 验证，其中包括一个 fixed-camera RGB/depth
> 路径；由于 CPU 仍是本讲的最低硬件要求，L05 状态为 `cpu-verified`，但这不表示本讲
> 已经 `published`。

## 本讲定位

L04 从一个关节目标出发，沿着位置控制、执行器限制、动力学和 `scene.step()`，观察它
怎样变成真实运动。本讲进一步追问：当任务用笛卡尔空间描述时，这个关节目标从哪里来？

> 已知 Franka 的关节配置时，怎样求出 hand 的位姿？已知期望 hand 位姿时，怎样求出并
> 验证关节目标，再通过 L04 控制器执行它，测量实际发生的结果？

这两个问题分别对应正运动学（forward kinematics，FK）和逆运动学（inverse
kinematics，IK）。它们在关节空间与机器人末端执行器的位姿之间建立联系。最后的简短
章节会添加一个固定相机，让同一个场景还能产生 RGB 与 depth 观测。

本讲包含三条短链：

```text
当前 q  ──FK──>  当前末端位姿

目标末端位姿  ──IK + residual 检查──>  q goal
q goal  ──L04 位置控制 + scene.step()──>  实测末端位姿

当前场景状态  ──固定相机──>  RGB + depth
```

不要混淆这些箭头。FK 预测位姿，但不会让机器人运动；IK 返回关节候选，但不会执行
控制器；相机图像展示场景，但不能证明某项数值误差已经达到阈值。

开始前，你应当能够：

- 解释 `init → declare → build → step/read` 生命周期；
- 找出 Franka 的 7 个 arm DOF 和 2 个 finger DOF；
- 区分状态重置与位置控制目标；
- 检查数组 shape、单位与数值有限性。

本讲不需要桌子、抓取物体、状态机、数据集或学习策略。L06 会把这条关节空间/任务空间
联系扩展到批量环境，L07 再加入抓取场景。

### 120 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–10 分钟 | 把 L04 控制重新连接到任务空间目标 | 画出 q、位姿、控制器与相机之间的关系 |
| 10–25 分钟 | Hand link、世界坐标系位姿和 `wxyz` 四元数 | 正确读取目标位姿，不混淆坐标系或四元数顺序 |
| 25–42 分钟 | 正运动学 | 解释给定 q 会预测出怎样的位姿 |
| 42–62 分钟 | 逆运动学与 residual | 判断返回的候选是否可以接受 |
| 62–88 分钟 | IK → FK 预测 → 动态执行 | 比较目标、预测和实测位姿 |
| 88–100 分钟 | 一个固定相机 | 获取 RGB/depth 并核对 shape |
| 100–112 分钟 | 不可达目标 | 根据 residual 拒绝有限的 best-effort 候选 |
| 112–120 分钟 | 检查点、练习与 L06 衔接 | 复述证据链及其边界 |

## 学习目标

完成 L05 后，你应当能够：

1. 把末端位姿描述为具名坐标系中的 position 与 orientation，并识别 Genesis 使用的
   w-x-y-z 四元数顺序；
2. 用 `q → FK → pose` 预测 Franka hand 位姿，同时解释为什么 FK 计算不会移动动态场景；
3. 用 `target pose → IK → q candidate` 求解目标，读取 6 维 IK residual，并避免把有限 q
   当作收敛证明；
4. 让已接受的 q 经过 L04 位置控制循环，区分 IK residual、FK prediction error 与实测
   execution error；
5. 拒绝明显不可达的目标，并且不把它的候选发送给控制器；
6. 添加一个固定相机，渲染 RGB 与 depth，并把 `res=(W, H)` 与返回的 `(H, W, 3)`、
   `(H, W)` 数组对应起来。

## 末端位姿

### 本讲以 hand link 作为末端执行器

机器人模型包含许多 Link。L05 把 Franka 的 `hand` Link 作为末端执行器：

```python
hand = franka.get_link("hand")
```

末端位姿由两部分组成：

```text
position     [x, y, z]       单位为 m
orientation  [w, x, y, z]    单位四元数
```

这些数值只有与参考坐标系放在一起才有意义。在这个简单的固定基座场景中，目标位置、
目标姿态和实测 hand 位姿都使用世界坐标系。Genesis 可以显式请求这种测量：

```python
measured_position = hand.get_pos(relative=False)
measured_quaternion = hand.get_quat(relative=False)
```

`relative=False` 请求世界坐标系中的 Link 位姿，因此实测位置可以直接与世界坐标系中的
目标位置比较。如果某个量位于相机坐标系或移动基座坐标系，直接相减就是错误的。

本 notebook 中的 Franka 使用默认固定姿态，因此 base 恰好与 world frame 重合。这只是
当前场景的性质，不是通用恒等关系。

### Genesis 使用 w-x-y-z 四元数顺序

实验中的目标姿态是：

```python
target_quaternion = np.array([0.0, 1.0, 0.0, 0.0])  # w, x, y, z
```

有些库使用 x-y-z-w。如果不重新排列就把数值复制到另一种约定中，旋转含义会发生改变。
四元数还必须具有单位范数。Notebook 使用一个短 helper，先检查 shape 和有限性，再归一化
很小的浮点漂移：

```python
def normalize_wxyz(quaternion):
    quaternion = np.asarray(quaternion, dtype=float)
    if quaternion.shape != (4,) or not np.isfinite(quaternion).all():
        raise ValueError("expected a finite wxyz quaternion with shape (4,)")
    norm = np.linalg.norm(quaternion)
    if norm < 1e-12:
        raise ValueError("a zero quaternion does not define an orientation")
    return quaternion / norm
```

单位四元数 `q` 和 `-q` 表示同一个物理旋转，因此姿态误差必须忽略这个符号选择。对于
已经归一化的四元数，最短角误差为：

```python
def quaternion_angle_error(measured_wxyz, target_wxyz):
    measured = normalize_wxyz(measured_wxyz)
    target = normalize_wxyz(target_wxyz)
    cosine_half_angle = np.clip(abs(np.dot(measured, target)), 0.0, 1.0)
    return float(2.0 * np.arccos(cosine_half_angle))
```

这就是主实验需要的全部四元数计算。本讲不要求欧拉角，也不推导通用坐标变换。

## 正运动学：从 q 到位姿

正运动学回答：

> 机器人处于关节配置 q 时，末端执行器在哪里、朝向哪里？

对于 hand Link，可以把映射写成：

```text
q  ──FK──>  (hand position, hand orientation)
```

对于确定的机器人模型，这个映射是确定的。它是一项计算，不是控制命令。为候选 q 调用
FK，不会改变当前 q，不会施加执行器作用力，不会推进仿真时间，也不能证明控制器能够
跟踪这个候选。

Genesis 可以预测给定 q 对应的 hand 位姿：

```python
fk_positions, fk_quaternions = franka.forward_kinematics(
    q_candidate_raw,
    links_idx_local=[hand.idx_local],
)
predicted_position = to_numpy(fk_positions).reshape(3)
predicted_quaternion = to_numpy(fk_quaternions).reshape(4)
```

返回值是所请求 Link 在世界坐标系中的位姿。发送任何控制命令之前，就可以把它与世界
坐标系中的目标位姿进行比较。

::: warning Genesis 1.3.3 调用顺序
在锁定的 Genesis 版本中，`forward_kinematics()` 目前会复用第一次 IK 调用所初始化的
scratch storage。因此，配套 notebook 会先讲解 FK，但实际调用会紧跟在第一次 IK 求解
之后。这是特定版本的 API 生命周期细节，不表示 FK 在数学上依赖 IK。
:::

## 逆运动学：从位姿到 q

逆运动学提出相反的问题：

> 哪一组关节配置可以把末端执行器放到期望位姿？

```text
目标 hand 位姿  ──IK──>  一个 q candidate
```

“一个”很重要。Franka 使用 7 个 arm joint 来满足 6 维 hand 位姿，不同起始姿态下的数值
IK 可能得到不同的有效配置。L05 不枚举所有解，也不推导 solver，只需要掌握 3 个事实：

- IK 是数值搜索，不是直接保证；
- joint limit 和初始配置会影响结果；
- 返回的 residual 说明候选是否满足目标位姿 tolerance。

### 同时读取候选与 residual

主实验使用 7 个 arm DOF 求解，同时保持 finger 的当前状态：

```python
q_candidate_raw, ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=target_position,
    quat=target_quaternion,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=position_tolerance,
    rot_tol=rotation_tolerance,
    return_error=True,
)
```

对于这个非批量 Franka，Genesis 返回 shape 为 `(9,)` 的 whole-entity q candidate，以及
shape 为 `(6,)` 的 error vector：

```text
ik_error[:3]  position residual vector，单位为 m
ik_error[3:]  rotation residual vector，单位为 rad
```

实验分别计算两个向量的 L2 norm，并与显式 tolerance 比较：

```python
q_candidate = to_numpy(q_candidate_raw).reshape(-1)
ik_error = to_numpy(ik_error_raw).reshape(-1)

position_residual = float(np.linalg.norm(ik_error[:3]))
rotation_residual = float(np.linalg.norm(ik_error[3:]))

ik_valid = bool(
    q_candidate.shape == (9,)
    and ik_error.shape == (6,)
    and np.isfinite(q_candidate).all()
    and np.isfinite(ik_error).all()
    and position_residual <= position_tolerance
    and rotation_residual <= rotation_tolerance
)
```

锁定版本 Genesis 的默认值是 position `5e-4 m`、rotation `5e-3 rad`。Notebook 会显式
传入这两个值，让 acceptance rule 直接可见。

Shape 和有限性检查是必要条件，却不是充分条件。不可达目标仍可能返回有限的 best-effort
q，只有 residual 才能说明它没有达到目标 tolerance。

### IK 不是运动规划

IK 产生的是 endpoint configuration，不是到该 endpoint 的无碰撞 trajectory。L05 场景
刻意只包含 Plane、Franka 和不参与碰撞的 target marker。L06 会将控制问题批量化，
L07、L08 再加入任务几何与安全 waypoint 逻辑；L05 的低 residual 不能被描述为抓取成功或安全路径。

## 求解、预测、执行与测量

可达实验沿用源课程中的世界坐标系目标：

```python
target_position = np.array([0.45, 0.0, 0.35])
target_quaternion = normalize_wxyz([0.0, 1.0, 0.0, 0.0])
```

随后依次执行 4 个阶段。

### 1. 求解 IK

调用 `inverse_kinematics(..., return_error=True)`，再应用直接可见的 acceptance rule。如果
任一 residual 超过 tolerance，就在进入控制器之前停止。

### 2. 使用 FK 预测

对已接受的 q candidate 调用 `forward_kinematics()`，将预测出的 hand 位姿与目标比较。
这一步检查候选在运动学上的含义，仍不会让仿真机器人运动。

### 3. 通过 L04 控制器执行

沿用 L04 已经建立的动态路径：

```python
for _ in range(180):
    franka.control_dofs_position(q_candidate)
    scene.step()
```

不要用 `set_dofs_position(q_candidate)` 代替这个循环。那样会瞬移状态，并从实验中移除
控制器和动力学。

Notebook 会在每个 step 后采样 hand position 与 orientation。一张简洁的 error 曲线用来
展示有限控制时窗内的实测位姿是否接近目标。

### 4. 测量最终位姿

步进完成后，读取世界坐标系 hand 位姿并计算 position/orientation error：

```python
measured_position = to_numpy(hand.get_pos(relative=False)).reshape(3)
measured_quaternion = to_numpy(hand.get_quat(relative=False)).reshape(4)

position_error = float(np.linalg.norm(measured_position - target_position))
orientation_error = quaternion_angle_error(
    measured_quaternion,
    target_quaternion,
)
```

实验为当前场景、控制器配置和 180-step 时窗设定的操作性阈值是 position error
`<0.02 m`、orientation error `<0.05 rad`。它们不是对真实 Franka 精度或所有目标的声明。

### 三种测量回答三个问题

| 证据 | 回答的问题 | 不能证明什么 |
|---|---|---|
| IK residual | 数值候选是否满足位姿 tolerance？ | 机器人是否已经运动？ |
| FK prediction error | 该 q 在运动学上预测出怎样的 hand 位姿？ | 控制器是否跟踪了 q？ |
| 实测 execution error | 动态 hand 在步进后最终位于哪里？ | 路径是否无碰撞，或抓取是否成功？ |

明确使用这些名称，比围绕它们搭建庞大的 validation framework 更有助于理解。

## 简要介绍固定相机

相机是连接后续视觉观测的一座小桥，不是 L05 的重点。Notebook 只使用一个观察全局的
固定相机。和其他 Scene 组件一样，它必须在 `scene.build()` 前声明：

```python
camera = scene.add_camera(
    res=(640, 360),
    pos=(1.2, -1.2, 1.0),
    lookat=(0.35, 0.0, 0.35),
    fov=45,
    GUI=False,
)
scene.build()
```

`pos` 和 `lookat` 都是世界坐标系中的点，`fov` 控制视野宽窄。本讲不推导 pinhole model，
不检查 camera intrinsics/extrinsics，不附着 wrist camera，也不讨论标定。

### RGB 与 depth

启用渲染后，一次调用就会返回本讲使用的两种观测：

```python
rgb, depth, _, _ = camera.render(rgb=True, depth=True)
rgb = to_numpy(rgb)
depth = to_numpy(depth)
```

Genesis 使用 `res=(width, height)` 声明相机，而图像数组先按行、再按列索引：

```text
camera res:  (W, H)
RGB shape:   (H, W, 3)
depth shape: (H, W)
```

对于 `res=(640, 360)`，预期 shape 是 `(360, 640, 3)` 和 `(360, 640)`。RGB 保存颜色值，
depth 保存当前 renderer 路径产生的模拟距离值。Notebook 会检查 shape、基本 dtype 和
有限性，再显示一组 RGB/depth。

CPU 最小 FK/IK 路径不强制要求渲染。使用 `ROBO_GENESIS_RENDER=0` 时，notebook 会明确
打印 `SKIP`，不会创建伪造的 camera array 或替代图。使用 `ROBO_GENESIS_RENDER=1` 时，
camera 失败就是所请求路径的真实失败。

图像能够展示机器人、marker 与最终姿态，但 IK residual 和 execution error 仍必须来自
solver 与实测状态。

## 配套实验

Notebook 会刻意贴近源 Module 04 实验，只包含一个 Scene、一个可达目标、一个固定相机和
一个不可达负例。

### 运行前先预测

执行 notebook 前先写下答案：

1. 如果 IK 返回有限的 `(9,)` q，它是否必然已经收敛？
2. 对 `q_candidate` 调用 FK 会不会让机器人运动？
3. 如果 IK residual 很小，动态 hand 是否必然已经到达目标？
4. 对于 `res=(640, 360)`，预期的 RGB 与 depth shape 分别是什么？

### 运行可达目标

Notebook 会：

1. 初始化选定的 backend 与可选 render 分支；
2. 声明 Plane、Franka、target marker 和可选 fixed camera；
3. 构建 Scene，并读取初始 q 和世界坐标系 hand 位姿；
4. 求解可达目标的 IK，检查两项 residual norm；
5. 使用 FK 预测候选 hand 位姿；
6. 通过 position control 执行已接受的 q，共运行 180 个 step；
7. 读取实测 hand 位姿，并绘制简洁的 error history；
8. 在请求渲染时获取一组 RGB/depth。

打印输出应当让你直接追踪 target pose → IK candidate → FK prediction → controller →
measured pose，而不必在大量 helper table 或自动生成的解释中寻找主线。

### 拒绝不可达目标

第二个目标被刻意放到远处：

```python
unreachable_position = np.array([2.0, 0.0, 2.0])
```

对它运行相同 IK 调用和 residual 检查。Genesis 可能返回有限 q，但 position 或 rotation
residual 应当超过 tolerance，因此正常结果是：

```text
IK valid: no
command sent: no
```

不要执行被拒绝的候选。这个负例已经证明了关键事实：返回的 q 只是候选，residual 决定
它是否满足当前位姿请求。

## 常见失败与简短诊断顺序

### Hand 姿态不符合预期

检查目标是否使用 w-x-y-z 顺序、是否具有单位范数，以及是否与实测 hand 位姿使用相同的
世界坐标系。不要不断交换分量，直到画面看起来合理为止。

### FK 看起来让机器人运动了

检查它附近的代码。FK 本身只是一项计算；改变动态状态的是后续 controller command、
state reset 或 `scene.step()`。

### IK 返回有限 q，但 `ik_valid` 为 false

这可能是正常的 best-effort 结果。分别检查 position 与 rotation residual。不要只为了让
不可达目标通过，就放宽 tolerance。

### FK prediction 很准确，但 execution error 很大

确认已接受的 q 确实进入 `control_dofs_position()`，Scene 按预期时长完成步进，而且之后
才读取实测位姿。随后检查 error history 和 joint tracking。FK 不包含动态跟踪过程。

### RGB 的宽高似乎反了

记住，相机配置使用 `(W, H)`，数组使用 `(H, W, ...)`。把 `camera.res`、`rgb.shape` 和
`depth.shape` 放在一起打印。

### 渲染失败

如果明确请求了 rendering，就保留错误，并检查 graphics environment 和 build 顺序。如果
主动关闭 rendering，则只报告数值 FK/IK 路径以及明确的 camera `SKIP`。

按照以下顺序诊断：

```text
版本、backend 与 render mode
  → build boundary 与 hand link
  → world frame、单位与 quaternion 顺序
  → q 和 residual shape
  → IK residual 与 acceptance
  → FK prediction
  → controller、step 数量与 measured pose
  → 可选 RGB/depth shape
```

## 检查点与练习

### 概念检查

不要回看前文，回答以下问题：

1. FK 的输入和输出是什么？
2. IK 的输入和输出是什么？
3. 为什么有限 q 不能证明 IK 已经收敛？
4. IK residual 与实测 execution error 有什么区别？
5. 为什么 FK prediction 不能证明 controller 已经执行 q？
6. 为什么 target pose 与 measured pose 必须使用同一个参考坐标系？
7. Genesis 使用哪一种四元数分量顺序？
8. `res=(640, 360)` 对应怎样的 RGB/depth shape？

### 动手练习

基线实验通过后，只把可达目标的 x 坐标增加 `0.03 m`，orientation 保持不变。

运行前，先预测目标是否仍然可达。然后报告：

1. IK position/rotation residual；
2. FK 预测的 position/orientation error；
3. 经过 180 个 step 后，最终实测 position/orientation error；
4. camera shape 合同是否发生变化。

用 controller 与有限观测窗口解释 FK prediction 和实测 execution 之间的差异。不要添加
桌子、物体、抓取、batch dimension 或新相机；这些改动会形成另一讲内容。

## 小结与后续衔接

- 末端位姿是具名坐标系中的 position 与 orientation。L05 使用世界坐标系 hand 位姿和
  Genesis 的 w-x-y-z 四元数顺序。
- FK 把 q 映射为预测 hand 位姿，但不会让机器人运动。
- IK 把目标位姿映射为一个 q candidate。Shape 和有限性还不够；position/rotation
  residual 决定当前请求是否通过。
- 已接受的候选仍要经过 L04 位置控制和反复调用 `scene.step()`，执行后再测量 hand 位姿。
- IK residual、FK prediction 和实测 execution error 回答不同的问题。
- 不可达目标仍可能返回有限的 best-effort q。应当拒绝它，不要发送给控制器。
- 一个固定相机提供 RGB 与 depth；`res=(W, H)` 对应 RGB `(H, W, 3)` 和 depth `(H, W)`。

L06 会在并行环境中应用同一套 IK 和控制合同。L07 会把受控机器人放入桌面抓取场景，
L08 再把多个位姿目标组织成脚本化专家。这些讲次都不能把 IK 当作无碰撞 path planner，
也不能把低 residual 当作抓取成功。

## 参考资料

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  — 官方用户文档和 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  — 本课程锁定的精确引擎版本。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — 版本锁定的 FK、IK、Link state 和 control API 行为。
- [Genesis 1.3.3 `Camera` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — 版本锁定的 camera declaration、resolution、rendering 和 depth 行为。
- [Genesis 1.3.3 内置 Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — 本讲使用的机器人模型、joint、limit 和 actuator 配置。
- [Modern Robotics，Lynch 与 Park](https://modernrobotics.northwestern.edu/nu-gm-book-resource/)
  — frame、正运动学、逆运动学与机器人运动的开放教材背景。
