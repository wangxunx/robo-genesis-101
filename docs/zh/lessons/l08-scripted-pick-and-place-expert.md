# L08 · 脚本化抓取放置专家

> **L08 第二篇：** 本文把前一篇的数据来源选择落实为一个可执行的 banana-to-bowl 专家。
> 你可以返回[演示数据获取方法](./l08-demonstration-acquisition-methods.md)或
> [本讲导览](./l08-demonstration-acquisition-and-scripted-experts.md)。

## 从任务意图到可执行 rollout

“把香蕉放进碗里”只是任务描述，还不是机器人命令。专家需要连接多个层次：

```text
任务：banana → bowl
  → 抓取配置：方向、高度、闭合力
  → 阶段目标：hand pose 与 gripper intent
  → 运动基元：plan、descend、hold、interpolate
  → 逐步命令与实测状态
  → 最终 containment 结果
```

实现的真相源是 `robo_genesis.grasp_demo`。讲义会展开它的状态机与公式，让 notebook 中的
`run_pick_place()` 不至于成为黑箱，同时避免复制出第二套完整控制实现。

## 两个小对象定义任务合同

### `TaskSpec`：要完成什么？

Task spec 指定要抓取的物体、放置目标和水平方向容差：

```python
from robo_genesis.grasp_demo import TaskSpec

task = TaskSpec(
    pick_object="011_banana",
    place_target="024_bowl",
    success_tol=0.06,
)
```

`place_target` 也可以是一组桌面 `(x, y)` 坐标，但核心实验使用 bowl。具名容器既允许专家
读取碗的当前位置，也允许结果判据使用碗当前的 AABB。

### `GraspProfile`：怎样抓这个物体？

Task 决定抓“哪个”物体，grasp profile 则决定夹爪如何接触该物体的几何形状：

```python
from robo_genesis.grasp_demo import GraspProfile
from robo_genesis.scene_config import TABLE_TOP_Z

banana_profile = GraspProfile(
    yaw_offset=90.0,
    grasp_hand_z=TABLE_TOP_Z + 0.105,
    close_force=-10.0,
    center_align=False,
)
```

Banana profile 使用 90 度 yaw offset、调优后的固定 hand height 和 `-10 N` 闭合力。Lemon、
plum 等近似球形的物体使用 `center_align=True`，从静置后的物体 AABB 推导抓取高度。
Profile 把物体特定的抓取假设显式写出，避免把这些参数隐藏在阶段代码里。

## 七阶段专家

专家会先让场景静置。静置用于准备 episode，不计入动作阶段。随后依次执行七个阶段：

| 阶段 | 任务目的 | 共享运动基元 | 可观察事件 |
|---|---|---|---|
| 1. pregrasp | 张开手指，到达物体上方 | IK 后调用 `plan_path()` | Hand 到达抓取点上方 |
| 2. descend | 避免横向扫过，沿竖直方向靠近 | 沿下降 z waypoint 重复求 IK | Hand 下移，物体仍留在桌面 |
| 3. grasp | 建立接触并夹持物体 | 手臂位置保持，手指使用力控制 | 手指闭合，物体可以跟随 hand |
| 4. lift | 离开桌面 | 保持手指力，并使用受限增量的手臂目标 | 物体底部高于桌面 |
| 5. transport | 把物体搬到碗上方 | 保持手指力，并使用受限增量的手臂目标 | 物体 xy 接近碗的 xy |
| 6. release | 让物体落入碗内 | 手臂保持，手指回到张开位置目标 | 物体与 hand 分离 |
| 7. retreat | Hand 离开并等待物体稳定 | Direct retreat 后短暂 settle | 可以检查最终物体与碗的几何关系 |

这个顺序编码了任务语义：下降前闭合会抓空；提起前搬运可能撞到桌面；释放前就检查
containment，则检查到的仍是被夹在碗上方的物体。

## 把物体几何转换成抓取位姿

### Top-down 抓取方向

专家读取物体静置后的 yaw，再加上 profile offset：

```text
grasp_yaw = object_yaw + profile.yaw_offset
grasp_quat = quaternion(roll=180°, pitch=0°, yaw=grasp_yaw)
```

180 度 roll 让 hand 朝下，额外 yaw 则决定夹爪在桌面平面中的方向。对于细长的香蕉，
90 度 offset 会让夹爪横跨较短方向闭合，而不是顺着香蕉长度夹持。

L05 已经解释过世界坐标位姿、Genesis `wxyz` 四元数和 IK。这里的 IK 是任务阶段中的一个
环节：`_ik()` 把每个目标 hand pose 转成关节候选值，随后由所选运动基元决定如何接近它。

### 固定高度与几何自适应高度

香蕉使用针对当前任务调优的固定 hand-link height。对于近似球形物体，如果下降到同一个
高度，finger crossbar 可能碰到物体顶部并将其推走。自适应 profile 会测量静置后的 AABB：

```text
center_z      = (z_min + z_max) / 2
half_height   = (z_max - z_min) / 2
fingertip_z   = center_z - drop_fraction × half_height

z_from_jaws  = fingertip_z + hand_to_fingertip
z_from_clear = z_max + palm_clearance

grasp_hand_z = max(z_from_jaws, z_from_clear)
```

