# RoboGenesis 101 许可边界

> 状态：M0.5 已由项目负责人验收
>
> 批准日期：2026-08-28（Asia/Shanghai）

本文档定义原创代码、原创课程内容和第三方材料之间的许可边界。它本身不替代许可证全文，也不改变任何第三方材料的原始许可。项目根目录的 `LICENSE` 已在 M1.1 按本方案建立；第三方许可证文件随相应材料迁入时补齐。

## 1. 总体方案

RoboGenesis 101 的原创材料统一采用 MIT License，并把第三方材料作为独立许可区域管理：

| 内容类别 | 采用的许可 | 核心边界 |
|---|---|---|
| 原创课程代码 | MIT License | 包括独立源码、工具、测试和构建配置 |
| 原创讲义与教学内容 | MIT License | 包括讲义、notebook、练习、原创图表和教学媒体 |
| 第三方资产、代码、数据和模型 | 各自原始许可 | 不受项目 MIT License 覆盖，必须单独记录来源和约束 |
| Datawhale 名称、标志及其他商标 | 不由上述许可证授予 | 仅在项目负责人确认品牌使用授权后保留 |

仓库级声明应使用“除另有注明的第三方材料外，项目原创内容采用 MIT License”，避免把 MIT 错误地扩展到第三方资产或商标。

## 2. MIT 代码范围

除非文件中另有声明，以下原创内容采用 MIT License：

- `src/` 下的 Python 包和命令行实现；
- `tests/` 下的测试代码；
- `scripts/` 下的构建、验证、数据准备和开发脚本；
- `.github/workflows/` 下的自动化配置；
- VitePress 配置、主题代码和样式；
- `pyproject.toml`、`package.json` 等用于构建和运行项目的配置；
- notebook 中由本项目原创的代码单元；
- 讲义中的原创示例代码块。

从两个源课程迁入的 19 个 Python 文件，在项目负责人确认其拥有相应授权后，作为 RoboGenesis 101 代码的一部分采用 MIT。迁移记录仍保留在 `MIGRATION.md`，避免丢失原始作者和来源信息。

第三方代码片段不能因为进入上述目录而自动变成 MIT。若后续确实复制第三方实现，必须保留其原许可证并在 `NOTICE.md` 增加文件级记录；无法确认许可的实现只能参考后重写，不能复制。

## 3. MIT 教学内容范围

除非文件中另有声明，以下原创教学内容同样采用 MIT License：

- README、课程首页、章节讲义和练习说明；
- notebook 的 Markdown 单元、题目、解释和教学结构；
- `course.json` 中的课程标题、简介、学习目标和课程结构信息；
- 原创图表、示意图、截图、录屏、动画和其他教学媒体；
- 从已审核 Markdown 或 notebook 生成的 PPTX、PDF 和 HTML 课程版本；
- `MIGRATION.md`、`NOTICE.md`、贡献指南和内容规范等项目文档。

PPTX、PDF 或网页中包含第三方资产时，相关资产仍保留原许可，不能因为出现在 MIT 课程内容中而被重新许可。

## 4. Notebook 和讲义代码块

Notebook 中的原创代码和原创教学内容均采用 MIT，因此不再需要在代码单元与 Markdown 单元之间拆分许可证：

- 原创代码单元采用 MIT；
- 原创 Markdown、题目和叙述采用 MIT；
- 输出图片和嵌入媒体按照其自身来源处理；
- 第三方代码单元保留第三方许可和署名。

每个正式 notebook 的首个 Markdown 单元应包含简短声明：

> Unless otherwise noted, original code, prose, exercises, and course media in
> this notebook are licensed under the MIT License. Third-party material
> retains its original license; see the repository NOTICE.

讲义中的原创代码块和周围的原创解释文字都采用 MIT。较长或可直接运行的实现仍应进入 `src/` 或 `scripts/`，避免只在讲义中维护另一份实现。

