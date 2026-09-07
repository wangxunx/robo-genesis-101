# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-07（Asia/Shanghai）。

本文件只记录新 thread 最容易遗漏的当前状态、未决决定和恢复顺序。课程范围、逐步验收
规则和当前状态摘要以本地 `robo_genesis_101_course_development.plan.md` 为准；逐讲的
设计、交付与验收历史位于本地 `course_development/lessons/`；运行环境与可公开引用的
实测证据以 `COMPATIBILITY.md` 为准；迁移来源与历史取舍以 `MIGRATION.md` 为准。

## 1. 当前 Git 快照

- 当前分支为 `main`，HEAD、`origin/main` 与 `origin/HEAD` 均为 `831dd3e`，提交说明为
  `verified en/zh notebooks l06 parallel simulation`；本地与远端计数为 `0 0`。
- 更新本文件前 tracked worktree 干净；本次 handoff 更新会使
  `docs/handoffs/current.md` 成为预期的 tracked 修改。不要丢弃该修改。
- 本地开发记录 `robo_genesis_101_course_development.plan.md` 与
  `course_development/` 有意保持 untracked，但包含最新且已验收的 L06 历史，必须保留。
- 既有未跟踪内容 `.vscode/`、`0001-4-cards-failure.patch`、`MIGRATION.md` 和
  `genesis_公开课体系规划_2ba5d82e.plan.md` 也必须保留，不要清理或覆盖。
- 本次 handoff 更新没有创建 commit、push 或发布外部 artifact。

新 thread 开始工作前必须重新运行 `git status --short --branch` 和
`git log -1 --oneline --decorate`，不要假设上述快照之后没有变化。

## 2. 当前里程碑与唯一下一步

以下开发范围已经项目负责人逐步验收：

- M0、M1、M2、M3.1；
- `M3.L03.1`–`M3.L03.6`；
- `M3.L04.1`–`M3.L04.6`；
- L05 精简重做的 `M3.L05R.1`–`M3.L05R.6`；
- 13 讲结构迁移 `M3.R13.1`–`M3.R13.3`；
- 新 L06 的 `M3.L06.1`–`M3.L06.6`。

L06 六个子步骤已于 2026-09-07 全部验收，公开状态为 `cpu-verified`。当前没有正在实施的
子步骤；唯一候选下一步是 `M3.L07.1`，必须等待项目负责人明确启动，不能自动进入 L07。

当前公开 manifest 共 13 讲：

- L01–L06：6 个 `cpu-verified`；
- L12：1 个 `gpu-verified`；
- L07–L11 与 L13：6 个 `planned`。

课程编号已经完成迁移，不得恢复旧 12 讲结构。当前 L07 是“抓取任务场景搭建” /
“Building a Grasping Task Scene”；训练课是 L12，闭环评估与 Capstone 是 L13。

## 3. L06 最终教学与 notebook 合同

L06 位于单环境 L05 和抓取场景 L07 之间，集中讲 Genesis 并行仿真、leading environment
dimension、batched IK/control 和 selective update，不引入抓取状态机、数据集、policy
或完整并行 recorder。

双语讲义：

- `docs/en/lessons/l06-parallel-simulation-and-batched-franka-control.md`；
- `docs/zh/lessons/l06-parallel-simulation-and-batched-franka-control.md`。

双语 notebook：

- `notebooks/en/l06-parallel-simulation-and-batched-franka-control.ipynb`；
- `notebooks/zh/l06-parallel-simulation-and-batched-franka-control.ipynb`。

每份 notebook 为 16 个 cell、7 个 code cell；EN/ZH cell-type sequence、code-cell ID 与
code source 完全一致，提交版保持空 outputs 和 `execution_count: null`。当前状态同步后的
code-cell ID/source 规范化 SHA-256 为
`7be4b1574090ed727f084f03b6f74d1c65ff2c562a1e74311eb81e592bbfb97d`。

实验主线：

```text
one topology → scene.build(n_envs=4) → state shape (4, D)
four world-frame targets → batched IK → per-environment acceptance
accepted q rows → 180-step batched PD → measured per-environment error
envs_idx=[1,3] → two-row selective IK/control → selected + retained checks
optional environment-separated camera → RGB/depth batch → 2×2 mosaic
```

关键合同：

- qpos `(4,9)`，full target `(4,3)/(4,4)`，full IK `(4,9)/(4,6)`；
- selective row 0/1 明确映射 env 1/3，selective IK `(2,9)/(2,6)`；
- IK residual 逐环境检查 `<=5e-4 m` / `<=5e-3 rad`；
- 动态误差逐环境检查 `<0.02 m` / `<0.05 rad`；
- env 0/2 不被描述为冻结，而是继续跟踪 retained target；同时检查额外 motion
  `<0.005 m` 与 retained position-error increase `<=0.002 m`；
- `render=0` 明确 `SKIP`；`render=1` 使用 `env_separate_rigid=True`，期望 RGB
  `(4,360,640,3)` 与 depth `(4,360,640)`；
- 不设置固定 speedup 门槛，不把 batched API、仿真吞吐、batched rendering 与完整并行
  recorder 混成同一个结论。

现有 `course_utils` 与 `scene_config` 已覆盖本讲需要的公共行为，L06 没有新增 `src/`
接口、测试依赖或第三方依赖。

## 4. L06 已验收运行证据

`M3.L06.5` 完成四条独立 clean-kernel 路径：

