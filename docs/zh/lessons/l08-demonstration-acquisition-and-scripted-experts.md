---
lesson: L08
slug: demonstration-acquisition-and-scripted-experts
locale: zh
title: "演示数据获取与脚本化专家"
duration_minutes: 120
hardware: gpu-recommended
status: planned
---

# L08 · 演示数据获取与脚本化专家

> **课程状态：** 双语讲义已经完成，配套 notebook 和 clean-kernel 运行证据仍待完成，
> 因此 L08 继续保持 `planned`。

## 本讲定位

L07 已经搭建出能够稳定静置的桌面任务场景，并提供了 Franka、香蕉和碗的具名句柄。
L08 将为这个场景加入一个能够完成整套抓取放置任务的专家，最终得到一条任务结果明确、
并且包含时序化命令动作与机器人实测状态的 rollout。

本讲沿着一条主线展开：

```text
演示数据来源
  → 任务与抓取合同
  → 七阶段脚本化专家
  → 命令动作 / 实测状态轨迹
  → 入碗结果判定
```

这条链把任务场景连接到数据生成。L09 才会定义采样、时间对齐、图像编码、LeRobot schema
和持久化 episode；L11 才会引入域随机化。这些机制都不属于 L08 rollout。

开始本讲前，你应当能够：

- 找出 Franka 的 7 个 arm DOF 和 2 个 finger DOF；
- 区分关节位置目标与实测关节状态；
- 读取世界坐标系中的末端位置和四元数；
- 解释 IK 返回什么，以及为什么求解结果仍需经过控制和仿真 step 才能真正执行；
- 检查物体位置和轴对齐包围盒（axis-aligned bounding box，AABB）；
- 通过 `build_scene()` 构建 L07 的固定任务场景。

## 学习目标

完成 L08 后，你应当能够：

1. 从成本、规模、任务覆盖、原始信号与适配需求几个方面比较常见的演示数据获取路线，
   并解释当前任务为什么选择脚本化专家；
2. 用 `TaskSpec`、`GraspProfile` 和七阶段流程表达 banana-to-bowl 任务，把任务转成末端目标、
   夹爪命令和运动基元；
3. 解释手臂位置控制、手指力控制和受限关节目标增量的不同作用，同时区分 commanded
   action 与 measured state；
4. 执行一次脚本化 rollout，解读 action/state 轨迹，并通过 bowl containment 判断任务
   是否完成。

## 精简的 120 分钟学习路径

| 时间 | 主题 | 学员产出 |
|---:|---|---|
| 0–25 分钟 | 演示数据获取方法与近期混合式路线 | 比较六类路线，并为一个任务说明来源选择 |
| 25–45 分钟 | `TaskSpec`、`GraspProfile` 与抓取几何 | 把任务写成明确的物体、目标、位姿和夹持参数 |
| 45–75 分钟 | 七阶段专家与控制分工 | 解释每个阶段、运动基元与控制模式 |
| 75–105 分钟 | 一次固定 banana-to-bowl rollout | 生成内存 action/state 轨迹和可选阶段画面 |
| 105–120 分钟 | 结果诊断、单变量练习与 L09 衔接 | 解读 containment 与关节目标 schedule |

前 25 分钟不会只罗列方法名称，而是解释现代数据管线为什么经常组合人工采集、仿真、
自动扩增和异构数据。随后，本讲会选取其中一条路线深入到能够实际执行和检查的程度。

## 分两篇学习本讲内容

### 第一篇——选择演示数据来源

[演示数据获取方法](./l08-demonstration-acquisition-methods.md)将比较：

- 遥操作（teleoperation）；
- 拖动示教（kinesthetic teaching）；
- 脚本化专家（scripted expert）；
- 使用仿真特权状态的学习型专家；
- 从 seed demonstration 出发的自动扩增；
- 人类视频迁移与 retargeting。

比较会先区分每条路线的原始信号，以及将其转换成机器人学习演示所需的 adapter，再把
低成本接口、in-the-wild 采集、跨本体汇聚、仿真扩展和第一视角视频等近期方向连接起来，
而不会假设这些来源可以直接互换。

### 第二篇——构建并检查脚本化专家

[脚本化抓取放置专家](./l08-scripted-pick-and-place-expert.md)将展开本仓库实际使用的专家：

```text
pregrasp → descend → grasp → lift → transport → release → retreat
```

正文会把 `TaskSpec` 和 `GraspProfile` 连接到 top-down 抓取几何，解释手臂与手指为什么使用
不同控制模式，推导搬运物体时的受限关节目标 schedule，并以两部分 containment 检查收束。

## 实验合同

配套 notebook 将构建一个固定的 `011_banana → 024_bowl` 任务，只调用一次共享专家，并在
内存中保留两组对齐数组：

```text
measured robot state : (T, 9)
commanded action     : (T, 9)
```

前 7 个值表示 arm joints，最后 2 个值表示 fingers。两组数组宽度相同，但回答的问题不同：
action 是专家发出的请求，state 则是采样时仿真机器人已经到达的状态。

核心路径不需要创建相机。显式开启渲染后，world camera 会额外给出一张起始画面和七个阶段
后的画面。这些图片方便观察动作顺序；任务证据仍来自数值轨迹与 containment 几何量。

## 一个任务，一次结果

L08 不做大规模 benchmark。核心实验回答的是一个更小但清楚的问题：

> 这一次固定 expert rollout 是否把香蕉放进了碗里？我们能否根据命令、实测状态和最终
> 几何关系解释这个结果？

结果判定同时要求香蕉在水平方向落入碗口范围，并且香蕉 AABB 的底部低于碗沿。单次成功
rollout 是一条完成任务的演示；若要报告成功率，还需另行设计多 seed 协议。

## 继续学习

先阅读[演示数据获取方法](./l08-demonstration-acquisition-methods.md)，再继续学习
[脚本化抓取放置专家](./l08-scripted-pick-and-place-expert.md)。