## 5. YCB 资产方案

采用 M0.4 后确认的最小内置方案：只迁入当前课程主线实际需要的四个对象。

- `011_banana`
- `014_lemon`
- `018_plum`
- `024_bowl`

实际目录为：

```text
assets/third_party/ycb/
├── README.md
├── LICENSE-CC-BY-NC-4.0.txt
├── SHA256SUMS
└── models/
    ├── 011_banana/
    ├── 014_lemon/
    ├── 018_plum/
    └── 024_bowl/
```

适用规则：

- 四个对象保留 ManiSkill 声明的 CC BY-NC 4.0，不纳入项目 MIT License；
- `README.md` 记录 ManiSkill、YCB、下载地址、归档校验和、对象清单和论文引用；
- `SHA256SUMS` 记录实际内置文件，防止来源或内容发生无记录变化；
- 课程不使用或生成缩放资产，迁入文件保持原样；
- 未来若提议修改几何、材质、纹理或缩放，必须重新进行资产与许可审查；
- 其余六个已审计对象不迁入，只有被具体课程内容使用时才单独审查和增加；
- README 必须提示：MIT 代码可以在替换资产后独立使用，但随附 YCB 资产不得用于 CC BY-NC 4.0 不允许的商业用途。

本方案选择内置最小集合，而不是运行时下载整个 ManiSkill YCB 包，以减少下载失败、上游漂移和学员环境差异。四个对象在 M1.4 按上述许可边界迁入。

## 6. Franka 模型方案

不迁入源课程中缺少模型级 `LICENSE` 的 36.6 MB Franka 目录。课程直接使用经过 M0.6-M0.7 固定和验证的 Genesis 版本所自带的 `xml/franka_emika_panda/panda.xml`。

适用规则：

- `NOTICE.md` 保留 Genesis、MuJoCo Menagerie、Franka 描述和 Apache-2.0 来源；
- 课程代码通过 Genesis 支持的资产解析方式访问模型，不写 site-packages 或开发机绝对路径；
- M0.6–M0.7 已确认固定的 Genesis 版本包含该模型，并验证了场景、IK 和夹爪控制；
- 如果固定版本未包含兼容模型，再提交单独方案，从固定 MuJoCo Menagerie commit 获取模型并附带模型级 Apache-2.0 许可证；
- “Franka”和“Panda”只用于描述来源，不声明任何商标授权或官方背书。

该方案避免在本仓库重复保存模型和遗漏上游许可证，同时让运行时模型版本与 Genesis 版本保持一致。

## 7. Datawhale 模板与品牌材料

现有 `docs/public/datawhale-logo.png`、`docs/public/learning.GIF` 和项目中的 Datawhale 名称属于品牌或第三方材料问题，不由 MIT License 自动解决。README 曾引用但未存储的 Datawhale 公众号二维码已在 M1.10 按项目负责人决定移除。

建议处理方式：

- 项目负责人确认本课程作为 Datawhale 项目使用名称、标志和官方链接的权限；
- 获确认后，在 `NOTICE.md` 记录用途和授权依据，不把商标描述成 CC 或 MIT 内容；
- `docs/public/learning.GIF` 缺少独立来源记录，M1.8 默认用本课程原创视觉替换；
- M1.10 不再保留 README 中来源和许可未确认的远程公众号二维码；
- 未确认前不修改、重新设计或对外发布 Datawhale 品牌素材。

## 8. 源课程媒体

项目负责人已确认两个源课程的代码、讲义和教学内容均为其原创。因此，源课程中的原创截图、GIF、SVG 和演示文稿可在迁入后按 MIT License 发布，但其中显示或嵌入的 YCB、Franka 等第三方材料仍保留原许可。

迁移到 M2-M4 时按以下规则处理：

