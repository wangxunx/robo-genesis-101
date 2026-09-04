# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-06（Asia/Shanghai）。

本文件只记录新 thread 最容易遗漏的当前状态、未决决定和恢复顺序。课程范围、逐步验收
规则和当前状态摘要以本地 `robo_genesis_101_course_development.plan.md` 为准；逐讲的
设计、交付与验收历史位于本地 `course_development/lessons/`；运行环境和可公开引用的
实测证据以 `COMPATIBILITY.md` 为准；迁移来源与历史取舍以 `MIGRATION.md` 为准。

## 1. 当前 Git 快照

- 当前分支：`M3.L05`。
- 当前 HEAD：`06e39a2`，提交说明为 `verified refactored l05 notebooks`。该提交已包含
  M3.L05R.6 的双语 L05 状态说明、`COMPATIBILITY.md` 新版第 14 节和本 handoff 的
  重构后快照。
- 当前 worktree 的 tracked 修改只有本 handoff 的验收日期与门禁同步；本地开发计划和
  L05 档案仍按约定保持 untracked。
- M3.L05R.1–M3.L05R.6 已由项目负责人逐步验收；L05 精简重做轮次正式完成并保持
  `cpu-verified`。当前只等待项目负责人另行明确开始 `M3.L06.1`。
- 本地开发计划和 `course_development/` 是有意保持 untracked 的开发记录，不应加入发布
  结构。既有未跟踪内容 `.vscode/`、`0001-4-cards-failure.patch`、`MIGRATION.md` 和
  `genesis_公开课体系规划_2ba5d82e.plan.md` 也必须保留。
- 本轮没有创建 commit、push 或发布外部 artifact。

新 thread 开始工作前仍须重新运行 `git status --short` 和 `git log -1 --oneline`，不要
假设上述快照之后没有变化。

## 2. 里程碑、验收握手与公开状态

- 已验收：M0、M1、M2、M3.1、M3.L03.1–M3.L03.6、M3.L04.1–M3.L04.6，以及
  L05 精简重做的 M3.L05R.1–M3.L05R.6。
- 当前门禁：等待项目负责人另行明确开始 M3.L06.1；不得因 L05 已完成而自动开始 L06。

当前公开 manifest 状态为：L01–L05 共 5 讲 `cpu-verified`，L11 为 `gpu-verified`，
L06–L10 和 L12 共 6 讲 `planned`。L05 继续使用 `cpu-verified`，因为已验收的新版
EN/ZH CPU clean-kernel 满足最低 `cpu-ok` 合同；参考 R9700 + EGL 是附加兼容性证据，
不把 GPU 变成学习门槛，也不表示 L05 已经 `published`。

## 3. 当前 L05 精简实现

项目负责人认定旧版 L05 的 23 个 cell、14 个 code cell 和 1470 行 code source 对基础
学习者过于复杂，因此要求参考原课程一 Module 04，围绕 FK、IK、end-effector pose 和
轻量 camera 重新开发。新的双语 notebook 各有 15 个 cell，其中 8 个 Markdown、7 个
code cell、330 行 code source；EN/ZH cell-type sequence 和 code-cell ID/source 完全一致。

当前实验只有一条主线：

```text
current q → FK → current pose
target pose → IK + residual check → q goal
q goal → L04 position control → measured pose
scene → one fixed camera → RGB + depth
```

保留内容：

- 一个 Scene、Plane、Franka 和 reachable target marker；
- world-frame hand position 与 Genesis `wxyz` quaternion；
- reachable IK、6D residual acceptance 和 finite/shape 检查；
- 接受 q 后的 FK pose prediction；
- 180-step L04 joint-position control 和 measured pose-error 曲线；
- 一个可选 fixed camera 的 RGB/depth shape、dtype 和 finite 检查；
- `[2,0,2]` 不可达负例，明确 residual rejection 和 `command sent: no`；
- 简短 final checks 和 `L05 CHECK: PASSED`。

已移出：Jacobian/SVD/singularity、DLS、wrist camera、K/intrinsics/extrinsics、attached
camera lifecycle、depth clipping analysis、diagnostic override、B=4 batched IK/control、
`envs_idx` selective update，以及与这些主题绑定的大型回归代码和表格。

