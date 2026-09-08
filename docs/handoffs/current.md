# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-08（Asia/Shanghai）。

本文件只记录新 thread 最容易遗漏的当前状态、未决验收、近期运行证据和恢复顺序。课程
范围、通用门禁与里程碑状态以本地 `robo_genesis_101_course_development.plan.md` 为准；
逐讲设计、交付和验收历史位于本地 `course_development/lessons/`；运行环境与可公开引用的
实测证据以 `COMPATIBILITY.md` 为准；仓库级协作规则以根目录 `AGENTS.md` 为准。

## 1. 当前 Git 快照

- 当前分支为 `M3.L09`，HEAD 为 `df9cefa`，提交说明为
  `verified en/zh notebooks of l08 demonstration acquisition`；`origin/main`、
  `origin/HEAD`、本地 `main` 和 `M3.L08` 也指向该提交。
- 分支名不等于开发步骤已启动。开发记录明确显示 `M3.L09.1` 尚未启动，必须等待项目
  负责人明确指令。
- 更新本文件前 tracked worktree 干净；本次 handoff 更新会使
  `docs/handoffs/current.md` 成为预期的 tracked 修改，不要丢弃。
- 下列未跟踪内容均为既有的本地配置、补丁或开发记录，必须保留，不得清理或覆盖：
  `.vscode/`、`0001-4-cards-failure.patch`、`MIGRATION.md`、`course_development/`、
  `genesis_公开课体系规划_2ba5d82e.plan.md`、
  `robo_genesis_101_course_development.plan.md`。
- 本次交接没有创建 commit、push 或发布外部 artifact。

新 thread 开始工作前重新运行：

```sh
git status --short --branch
git log -1 --oneline --decorate
```

不要假设上述快照之后没有变化，也不要因当前分支名而跳过 L08.6 验收门禁。

## 2. 当前里程碑与唯一下一步

- L03–L07 的逐讲 `.1`–`.6` 均已完成并通过项目负责人验收。
- `M3.L08.1`–`M3.L08.5` 已于 2026-09-07 至 2026-09-08 逐步验收通过。
- 项目负责人已明确启动 `M3.L08.6`；其状态同步、更新后 clean-kernel 与完整门禁均已
  完成并交付，当前等待项目负责人验收。
- L08 已在公开来源中从 `planned` 原子同步为 `gpu-verified`。这表示 `.6` 的实施结果已经
  落地，不表示项目负责人已经验收 `.6`。
- `M3.L09.1` 尚未启动。当前唯一下一步是等待 `M3.L08.6` 的验收结论；若验收通过，仍需
  再等待项目负责人明确说“开始 `M3.L09.1`”，不能自动进入 L09。

当前 `course.json` 共 13 讲：

- L01–L07：7 个 `cpu-verified`；
- L08 与 L12：2 个 `gpu-verified`；
- L09–L11 与 L13：4 个 `planned`。

L08 为 120 分钟、`gpu-recommended`。L09–L11 与 L13 仍只有 `planned` 骨架，不能因已有
文件或当前 Git 分支名称而视为已经开发。

## 3. 近期验收形成的教学设计约束

以下偏好已经在 L07/L08 review 中由项目负责人明确，后续课程设计应继续遵循：

- 学习目标只写本讲真正能教会学习者什么、通过什么正向证据可以确认；不要把 notebook
  中的单个操作拆成目标，也不要为了凑目标而罗列“不能证明什么”。必要的证据边界可放在
  实验结论或验证说明中。
- 控制粒度和课时。已有充分前置铺垫时不要重复展开；L07 已因此从 120 分钟收敛为
  90 分钟并完成全局同步。
- learner-facing 内容只讲课程所需知识。L07 在仓库已经完成合规治理的前提下教学如何使用
  开源社区资产搭建 scene，不教授许可证审计或维护者治理流程，也避免冗余描述没有采用的
  下载、复制或路径猜测方式。
- 不要用“CPU minimum path”等措辞让学习者误解课程优选 CPU。应区分最低兼容路径、正常
  教学体验和附加平台证据。
- 抽象或新颖的方法适合配直观图示；图应先解释通用机制，再进入本课具体实现。例如 L08
  的 scripted expert 图使用通用 phase/transition 流程，没有提前绑定 notebook 七阶段。
  SVG 需要实际渲染检查箭头、连线、对齐、遮挡和中英文可读性。
- Notebook 应优先让学习者观察仿真画面、阶段图、曲线和几何关系，避免把学习体验变成
  连续阅读 `PASS` 日志。详细断言成功时保持静默，失败时给出具体项，最终只保留一条总检查。
