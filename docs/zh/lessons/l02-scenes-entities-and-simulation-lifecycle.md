---
lesson: L02
slug: scenes-entities-and-simulation-lifecycle
locale: zh
title: "场景、实体与仿真生命周期"
duration_minutes: 90
hardware: cpu-ok
status: planned
---

# L02 · 场景、实体与仿真生命周期

> **课程状态：** 讲义内容已经提供，但配套的可执行 notebook 及其干净
> kernel 验证尚未发布，因此 L02 仍保持 `planned`。

## 本讲定位

L01 已经说明，“环境可用”并不是一个简单的是非判断：同一台机器对文档阅读、
核心仿真、图像渲染和完整训练流程的支持程度可能不同。L02 接下来回答所有后续
仿真程序都会遇到的第一个结构问题：

**一段 Python 场景描述在什么时候才会变成可以推进和测量的仿真状态？**

答案是 Genesis 的生命周期：

```text
gs.init
  → 配置 Scene
  → 添加实体和相机
  → scene.build()
  → scene.step()
  → 读取状态和渲染观测
```

这套模式会反复出现在后续课程中：L03 的刚体实验、L04 的关节机器人、L05 的
逆运动学与相机，以及 L06 的完整抓取场景都会沿用它。本讲刻意只使用 Genesis
内置的 Plane 和 Box primitive（基本几何体），让生命周期本身清楚可见，而不是
被任务专用的高层封装遮住。

开始前，你应当能够：

- 从干净 kernel 启动并运行 notebook；
- 识别当前环境实际选择的后端；
- 知道 `gs.init()` 是进程级初始化；
- 区分“函数没有报错”和“结果已经得到验证”。

## 学习目标

完成 L02 后，你应当能够：

1. 在 Genesis 程序中标出初始化、拓扑声明、构建和运行四类操作，并识别错误的
   调用顺序；
2. 将 `scene.add_entity(...)` 的参数归入 Morph、Material 或 Surface，并解释
   三者各自负责什么；
3. 解释刚体对象的 `Scene → RigidEntity → RigidLink → RigidGeom` 层级，并在
   一个 primitive 上检查实际结构；
4. 在自动选择的已验证后端上构建并推进最小场景，读取位置、四元数和线速度，
   报告它们的 shape、device、数值有限性和实际变化；
5. 用受控的预期异常证明 `build()` 边界；
6. 在启用渲染时验证离屏 RGB 观测，或在未启用时明确报告 `SKIP`，并用基于
   状态数据的示意图完成核心实验。

## 从配置到运行时状态

阅读仿真代码时，可以先把它分为三个阶段：

| 阶段 | 需要回答的问题 | 典型操作 |
|---|---|---|
| 声明 | 这个世界里有哪些对象？ | 创建 `Scene`，添加实体和相机 |
| 构建 | 描述如何转化为可执行状态？ | `scene.build()` |
| 运行 | 接下来发生了什么，能够观测到什么？ | `scene.step()`、状态 getter、相机渲染 |

声明阶段创建的是用于描述场景的 Python 对象。例如，调用
`scene.add_entity(...)` 后会立即得到一个实体 handle（句柄），但这并不代表
全部运行时状态已经存在。求解器缓冲区和编译后的 kernel 要到构建边界才准备好。

构建成功后，运行阶段的操作才能推进和读取这些状态。这个区别解释了两个初看
有些意外的错误：

- 在构建前读取刚体实体的位置，会得到包含 `is not built yet` 的错误；
- 在构建后继续添加实体，会得到 `Scene is already built.` 错误。

这两条是生命周期约束，并非任意设置的限制。Genesis 只有先确定场景拓扑，才能
分配求解器状态，并准备操作这些状态所需的 kernel。

## Scene 与 Entity

### Scene 负责什么

`gs.Scene` 是一个仿真世界的顶层容器，它把多类配置和状态组织在一起：

- `dt`、`substeps` 等仿真时间配置；
- 求解器专用选项；
- 实体及其物理表示；
- 相机和可视化配置；
- 构建后由 `scene.step()` 推进的运行时状态。

L02 使用时间配置只是为了得到一个具体可运行的场景。L03 才会研究时间步长、
子步、接触和摩擦如何改变物理结果，不要从本讲的单条轨迹推导这些参数的效果。

### Entity 是什么

Entity（实体）是 `scene.add_entity(...)` 返回的运行时操作对象。代码会保留这个
handle，以便随后检查或修改它所代表的对象：

