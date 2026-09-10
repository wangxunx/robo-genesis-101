# RoboGenesis 101 当前工作交接

最后核对日期：2026-09-10（Asia/Shanghai）。

本文件只记录新 thread 最容易遗漏的当前状态、近期运行结论、跨课程 review 偏好和恢复
顺序。通用协作规则以根目录 `AGENTS.md` 为准；课程总状态与步骤门禁以本地
`robo_genesis_101_course_development.plan.md` 为准；逐讲设计与验收历史位于本地
`course_development/lessons/`；运行环境和实测证据以 `COMPATIBILITY.md` 为准。

## 1. 一句话恢复状态

- L03–L09 的逐讲开发步骤均已完成并通过项目负责人验收。
- L09 已于 2026-09-10 完成 `M3.L09.1`–`M3.L09.6` 全部验收，公开状态为
  `gpu-verified`。
- L10 尚未启动；当前唯一下一步是等待项目负责人明确说“开始 `M3.L10.1`”。不要因分支名
  为 `M3.L10`、L10 骨架已存在或前置课程完成而自动开始。
- L10 启动后必须先做 `.1` 教学设计、来源取舍、视觉方案、notebook 合同和 `.5`–`.6`
  验收门禁，不得直接写讲义或 notebook，也不得提前改变 L10 的 `planned` 状态。

## 2. 当前 Git 快照与工作树保护

更新本文件前的快照：

- 当前分支：`M3.L10`；
- HEAD：`7ef666d update workflow validate yml`；
- `origin/main`、`origin/HEAD` 和本地 `main` 同样指向 `7ef666d`；
- 近期相关提交：`767173b update COMPATIBILITY doc after l09`、
  `0ad831e verified en/zh notebooks of l09 synthetic data recording`。

分支和 HEAD 可能在新 thread 启动前继续变化，因此首先重新运行：

```sh
git status --short --branch
git log -3 --oneline --decorate
```

本次 handoff 更新后，预期的 tracked 修改只有 `docs/handoffs/current.md`。L09 `.6` 的
2026-09-10 验收结论已经出现在当前 `COMPATIBILITY.md` 中，不应再把它视作待补记录。

下列 untracked 内容在本次工作开始前已经存在，属于本地配置、补丁或开发记录，必须保留，
不得清理、覆盖或误当成本轮新建文件：

- `.vscode/`；
- `0001-4-cards-failure.patch`；
- `0001-rewrite-l09-lectures.patch`；
- `MIGRATION.md`；
- `course_development/`；
- `genesis_公开课体系规划_2ba5d82e.plan.md`；
- `robo_genesis_101_course_development.plan.md`。

根开发计划和 L09 单课档案位于 untracked 路径中，但它们是当前开发状态的重要记录；不要
因为 `git diff` 不显示其变化而忽略或删除。当前 thread 没有执行 commit、push 或发布。

## 3. 当前公开课程状态

`course.json` 仍是课程元数据的唯一结构化来源。当前共 13 讲：

- L01–L07：7 个 `cpu-verified`；
- L08、L09、L12：3 个 `gpu-verified`；
- L10、L11、L13：3 个 `planned`；
- 0 个 `published`。

L09 的 120 分钟时长、`gpu-recommended` 硬件字段、slug 和双语路径均未改变。`.6` 已将
以下来源原子同步为 `gpu-verified`：

- `course.json`；
- 双语 L09 讲义 frontmatter 与课程状态说明；
- 双语 L09 notebook metadata、setup assert 和 final-check manifest contract；
- 双语 README、双语首页和根语言入口；
- manifest 与 L09 notebook 合同测试。

完整逐步记录见 `course_development/lessons/l09.md`；兼容性与运行证据见
`COMPATIBILITY.md` 第 20 节。

## 4. L09 最终教学与实现合同

L09 把 L08 的 scripted banana-to-bowl rollout 转换为小型持久化 LeRobot 数据集，主线是：

```text
同一决策时刻的 observation/action 对齐
→ 按 dataset FPS 对 control callback 采样
→ 整条 attempt 暂存
→ success 后提交 episode，失败则整体丢弃
→ finalize、重新打开并检查数值和双路视频
```

关键实现事实：

