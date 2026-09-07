---
lesson: L07
slug: building-a-grasping-task-scene
locale: zh
title: "抓取任务场景搭建"
duration_minutes: 90
hardware: cpu-ok
status: cpu-verified
---

# L07 · 抓取任务场景搭建

> **课程状态：** 双语讲义和 notebook 均已完成。EN/ZH CPU 无渲染路径已经通过；英文
> CPU+EGL 双相机路径和参考 AMD+EGL 路径也已作为附加检查通过。L07 当前为
> `cpu-verified`。场景搭建具有完整的无渲染数值路径；RGB/depth 渲染仍是单独的能力分支。

## 本讲定位

L03 建立了接触与稳定步进的基础，L04 让 Franka 关节运动起来，L05 打通了关节空间、
末端位姿和 fixed camera，L06 则加入了环境维度。L07 将这些能力组合成一套任务环境，
供后续操作流程共同使用。

本讲的核心问题是：

> 怎样把项目准备好的开源社区资产、配置几何、Genesis entity 和两类相机组织成一个
> 可以验证的抓取任务场景？

完整主线如下：

```text
受支持的开源资产 → 项目预检与稳定路径
  → 桌面、物体、机器人与相机配置
  → 构建一个基础场景
  → 保持机器人并让场景静置
  → 测量机器人与物体状态
  → 按需检查 world/wrist RGB 与 depth
```

这条链在执行抓取之前结束。稳定场景只是 L08 脚本化专家的输入，并不能证明物体已经
可以成功抓起并放入容器。L09 才会定义从该场景记录哪些数据，L11 才会通过域随机化改变
其中选定的属性。数据录制与随机化都不属于 L07 实验。

开始本讲前，你应当能够：

- 解释 `init → declare → build → control → step → read/render` 生命周期；
- 区分静态实体、动态刚体和关节实体；
- 找出 Franka 的 7 个 arm DOF 与 2 个 finger DOF；
- 配合重复 `scene.step()` 使用 PD position target；
- 理解世界坐标位置、桌面接触与轴对齐包围盒（axis-aligned bounding box，AABB）；
- 区分固定相机与附着到运动 link 的相机；
- 记得 L06 中 leading environment dimension 会改变数组 shape；本讲则有意回到一个
  无 batch 维度的任务场景。

### 精简的 90 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–10 分钟 | 任务场景与已准备的社区资产 | 把四个 YCB 网格对应到各自的任务角色 |
| 10–30 分钟 | 配置与布局几何 | 推导桌面边界、rest z、footprint 与 separation |
| 30–50 分钟 | 基础场景构建 | 完成一次 build 并检查具名 `SceneBundle` 组件 |
| 50–70 分钟 | 静置与检查 | 检查 Franka qpos、物体 position、AABB 与 drift |
| 70–90 分钟 | World/wrist observation、布局练习与 L08 衔接 | 对比两个视角并判断一个新的 xy candidate |

Scene 生命周期、entity 分类、PD 控制和相机基础已在 L02–L06 建立。本讲只在搭建和检查
任务场景需要时简短调用这些先修知识，不再单独安排复习环节。

## 学习目标

完成 L07 后，你应当能够：

1. 解释桌面、YCB 物体、Franka 与相机怎样组成一个可供后续脚本化演示、数据采集和策略
   流程复用的抓取任务场景；
2. 使用项目准备好的社区资产与场景配置搭建 Genesis 基础场景，包括适合仿真的 mesh
   collision geometry，以及根据桌面和 mesh bounds 得到的物体布局；
3. 检查静置后的场景及其 world/wrist observation，判断机器人、物体、布局和相机是否
   已为后续任务执行准备就绪。

## 任务场景是下游接口

任务场景不只是“一张机器人站在物体旁边的图片”，它还是后续代码共同消费的合同。
脚本化专家需要具名的物体与机器人句柄，记录器需要稳定的观察来源，随机化代码需要清晰
的配置边界，评估代码也需要复用相同的任务几何和成功判据相关实体。

可以用四层结构理解这份合同：