第一个候选值把 fingertip 中线对准物体中心稍下方，第二个候选值让 palm 和 crossbar 高于
物体顶部；取较高者即可同时满足两个条件。这个公式能根据静置后的物体高度调整一类 profile，
但不能取代对具体物体的实际验证。

## 为每个阶段匹配运动基元

### 规划张开夹爪时的接近路径

Pregrasp 是唯一调用 `plan_path()` 的阶段。Genesis 1.3.3 当前接口默认使用 `RRTConnect`，
除非显式传入 `ignore_collision=True`，否则会执行碰撞检查。共享专家保留碰撞检查，并在
手指张开时执行规划得到的关节 waypoint。

这里适合使用规划器，是因为手臂初态可能离物体较远，而且尚未携带任何物体。到达 pregrasp
之后，接近动作具有更明确的任务约束：沿竖直方向靠近已知物体，而不是在物体附近直接发送
一个远端关节目标，让动态执行产生横向扫动。

### 沿笛卡尔 z waypoint 下降

Descend primitive 保持 xy 和 orientation 不变，从 pregrasp 高度向 grasp height 采样 z。
每个目标位姿都重新求解 IK，并在每次关节命令后推进仿真。这样，目标中的笛卡尔竖直接近
会直接体现在运动基元里。

两种做法的区别是：

```text
一个远端 IK 目标 + 立即发送命令
    动态执行时可能让 hand 横向扫过

多个固定 xy、逐步下降 z 的目标
    显式表达期望的竖直接近路径
```

### 保持手臂位置，用力控制手指

在 grasp 和 transport 期间，手臂继续使用 position control，两个 finger DOF 则接收 force
command。位置目标描述关节要去哪里；物体接触阻止手指到达完全闭合位置后，力命令仍能维持
夹持力。

力的符号与限制由具体实现决定。当前 profile 中，两个手指都接收该 Franka 模型所需的负
`close_force`，而 scene builder 已经配置好 actuator force range。

在后续学习接口中，专家仍把 9 维 action 的最后两个 finger component 记录成 open/closed
位置目标。这样可以保持 action representation 一致，即使实际执行夹持时的低层模式是力控制。
执行器控制模式与记录动作语义彼此相关，却不是同一个概念。

### 搬运物体时限制命令目标增量

Lift 和 transport 使用 `_goto_interp()`，因为此时物体已经被夹住。设实测手臂初态为
`q_start`，IK 目标为 `q_goal`，并定义：

```text
Δq∞ = max(abs(q_goal - q_start)).
```

实现采用：

```text
n = max(MOVE_MIN_STEPS, ceil(Δq∞ / MOVE_MAX_DQ))
```

然后依次发送线性序列：

```text
q_i = q_start + (q_goal - q_start) × i/n,  i = 1, ..., n.
```

因此，相邻两个 commanded arm target 的 infinity norm 差值不会超过 `MOVE_MAX_DQ`。当前
常量为 `MOVE_MAX_DQ = 0.006 rad`、`MOVE_MIN_STEPS = 40`，ramp 结束后还会短暂保持目标。

这条结论描述的是 command schedule。实测速度和加速度仍取决于控制器 gain、force limit、
接触、求解器行为和仿真时间步。Notebook 将直接验证命令增量上界并观察 measured trace，
不会沿用其他环境中的历史 acceleration 或 slip 数字。

## 命令动作与实测状态

每个控制 step 中，recorder hook 会收到一个 9 维 commanded action，同时读取 Franka 当前
的 9 维 qpos：

```text
state_t  = measured [arm_q(7), finger_q(2)]
action_t = commanded [arm_target(7), finger_target(2)]
```

规划中的 L08 notebook 只把这些值保存在内存中。最小 recorder 只承担一个职责：

```python
from robo_genesis.course_utils import to_numpy

class TraceRecorder:
    def __init__(self, bundle):
        self.bundle = bundle
        self.states = []
        self.actions = []

    def on_step(self, action):
        state = self.bundle.franka.get_qpos()
        self.states.append(to_numpy(state).reshape(-1))
        self.actions.append(to_numpy(action).reshape(-1))
```

Hook 在发送对应 command、推进模拟器之前读取 state。这是一种 transition alignment 选择，
还不是完整的数据集 schema。L09 将定义 timestamp、图像采样、降频、episode boundary 和
持久化字段。

Shape 相同不代表数值相同。Tracking error、接触、actuator limit 和控制器的有限响应都会让
实测 qpos 与请求目标产生差异。因此，轨迹应检查长度一致、shape 为 `(T, 9)`、数值全部
finite，并确认运动期间存在非零 command/state 差值。

## 判断香蕉是否进入碗中

Release、retreat 和 settle 结束后，`check_success()` 会从两个方面检查 container target。

首先，根据物体与碗当前中心位置计算水平关系：