- 双语 notebook 为 18 cells / 8 code cells；cell type、code-cell ID/source 完全一致，
  提交版保持 clean output；
- 最终状态同步后的 code SHA-256 为
  `614980d9aeb5a6cd42e88f9caf57293608ae461375665cc22501979afc98ede5`；
- 完整实验固定 `n_envs=1`、100 Hz control、5 FPS dataset、`160×120` world/wrist RGB、
  H.264/PyAV、2 条成功 episode；这些是教学 smoke 配置，不是大规模采数方案；
- `ROBO_GENESIS_RENDER=1` 是正常教学路径，也是完成双相机录制实验的必要条件；`0` 只运行
  sampling/schema 诊断，不创建 scene、camera、recorder、writer 或 dataset，不能算完成
  核心实验；
- `EpisodeRecorder` 保留源码原有 fractional accumulator 与相位。100 个 callback 下，
  5 FPS indices 为 `0,19,39,59,79,99`，30 FPS 以 `0,3,6,10,13,...` 开始；不要为了让
  教学示例更整齐而修改共享源码行为；
- notebook 复用 `src/robo_genesis/` 的 scene、expert、recorder 与 LeRobot integration，
  同时直接展示 sampling、feature schema、success gate、writer lifecycle 和 readback；
- GPU 默认设备下，Hugging Face `Column` 的元素可能成为 GPU tensor。当前读取逻辑使用
  `plain_rows = rows.with_format(None)`，让 Arrow 数据以普通 Python 格式提供给 NumPy；
  这不是对单个 tensor 调用 `.cpu()` 的替代惯例，而是因为对象本身是 `Column` 而非
  `torch.Tensor`。若处理直接 tensor，仍应使用 `.detach().cpu().numpy()`。

## 5. L09 已验收运行证据

正式证据位于 `COMPATIBILITY.md` 第 20.1–20.6 节。`.5` 的四条独立 kernel 均通过：

| 路径 | 总耗时 | 结论 |
| --- | ---: | --- |
| EN CPU / `render=0` | 8.24 秒 | 8/8 cells；诊断通过，明确核心实验未完成 |
| ZH CPU / `render=0` | 8.25 秒 | 8/8 cells；与英文诊断路径一致 |
| EN CPU+EGL / `render=1` | 92.24 秒 | 真实双相机录制/readback，`L09 CHECK: PASSED` |
| EN R9700 AMD+EGL / `render=1` | 163.26 秒 | 实际 `amdgpu`，无 CPU fallback，`L09 CHECK: PASSED` |

两条完整路径均为 2 attempts / 2 successes，episode frames `[42,43]`，合计 85 frames、
2 episodes、1 task。全局 index、episode boundary、frame/timestamp reset、9 维 state/action、
task text、metadata、持久化文件和两路 H.264/PyAV 解码均通过。CPU dataset 为 221917 bytes，
AMD dataset 为 221949 bytes。

人工检查 CPU/AMD 的 2×3 world/wrist montage：start 时 banana 在桌面，middle 位于夹爪
附近，end 位于 bowl 内；同列两视角的 episode/frame/timestamp 一致。timeline 与 arm/finger
曲线正常。EN/ZH SVG 也实际渲染为 `1400×760` RGBA PNG，无裁切。

这些结果只证明当前固定任务可录制和读取，不构成专家成功率、数据多样性、训练充分性、
并行 recorder 吞吐或闭环策略质量证据。临时运行目录位于 `/tmp`，新 thread 不应假设仍然
存在或依赖其中产物。

`.6` 只更新状态 literal 与公开摘要，没有改变录制行为，因此 `.5` 的完整视觉证据继续
适用。最终 English CPU / `render=0` clean-kernel 又以新 code hash 执行 8/8 cells，耗时
8.24 秒，读取 `status=gpu-verified`，没有创建 dataset。

## 6. 项目负责人已明确的写作与实现偏好

后续 L10 及其他课程继续遵循：

- 假设学习者有基础机器学习知识，但刚接触机器人技术与仿真；讲义必须让这类学习者能
  顺畅阅读。
- 学习目标应高层、直观、数量克制，说明“学完能做什么”，不要把 phase accumulator、
  字段所有权、writer lifecycle 或单个断言等工程步骤拆成学习目标。