| 层次 | 回答的问题 | L07 中的例子 |
|---|---|---|
| 资产就绪 | 项目能否解析全部受支持的资源？ | 四个 YCB `textured.obj` 路径 |
| 配置 | 应当声明怎样的场景？ | 桌面尺寸、物体 xy/yaw、home q、相机位姿 |
| 装配 | 配置怎样变成 Genesis entity？ | `build_scene()` 添加实体、执行一次 build 并附着 wrist camera |
| 运行状态 | 物理推进后实际发生了什么？ | Franka qpos、物体 position/AABB、RGB/depth |

这四层回答的问题并不相同。文件存在时，entity 仍可能构建失败；Scene 能够 build 时，
物体仍可能从桌面下方开始；相机画面看似合理时，数值状态仍可能包含非有限值。反过来，
即使完全不创建相机，一个数值稳定的场景仍能完成核心检查。

因此，证据层级应当写成：

```text
资产已就绪
  ≠ entity 已构建
  ≠ step 后状态稳定
  ≠ 相机观察可用
  ≠ 脚本抓取成功
```

不能用较低一层的证据支持更强的结论。

## 使用项目准备的开源社区资产

### 先运行预检

课程仓库已经准备好任务所需的四个 YCB 物体。通过项目接口解析它们：

```python
from robo_genesis.scene_config import get_ycb_assets
from robo_genesis.setup_assets import setup_assets

models_dir = setup_assets()
assets = get_ycb_assets(models_dir)

print(models_dir)
for name, asset in assets.items():
    print(name, asset.mesh_path)
```

返回的 key 必须是：

```text
011_banana
014_lemon
018_plum
024_bowl
```

`setup_assets()` 检查已准备的资产是否就绪，并返回 models directory；随后，
`get_ycb_assets()` 为每个受支持的对象返回 `YCBAsset` 记录，其中包含 mesh path 和从
网格推导出的几何量。如果预检失败，应先处理错误信息指出的环境问题，再构建场景。

### 网格承担视觉与物理两类职责

基础场景 builder 会把每个已经解析的 `textured.obj` 变成 Genesis Mesh entity。关键
模式如下：

```python
asset = assets[name]
x, y, _ = YCB_LAYOUT[name]["pos"]
z = TABLE_TOP_Z + asset.rest_z_offset

entity = scene.add_entity(
    morph=gs.morphs.Mesh(
        file=str(asset.mesh_path),
        pos=(x, y, z),
        euler=YCB_LAYOUT[name]["euler"],
        align=False,
        convexify=True,
        decimate_face_num=500,
    ),
    material=gs.materials.Rigid(
        rho=300.0,
        friction=YCB_LAYOUT[name].get("friction"),
    ),
)
```

带纹理的表面决定渲染器如何呈现物体；刚体求解器则需要适合碰撞计算的几何表示。在当前
实现中，`convexify=True` 要求 Genesis 从输入网格构建凸碰撞近似，
`decimate_face_num=500` 则限制其复杂度。这种碰撞近似不等于逐三角形复现视觉网格。

理解这一差别有助于正确解读接触。近距离画面可能显示细致的边缘或凹陷，但碰撞表示只会
近似这些特征。L07 检查物体能否在桌面上静置，并不声称所有细小几何特征都有精确接触
行为。

::: warning 保持资产使用可复现
只使用项目支持的四个 object ID，以及 `get_ycb_assets()` 返回的路径。替换网格、改变
scale 或修改网格原点都会改变静置高度、footprint、碰撞行为和后续抓取参数。这属于新的
实验，而不是无关紧要的路径修复。
:::

## 组成抓取任务场景

### 让每个组件承担明确职责

基础场景包含六类组件：

| 组件 | Genesis 表示 | 在本讲中的职责 |
|---|---|---|
| Ground | `gs.morphs.Plane()` | 位于桌面下方的静态世界参考 |
| 桌面板与四条桌腿 | 5 个固定 `gs.morphs.Box` entity | 提供顶面高度已知的稳定任务支撑 |
| Banana、lemon 与 plum | Mesh + `gs.materials.Rigid` | 动态候选抓取物体 |
| Bowl | Mesh + `gs.materials.Rigid` | 后续课程使用的动态放置容器 |
| Franka Panda | Genesis 内置 MJCF | 本讲保持在 home q 的 9-DoF 关节机器人 |
| World 与 wrist camera | 固定相机与 hand-attached camera | 提供全局和局部观察证据 |