- 中文 notebook 的 `Before you run` 沿用既有译法“运行前准备”。共享 `src/` 行为只有在
  确有必要时才修改，并在交付中清楚说明原因和影响范围。

## 4. L08 最终讲义与 notebook 合同

L08 的教学定位是：先比较演示获取方法及其优缺点，再以一个 scripted expert 把 L07 的
banana-to-bowl scene 转换为可观察的 action/state rollout，为 L09 数据录制提供输入，但
本讲不教授 LeRobot schema、时间对齐、episode 持久化或数据集写盘。

讲义采用一个导览和两篇双语正文：

- `l08-demonstration-acquisition-and-scripted-experts.md`：课程定位与学习路径；
- `l08-demonstration-acquisition-methods.md`：遥操作、拖动示教、脚本化专家、特权学习
  teacher、可信 seed 自动扩增和人类视频迁移；
- `l08-scripted-pick-place-expert.md`：task/profile、阶段程序、动作执行与成功证据。

acquisition methods 已配双语直观示意图。人类视频迁移不应被窄化为“必然先提取完整人体
skeleton”：骨架、手部姿态、物体轨迹、接触事件、时序阶段等都可能是中间任务线索，仍需
映射到机器人本体并通过执行验证。

双语 notebook：

- `notebooks/en/l08-demonstration-acquisition-and-scripted-experts.ipynb`；
- `notebooks/zh/l08-demonstration-acquisition-and-scripted-experts.ipynb`。

最终合同为 16 cells / 7 code cells；EN/ZH cell-type sequence、code-cell ID 与 source
完全一致，提交版保持 clean output。主实验只执行一次固定 `011_banana → 024_bowl`
rollout，并串联：

```text
task/profile → seven-phase program → command schedule
→ in-memory commanded/measured trace → containment → world-camera montage
```

学习输出包括七阶段流程图、command schedule、commanded/measured trace、containment
俯视/侧视图，以及默认渲染时的 `00_start` 加七阶段共 8 帧 world-view montage。检查成功时
最终只打印一次 `L08 CHECK: PASSED`。结尾使用 checkpoint 回看运行前预测，不另设突兀的
编号式参考答案页。

`motion_probe.py --compare` 是明确的可选对照实验：在同一 seed 起点比较 direct-target
`baseline` 与限步长插值 `landed`，联合观察 transport acceleration、in-gripper slip、
steps 和 success；可用 `--pick 014_lemon` 或 `--pick 018_plum` 替换抓取对象。该扩展没有
纳入 `.5` 的正式运行矩阵。

从 L08 开始，凡 notebook 提供 `ROBO_GENESIS_RENDER` 开关，默认值必须为 `1`，使 Genesis
仿真画面成为正常教学路径；`0` 是无法渲染时的显式无相机 fallback。该规则已同步到
`CONTENT_GUIDE.md`。L09–L13 当前骨架没有该开关，后续实现时按实际课程需要应用，不要
机械注入无效配置。

状态同步后的双语 notebook code-cell ID/source 规范化 SHA-256 为：

```text
da664ce963a3e8cb1eebca5c48bef9aa16dec2a4e3455bfdf9f3d691dbef2c52
```

## 5. M3.L08.5 已验收运行证据

正式记录位于 `COMPATIBILITY.md` 第 19.1–19.5 节。四条独立 clean-kernel 均通过：

| 路径 | 请求 → 实际 backend | render | runtime | 结果 |
| --- | --- | ---: | ---: | --- |
| English CPU | `cpu` → `cpu` | `0` | 70.23 秒 | `L08 CHECK: PASSED` |
| 中文 CPU | `cpu` → `cpu` | `0` | 72.31 秒 | `L08 CHECK: PASSED` |
| English CPU+EGL | `cpu` → `cpu` | `1` | 85.21 秒 | `L08 CHECK: PASSED` |
| English AMD+EGL | `auto` → `amdgpu` / R9700 | `1` | 127.24 秒 | `L08 CHECK: PASSED` |

共同结果：

- 四条路径均为 7/7 code cells、0 error、`success=True`；
- CPU 三条路径的 state/action 为 `(850, 9)`，AMD 为 `(849, 9)`；数组等长、floating、
  finite，步数末位差异不作为跨 backend 固定答案；
- horizontal footprint 与 bottom-below-rim containment 均通过；
- `render=0` 不创建 camera，stage images 为 0，并明确 `SKIP`；
- `render=1` 均生成 8 张 `(720, 1280, 3)` `uint8` RGB；人工检查确认预抓取、下降/闭合、
  抬升、移至 bowl 上方、释放和退回顺序清楚，最终 banana 位于 bowl 内；
