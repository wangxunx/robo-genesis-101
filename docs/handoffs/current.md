# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-03（Asia/Shanghai）。

本文件只记录新 thread 最容易遗漏的当前状态、未决决定和恢复顺序。课程范围、逐步验收
规则和当前状态摘要以本地 `robo_genesis_101_course_development.plan.md` 为准；逐讲的
设计、交付与验收历史已拆分到本地 `course_development/lessons/`，按需读取；
运行环境和实测证据以 `COMPATIBILITY.md` 为准；迁移来源与历史取舍以 `MIGRATION.md`
为准。

## 1. 当前 Git 快照

- 当前分支：`M3.L05`。
- 当前 HEAD：`1997d9a`，提交说明为 `update handoff doc`；其父提交 `46b9b62` 为
  `verified en/zh notebooks l05 IK and end effector poses and cameras`。
- 当前 HEAD 已包含 M3.L05.6 的 tracked 状态同步：L05 在 `course.json`、双语 README/
  首页、双语讲义、双语 notebook 和状态测试中均为 `cpu-verified`，`COMPATIBILITY.md`
  也记录了状态边界。
- “状态同步已进入 HEAD”不等于“项目负责人已经验收 M3.L05.6”。截至本 handoff，项目
  负责人只明确验收了 M3.L05.1–M3.L05.5；M3.L05.6 仍为待验收，且后续提出了重要的
  L05 简化意见，见第 4 节。
- 本地开发计划已从 3901 行收敛为 554 行的总纲、当前状态和档案索引；原第 522 行以后
  的内容按讲次完整拆分为 `course_development/lessons/l01.md`、`l02.md`、`l03.md`、
  `l04.md`、`l05.md` 和 `l11.md`。除文件末尾空行规范化外，原历史内容未改写。
- `robo_genesis_101_course_development.plan.md` 与 `course_development/` 都是有意保持
  untracked 的本地开发记录，不应提交，也不应加入仓库级 `AGENTS.md`、README、验证器
  或其他发布结构。新的课程档案在对应 `.1` 启动时才创建，不建立空占位文件。
- 其余既有未跟踪内容 `.vscode/`、`0001-4-cards-failure.patch`、`MIGRATION.md` 和
  `genesis_公开课体系规划_2ba5d82e.plan.md` 也不得擅自删除、覆盖或顺手纳入提交。
- 本次只为新 thread 恢复更新此 handoff；没有创建 commit、push 或发布外部 artifact。

新 thread 开始工作前必须重新运行 `git status --short` 和 `git log -1 --oneline`，不要
假设上述快照之后没有变化。

## 2. 里程碑、验收握手与公开状态

- 已由项目负责人验收：M0、M1、M2、M3.1、M3.L03.1–M3.L03.6、
  M3.L04.1–M3.L04.6、M3.L05.1–M3.L05.5。
- M3.L05.6 已完成状态同步并写入 HEAD，但尚未收到项目负责人的明确验收。
- 不得把 commit、测试通过、文件存在或 `cpu-verified` literal 自动解释成项目负责人验收。
- 不得开始 L06；必须先处理第 4 节的 L05 简化方向，并由项目负责人决定 M3.L05.6 的
  后续验收方式。

当前公开 manifest 状态是：L01–L05 共 5 讲为 `cpu-verified`，L11 为
`gpu-verified`，L06–L10 和 L12 共 6 讲为 `planned`。L05 使用 `cpu-verified` 是因为
`cpu-ok` 是最低硬件合同；参考 AMD R9700 + EGL 是附加兼容性证据，不把 GPU 变成
学习门槛，也不表示课程已经 `published`。

## 3. 当前 L05 实现与已经完成的验证

当前 L05 并非只迁移原课程 Module 04。按已验收的 M3.L05.1 设计，它合并了原课程 commit
`03af81cbe6d4d2b3ef658ae1ab3e85f028bff9c6` 的两部分：

- `hello-genesis-world/en/module_04_ik_and_cameras/04_ik_and_cameras.ipynb`：单环境
  reachable/unreachable IK、动态控制、fixed camera RGB/depth；
- `hello-genesis-world/en/module_05_parallel_and_capstone/05_parallel_and_capstone.ipynb`：
  B=4 batched IK/control 和 `envs_idx=[1,3]` selective update。

当前 EN/ZH L05 notebook 各有 23 个 cell、14 个 code cell，主要结构是：