桌子有意使用 primitive 组合而成，因此物理尺寸明确，也便于检查。YCB 物体保留各自的
视觉特征，同时使用 Genesis 的碰撞近似。Franka 是关节实体，它的状态与控制接口不同于
固定 Box 和自由运动的刚体。

共享 builder 还支持 video camera 与 domain-randomization hooks，但它们不属于 L07
基础场景。视频留给后续评估，随机化则是 L11 的主题。

### 先声明、只构建一次、再附着

前几讲的生命周期仍然有效，但 attached camera 增加了一条重要边界：

```text
build 前：
  声明 Plane、桌面、YCB entity、Franka、world camera 和 wrist camera

scene.build()：
  实例化已经声明的仿真

build 后：
  配置 Franka 控制器
  解析运行时 hand link
  把 wrist camera 附着到该 link
  同步 attached camera
```

wrist camera 和固定 world camera 一样，都必须在 `scene.build()` 前声明；但 attachment
需要 hand link 的运行时位姿，因此 `Camera.attach(...)` 要在 build 后调用。以后每个
物理步之后，还要通过 `SceneBundle.update_wrist_cam()` 调用 `move_to_attach()`。

在 build 后调用 `add_camera()` 会破坏声明边界；在 build 前调用 `attach()` 则过早请求
运行时 link 状态。若省略逐步同步，机器人运动后 wrist 图像仍可能停留在旧位姿。

## 配置、装配与运行状态

项目为不同职责规定了各自的归属：

| 职责 | 当前真相源 | 示例 |
|---|---|---|
| 稳定项目路径 | `robo_genesis.paths` | YCB 资产目录、输出目录 |
| 任务配置 | `robo_genesis.scene_config` | 桌面几何、YCB 布局、Franka home q、相机 |
| 资产就绪 | `robo_genesis.setup_assets` | 项目预检及返回的 models directory |
| 可复用装配 | `robo_genesis.build_scene` | entity 声明、build、控制器配置、相机附着 |
| 运行测量 | Genesis entity/camera handle | qpos、position、AABB、RGB、depth |

不要把完整 builder 复制进 notebook。两份装配实现会在桌面尺寸、相机参数或机器人配置
变化时产生漂移。正确做法是直接检查配置、展示关键几何推导、调用一次共享 builder，再
检查它返回的运行时句柄。

### `SceneBundle` 是运行时句柄映射

`build_scene()` 返回 `SceneBundle`，而不是裸 `Scene`：

```text
bundle.scene       已构建的 Genesis Scene
bundle.table       [桌面板, 桌腿, 桌腿, 桌腿, 桌腿]
bundle.ycb         object ID → 动态刚体 entity
bundle.franka      Franka 关节实体
bundle.world_cam   fixed camera 或 None
bundle.wrist_cam   attached camera 或 None
bundle.video_cam   evaluation camera 或 None
```

这份映射避免依赖脆弱的实体顺序。后续代码可以直接请求
`bundle.ycb["014_lemon"]`，而不用猜测哪个匿名 entity index 代表 lemon。相同的对象名称
会把场景构建连接到 L08 专家。

`SceneBundle` 并没有隐藏运行机制。调用者仍然决定何时 step、何时更新 wrist camera、
读取哪些状态，以及哪些证据才算通过。

## 把布局写成几何合同

### 推导桌面边界

桌面板中心为 `(0.35, 0.0)` m，尺寸为 `(1.20, 0.80, 0.05)` m。若 `(c_x, c_y)`
是 xy 中心，`(L_x, L_y)` 是平面尺寸，则：

```text
x_min = c_x - L_x / 2 = -0.25 m
x_max = c_x + L_x / 2 =  0.95 m
y_min = c_y - L_y / 2 = -0.40 m
y_max = c_y + L_y / 2 =  0.40 m
```

桌面板 entity 的中心 z 是 `TABLE_TOP_Z - thickness / 2`，所以它的上表面恰好位于：

```text
TABLE_TOP_Z = 0.75 m
```

这个具名高度是物体初始放置和静置后 AABB 检查的共同参考。

### 从网格边界推导静置高度

物体的 mesh origin 不一定位于最低点。如果把所有原点都放在 `z=0.75`，部分网格可能
陷入桌面，另一些则可能悬空。

设网格局部轴对齐边界的最小点为 `(b_x^min, b_y^min, b_z^min)`，项目推导：