```text
horizontal_distance = norm(object_xy - bowl_xy)
allowed_radius = min(task.success_tol, bowl_rim_radius)
within_footprint = horizontal_distance < allowed_radius
```

Bowl rim radius 来自其当前 AABB 较短的水平边长。随后，比较 banana AABB bottom 与 bowl
AABB top：

```text
inside_bowl = object_aabb_bottom_z < bowl_rim_z - rim_margin
```

只有两个布尔量都为 true，rollout 才算成功：

```text
success = within_footprint and inside_bowl
```

之所以使用香蕉底部，是因为细长物体可能只有一部分落入碗中，而中心仍高于碗沿。分别打印
两个分量也能让失败原因更清楚：物体可能在水平方向错过碗口，也可能仍然高于碗沿。

这套 predicate 就是当前 bowl 配置下的操作性任务定义。专家释放物体并等待静置后才执行
检查，因此结果能够直接回答本讲的任务问题。

## 配套实验

Notebook 将在一个 clean kernel 中只运行一个固定任务：

```python
task = TaskSpec("011_banana", "024_bowl")
success, frames = run_pick_place(
    bundle,
    task,
    save_frames=render_enabled,
    recorder=trace,
)
```

Notebook 默认使用 `ROBO_GENESIS_RENDER=1`。在这条正常学习路径中，`run_pick_place()` 会
保存 8 张 world-camera 图像：静置后的起点，加上每个阶段完成后的画面。无法使用渲染栈的
学习者可以显式设为 `0`；这条 fallback 不创建相机，但仍会执行完整 rollout、生成
action/state trace 与数值图、展开两项 containment 分量并检查结果。预期图像 tag 顺序为：

```text
00_start
01_pregrasp
02_reach
03_grasp
04_lift
05_above_target
06_release
07_done
```

Montage 应当让阶段顺序在视觉上清楚可读；最终 notebook 结果仍由数值轨迹与 containment
检查决定。

## 按失败阶段诊断

按照状态机顺序排查，不要同时修改多个参数：

1. **Task 或 profile 错误：** 打印 object key、target、yaw offset、height strategy 与
   closing force；
2. **Pregrasp 未完成：** 检查当前 object pose、目标 hand pose、IK candidate 和 path
   planning 结果；
3. **物体在下降时被碰走：** 检查 jaw yaw、AABB-derived grasp height、palm clearance 和
   预期 fixed-xy 路径；
4. **物体在 lift/transport 时滑脱：** 确认 finger force 持续施加，并检查相邻 commanded
   arm target 是否满足增量上界；
5. **最终结果为 false：** 在修改 task tolerance 前，分别打印 `within_footprint` 和
   `inside_bowl`。

如果渲染不可用，就运行无渲染数值分支，并明确把视觉分支标为 skipped；不能用伪造图片
替代缺失画面。

## 检查问题与练习

### 概念检查

1. 哪些信息属于 `TaskSpec`，哪些属于 `GraspProfile`？
2. 为什么场景静置不计入七个动作阶段？
3. 为什么专家在接近阶段使用 path planning，却在物体附近使用显式竖直下降？
4. 为什么手指可以执行 force control，而 recorded action 仍包含 closed position target？
5. `MOVE_MAX_DQ` 能够证明 commanded target 的什么性质？
6. 为什么 bowl success 同时需要水平与 below-rim 两个条件？

### 单变量练习：修改命令增量

保持示例中的 `q_start` 和 `q_goal` 不变，只把 `MOVE_MAX_DQ` 替换成一个候选值。计算前先
预测更小的取值会怎样改变：

- `ceil(Δq∞ / max_dq)`；
- 最终 waypoint 数量；
- 相邻 commanded target 的最大差值。

随后用 NumPy 计算 schedule，并检查端点与最大 step。不要重新运行完整抓取、修改 controller
gain，也不要宣称更小的增量必然提高任务成功率。这个练习只隔离 command schedule，不混入
物理响应。

## 小结与 L09 衔接

- `TaskSpec` 定义物体、放置目标和容差，`GraspProfile` 定义物体特定的抓取几何与力；
- 专家由七个可读阶段组成，而不是一段无法解释的动作序列；
- Top-down yaw 和 grasp height 把静置后的物体几何连接到 IK target；
- Arm position control、finger force control 和 recorded finger target 各有不同职责；
- 插值在 lift 和 transport 阶段限制相邻 commanded joint target；
- 内存 trace 始终区分 commanded action 与 measured state；
- 水平 footprint 与 below-rim depth 共同定义当前 banana-to-bowl 任务是否完成。

L09 会把正式 recorder 接到同一个 per-step hook，选择数据集帧率，对齐 image 与 state/action
sample，定义 episode boundary，并只持久化满足任务合同的演示数据。

## 参考资料

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)——官方引擎与 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)——本课程固定
  使用的准确引擎版本。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)——固定版本的
  IK、path planning、joint state 与 control 接口。
- Kuffner and LaValle, [“RRT-Connect: An Efficient Approach to Single-Query
  Path Planning”](https://doi.org/10.1109/ROBOT.2000.844730), 2000——Genesis 当前默认使用的
  bidirectional planner。