```python
box = scene.add_entity(
    morph=gs.morphs.Box(
        size=(0.10, 0.10, 0.10),
        pos=(0.0, 0.0, 0.50),
    ),
    material=gs.materials.Rigid(rho=500.0),
    surface=gs.surfaces.Default(color=(0.20, 0.60, 0.90, 1.0)),
    name="falling_box",
)
```

这里的赋值并不是把一个位置复制到独立的 Python 数据结构中。`box` 指向的是由
`scene` 管理的对象；构建完成后，它的 getter 会读取场景当前的求解器状态。

## 刚体层级

Entity 是 Genesis 中的通用概念。本讲的 Box 使用 `gs.materials.Rigid`，因此
这里只讨论刚体实体：

```text
Scene
└── RigidEntity
    └── RigidLink
        └── RigidGeom
```

每一层的职责不同：

- `RigidEntity` 是提供给用户的对象级 handle；
- `RigidLink` 是实体中的一个刚体链节；
- `RigidGeom` 是隶属于某个 link 的碰撞几何体。

一个 Box primitive 通常会产生一个刚体实体，其中包含一个 link 和一个碰撞
geom。关节机器人仍然可以是一个实体，但内部会有多个 link 和 joint。L04 将
详细解释关节结构、关节状态和自由度；L02 只建立容器层级的基本认识。

不要只相信示意图，应当用 API 检查实际对象：

```python
print(type(box).__name__)
print(box.n_links, len(box.links))
print(box.n_geoms, len(box.geoms))
```

对于本课程锁定的 Genesis 1.3.3 和这里使用的 primitive，预期结果是一个 link
和一个碰撞 geom。这个结果只描述当前 primitive，不能推广成所有 Entity 或
所有导入资产的通用基数。

视觉几何体和碰撞几何体也不一定相同。导入机器人和物体资产后，这个区别会很
重要；本讲先不展开视觉 geom，以免偏离生命周期主线。

## Morph、Material 与 Surface

`scene.add_entity(...)` 会组合三类配置。把它们区分清楚，代码审查和故障诊断
都会容易很多。

| 输入 | 在 L02 中的职责 | 示例 | 常见混淆 |
|---|---|---|---|
| Morph | 形状、尺寸、初始位姿，以及 `fixed` 等导入标志 | `gs.morphs.Box(size=..., pos=...)` | Morph 是创建描述，不是运行时 Entity |
| Material | 物理模型和物理参数 | `gs.materials.Rigid(rho=...)` | 这里的“材质”不是物体显示出来的颜色 |
| Surface | 颜色、纹理等渲染外观 | `gs.surfaces.Default(color=...)` | 红色物体不会因此自动变得更滑或更涩 |

### Morph 描述创建什么

Morph（形态描述）告诉 Genesis 要创建什么几何形状，以及把它放在什么初始
位置。内置 primitive Morph 包括 Plane、Box 和 Sphere；基于文件的 Morph
还可以描述 mesh 和关节资产，后续课程会使用这些形式。

有些决定对象如何进入仿真的标志也属于 Morph。例如，`fixed=True` 会把
primitive 固定住，而不是允许它自由运动。但这不会让 Morph 变成运行时状态；
`add_entity` 返回的 Entity 才是提供运行时方法的对象。

### Material 决定物理行为

Material（物理材质）选择实体所采用的物理模型。本讲中，
`gs.materials.Rigid(...)` 选择刚体求解路径，并提供密度。刚体 Material 还可以
携带摩擦等其他物理参数。

L02 固定使用一组参数，只为了让这个配置类别在代码中可见。本讲不会通过改变
密度或摩擦得出物理结论；L03 会在受控条件下改变物理参数并测量其影响。

### Surface 决定外观

Surface（表面外观）描述实体如何被渲染。`gs.surfaces.Default(color=...)` 中的
RGBA 元组只改变外观，不改变接触摩擦。如果希望“让蓝色方块变得更滑”，修改
颜色不是正确操作；对应的物理参数属于 Material。

这是一个重要的调试习惯：先判断问题属于几何、物理还是外观，再检查对应的
输入类别。

## `build()` 边界

### 从概念上看，build 做了什么

只有在声明完本次运行需要的实体和相机后，才能调用 `scene.build()`。在锁定的
Genesis 1.3.3 实现中，build 会固定已经声明的结构、分配求解器状态、准备所选的
环境布局、编译所需的仿真 kernel、重置初始状态，并构建可视化组件，使场景进入
可执行状态。

这些实现细节解释了为什么第一次 build 可能比之后的单次 step 更耗时，但它们
不意味着课程代码应该依赖私有属性或精确的内部调用顺序。需要记住的公开约定很
简单：