```text
rest_z_offset = -b_z^min
object_origin_z = TABLE_TOP_Z + rest_z_offset
```

`align=False` 会保留网格创作时的原点。这样，最低的局部 z 点会从桌面表面开始：

```text
object_origin_z + b_z^min = TABLE_TOP_Z
```

这只是初始放置计算，并不能证明接触稳定。物体还必须进入动力学循环，在重力作用下静置，
然后重新检查世界坐标状态。

### 使用保守平面 footprint

只检查物体中心并不充分：中心可能在桌面内，但物体的一部分已经伸出边缘。项目根据网格
xy bounds 计算：

```text
width_x  = b_x^max - b_x^min
width_y  = b_y^max - b_y^min
radius_xy = 0.5 * sqrt(width_x² + width_y²)
```

`radius_xy` 是轴对齐 xy 包围盒对角线的一半。把它当作圆形半径，可以得到对 yaw 旋转
保持安全的保守界：实际网格也许占用更小面积，但这个圆不会因为物体旋转而缩小。

对于中心 `(x_i, y_i)` 和半径 `r_i`，只有满足以下条件，完整的保守 footprint 才位于
桌面内：

```text
x_min + r_i ≤ x_i ≤ x_max - r_i
y_min + r_i ≤ y_i ≤ y_max - r_i
```

两个 footprint 保守分离的条件是：

```text
sqrt((x_i - x_j)² + (y_i - y_j)²) > r_i + r_j
```

把左侧减去右侧定义为 pairwise margin。正值表示通过；零或负值表示两个保守圆相切或
重叠。

### 检查当前基础布局

当前配置从已准备网格中推导出以下近似值：

| 物体 | 职责 | xy（m） | yaw | 原点 z（m） | `radius_xy`（m） |
|---|---|---:|---:|---:|---:|
| `011_banana` | 抓取物体 | `(0.31, 0.22)` | `35°` | `0.768660` | `0.104660` |
| `014_lemon` | 抓取物体 | `(0.34, -0.08)` | `0°` | `0.776508` | `0.042389` |
| `018_plum` | 抓取物体 | `(0.44, 0.08)` | `0°` | `0.776520` | `0.038420` |
| `024_bowl` | 放置容器 | `(0.50, -0.10)` | `0°` | `0.777505` | `0.114066` |

四个中心及其保守 footprint 都位于桌面内，四个中心也都位于课程 working region：

```text
REACH_X = [0.30, 0.50] m
REACH_Y = [-0.22, 0.28] m
```

最小的保守 pairwise margin 出现在 lemon 与 bowl 之间，约为 `0.004790 m`。它仍为正，
但余量很小，因此看似轻微的布局改动也可能造成初始重叠。

::: warning Working region 不是可达性证明
`REACH_X` 和 `REACH_Y` 是后续专家与随机化代码使用的课程配置范围。位于其中，并不能
证明该 xy 上的所有位姿都存在无碰撞 IK 解；orientation、height、joint limit、障碍物和
路径几何仍然会影响结果。
:::

### 让检查可以执行

配套实验会在调用 builder 前直接展示这段逻辑：

```python
from itertools import combinations
import numpy as np

from robo_genesis.scene_config import (
    REACH_X,
    REACH_Y,
    TABLE_CENTER,
    TABLE_TOP_SIZE,
    TABLE_TOP_Z,
    YCB_LAYOUT,
    get_ycb_assets,
)
from robo_genesis.setup_assets import setup_assets

assets = get_ycb_assets(setup_assets())

cx, cy = TABLE_CENTER
length_x, width_y, _ = TABLE_TOP_SIZE
table_x = (cx - length_x / 2, cx + length_x / 2)
table_y = (cy - width_y / 2, cy + width_y / 2)

for name, layout in YCB_LAYOUT.items():
    asset = assets[name]
    x, y, _ = layout["pos"]
    r = asset.radius_xy
    origin_z = TABLE_TOP_Z + asset.rest_z_offset

    assert np.isfinite([x, y, r, origin_z]).all()
    assert table_x[0] + r <= x <= table_x[1] - r
    assert table_y[0] + r <= y <= table_y[1] - r
    assert REACH_X[0] <= x <= REACH_X[1]
    assert REACH_Y[0] <= y <= REACH_Y[1]

for left, right in combinations(YCB_LAYOUT, 2):
    left_xy = np.asarray(YCB_LAYOUT[left]["pos"][:2], dtype=float)
    right_xy = np.asarray(YCB_LAYOUT[right]["pos"][:2], dtype=float)
    margin = (
        np.linalg.norm(left_xy - right_xy)
        - assets[left].radius_xy
        - assets[right].radius_xy
    )
    assert margin > 0.0, (left, right, margin)
```

