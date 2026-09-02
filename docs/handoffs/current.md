# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-02。

本文件只记录新 thread 最容易遗漏的当前状态。课程范围、逐步验收规则、历史决策和
详细交付记录以仓库根目录的 `robo_genesis_101_course_development.plan.md` 为准；运行
环境与实测证据以 `COMPATIBILITY.md` 为准；迁移来源与取舍以 `MIGRATION.md` 为准。

## 1. 当前 Git 快照

- 当前分支：`M3.L03`。
- 当前 HEAD：`155ff6b`，提交说明为 `inline core code in notebooks of l03 rigid body physics`。
- 该提交已经包含 L03 从 `planned` 到 `cpu-verified` 的状态同步、runner 核心代码展示、
  Part A/Part B 动态解释及相应测试更新。
- 当前 HEAD 之后存在一组待项目负责人复核的 L03 相机关键帧改动，涉及双语
  notebook/讲义、两个刚体实验 runner、定向测试和兼容性证据；不得误认为已经提交。
- 当时已有以下未跟踪内容，均应视为现有工作区内容，不得擅自删除、覆盖或纳入其他
  步骤：`.vscode/`、`0001-4-cards-failure.patch`、`MIGRATION.md`、
  `genesis_公开课体系规划_2ba5d82e.plan.md`、
  `robo_genesis_101_course_development.plan.md`。
- 本 handoff 文件也是新创建文件；是否纳入提交由项目负责人决定。

新 thread 开始工作前必须重新运行 `git status --short` 和 `git log -1 --oneline`，
不要假设上述快照之后没有变化。

## 2. 里程碑与验收握手

- 已由项目负责人验收：M0、M1、M2、M3.1，以及 M3.L03.1–M3.L03.6。
- M3.L03.6 在完成核心 runner 代码展示、Part A/Part B 动态解释及相应复验后，已于
  2026-09-02 由项目负责人明确验收通过。
- L03 的六个开发子步骤已经全部完成；`M3.L04.1` 尚未开始。
- 在收到项目负责人明确开始 `M3.L04.1` 的指令前，不得自行进入 L04。

当前公开课程状态是：L01、L02、L03 为 `cpu-verified`，L11 为 `gpu-verified`，其余
讲次为 `planned`。L03 之所以标记为 `cpu-verified`，是因为 `cpu-ok` 是最低硬件合同；
这不否认其参考 AMD ROCm 路径已经实测通过。

## 3. M3.L03.6 已验收内容

L03 状态已在以下位置保持一致：

- `course.json`；
- `README.md`、`README_en.md`；
- `docs/zh/index.md`、`docs/en/index.md`；
- EN/ZH L03 讲义 frontmatter 和开头状态说明；
- EN/ZH L03 notebook metadata；
- `tests/test_course_manifest.py` 的课程状态合同。

本步没有修改 L03 实验代码、标题、时长、硬件要求或路径，也没有开始 L04。完整的
L03 CPU/AMD clean-kernel 命令、环境和数值关系证据位于 `COMPATIBILITY.md` 第 12 节；
M3.L03.1–M3.L03.6 的设计和交付记录位于 plan 第十三至十八节。

2026-09-02 的 M3.L03.6 review 反馈要求在四组 contact 子进程调用前展示
`rigid_contact` 的关键真实代码，并对 Part B 的 `rigid_friction` 做同样处理。EN/ZH
notebook 已增加两个同构 Markdown 单元：前者展示 Scene 配置、实体创建、`build()`、
逐步状态读取和接触采样，后者展示双方块摩擦场景、沉降、初速度设置及平移/转动/接触
采样。公共模块仍是唯一可执行真相源，测试会逐字核对两段展示与各自源码标记区域。本次
返工还把被压缩的结果摘要恢复为基于实测数组生成的四段式 `Guided interpretation`，
分别引导固定 `dt`、匹配 `substep_dt`、限定结论范围和联合判断反弹。runner 和实验参数
没有变化；notebook 的纯 NumPy 解释 code cell 已修改并复验。Part B 也已补回基准实验的
四段式 `Guided friction interpretation` 和桌面摩擦练习的四段式 `Guided one-factor
interpretation`，动态覆盖受控变量、有效摩擦、持续停止、角速度/contact、停止距离方向
和控制通道容差。没有开始 L04。

### 验收后的视觉呈现复查（待项目负责人复核）