- 名词、缩写或短语首次出现时先用普通语言建立含义，再使用准确术语；避免指代不清的
  `it`/`its`、过度压缩的短语和需要学习者猜测上下文的表述。
- 清楚不等于冗长。默认学习者已有机器学习基础，不要把每个常识性概念扩写成大段说明；
  在“晦涩”和“啰嗦”之间优先采用一句直白定义加后续正常使用。
- learner-facing 主线只保留理解当前机制和完成实验所需内容。调试约定、维护者流程、未在
  notebook 中体现的旁支功能和没有代码对照的实现细节应删除或移到开发记录。
- 讲义示例和 notebook 应忠实解释当前源码行为。不要为了配合讲义中更整齐的示例而改变
  公共源码；如果发现不一致，先确认 source of truth，再让教学内容对齐实现。
- 共享实现放在 `src/robo_genesis/`，notebook 不维护分叉副本，但仍需把本课关键逻辑展示
  给学习者，不能只作为黑盒调用器。
- 相机图像是课程数据源时，`render=0` 只能是明确受限的诊断路径；不能用数组长度、纯逻辑
  smoke 或合成 writer probe 代替真实渲染、编码、解码和人工图像检查。
- EN/ZH notebook code cells 必须逐字一致；Markdown 自然本地化，不做生硬逐句翻译。

## 7. 已知限制与非阻断 warning

- `uv lock --check` 已解析 235 packages；隔离 `uv sync --extra data --locked --dry-run`
  也成功规划 218 packages。
- 通用 Linux PyPI data-extra 路径会带入约 3 GiB PyTorch/NVIDIA CUDA wheels。此前完整
  隔离下载因等待时间过长主动中止，不能把它写成“完整隔离安装通过”。仓库现有 `.venv`
  中的 LeRobot 0.6.0 真实录制、H.264 编码和 PyAV 读取均已通过。
- 最近 `npm ci` 报告 11 项既有 advisory（4 low、1 moderate、6 high）；没有运行
  `npm audit fix`。
- Genesis Franka tendon approximation、neutral qpos、solver time constant 调整、neutral
  self-collision filtering、Quadrants tuple weak-reference/cache 和第三方 `ast.Str`
  deprecation warning 均已记录；没有导致 L09 的 scene、录制、视频或 readback 失败。
- 其他 AMD/ROCm 组合、NVIDIA、Apple Silicon、Windows、viewer、并行 recorder、大规模
  采数、长时间稳定性、策略训练和闭环成功率仍未由 L09 验证。

## 8. 最近门禁与新 thread 恢复顺序

L09 `.6` 状态同步后的最终门禁：

- `.venv/bin/python -m robo_genesis.course_validation`：13 lessons、32 localized Markdown
  files、26 notebooks、32 Python files；
- `.venv/bin/python -m pytest`：41 passed；
- `.venv/bin/python -m compileall -q src scripts tests`：通过；
- `UV_CACHE_DIR=<tmp> uv lock --check`：235 packages；
- `npm ci`：通过，保留第 7 节 advisory；
- `npm run docs:build` 与 `EDGEONE=1 npm run docs:build`：通过；
- `git diff --check`：通过。

新 thread 建议按以下顺序恢复：

1. 完整读取根目录 `AGENTS.md`。
2. 运行 Git 快照命令，保护第 2 节列出的 tracked/untracked 内容。
3. 完整读取 `robo_genesis_101_course_development.plan.md`，确认当前步骤仍为“未开始 L10”。
4. 读取本文件，再读取 `COMPATIBILITY.md` 第 20 节；需要追溯 L09 决策时读取
   `course_development/lessons/l09.md`。
5. 核对 `course.json`、README 和双语首页的 L09 状态均为 `gpu-verified`。
6. 等待项目负责人明确启动 `M3.L10.1`；未收到该指令前不创建 L10 开发档案、不改 L10
   讲义/notebook，也不执行后续步骤。

持续适用的协作边界：每个子步骤完成后单独等待项目负责人验收，不自动开始下一步；
`docs/handoffs/current.md` 只在项目负责人准备切换 thread 时更新；不创建 commit、不 push、
不发布外部 artifact，除非项目负责人明确要求。