这些检查分别回答三个问题：物体中心是否位于配置的 working region、保守 footprint 是否
完整留在桌面上，以及它是否与其他所有物体保持保守分离。不要把这些结果压成一个没有
标签的 Boolean；不同类别的失败需要不同修正。

## 构建一个基础场景

资产与布局检查通过后，调用共享实现：

```python
from robo_genesis.build_scene import build_scene

bundle = build_scene(
    show_viewer=False,
    n_envs=1,
    add_world_cam=render_enabled,
    add_wrist_cam=render_enabled,
    add_video_cam=False,
    scene_dr=None,
)
```

这次调用明确关闭 evaluation video camera 与 domain randomization。`build_scene()` 继续
是唯一可复用的装配实现；notebook 负责解释配置并检查结果。

对这个 wrapper 而言，`n_envs=1` 会选择单场景教学路径，实现内部调用不带 `n_envs`
参数的 `scene.build()`。所以运行数组没有 batch 维度：Franka qpos 是 `(9,)`，而不是
`(1, 9)`。这是 wrapper 自己的选择。正如 L06 所讲，直接调用 Genesis API
`scene.build(n_envs=1)` 仍会保留 leading dimension。

构建后应立即检查结构：

```python
from robo_genesis.course_utils import to_numpy

expected_objects = {
    "011_banana",
    "014_lemon",
    "018_plum",
    "024_bowl",
}

q_initial = to_numpy(bundle.franka.get_qpos())

assert len(bundle.table) == 5
assert set(bundle.ycb) == expected_objects
assert q_initial.shape == (9,)
assert np.isfinite(q_initial).all()
assert bundle.video_cam is None
```

5 个 table entity 表示一块桌面板加四条桌腿，不包括 ground plane。YCB key 相符，只能
证明返回了预期句柄，尚不能证明它们的物理状态已经稳定。

## 保持、静置与测量

### 已构建的场景仍需随时间演化

动态物体从根据几何推导的接触高度开始，物理系统仍需经过一段时间处理重力和接触。
Franka 在此期间也需要持续的有效 target；只设置一次初始 q，并不等于持续保持 position
controller target。

基础实验先保存初始物体 xy，再推进约 60 步：

```python
from robo_genesis.scene_config import FRANKA_QPOS

home_q = np.asarray(FRANKA_QPOS, dtype=float)
initial_xy = {
    name: to_numpy(entity.get_pos()).reshape(3)[:2].copy()
    for name, entity in bundle.ycb.items()
}

for _ in range(60):
    bundle.franka.control_dofs_position(home_q)
    bundle.scene.step()
    bundle.update_wrist_cam()
```

没有 wrist camera 时，bundle 方法会检查 `None`，因此这次更新没有副作用。把它保留在
循环中，可以明确生命周期，并防止渲染分支使用已经过期的 attached pose。

### 同时读取原点位置与 AABB

对每个物体读取两个相关但不同的量：

```python
for name, entity in bundle.ycb.items():
    position = to_numpy(entity.get_pos()).reshape(3)
    aabb = to_numpy(entity.get_AABB()).reshape(2, 3)

    bottom_z = aabb[0, 2]
    xy_drift = np.linalg.norm(position[:2] - initial_xy[name])

    assert np.isfinite(position).all()
    assert np.isfinite(aabb).all()
    assert abs(bottom_z - TABLE_TOP_Z) < 0.005
    assert xy_drift < 0.01
```

`position` 是 Genesis user frame 中的 base-link origin；在这个非批量场景里，其 xy 轴
和原点就是布局所用的场景坐标。`aabb[0]` 与 `aabb[1]` 则是当前 collision AABB 在世界
坐标系中的最小角点和最大角点。因此，AABB bottom 比 entity origin z 更适合检查桌面
支撑。

配套实验使用以下有限时间窗口判据：