1. backend/render 运行合同与运行前预测；
2. 单环境 Plane、Franka、reachable marker、fixed camera 和 wrist camera；
3. world/base/hand/camera frame map、9 DOF 结构和初态检查；
4. quaternion、FK、full/arm Jacobian、camera K/extrinsics 与 RGB/depth helper；
5. reachable IK candidate acceptance、IK 状态恢复和 FK prediction；
6. 180-step joint-position PD 动态执行、pose trajectory 与 fixed/wrist camera 观测；
7. 基于本次数组生成的四段式 Guided reachable interpretation；
8. `[2,0,2]` unreachable target 的正常拒绝、显式 diagnostic override 和四段式解释；
9. 第二个 B=4 Scene 的 batched reaching、逐环境验收；
10. `envs_idx=[1,3]` selective update、未选环境 retained-target 检查和 Guided batch
    interpretation；
11. 汇总全部 runtime checks 并输出 `L05 CHECK: PASSED`。

当前实现严格区分五种证据：candidate 结构安全、IK solver residual、FK prediction、
动态 measured tracking error、camera pixels。它还包含 Genesis 1.3.3 的版本限制：
`forward_kinematics()` 依赖第一次 IK 初始化内部 scratch/cache，因此当前调用顺序是先 IK、
再 FK；IK 后、FK 前读取状态，以免把 FK 重算混入“solver 是否改变 scene state”的检查。

M3.L05.5 已验收的四条最终 clean-kernel 路径是：