- build 前声明拓扑；
- 只 build 一次；
- build 后再进行步进、控制、状态读取和渲染。

### “构建后拓扑固定”意味着什么、不意味着什么

Genesis 1.3.3 要求调用 `add_entity`、`add_camera` 和 `build` 时 Scene 尚未构建。
Scene 构建完成后，就不能再通过这些声明接口改变该场景的拓扑。

这**不代表** build 后所有数值都不可修改。运行时 API 仍然可以修改受支持的
状态、控制目标和相机位姿，后续课程正会这样做。准确的规则是：构建完成后，
不要再通过 build 前的声明 API 添加新的场景成员。

### 构建前的受控失败

`add_entity` 返回后，实体 handle 已经存在，但其动态状态尚不可用。实验会明确
检验这条结论：

```python
try:
    box.get_pos()
except gs.GenesisException as exc:
    if "not built yet" not in str(exc).lower():
        raise
    print("PASS — state is unavailable before build")
else:
    raise AssertionError("get_pos unexpectedly succeeded before scene.build()")
```

只有捕获到预期的 Genesis 异常，并且消息内容正确，这个测试才算通过。不同的
异常表示出现了意外故障，必须继续向外抛出。

### 构建后的受控失败

与之相反的测试在 `scene.build()` 之后运行：

```python
try:
    scene.add_entity(gs.morphs.Sphere(radius=0.05))
except gs.GenesisException as exc:
    if "already built" not in str(exc).lower():
        raise
    print("PASS — topology declaration is closed after build")
else:
    raise AssertionError("add_entity unexpectedly succeeded after scene.build()")
```

不要在这两个测试外层使用宽泛的 `except Exception`。否则拼写错误、导入问题或
无关的引擎故障，都可能被伪装成支持生命周期结论的证据。

## `step()`、状态与证据

构建完成后，每次 `scene.step()` 会把仿真向前推进一个外层时间步。设置
`SimOptions(dt=0.01, substeps=2)` 时，调用 20 次就表示推进 20 个外层时间步；
substeps 是内部细分，不是额外的 Python 调用。L03 会解释这个区别为什么会影响
稳定性。

对于单个、未批处理的刚体实体，本讲使用的 getter 会返回以下 shape 的 PyTorch
tensor：

| Getter | 含义 | 未批处理 shape |
|---|---|---:|
| `box.get_pos()` | base link 的位置 | `(3,)` |
| `box.get_quat()` | base link 的朝向，顺序为 `(w, x, y, z)` | `(4,)` |
| `box.get_vel()` | base link 的线速度 | `(3,)` |

返回 tensor 的 device 跟随运行时后端。在使用 ROCm 的 PyTorch 构建中，AMD
设备也可能通过 PyTorch 的 CUDA 兼容命名空间显示，因此应同时检查 Genesis
实际选择的后端和 `tensor.device`，不能只看到 `cuda` 一词就推断硬件平台。

每一份用作证据的状态至少要检查：

1. Python 对象或 tensor 类型；
2. 预期 shape；
3. device；
4. 所有数值是否有限；
5. 观测到的变化是否符合定性预测。

L02 的 Box 从 Plane 上方开始运动。推进固定步数后，核心检查要求最终高度低于
初始高度，但不要求某个唯一的最终数值：最终接触位置等绝对数值可能受锁定的
引擎配置影响，而精确落点不是本讲要验证的概念。

图像可以帮助人理解场景，但不能代替状态检查；反过来，一个看似合理的状态
tensor 也不能证明相机图像已经正确渲染。每一条结论都应使用同类证据来支持。

## 后端选择与渲染能力

下面两个经常被混为一谈的选择其实彼此独立：

- **仿真后端**负责执行物理计算和已编译的 kernel；
- **渲染路径**负责生成相机观测。

### 仿真后端模式

实验提供两种后端模式：

- `auto` 是面向学习者的默认模式。当前课程帮助函数优先选择已经验证的 AMD
  ROCm 路径；该路径可用时选择 `gs.amdgpu`，否则选择 `gs.cpu`；
- `cpu` 显式选择 `gs.cpu`，既支持没有已验证加速器的学习者，也用于回归验证
  本讲的 `cpu-ok` 最低能力声明。

在参考 AMD Radeon AI PRO R9700 机器上，`auto` 应当选择 `gs.amdgpu`，课程不会
强制这台机器改用 CPU。同时，`cpu-ok` 标签要求核心实验还要在另一个强制 CPU
的干净 kernel 中通过。