| 路径 | 请求 → 实际 backend | camera | 结果 |
|---|---|---|---|
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L06 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L06 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | 四环境 RGB/depth | `L06 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | 四环境 RGB/depth | `L06 CHECK: PASSED` |

CPU 关键结果：

- baseline IK position residual 约为 `0.000001–0.000492 m`，rotation residual 约为
  `0.000000–0.000297 rad`；
- baseline 四环境 position error 约为 `0.004860–0.005593 m`，orientation error 约为
  `0.010948–0.012569 rad`；
- selective env 1/3 position error 约为 `0.005276/0.006059 m`，orientation error 约为
  `0.012084/0.013394 rad`；
- untouched env 0/2 的额外 motion 与 retained position-error change 均报告为
  `0.000000 m`。

CPU+EGL 与 AMD+EGL 均得到 RGB `(4,360,640,3)` `uint8`、depth `(4,360,640)`
`float32`。人工检查两条 2×2 RGB mosaic，四幅图均能看到对应 Franka 与棋盘地面，无
空白、全黑、明显错位或损坏。depth 只完成数组、有限性和正值像素检查，没有被表述为
人工视觉结果。

`.5` 执行时的旧 code hash 为
`d1bab5f21645f42148ee0c6c29d7e294b0ac50fda1d5a90b06a8dd28d88160ee`。`.6` 只把 manifest
状态断言从 `planned` 改为 `cpu-verified`，随后又以当前新 hash 独立执行 English CPU
`render=0`；7/7 code cell、0 error，最终再次得到 `L06 CHECK: PASSED`。中文 CPU、
CPU+EGL 与 AMD+EGL 的 `.5` 证据继续适用，因为仿真与渲染逻辑没有改变。

正式可引用证据位于 `COMPATIBILITY.md` 第 17 节；执行后 notebook、图片和 cache 只写入
`/tmp`，没有提交。临时目录曾为 `/tmp/rg101-l06.5.3qCqss/` 和
`/tmp/rg101-l06.6.KLZj2g/`，但新 thread 不应假设临时文件仍存在。

## 5. M3.L06.6 状态同步范围

以下公开来源现已一致为 L06 `cpu-verified`：

- `course.json`；
- `README.md` / `README_en.md` 的顶部摘要和课程表；
- `docs/zh/index.md` / `docs/en/index.md` 的状态摘要和课程表；
- 双语 L06 lecture frontmatter 与开头状态说明；
- 双语 L06 notebook metadata 与 setup manifest 断言；
- `tests/test_course_manifest.py` 的课程状态序列；
- `COMPATIBILITY.md` 的平台矩阵和第 17.5 节状态结论。

状态同步没有改变课程顺序、slug、路径、时长或硬件要求，因此
`docs/.vitepress/config.mts` 无需修改。`cpu-verified` 只表示 CPU 最低路径已验证；参考
R9700 是附加证据，不表示 GPU 必修，也不表示 L06 已经 `published`。

## 6. 最近完整验证结果

M3.L06.6 交付前完成：

- manifest 状态计数：6 个 `cpu-verified`、1 个 `gpu-verified`、6 个 `planned`；
- `.venv/bin/python -m pytest tests/test_course_manifest.py`：9 passed；
- 更新后的 English L06 CPU `render=0` clean-kernel：7/7 code cell、0 error、
  `L06 CHECK: PASSED`；
- `.venv/bin/python -m robo_genesis.course_validation`：通过，13 lessons、
  28 localized Markdown files、26 notebooks、31 Python files；
- `.venv/bin/python -m pytest`：35 passed；
- `.venv/bin/python -m compileall -q src scripts tests`：通过；
- `npm ci`：成功安装 190 个包；仍报告既有 13 项 advisory（6 low、1 moderate、6 high），
  没有运行 `npm audit fix`；
- `npm run docs:build` 与 `EDGEONE=1 npm run docs:build`：均通过；
- 双语状态一致性、notebook parity/clean-output/source integrity、旧状态残留、尾随空白与
  `git diff HEAD --check`：均通过。

## 7. 新 thread 恢复顺序

1. 完整读取根目录 `AGENTS.md`、本文件、`robo_genesis_101_course_development.plan.md`，
   并按需读取 `course_development/lessons/l06.md` 与 `COMPATIBILITY.md` 第 17 节。
2. 重新检查 Git 分支、HEAD 和工作树，保护上述 untracked 开发记录与用户文件。
3. 将 `M3.R13.1`–`.3` 和 `M3.L06.1`–`.6` 视为已验收历史，不重复编号迁移、L06 开发、
   四路径运行或状态同步。
4. 等待项目负责人明确启动 `M3.L07.1`。启动后先创建/维护
   `course_development/lessons/l07.md`，完成 L07 教学设计、源内容映射、视觉方案、
   notebook 合同和 `.5`–`.6` 验收门禁；不要直接编写讲义或 notebook。
5. L07 当前公开状态必须保持 `planned`，直至其 `.6` 状态同步通过；不要因为文件存在或
   L06 已完成而提前提升。

持续适用的协作边界：每个子步骤单独等待项目负责人验收；不要自动开始后续步骤；
`docs/handoffs/current.md` 只在项目负责人准备切换 thread 时更新；不创建 commit、不 push、
不发布外部 artifact，除非项目负责人明确要求。不要把静态状态 literal、低 IK residual、
camera frame、训练 loss 或开环动作预测写成闭环任务成功证据。