项目负责人随后要求按“原课程内容保留优先”和“优先使用 Genesis 原生视觉呈现”的原则
重新对照原课程 notebook。审计确认，独立 Learning objectives 和静态 Summary 属于新版
notebook 的全课程结构取舍，不在 L03 局部恢复；获批实施的是原课程 Part A、Part B 的
Genesis camera 关键帧，且本轮不增加视频。

- `rigid_contact.py` 和 `rigid_friction.py` 新增显式 `--render` 分支，只在启用时于
  `build()` 前添加 camera，采集并严格校验 `initial_rgb`/`final_rgb`；渲染失败会直接
  暴露，关闭时则保存 shape 为 `(0,)` 的明确空字段。
- 双语 notebook 沿用 `ROBO_GENESIS_RENDER=0/1` 合同。Part A 在开启渲染时展示共享
  初始帧和 N1–N4 最终帧五联图；Part B 展示基准实验速度注入前/测量结束后的画面，以及
  table friction 0.50/0.30 的最终帧对照。关闭渲染时使用实测状态生成同构示意图，并
  明确标注不是 camera 输出。
- 原有高度、速度、接触、角速度和停止距离 Matplotlib 定量图全部保留；camera 画面承担
  场景与运动结果的直观证据，两者不互相替代。
- EN/ZH notebook 仍为 20 个 cell、10 个 code cell，code-cell ID/source 完全一致，
  提交文件不含 output 或 execution count。`COMPATIBILITY.md` 第 12.4 节记录本轮命令、
  RGB 属性、人工图像检查和证据边界。

本项是已经验收的 L03 范围内修正，尚待项目负责人复核；课程状态仍为
`cpu-verified`，没有开始 L04。

## 4. 最近一次验证结果

针对当前待复核的 L03 camera 修改，已经得到以下结果：

- `.venv/bin/python -m robo_genesis.course_validation`：通过，统计为 12 lessons、
  26 localized Markdown files、24 notebooks、31 Python files。
- `.venv/bin/python -m pytest`：通过，`35 passed`。
- `.venv/bin/python -m compileall -q src scripts tests`：通过。
- `npm ci`：成功；报告既有的 13 项 advisory（6 low、7 high），本步没有修改依赖。
- `npm run docs:build`：通过。
- `EDGEONE=1 npm run docs:build`：通过。
- `git diff --check`：通过。
- L03 双语 notebook JSON/course validation/code parity 通过；无 output 或 execution
  count。规范化 code-cell SHA-256 为
  `bd5db9c7c3427f1ba9b13fc0f0f3786b51497077e4da36f1cd533e718734e955`。

相机恢复后使用三个独立 clean kernel 复验，三条路径均输出 `L03 CHECK: PASSED`：

- EN / AMD R9700 + EGL / `ROBO_GENESIS_RENDER=1`：实际后端为 `amdgpu`，六个 runner
  均捕获真实 camera 图像；接触 RGB 为 `(360, 640, 3)`，摩擦 RGB 为
  `(400, 720, 3)`，均为非空 `uint8` 有限数组。三张组合图经人工检查，场景、运动结果
  和 table friction 单变量位移差异均清晰。
- EN / CPU / `ROBO_GENESIS_RENDER=0`：六个结果均保存 `(0,)` 空画面字段并明确打印
  `SKIP`，状态示意图 fallback 与全部数值关系检查通过。
- ZH / CPU / `ROBO_GENESIS_RENDER=0`：同样通过空画面字段、fallback 和数值关系检查。

数值证据保持不变：N1–N4 的穿透代理约为 13.193、7.797、23.984、13.193 mm；
baseline 摩擦停止距离约为 0.410/0.224 m，table friction 降至 0.30 后约为
0.675/0.224 m。`npm ci` 仍只报告既有的 13 项 advisory，本轮没有修改依赖。

## 5. 新 thread 的读取顺序

1. 阅读根目录 `AGENTS.md`。
2. 阅读本文件并重新核对 Git 状态。
3. 阅读 plan 的“第五部分：实施顺序与验收闸门”以及第十三至十八节。
4. 涉及运行环境或 L03 证据时，阅读 `COMPATIBILITY.md` 第 12 节。
5. M3.L03.6 已验收；未获明确指令时不要开始 `M3.L04.1`。

仓库现有 `.venv` 是按 `COMPATIBILITY.md` 建立并用于近期验证的环境。后续验证应优先
复用它，避免无必要地重新解析或下载大型 PyTorch 依赖。
