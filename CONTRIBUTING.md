# 贡献指南 / Contribution Guide

[中文](#中文) · [English](#english)

## 中文

感谢你帮助改进 RoboGenesis 101。本项目当前处于 Alpha 阶段：仓库基础设施和公共 Python 代码已经建立，但 12 讲课程内容仍是 `planned` 骨架。提交内容时，请准确描述已经完成和实际验证的部分，不要因为文件存在就提高课程状态。

### 可以贡献什么

- 修正文档错误、失效链接、术语不一致和不准确的技术说明；
- 改进双语讲义、notebook、练习和故障排查内容；
- 修复或测试 `robo_genesis` 中的可复用实现；
- 补充有完整环境、命令和结果记录的平台兼容性证据；
- 报告可复现的问题或提出课程结构建议。

小型拼写和链接修复可以直接提交 Pull Request。课程顺序、公共接口、依赖版本、课程状态、许可边界或第三方材料变更，应先通过 Issue 说明动机、范围和验证方案。

### 开发环境

文档 CI 使用 Node.js 24；建议本地采用相同主版本：

```sh
npm ci
npm run docs:dev
```

轻量 Python 验证环境不安装 Genesis、渲染和训练依赖，只包含 pytest 和纯逻辑测试所需的 numpy：

```sh
UV_PROJECT_ENVIRONMENT=.venv uv sync --only-group dev --locked
uv pip install --python .venv/bin/python --no-deps --editable .
```

需要运行 Genesis、数据处理或训练代码时，使用：

```sh
uv sync --locked --all-extras
```

完整安装会涉及较大的运行时依赖。AMD ROCm 参考环境还需要遵循[兼容性矩阵](COMPATIBILITY.md)中的 wheel 版本和校验和；不要根据未实测平台推断支持状态。

### 修改规则

1. `course.json` 是讲次顺序、标题、slug、时长、硬件和状态的唯一结构化来源。元数据变化必须同步讲义、notebook、首页和 README。
2. 讲义和 notebook 必须在同一个 Pull Request 中同步修改 EN/ZH 版本。英文是机制内容的开发源，中文应自然改写，而不是逐句机械翻译。
3. 双语 notebook 的 cell 类型顺序和 code cell 必须一致；本地化只发生在 Markdown cell。不要提交执行输出、缓存或机器路径。
4. 可复用实现放在 `src/robo_genesis/`。notebook 应展示本讲关键逻辑，但不得通过 `sys.path`、相邻仓库或开发机绝对路径导入代码。
5. 数据集、checkpoint、日志、视频和生成输出不得提交到 Git。需要发布的 artifact 留待专门的版本、许可和校验和流程。
6. 不得虚构运行结果、性能数字、硬件支持或引用。未执行的验证必须明确写出。

完整的课程写作和状态标准见[课程内容规范](CONTENT_GUIDE.md)。第三方材料必须遵守 [NOTICE.md](NOTICE.md) 和 [LICENSE_POLICY.md](LICENSE_POLICY.md)。

### 提交前验证

至少运行：

```sh
.venv/bin/python -m robo_genesis.course_validation
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src scripts tests
npm run docs:build
git diff --check
```

若修改了依赖，还要运行相应的锁文件更新和安装验证。若修改了 notebook 或运行时代码，应增加与风险匹配的单元测试、clean-kernel smoke、CPU/GPU smoke 或最小训练验证。

### Pull Request 说明

请在 PR 中写明：

- 修改目的和范围；
- 新增、修改和删除的文件；
- 实际执行的命令及结果；
- 未执行的验证、原因和风险；
- 需要 reviewer 重点检查的接口、课程内容或许可问题；
- 若更新课程状态，对应的完成证据。

保持每个 PR 聚焦一个可验收目标，不混入无关重构或批量格式化。

### 许可与署名

提交原创贡献即表示你有权提供该内容，并同意按项目 [MIT License](LICENSE) 发布。不要提交无权再许可的文本、代码、图片、数据、模型或其他材料。

确需引入第三方材料时，PR 必须说明来源、作者、精确版本或 revision、原始许可证、是否修改和再分发限制，并同步更新 [NOTICE.md](NOTICE.md)。无法确认许可的材料不能进入仓库。

## English

Thank you for helping improve RoboGenesis 101. The project is currently in Alpha: repository infrastructure and shared Python code exist, but all 12 lessons remain `planned` scaffolds. Describe completed and actually verified work accurately; the existence of a file does not justify advancing its course status.

### What to contribute

- Fix documentation errors, dead links, inconsistent terminology, or inaccurate technical claims.
- Improve bilingual lectures, notebooks, exercises, and troubleshooting material.
- Fix or test reusable implementations in `robo_genesis`.
- Add platform evidence that includes the environment, commands, and observed results.
- Report reproducible problems or propose improvements to the learning path.

Small spelling and link fixes may go directly to a pull request. Changes to course order, public interfaces, dependency versions, lesson status, licensing boundaries, or third-party material should first be described in an issue with their motivation, scope, and verification plan.

### Development environments

The documentation CI uses Node.js 24; using the same major version locally is recommended:

```sh
npm ci
npm run docs:dev
```

The lightweight Python validation environment omits Genesis, rendering, and training dependencies. It carries only pytest and the numpy that the pure-logic tests need:

```sh
UV_PROJECT_ENVIRONMENT=.venv uv sync --only-group dev --locked
uv pip install --python .venv/bin/python --no-deps --editable .
```

To run Genesis, data processing, or training code, use:

```sh
uv sync --locked --all-extras
```

The full installation includes large runtime dependencies. The AMD ROCm reference environment must also follow the wheel versions and checksums in the [compatibility matrix](COMPATIBILITY.md). Do not infer support for an untested platform.

### Change rules

1. `course.json` is the canonical structured source for lesson order, titles, slugs, duration, hardware, and status. Metadata changes must be reflected in lectures, notebooks, homepages, and READMEs.
2. Update EN/ZH lectures and notebooks in the same pull request. English is the development source for mechanism-level content; Chinese should be a natural adaptation rather than a sentence-by-sentence mechanical translation.
3. Bilingual notebooks must have the same cell-type sequence and code cells. Localization belongs in Markdown cells. Do not commit execution output, caches, or machine-specific paths.
4. Put reusable implementations in `src/robo_genesis/`. A notebook should expose the key logic for its lesson, but it must not import through `sys.path`, a sibling repository, or a developer-machine absolute path.
5. Do not commit datasets, checkpoints, logs, videos, or generated outputs. Publishable artifacts require a separate version, license, and checksum process.
6. Do not fabricate runtime results, performance numbers, hardware support, or citations. State explicitly which checks were not run.

See the [course content guide](CONTENT_GUIDE.md) for the complete writing and status rules. Third-party material must comply with [NOTICE.md](NOTICE.md) and [LICENSE_POLICY.md](LICENSE_POLICY.md).

### Checks before a pull request

Run at least:

```sh
.venv/bin/python -m robo_genesis.course_validation
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src scripts tests
npm run docs:build
git diff --check
```

Dependency changes also require the corresponding lockfile update and installation check. Notebook or runtime-code changes need risk-appropriate unit tests, clean-kernel smoke tests, CPU/GPU smoke tests, or minimal training checks.

### Pull request description

Include:

- the purpose and scope of the change;
- files added, modified, and removed;
- commands actually run and their results;
- checks not run, with reasons and risks;
- interfaces, course content, or licensing decisions that need focused review;
- completion evidence for any lesson-status change.

Keep each pull request focused on one reviewable goal. Avoid unrelated refactors or bulk formatting.

### License and attribution

By submitting an original contribution, you confirm that you have the right to provide it and agree to release it under the project [MIT License](LICENSE). Do not submit text, code, images, data, models, or other material that you cannot relicense.

If third-party material is necessary, the pull request must identify its source, author, exact version or revision, original license, modifications, and redistribution restrictions, and must update [NOTICE.md](NOTICE.md). Material with an unconfirmed license cannot enter the repository.