| 路径 | 请求 → 实际 backend | camera | 结果 |
|---|---|---|---|
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L05 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L05 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | fixed/wrist RGB、fixed depth | `L05 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | fixed/wrist RGB、fixed depth | `L05 CHECK: PASSED` |

M3.L05.6 状态 literal 更新后又复跑了一次英文 CPU、`render=0` clean kernel：请求与实际
backend 都是 `cpu`，camera 分支明确 `SKIP`，无 error output，最终为
`L05 CHECK: PASSED`。完整门禁结果为：

- `.venv/bin/python -m pytest tests/test_course_manifest.py`：9 passed；
- `.venv/bin/python -m robo_genesis.course_validation`：通过，12 lessons、
  26 localized Markdown files、24 notebooks、31 Python files；
- `.venv/bin/python -m pytest`：35 passed；
- `.venv/bin/python -m compileall -q src scripts tests`：通过；
- `npm ci`：成功，仍报告既有 13 项 advisory（6 low、1 moderate、6 high）；
- `npm run docs:build` 和 `EDGEONE=1 npm run docs:build`：通过；
- EN/ZH notebook JSON、Python syntax、cell type/ID/code source parity、空 output、空
  execution count 和 `cpu-verified` metadata：通过；
- `git diff --check` 与未跟踪开发计划的尾随空白检查：通过。

以上运行证据只适用于当前 HEAD 中的现有复杂版 notebook；若按第 4 节重构，必须重新
验证，不能把旧结果直接当作新 notebook 已通过。

## 4. 最新且尚未实施的 L05 简化方向

项目负责人在 M3.L05.6 验收前指出，当前 notebook 相比原课程明显过于复杂，学习者很难
看清主线。审查确认该判断成立：

- 当前 L05 有 14 个 code cell、约 1470 个 code source 行；
- 原 Module 04 有 5 个 code cell、约 185 行；
- 原 Module 05 有 5 个 code cell、约 121 行；
- 即使把两份原 notebook 合计作为基线，当前代码量仍约为其 4.8 倍；当前普通 Markdown
  解释反而少于两份原 notebook 合计，部分解释藏在长 Python f-string 中。

复杂度来自把两个源 notebook 合并，并叠加 FK、Jacobian、wrist camera、intrinsics、
extrinsics、双 render 分支、严格数组合同、跨后端兼容性检查和最终 regression harness。
当前机制与证据逻辑是自洽的，但“教学主线”和“工程验收代码”没有清楚分层。

项目负责人最新提出的考虑是：

1. **学习者易于学习、教程简明清晰是最高优先级。**
2. L05 只讲 IK、FK、end-effector poses 和 cameras，整体回到原课程 Module 04 的范围，
   相比原版只明确新增 FK。
3. 暂时移除所有 parallel、B=4、batched IK/control 和 selective `envs_idx` 内容。
4. Camera 不是本讲重点，只做轻量介绍并提及 depth；不讲 pinhole model、intrinsics 和
   extrinsics。

这项方向**尚未实施，也尚未写成新的正式验收设计**。上一个 thread 在项目负责人询问
“你觉得我的想法如何？”之后因 context 切换结束，Codex 还没有给出最终回应。新 thread
应先明确回应：该方向符合 L04→L05→L06 的学习主线，能够显著提高可读性；parallel/
batched 内容并非 L06 抓取场景的必要先修，可以明确记录为“暂缓并留待后续讲次重新
评估”，而不是静默丢弃。

若项目负责人随后明确要求实施，建议先确认并记录如下精简边界：

- 保留：world-frame target、Genesis `wxyz` quaternion 的最低必要说明、reachable IK、
  residual acceptance、FK 对 candidate pose 的预测、通过 L04 joint-position PD workflow
  动态执行、measured end-effector pose/error、一个简单 fixed camera 的 RGB/depth 获取、
  unreachable negative case、简短且基于本次结果的 Guided interpretation。
- 删除或移出 L05 主线：Part C 整体、第二个 B=4 Scene、batched arrays、selective update、
  batch plots/checks；Jacobian/SVD；wrist camera；pinhole K；intrinsics/extrinsics；与这些主题
  绑定的大量检查和最终汇总项。
- Camera 建议恢复到原 Module 04 的教学粒度：`add_camera()`、`render(rgb=True,
  depth=True)`、显示 RGB/depth 并说明 shape/基本含义即可，不发展成相机标定课程。
- FK 与 IK 的推荐主线是：解释 FK/IK 的相反查询 → 求 reachable IK candidate → 用 FK
  预测该 candidate 的 hand pose → 经 PD + `scene.step()` 执行 → 比较 measured pose。
  Genesis 1.3.3 的“先 IK 初始化、再调用 FK”限制应保留一条透明说明，但不应继续扩张为
  大段兼容性教学。
- 保留关键代码直接可读：`inverse_kinematics()`、residual 判据、
  `forward_kinematics()`、`control_dofs_position()+scene.step()`、`add_camera()` 和
  `camera.render()`；重复 shape/finite/table/export/final aggregation 可压缩，但不得把
  核心逻辑改成学习者看不到的黑盒。

由于已验收的 M3.L05.1 曾明确要求保留原 Module 05 的 batch extension，上述新方向一旦
确认，必须在开发计划中新增一条显式的“项目负责人后续调整”记录，说明 batched 内容是
暂缓/迁移候选而非无声删除，并同步审查双语讲义、双语 notebook、`COMPATIBILITY.md`
和相关测试。不要直接改一个英文 notebook 后就结束。

## 5. 新 thread 的建议恢复顺序

1. 完整阅读根目录 `AGENTS.md`。
2. 运行 `git status --short` 和 `git log -1 --oneline`，保护所有既有未跟踪内容。
3. 阅读本地开发主计划；重点是“当前阶段状态”和“M3 Notebook 迁移与视觉呈现门禁”，
   不需要加载其他已完成课程的单课档案。
4. 阅读本文件。
5. 读取 `course_development/lessons/l05.md` 中的 M3.L05.1–M3.L05.6 详细历史；涉及现有
   运行证据时再读取 `COMPATIBILITY.md` 第 14 节。
6. 查看原课程 commit `03af81cbe6d4d2b3ef658ae1ab3e85f028bff9c6` 的 EN Module 04
   和 Module 05 notebook，再查看当前 EN L05 的 23-cell 结构。
7. 先回应/确认第 4 节的简化方向；未经项目负责人明确实施指令，不自行重写 L05。
8. 未完成 L05 简化、复验和 M3.L05.6 验收前，不开始 `M3.L06.1`。

## 6. 持续适用的课程开发原则

- Notebook 迁移以保留教学意图为默认；拟删除或迁移内容必须提前列出并让项目负责人
  review。第 4 节已经提出新的明确方向，但仍应在正式实施记录中说明去向。
- 学习者可读性优先于把所有 CI/兼容性检查塞进主实验；同时必须保留当前课程真正需要
  学习者阅读的关键 API 和判据。
- Genesis camera 画面与 Matplotlib 定量证据各有职责，不能把状态示意图冒充 camera。
  但并非每讲都要教授完整相机模型；L05 最新方向明确要求轻量化 camera 内容。
- EN/ZH 讲义结构与内容必须同步；EN/ZH notebook 的 cell-type sequence、code-cell ID 和
  code source 必须一致，只本地化 Markdown。
- Notebook 必须从 clean kernel 自上而下运行，提交文件不得含无教学价值的 outputs、
  execution counts、缓存或机器绝对路径。
- 不伪造运行结果；重构后未复跑的 CPU、EGL 或 AMD 路径必须明确写为未验证。
- 不创建 commit、不 push、不发布外部 artifact，除非项目负责人明确要求。

仓库现有 `.venv` 是近期 L05 验证使用的环境。后续验证应优先复用它，并把执行后
notebook、图片和缓存写入 `/tmp` 或既有 ignored outputs 目录。