如果 `auto` 已经选择经过验证的 AMD 后端，之后初始化或执行失败，notebook 必须
暴露这个错误。静默改用 CPU 会隐藏兼容性回归。当前兼容性记录尚未验证 NVIDIA
CUDA 和其他加速器，因此仅仅检测到设备并不足以声明这些路径受到支持。

### 渲染是独立开关

相机必须在 build 前添加，因此 notebook 会在确定最终拓扑前决定是否加入相机：

```python
camera = None
if render_enabled:
    camera = scene.add_camera(
        res=(640, 360),
        pos=(1.1, -1.1, 0.8),
        lookat=(0.0, 0.0, 0.25),
        fov=40,
        GUI=False,
    )
```

启用渲染时，相机创建、场景构建、渲染和 RGB 校验共同组成一项测试。渲染异常
必须让这项测试失败，不能触发静默降级。

如果运行前已经关闭渲染，notebook 会明确打印
`SKIP: rendering disabled for this run`，并根据实测的初始与最终位置绘制简单的
侧视示意图。这个图由状态数据生成，不是 Genesis 相机图像；它让 CPU 核心路径
在没有渲染时仍然有用，同时不会制造虚假的渲染声明。

选择 `gs.cpu` 本身不能证明渲染不可用，选择 `gs.amdgpu` 也不能证明渲染正常。
课程会分别验证这两项能力。

## 实验：一个方块，一次生命周期

配套的可执行 notebook 尚未发布。本节只定义如何理解实验，以及实验必须产生
哪些证据，不会声称尚未执行的实验已经运行。

### 阶段 1——只初始化一次

notebook 会在不修改 `sys.path` 的前提下导入已经安装的 `robo_genesis` 包，选择
`auto` 或强制 `cpu` 模式，报告实际后端，并且只调用一次 `gs.init()`。更换后端
或渲染模式后，需要从干净 kernel 重新运行整本 notebook。

### 阶段 2——声明场景

场景包含：

- 一个 Plane；
- 一个有名称、可运动的 Box，显式配置 Morph、Material 和 Surface；
- 只在运行前已启用渲染的情况下添加一个离屏相机。

此时 `scene.is_built` 必须为 `False`。可以检查 Box handle 及其声明结构，但读取
动态状态的 getter 必须拒绝构建前访问。

### 阶段 3——跨过一次构建边界

notebook 只调用一次 `scene.build()`，并验证 `scene.is_built` 已变为 `True`。随后
检查 primitive 的层级结构，并读取第一份有效状态。

### 阶段 4——步进并比较

notebook 先记录初始位置、四元数和线速度，再推进 20 步并记录最终状态。它会
检查 shape 和有限性，并验证方向性预测 `final_z < initial_z`，而不是断言一个
编造出来的绝对坐标。

### 阶段 5——如实观测

启用渲染时，notebook 会验证返回的 RGB 数组：它必须包含图像高度和宽度维度，
通道数应是当前渲染器支持的 3 或 4，所有数值必须有限，而且数值范围应当符合
其 dtype。关闭渲染时，只生成明确标注的状态示意图。

### 阶段 6——证明拓扑已经关闭

最后，notebook 会尝试在 build 后调用一次 `add_entity`，并且只接受消息中包含
`already built` 的预期 `GenesisException`。

## 验收证据

只有同时满足以下条件，核心实验才算通过：

- 报告已安装的 Genesis 版本和实际后端；
- 不使用源仓库、开发机绝对路径或 `sys.path` 注入；
- `scene.is_built` 在一次 build 前后从 `False` 变为 `True`；
- 构建前读取状态产生经过严格检查的预期失败；
- 在锁定的 Genesis 1.3.3 下，当前 primitive 包含一个 link 和一个碰撞 geom；
- position、quaternion 和 velocity 具有预期的未批处理 shape，且数值有限；
- 20 步后 Box 的实际高度下降；
- 构建后添加拓扑产生经过严格检查的预期失败；
- 启用渲染时验证 RGB 数据；关闭渲染时明确报告 `SKIP`，并且只生成有清楚标注的
  状态示意图。

在 L02 被标记为已验证之前，同一本 notebook 必须在参考机的两个干净 kernel 中
通过：默认 `auto` 必须选择 `gs.amdgpu`，强制 `cpu` 必须选择 `gs.cpu`。启用渲染
的参考运行提供额外证据，但不会把 GPU 变成核心课程的先决条件。

## 常见失败与诊断

### `Genesis hasn't been initialized`

在 `gs.init()` 之前创建了 Scene 或其他 Genesis 对象。重启 kernel，只运行一次
初始化，然后按顺序执行后续 cell。