1. 记录素材来自哪个源课程和 commit；
2. 能稳定复现的仿真截图和动画优先重新生成；
3. 显示 YCB 或 Franka 模型的媒体同时保留相应第三方说明；
4. 若发现并非源课程原创的外部素材，则单独审计，无法确认来源时舍弃；
5. PPTX/PDF 从已审核的 Markdown、notebook 或其他明确源文件重新生成。

源课程中的五个唯一仿真输出，其原创表现部分可按 MIT License 发布，同时继续遵守其中 YCB 和 Franka 模型的第三方条款。

## 9. 数据集、checkpoint 与模型

本方案不向任何数据集、checkpoint 或预训练模型授予项目许可证。M5 发布每项外部 artifact 前必须单独记录：

- 创建者和版本；
- 训练数据及基础模型来源；
- 原始许可证和使用限制；
- 不可变下载地址与 SHA-256；
- 引用方式；
- 是否允许再分发、修改和商用。

本地数据集、训练输出、日志和缓存继续排除在 Git 之外。

## 10. 权利人和署名方式

建议 MIT 文件使用以下版权声明，避免把未来贡献错误地归到单一个人名下：

```text
Copyright (c) 2026 RoboGenesis 101 contributors
```

原创课程内容的推荐署名为：

```text
RoboGenesis 101 contributors；项目负责人：王迅（Xun Wang）
```

对外署名应同时链接项目仓库。只有在 Datawhale 确认项目归属和品牌使用方式后，才把 Datawhale 写成发布组织或品牌方；本方案不把 Datawhale 声明为未经确认的版权人。

贡献指南应说明：提交原创贡献即表示贡献者同意按 MIT License 提供贡献。贡献者不能提交无权再许可的第三方内容；带有独立许可证的贡献必须在提交时说明。

## 11. 仓库中的许可文件

本方案获批后，在迁移受许可内容之前建立以下文件：

```text
LICENSE                 # 标准 MIT 全文及其适用范围
NOTICE.md               # 第三方来源、许可和排除边界
assets/third_party/ycb/LICENSE-CC-BY-NC-4.0.txt
```

`LICENSE` 使用标准 MIT License 全文，并明确其只覆盖项目有权许可的原创材料。README、英文 README 和站点 footer 使用同一段简短说明，并链接到 `LICENSE` 和 `NOTICE.md`。任何目录级许可证优先适用于该目录，文件自身的许可声明又优先于目录级规则。

实施顺序为：

1. M0.5 批准许可边界；
2. M1.1 创建 MIT `LICENSE`，并立即把现有 README 的许可段落同步为“原创内容 MIT、第三方材料按原许可”，再建立代码骨架；
3. M1.3 在 MIT 边界下迁入已批准代码；
4. M1.4 按已批准方案接入 YCB 与 Genesis 内置 Franka 资产；
5. M1.8-M1.10 在站点与课程结构完善时继续同步 footer、完整 README、notebook 模板和贡献说明。

## 12. M0.5 批准记录

项目负责人已于 2026-08-28 验收 M0.5，并确认：

1. 有权将两个源课程中的原创代码、讲义、notebook 和确认原创的教学媒体以 MIT License 发布；
2. 接受以 “RoboGenesis 101 contributors” 作为 MIT 版权声明，并按第 10 节方式署名原创课程内容；
3. 接受 notebook 中的原创代码与原创教学内容统一使用 MIT；
4. 接受仅内置四个 YCB 对象并保留 CC BY-NC 4.0；
5. 接受优先使用固定 Genesis 版本内置的 Franka 模型，而不复制当前不完整的源目录；
6. 将确认 Datawhale 品牌使用权限，并在无法确认时替换或移除相关素材；
7. 将在 M2-M4 迁移媒体时记录来源，并对其中新发现的外部素材单独审计；
8. 同意任何第三方材料均不被项目 MIT License 重新许可。

后续若发现新的第三方材料或权利边界变化，必须重新审计并更新 `NOTICE.md`，不得自动纳入项目 MIT License。