Genesis 1.3.3 的 `forward_kinematics()` 仍依赖第一次 IK 初始化内部 scratch，因此讲义先
解释 FK，notebook 第一次实际 FK 调用则位于 IK 之后。该限制只保留为透明的调用顺序说明，
没有继续扩张为 cache/state regression 教学。

## 4. 新版运行证据

M3.L05R.5 已验收的四条 clean-kernel 路径为：

| 路径 | 请求 → 实际 backend | camera | 结果 |
|---|---|---|---|
| EN / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L05 CHECK: PASSED` |
| ZH / CPU | `cpu` → `cpu` | 明确 `SKIP` | `L05 CHECK: PASSED` |
| EN / CPU + EGL | `cpu` → `cpu` | 一个 fixed RGB/depth | `L05 CHECK: PASSED` |
| EN / AMD + EGL | `auto` → `amdgpu` | 一个 fixed RGB/depth | `L05 CHECK: PASSED` |

关键数值：

- CPU reachable IK position/rotation residual 约为 `0.000110217 m` /
  `0.000002741 rad`；AMD 约为 `0.000110271 m` / `0.000002465 rad`；
- FK prediction error 与对应 solver residual 一致；
- 180-step 最终 measured position/orientation error 约为 `0.005211 m` /
  `0.011822 rad`，低于 `0.02 m` / `0.05 rad` 阈值；
- 不可达目标在 CPU 上的 residual 约为 `2.062891 m` / `1.088002 rad`，AMD 约为
  `2.055613 m` / `1.120848 rad`，两种路径都拒绝且未执行；
- CPU+EGL 与 AMD+EGL 的 RGB 均为 `(360,640,3)` `uint8`，depth 均为
  `(360,640)` `float32`，全部 finite。

人工检查确认 CPU/AMD RGB 中 Franka 与棋盘地面清晰，depth silhouette 与 RGB 位置
对应，没有空白、全黑或损坏画面。Orientation error 有短暂上升，但最终低于阈值；不得
把结果描述成单调收敛。相机帧只证明场景可观察，不证明 IK residual、tracking quality、
路径安全或抓取成功。

完整命令、环境、warning 和限制已更新到 `COMPATIBILITY.md` 第 14 节。旧版复杂
notebook 的运行结果只作为历史保留在本地 L05 开发档案，不再出现在当前兼容性结论中。

## 5. M3.L05R.6 状态同步范围与门禁

本轮确认以下公开来源一致：

- `course.json`：L05 为 `cpu-ok` / `cpu-verified`；
- 双语 README 与双语首页：L01–L05 为 `cpu-verified`，其余计数正确；
- 双语 L05 frontmatter 与 notebook metadata：`cpu-verified`；
- 双语讲义正文状态说明：重构内容已通过 CPU 和参考 AMD 路径，但未 `published`；
- `tests/test_course_manifest.py`：前 5 讲期望 `cpu-verified`；
- `COMPATIBILITY.md`：只引用新版 15-cell notebook 和 M3.L05R.5 证据。

M3.L05R.6 交付前完成的门禁结果：

- `.venv/bin/python -m pytest tests/test_course_manifest.py`：9 passed；
- `.venv/bin/python -m robo_genesis.course_validation`：通过，12 lessons、
  26 localized Markdown files、24 notebooks、31 Python files；
- `.venv/bin/python -m pytest`：35 passed；
- `.venv/bin/python -m compileall -q src scripts tests`：通过；
- `npm ci`：成功；仍有既有 13 项 advisory（6 low、1 moderate、6 high）；
- `npm run docs:build` 和 `EDGEONE=1 npm run docs:build`：通过。

## 6. 下一步恢复顺序

1. 读取根目录 `AGENTS.md`、本文件、主开发计划和 `course_development/lessons/l05.md`
   的 M3.L05R.6 记录。
2. 重新检查 Git 状态，保护未跟踪内容和用户后续修改。
3. 将 M3.L05R.1–M3.L05R.6 视为已验收历史，不重复开发或回退精简教学边界。
4. 只有收到项目负责人另行开始 L06 的明确指令后，才进入 `M3.L06.1`。

持续适用的边界：不创建 commit、不 push、不发布外部 artifact，除非项目负责人明确要求；
不把静态状态 literal 当作运行证据；不把 R9700 结果外推到其他 AMD/ROCm、NVIDIA、
Apple Silicon 或 Windows；不把低 IK residual 或 camera frame 描述为抓取成功。