- `.5` 执行时 code hash 为
  `627e260f1d34ef1b3cc18af8c1baccc0d58791857eeb7fc132c0834696ceca5a`。

参考环境为 Python 3.12.3、Genesis 1.3.3、PyTorch ROCm 7.2.1、HIP 7.2 和 AMD Radeon
AI PRO R9700。临时产物曾位于 `/tmp/rg101-l085.QCL68t`，新 thread 不应假设该目录仍存在。

该证据只记录固定 banana episode 在四条路径中成功完成的实例，不等于多 seed 成功率，
也没有验证 lemon/plum、其他平台或 `motion_probe.py --compare` 扩展。

## 6. M3.L08.6 已交付内容与更新后复验

L08 状态已经原子同步到以下公开来源：

- `course.json`；
- 双语 L08 导览 frontmatter 与状态说明；
- 双语 notebook metadata，以及 setup/final-check 中两处 manifest status 断言；
- `README.md` / `README_en.md`；
- `docs/zh/index.md` / `docs/en/index.md`；
- `tests/test_assets.py` 与 `tests/test_course_manifest.py`；
- `COMPATIBILITY.md` 第 19.6 节、L08 单课档案和根目录主开发计划。

两篇拆分正文没有独立 frontmatter，因此没有增加重复状态字段。课程顺序、slug、时长与
硬件字段未改变，sidebar 无需修改。

状态 literal 更新后，English notebook 又在独立 CPU、`render=0` kernel 中从头执行，
耗时 66.96 秒：7/7 code cells、0 error、实际 backend `cpu`、没有创建 camera、
state/action `(850, 9)`、`success=True`、两项 containment 通过，最终
`L08 CHECK: PASSED`。执行副本与当前 code hash 一致，临时产物曾位于
`/tmp/rg101-l086.wT3Yrk`；新 thread 不应依赖该目录。

`.6` 只改变状态相关字段和断言，没有改变 task、control、simulation 或 rendering 行为，
因此 `.5` 已验收的中文 CPU、CPU+EGL 与 AMD+EGL 证据继续适用。

## 7. 最近完整仓库门禁与已知 warning

状态同步后已通过：

- `.venv/bin/python -m robo_genesis.course_validation`：13 lessons、32 localized
  Markdown files、26 notebooks、31 Python files；
- `.venv/bin/python -m pytest`：38 passed；
- `.venv/bin/python -m compileall -q src scripts tests`；
- `npm ci`；
- `npm run docs:build` 与 `EDGEONE=1 npm run docs:build`；
- `git diff --check`。

既有非阻断信息：Node 20.18.2 `EBADENGINE` warning；npm 13 项 advisory（6 low、
1 moderate、6 high）；Genesis Franka tendon approximation、neutral qpos、solver
time-constant、neutral self-collision filtering warning；Quadrants template mapper cache
warning；AMD 路径有第三方 `ast.Str` deprecation warning。没有 EGL、OpenGL、backend
fallback、非有限值或任务检查错误。没有修改依赖，也没有运行 `npm audit fix`。

## 8. 新 thread 恢复顺序

1. 完整读取根目录 `AGENTS.md`、本文件和
   `robo_genesis_101_course_development.plan.md`。
2. 针对当前未决步骤读取 `course_development/lessons/l08.md` 的“六、M3.L08.6”和
   `COMPATIBILITY.md` 第 19 节；需要追溯讲义/notebook review 时再读取 L08 单课档案前文。
3. 重新核对 Git 分支、HEAD 与工作树，保护第 1 节列出的所有 untracked 文件和本 handoff
   修改。
4. 将 L03–L07 全部步骤与 `M3.L08.1`–`.5` 视为已验收历史，不重复开发、运行或状态同步。
5. 首先等待项目负责人对 `M3.L08.6` 的验收结论。验收前不得开始 L09；验收通过后也必须
   等待项目负责人明确启动 `M3.L09.1`。
6. 若收到“开始 `M3.L09.1`”，先按主计划建立或维护 L09 单课开发档案，完成教学设计、
   来源映射、视觉方案、notebook 合同与 `.5`–`.6` 验收门禁；不要直接跳到讲义或 notebook
   实现，也不要提前改变 L09 的 `planned` 状态。

持续适用的协作边界：每个子步骤单独等待项目负责人验收，不自动开始后续步骤；
`docs/handoffs/current.md` 只在项目负责人准备切换 thread 时更新；不创建 commit、不 push、
不发布外部 artifact，除非项目负责人明确要求。