| 推进约 60 步后的量 | 要求 |
|---|---:|
| Franka qpos | 有限，shape 为 `(9,)` |
| 相对 home q 的最大绝对误差 | `<0.02 rad` |
| 每个物体的 position | 有限，shape 为 `(3,)` |
| 每个物体的 AABB | 有限，shape 为 `(2, 3)` |
| `abs(AABB bottom z - TABLE_TOP_Z)` | `<0.005 m` |
| 物体 xy 相对初始中心的漂移 | `<0.01 m` |

这些阈值只描述当前配置的基础场景和较短静置窗口，并不是对任意 mesh、scale、friction、
physics solver 或长时间运行的通用保证。

AABB 靠近桌面并不能证明物体可抓。它只能说明当前碰撞几何静置在预期支撑面附近，不能
检查手指位置、力闭合、提起、无碰撞运动或 bowl containment。

## 通过 world 与 wrist camera 观察场景

### 固定视角与附着视角回答不同问题

可选渲染路径使用两台相机：

| 相机 | 位姿归属 | 有助于检查的内容 |
|---|---|---|
| World camera | 固定的世界坐标 `pos` 与 `lookat` | 桌面、物体、碗和机器人的整体布局 |
| Wrist camera | 通过刚体变换附着到 Franka `hand` | 夹爪附近的局部 eye-in-hand 视角 |

两台相机均使用课程仿真分辨率 `(1280, 720)` 和垂直 FOV `42°`。Genesis 相机配置采用
`res=(W, H)`，返回数组则把高度放在宽度之前：

```text
RGB:   (720, 1280, 3), uint8
depth: (720, 1280), 浮点数
```

world camera 的位姿在 build 前已经完整确定；wrist camera 同样在 build 前声明，但在
build 后才取得 hand-link attachment。当前 offset transform 相对于运动的 hand 定位与
定向相机，而不是在世界坐标系中固定它。

静置循环结束后，通过 bundle 渲染：

```python
frames = bundle.render(rgb=True, depth=True)

world_rgb, world_depth, _, _ = frames["world"]
wrist_rgb, wrist_depth, _, _ = frames["wrist"]

world_rgb = to_numpy(world_rgb)
world_depth = to_numpy(world_depth)
wrist_rgb = to_numpy(wrist_rgb)
wrist_depth = to_numpy(wrist_depth)
```

对每个视角检查准确 shape、RGB dtype、有限 depth、非空的 RGB 变化，以及至少一个正的
depth 值，然后人工观察图像：

- world view 应能辨认四个物体、桌面与 Franka 的整体布局；
- wrist view 应呈现与 hand attachment 一致的局部视角；
- 两张图都不应空白、全黑、明显损坏或显著偏离任务区域。

数组检查不能判断相机是否讲清了预期的视觉信息，因此仍需人工检查。反过来，合理的画面
也不能替代 qpos、position、AABB 或 drift 检查。

### 渲染是能力分支

配套 notebook 用 `ROBO_GENESIS_RENDER` 显式选择路径：

- `ROBO_GENESIS_RENDER=0`：不创建两台相机，完整执行资产、布局、build、settle 和状态
  检查，并输出明确的 camera `SKIP`；
- `ROBO_GENESIS_RENDER=1`：在 build 前创建两台相机，并要求两路 RGB/depth 都通过。

如果明确请求了渲染，但 EGL 或 renderer 失败，该能力分支就失败。不能用旧截图、空数组
或 Matplotlib 示意图替代，再将其称为 Genesis render。

当前 resolution、FOV、clipping plane 与 pose 都只是课程仿真参数，并不是 Intel
RealSense D435i 或任何其他真实相机的标定模型。本讲没有复现 lens distortion、exposure、
sensor noise、depth sensing、synchronization、rolling shutter 或安装公差。

## 配套实验

配套 notebook 会直接展示几何与证据，同时复用 `build_scene()` 完成整体装配。它既不会
复制 builder，也不会用一个不透明调用隐藏本讲机制。

### 运行前预测

执行前先写下答案：

1. 为什么物体中心可以位于桌面内，而它的 footprint 仍可能越界？
2. 为什么这些 mesh 的 `object_origin_z` 高于 `TABLE_TOP_Z`？
3. 场景中的哪些组件属于 fixed、dynamic rigid 或 articulated？
4. 为什么两台相机都必须在 build 前声明，而 wrist attachment 要在 build 后完成？
5. 这条 `build_scene(n_envs=1)` 路径应返回什么 qpos shape？
6. 合法的 world-camera 图像能否证明物体已经稳定落在桌面上？
7. 场景稳定后，L08 还需要增加哪些动作和成功检查？