### `... is not built yet`

在 `scene.build()` 之前调用了状态 getter 或 `scene.step()` 等运行时操作。找到
build 调用的位置，不要压制异常，也不要编造占位状态。

实验中唯一一次构建前 getter 是受控的反例测试，只应使用前文所示的严格异常
检查处理。

### `Scene is already built`

代码在跨过拓扑边界后又请求添加实体、添加相机或第二次 build。把声明操作移到
唯一一次 build 之前，并从干净 kernel 重新运行。

实验中唯一一次 build 后 `add_entity` 同样是受控的反例测试，不是正常构建场景
的示例。

### 状态 shape 不符合预期

先打印 getter 名称、类型、shape 和 device。本讲使用默认的未批处理场景，因此
不应出现额外的环境维度。L08 会有意引入批量环境，并解释相应的 shape。

### 状态包含非有限值或明显不合理

先确认初始化和 build 成功，再检查步进前的第一份状态，然后定位从哪一步开始
出现非有限值。不要只根据最后一张图像诊断问题；L03 会加入面向接触和稳定性的
物理诊断方法。

### 渲染失败

先确认运行前是否启用了渲染。如果本来就关闭了渲染，没有相机图像属于明确的
`SKIP`；如果已经启用，则应保留真实异常和环境信息，不能宽泛捕获后把它重新
标成成功的降级路径。

### 在同一个 kernel 中重复运行 `gs.init()`

更换后端或渲染模式需要重新进行进程级初始化。应重启 kernel，再从头到尾运行
notebook，而不是在带有隐藏状态的环境中反复执行初始化 cell。

## 课堂检查与练习

### 概念检查

先不回看前文表格，尝试回答：

1. `scene.add_camera(...)` 应当放在 `scene.build()` 的哪一侧？为什么？
2. 如果希望让蓝色方块变得更滑，应当修改 Surface 颜色，还是 Material 配置？
3. 为什么实体 handle 已经存在时，`get_pos()` 仍然可能无效？
4. “构建后拓扑固定”是否意味着所有运行时状态都不能再变化？
5. 如果 ROCm 系统中的 tensor 显示为 `cuda:0`，还需要查看什么证据，才能判断
   实际使用的后端？

### 动手练习

在 build 调用前添加一个固定标记：

```python
marker = scene.add_entity(
    morph=gs.morphs.Box(
        size=(0.06, 0.06, 0.06),
        pos=(0.18, 0.0, 0.03),
        fixed=True,
    ),
    surface=gs.surfaces.Default(color=(0.20, 0.80, 0.35, 1.0)),
    name="fixed_marker",
)
```

然后重启 kernel 并重新运行整本 notebook。通过对象检查验证这个 marker；启用
渲染时，还要在图像中确认它可见。解释哪些参数属于 Morph，哪些属于 Surface。

作为代码阅读扩展，打开 `src/robo_genesis/build_scene.py`，找出 Scene 创建、实体
声明、相机声明、build 调用和 build 后配置。现在不要运行完整抓取场景；这个练习
只要求识别 L06 将会使用的生命周期模式。

## 小结与 L03 衔接

- Scene 描述在 `scene.build()` 时转化为可执行的运行时状态；
- 实体和相机在 build 前声明，步进、状态读取和渲染在 build 后进行；
- 刚体 primitive 呈现 `RigidEntity → RigidLink → RigidGeom` 层级；
- Morph、Material 和 Surface 分别描述几何与初始位姿、物理行为和渲染外观；
- 状态的 shape、device、有限性和变化，比“没有报错”或一张看似合理的图像更能
  支持调试结论；
- `cpu-ok` 保证 CPU fallback，但不会强制已经验证的 AMD 机器放弃
  `gs.amdgpu`；
- 仿真后端与渲染能力需要分别验证。

L02 固定了物理配置，使生命周期成为唯一被考察的主题。L03 将主动改变时间步长、
substeps、接触和摩擦，并测量这些选择如何影响刚体仿真的稳定性。

## 资料来源

- [Genesis World 文档](https://genesis-world.readthedocs.io/en/latest/)
  ——官方用户文档和 API 文档；
- [PyPI 上的 Genesis World 1.3.3](https://pypi.org/project/genesis-world/1.3.3/)
  ——本课程锁定的版本；
- [Genesis World 官方仓库](https://github.com/Genesis-Embodied-AI/genesis-world)
  ——`Scene`、Entity、Morph、Material、Surface 和相机行为的实现来源。本讲
  的 API 结论依据锁定的 1.3.3 包核对，而不是根据未锁定分支推断。
