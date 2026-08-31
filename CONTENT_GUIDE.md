# 课程内容规范 / Course Content Guide

[中文](#中文) · [English](#english)

## 中文

本文档规定 RoboGenesis 101 的讲义、notebook、公共代码和验证证据如何协同。目标不是让所有页面形式完全相同，而是让学习路径、术语、接口和完成状态保持一致。

### 真相源与职责

| 内容 | 真相源 | 职责 |
|---|---|---|
| 讲次顺序、标题、slug、时长、硬件、状态 | [`course.json`](course.json) | 结构化元数据；其他入口必须与之同步 |
| 概念、机制和推理过程 | `docs/{zh,en}/lessons/` | 提供完整教学解释，不依赖幻灯提纲或代码注释替代 |
| 可复用行为 | `src/robo_genesis/` | 场景、数据、训练和评估的实现真相源 |
| 可执行练习 | `notebooks/{zh,en}/` | 把当前讲次概念连接到可观察实验 |
| 项目入口与课程进度 | README、双语首页、sidebar | 准确反映 `course.json`，不独立发明状态 |
| 兼容性与许可 | [`COMPATIBILITY.md`](COMPATIBILITY.md)、[`NOTICE.md`](NOTICE.md) | 记录实际验证的平台和第三方边界 |

如果文件由生成器产生，应修改已明确记录的源文件并重新生成。仓库没有定义生成关系时，不得假设某个文件是生成产物。

### 学习顺序与先修关系

课程必须遵守以下顺序：

1. 环境、场景、实体、物理和仿真生命周期；
2. DOF、关节控制、IK、末端位姿和相机；
3. 抓取场景、脚本化专家、演示数据和数据录制；
4. 数据集、模仿学习、域随机化、策略训练和闭环评估。

一个概念在成为当前任务的必要前提时完整讲解；提前出现时只做简短预告。不能在解释控制和 IK 之前要求完成抓取，也不能在解释数据格式之前进入策略训练。

### 每讲讲义结构

完成态讲义通常应包含：

1. 本讲定位与先修知识；
2. 可验证的学习目标；
3. 核心概念和必要推导；
4. 与 `robo_genesis` 接口对应的实现说明；
5. 分步骤实验、预期观察和最小验证路径；
6. 常见失败、诊断方法和平台限制；
7. 练习或扩展任务；
8. 小结以及与下一讲的连接；
9. 外部事实、论文、图片和代码的来源。

结构应服务于当前主题。简单概念不需要为了满足模板而增加空洞章节；复杂实验不能只给命令而不解释机制、输入、输出和失败条件。

### 双语规则

- 英文是机制内容的开发源，中文与英文在同一个变更中同步完成。
- 中文应保留技术含义、证据边界和结构，但使用自然中文表达，不做逐句机械翻译。
- 两种语言的标题层级、示例顺序、练习、警告和引用应一一对应。
- 产品名、API、类名、函数名、路径和命令保持原样。
- 首次出现的重要术语给出中英文对应；后续使用同一译法。

推荐术语：

| English | 中文 |
|---|---|
| scene / entity | 场景 / 实体 |
| degree of freedom (DOF) | 自由度（DOF） |
| joint control | 关节控制 |
| inverse kinematics (IK) | 逆运动学（IK） |
| end-effector pose | 末端位姿 |
| scripted expert | 脚本化专家 |
| demonstration | 演示数据 |
| imitation learning | 模仿学习 |
| domain randomization | 域随机化 |
| rollout | rollout（回合执行） |
| closed-loop evaluation | 闭环评估 |

### 讲义 frontmatter

每个正式讲义必须包含并只包含当前验证器支持的字段：

```yaml
---
lesson: L01
slug: introduction-and-environment-diagnostics
locale: zh
title: "导论、运行平台与环境诊断"
duration_minutes: 60
hardware: cpu-ok
status: planned
---
```

除 `locale` 和本地化 `title` 外，双语字段必须相同；所有值必须与 `course.json` 对应讲次一致。需要扩展 schema 时，应先更新 manifest 读取器、自动门禁和双语模板。

### Notebook 规范

- notebook 必须使用 nbformat 4，并提供合法且唯一的 cell ID。
- EN/ZH notebook 的 cell 类型顺序必须一致，所有 code cell 的 ID 和源码必须完全相同。
- 本地化内容只放在 Markdown cell；不要维护两套行为不同的代码。
- 从干净 kernel 自上而下运行，不依赖隐藏状态或手工执行顺序。
- 提交前清除 `execution_count` 和所有输出；不要提交 checkpoint、缓存或大型生成文件。
- `metadata.robo_genesis` 的 lesson、slug、locale、duration、hardware 和 status 必须与 `course.json` 一致。
- notebook 应展示本讲关键逻辑，同时复用 `src/robo_genesis/` 中已经稳定的公共实现。
- 长时间或高硬件要求的实验必须提供最小验证路径，并明确完整实验是否实际运行。

### Python 与命令规范

- 使用可安装的 `robo_genesis` 包和包内导入。
- 不使用 `sys.path` 注入、开发机绝对路径、父目录逃逸、相邻仓库或 Git URL 依赖。
- 资产、数据集和输出位置通过 `robo_genesis.paths` 或正式 CLI 参数解析。
- 命令、默认值、输出路径和版本说明必须与当前实现一致。
- 公共行为变化要有纯逻辑测试；课程命令变化要同步讲义和 notebook。
- notebook 不应只是黑盒包装器，关键机制仍需在教学上下文中可见。

### 状态与验证证据

| 状态 | 最低含义 |
|---|---|
| `planned` | 已确定位置和元数据，可以只有明确标注的结构骨架 |
| `draft` | 双语内容和实验路径已形成，但尚未完成正式 review |
| `reviewed` | 概念、结构、术语、引用和接口已经 review，不能含未解释的占位内容 |
| `cpu-verified` | 达到 `reviewed`，并在声明的 CPU 路径上完成相应 clean-run 验证 |
| `gpu-verified` | 达到 `reviewed`，并在记录的 GPU/软件环境中完成相应验证 |
| `published` | 双语讲义、notebook、代码、链接、许可和要求的运行证据全部满足发布标准 |

状态不是简单的线性进度百分比。某讲根据硬件要求可以从 `reviewed` 进入 `cpu-verified` 或 `gpu-verified`；只有发布条件全部满足后才能标记 `published`。

每次运行证据至少记录命令、环境、输入规模、seed（适用时）、关键观察和未运行项。训练 loss、单次开环动作或 checkpoint 可加载不能代替闭环任务成功率。

### 图片、数据和引用

- 图片应有描述性替代文本；截图和图表要说明来源、生成方式和必要上下文。
- 外部事实、论文结论、图片、代码、数据集和模型必须引用可靠来源。
- 第三方材料进入仓库前必须确认许可证允许预期使用，并更新 `NOTICE.md`。
- 原创代码和课程内容使用 MIT；YCB 等第三方资产保留自身许可证。
- 数据集、checkpoint、训练日志和构建产物默认不进入 Git。
- 不得编造成功率、显存占用、训练曲线、终端输出或引用。

### 完成检查清单

提交一讲进入验收前，确认：

- EN/ZH 讲义和 notebook 同步；
- frontmatter、notebook metadata、README、首页和 `course.json` 一致；
- 所有链接和图片可解析，外部材料有来源与许可记录；
- notebook 从干净 kernel 按顺序运行，输出已清除；
- 相关单元测试、smoke、文档构建和自动门禁已运行；
- 长训练、GPU 或外部下载未运行时已明确披露；
- 状态只提升到已有证据能够支持的级别。

## English

This guide defines how RoboGenesis 101 lectures, notebooks, shared code, and verification evidence work together. The goal is not to force every page into an identical template, but to keep the learning path, terminology, interfaces, and completion status aligned.

### Sources of truth and responsibilities

| Content | Source of truth | Responsibility |
|---|---|---|
| Lesson order, titles, slugs, duration, hardware, and status | [`course.json`](course.json) | Structured metadata that every public entry point must follow |
| Concepts, mechanisms, and reasoning | `docs/{zh,en}/lessons/` | Complete instruction; slide outlines and code comments are not substitutes |
| Reusable behavior | `src/robo_genesis/` | Implementation source of truth for scenes, data, training, and evaluation |
| Executable practice | `notebooks/{zh,en}/` | Connect lesson concepts to observable experiments |
| Project entry points and course progress | READMEs, bilingual homepages, sidebar | Reflect `course.json` rather than inventing status independently |
| Compatibility and licensing | [`COMPATIBILITY.md`](COMPATIBILITY.md), [`NOTICE.md`](NOTICE.md) | Record tested platforms and third-party boundaries |

If a file is generated, edit its explicitly documented source and regenerate it. Do not assume a generation relationship that the repository does not define.

### Learning order and prerequisites

The course must preserve this progression:

1. environments, scenes, entities, physics, and the simulation lifecycle;
2. DOFs, joint control, IK, end-effector poses, and cameras;
3. grasping scenes, scripted experts, demonstrations, and data recording;
4. datasets, imitation learning, domain randomization, policy training, and closed-loop evaluation.

Explain a concept fully when it first becomes necessary for the current task; give only a short preview if it appears earlier. Do not require grasping before control and IK, or policy training before the data format has been explained.

### Lecture structure

A complete lecture will normally contain:

1. its role in the course and prerequisites;
2. verifiable learning objectives;
3. core concepts and necessary derivations;
4. implementation guidance tied to `robo_genesis` interfaces;
5. a step-by-step experiment, expected observations, and a minimal verification path;
6. common failures, diagnostic methods, and platform limitations;
7. exercises or extension tasks;
8. a summary and connection to the next lesson;
9. sources for external facts, papers, images, and code.

Structure should serve the topic. A simple concept does not need empty sections merely to satisfy a template, while a complex experiment must not provide commands without explaining its mechanism, inputs, outputs, and failure conditions.

### Bilingual rules

- English is the development source for mechanism-level content; Chinese is completed in the same change.
- Chinese must preserve technical meaning, evidence boundaries, and structure while using natural prose rather than sentence-by-sentence mechanical translation.
- Heading levels, example order, exercises, warnings, and citations correspond across both languages.
- Product names, APIs, class and function names, paths, and commands remain unchanged.
- Introduce important terms bilingually on first use, then use one consistent translation.

Preferred terminology:

| English | 中文 |
|---|---|
| scene / entity | 场景 / 实体 |
| degree of freedom (DOF) | 自由度（DOF） |
| joint control | 关节控制 |
| inverse kinematics (IK) | 逆运动学（IK） |
| end-effector pose | 末端位姿 |
| scripted expert | 脚本化专家 |
| demonstration | 演示数据 |
| imitation learning | 模仿学习 |
| domain randomization | 域随机化 |
| rollout | rollout（回合执行） |
| closed-loop evaluation | 闭环评估 |

### Lecture frontmatter

Each lesson lecture must contain only the fields currently supported by the validator:

```yaml
---
lesson: L01
slug: introduction-and-environment-diagnostics
locale: en
title: "Introduction, Runtime Platforms, and Environment Diagnostics"
duration_minutes: 60
hardware: cpu-ok
status: planned
---
```

Except for `locale` and the localized `title`, bilingual fields must be identical, and every value must match the corresponding lesson in `course.json`. Extend the manifest reader, automated gates, and bilingual templates before extending this schema.

### Notebook rules

- Use nbformat 4 with valid, unique cell IDs.
- EN/ZH notebooks have the same cell-type sequence and exactly matching code-cell IDs and source.
- Localize Markdown cells only; do not maintain two behaviorally different implementations.
- Run top to bottom from a clean kernel without hidden state or manual execution order.
- Clear every `execution_count` and output before committing. Do not commit checkpoints, caches, or large generated files.
- The lesson, slug, locale, duration, hardware, and status in `metadata.robo_genesis` match `course.json`.
- Expose the lesson's key logic while reusing stable shared implementations from `src/robo_genesis/`.
- Long-running or hardware-intensive exercises provide a minimal verification path and say whether the full experiment was actually run.

### Python and command rules

- Use the installable `robo_genesis` package and package-relative imports.
- Do not use `sys.path` injection, developer absolute paths, parent-directory escapes, sibling repositories, or Git URL dependencies.
- Resolve assets, datasets, and outputs through `robo_genesis.paths` or explicit CLI arguments.
- Keep commands, defaults, output paths, and version statements consistent with the implementation.
- Add pure-logic tests for shared behavior changes; update lectures and notebooks when course commands change.
- A notebook must not become a black-box wrapper: the mechanism relevant to the lesson remains visible in context.

### Status and verification evidence

| Status | Minimum meaning |
|---|---|
| `planned` | Position and metadata are fixed; an explicitly labelled structural scaffold is allowed |
| `draft` | Bilingual content and experiment path exist but have not completed formal review |
| `reviewed` | Concepts, structure, terminology, citations, and interfaces have been reviewed, with no unexplained placeholders |
| `cpu-verified` | Meets `reviewed` and completes the declared clean-run checks on the CPU path |
| `gpu-verified` | Meets `reviewed` and completes the declared checks in a recorded GPU/software environment |
| `published` | Bilingual lectures, notebooks, code, links, licensing, and required runtime evidence all meet the release standard |

Status is not a simple linear percentage. Depending on its hardware requirement, a lesson may move from `reviewed` to `cpu-verified` or `gpu-verified`; it becomes `published` only after every release condition is satisfied.

Runtime evidence records the command, environment, input size, seed when applicable, key observations, and checks not run. Training loss, one open-loop action, or successful checkpoint loading does not replace closed-loop task success.

### Images, data, and citations

- Images have descriptive alternative text; screenshots and plots identify their source, generation method, and necessary context.
- External facts, paper findings, images, code, datasets, and models cite reliable sources.
- Confirm that a third-party license permits the intended use before adding material, and update `NOTICE.md`.
- Original code and course content use MIT; YCB and other third-party assets retain their own licenses.
- Datasets, checkpoints, training logs, and build artifacts stay out of Git by default.
- Never fabricate success rates, memory use, training curves, terminal output, or citations.

### Completion checklist

Before submitting a lesson for review, confirm that:

- EN/ZH lectures and notebooks are synchronized;
- frontmatter, notebook metadata, READMEs, homepages, and `course.json` agree;
- all links and images resolve, with provenance and license records for external material;
- the notebook runs in order from a clean kernel and committed outputs are cleared;
- relevant unit tests, smoke tests, documentation build, and automated gates were run;
- skipped long training, GPU work, or external downloads are disclosed;
- status advances only as far as the available evidence supports.