### 最低数值路径

关闭渲染时，实验仍能完成本讲核心内容：

1. 报告环境并初始化一个受支持 backend；
2. 运行 `setup_assets()` 并准确解析四个 YCB Mesh 路径；
3. 根据当前配置计算 table bounds、rest z、保守 footprint 和 pairwise margin；
4. 构建一个没有相机、没有随机化的场景；
5. 确认 5 个 table entity、4 个具名 YCB entity、无 video camera，以及有限的
   Franka `(9,)` qpos；
6. 持续发送 home q target 并推进约 60 个物理步；
7. 检查 home-q error、object position/AABB、桌面支撑与 xy drift；
8. 报告 camera `SKIP`；
9. 只有所有请求的能力分支都通过时，才打印 `L07 CHECK: PASSED`。

打开渲染时，同一个 notebook 会在 build 前声明两台相机，每步同步 wrist camera，验证
两组 RGB/depth，并把当前两张 RGB 图并排显示。它不会创建 video camera 或保存 rollout。

没有抛出异常并不等于通过。具名结构、shape、有限值、几何不等式、动态阈值和明确请求
的相机分支都需要直接证据。

## 常见故障和诊断顺序

### 资产预检失败

先运行 `setup_assets()` 并遵循错误提示，确认项目配置的资产目录正在生效。不要从相邻
源仓库复制文件，也不要在 notebook 中绕过预检。

### 路径只在某个工作目录下有效

删除 `../assets` 等相对猜测路径和所有 `sys.path` 注入。使用已安装的 `robo_genesis`
包及其路径接口。诊断时打印一次解析后的 models directory。

### 物体起始位置高于或低于桌面

打印 mesh lower z bound、`rest_z_offset`、派生 origin z 与 `TABLE_TOP_Z`。确认网格单位
为米，而且 `align=False` 没有被修改。step 后应检查 world-frame AABB bottom，不要假设
origin 就是接触点。

### 修改布局后物体重叠

重新计算每一对 footprint margin，不能只凭肉眼检查最近的中心距离；同时检查完整
footprint 是否越过桌面边界。基础布局中 lemon–bowl 的余量本来就是最小值。

### Scene 在 build 时失败

确认所有 entity 与所需 camera 都在唯一一次 build 前声明。区分正常的首次构建编译或
collision-processing 信息和真正异常；应查看第一份 traceback，而不是在同一个已经部分
初始化的 kernel 中重试。

### 静置时物体漂移或穿透

检查 origin z、初始重叠、AABB bottom、碰撞配置与有限状态。render 有助于定位物体，
但实验判据仍由数值 AABB 与 drift 决定。

### 物体静置时 Franka 下垂

确认 builder 已经配置 gain 与 force range，并确认循环在每次 `scene.step()` 前都调用
`control_dofs_position(home_q)`。不要在 L07 重新调节 gain；控制器解释由 L04 负责。

### Wrist view 没有跟随 hand

确认相机在 build 后附着到 `hand` link，并在每个 step 后调用
`bundle.update_wrist_cam()`。shape 正确的图像仍可能是已经过期的画面。

### 渲染为空或 EGL 不可用

如果明确请求了渲染，应把它视为相机能力路径失败并检查图形环境。如果原本就关闭了渲染，
则完成数值路径，并且只报告明确的 camera `SKIP`。

### 场景通过，所以假定抓取也通过

回到证据层级。L07 没有发送 IK grasp target、闭合手指、提起物体或检查物体是否位于碗内。
这些机制和成功判据从 L08 才开始。

按以下顺序诊断：

```text
版本、backend 与 render mode
  → 资产预检与解析路径
  → 配置与派生几何
  → 声明/build 边界
  → bundle 结构与无 batch shape
  → settle loop 与有限状态
  → object position、AABB 与 drift
  → 可选 camera attachment 与数组
```

## 检查点与练习

### 概念检查

不回看正文，回答以下问题：

1. 从磁盘上的资产到任务观察之间分为哪四层？
2. 为什么 notebook 应使用 `setup_assets()` 与 `get_ycb_assets()`，而不是相对路径或
   运行时下载？
3. 固定 table box、动态 YCB Mesh entity 与关节式 Franka 有什么区别？
4. `rest_z_offset` 如何推导？它在 step 前能够保证什么？
5. 为什么 `radius_xy` 对 yaw 是保守的？正 pairwise margin 表示什么？
6. 为什么位于 working region 不能证明 IK 可达？
7. 静置后为什么 object position 与 AABB 都有用？
8. world camera、wrist camera 与数值状态检查分别提供什么证据？
9. 哪些主张仍应留给 L08、L09、L11 和 L13？

### 动手练习：提出一个新的 banana xy

为 `011_banana` 选择一个新的 `(x, y)` candidate，只改变这一个变量：保持其 yaw、z 推导、
mesh、桌面、其他物体位置、机器人状态、相机设置与物理选项不变。

运行代码前，先预测 candidate 能否通过：

1. 中心位于 `REACH_X × REACH_Y`；
2. 完整保守 footprint 位于桌面内；
3. 与 lemon、plum 和 bowl 的 separation margin 都为正。

然后运行显式几何检查，带标签报告每个 margin。如果 candidate 通过，再解释为什么这仍
不能证明抓取可达且无碰撞。不要修改 `scene_config.py`，不要在同一个 kernel 中构建第二个
Genesis Scene，也不要执行 L08 抓取序列；这个练习只考察一个 placement 变量。

## 总结与衔接

- 可复用任务场景是下游接口，而不只是一张可信的图片。
- 学员代码通过项目预检与稳定路径接口取得四个受支持的 YCB 资产，再把每个 textured
  mesh 交给 Genesis。
- 场景明确区分固定支撑、动态物体、关节机器人，以及固定或附着的观察来源。
- configuration data、assembly behavior 与 runtime state 各有明确归属；`build_scene()`
  是唯一装配实现，`SceneBundle` 则暴露具名 runtime handle。
- mesh lower bound 决定初始 rest z；保守平面半径用于检查 yaw 下的桌面 containment 与
  pairwise separation。
- 课程 working region 只是配置范围，不是任意可达性或无碰撞路径证明。
- 必须先执行短暂的 hold-and-settle loop，再读取 position/AABB 证据。entity origin 与
  world-frame AABB bottom 回答的问题不同。
- fixed world camera 展示整体布局，hand-attached wrist camera 展示局部 eye-in-hand
  上下文。无渲染数值路径可以跳过二者，而且任何图像都不能替代数值检查。
- 稳定的基础场景不能证明抓取成功、数据时序正确、策略有效或闭环任务成功。

L08 将消费同一个 `SceneBundle`，选择一个具名物体，求解一系列运动目标，控制夹爪，并
定义明确的抓取与放置成功判据。本讲建立的稳定名称、几何、状态检查和相机生命周期，都是
该脚本化专家的先修条件。

## 来源

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  — 官方用户与 API 文档。
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  — 本课程固定使用的准确引擎版本。
- [Genesis 1.3.3 `Scene` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/scene.py)
  — 固定版本的场景声明与 build 行为。
- [Genesis 1.3.3 `Mesh` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/options/morphs.py)
  — 固定版本的 mesh 加载、decimation、convexification 与 alignment 选项。
- [Genesis 1.3.3 `RigidEntity` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — 固定版本的 entity state、AABB 与 position-control 行为。
- [Genesis 1.3.3 `Camera` 源码](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — 固定版本的 camera 声明、attachment、同步与渲染行为。
- [Genesis 1.3.3 内置 Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — 基础场景使用的机器人模型。
- [YCB Object and Model Set](https://www.ycbbenchmarks.com/)
  — 本讲所用社区物体集合的原始项目页面。
- Calli 等人，[《Benchmarking in Manipulation Research: Using the
  Yale-CMU-Berkeley Object and Model Set》](https://doi.org/10.1109/MRA.2015.2448951)，
  *IEEE Robotics & Automation Magazine*，2015 — YCB 数据集参考文献。
- [Intel RealSense D435i 产品文档](https://www.intelrealsense.com/depth-camera-d435i/)
  — 用作真实硬件参考，以明确本课程的简化仿真相机参数不构成经过标定的传感器复现。
