# AGENTS.md

This file guides Codex when working in this repository and applies to the entire repository. If a subdirectory contains a more specific `AGENTS.md`, follow the file with the narrower scope. Explicit instructions in the current user request always take precedence.

## Repository Purpose

This project is a Datawhale open-source course on building robot learning workflows with Genesis. It is intended for learners with basic Python experience who want a practical introduction to robot simulation, manipulation, and policy learning.

The course guides learners from simulation fundamentals through robot control and grasping, demonstration data generation, dataset construction, policy training, and closed-loop evaluation. Its goal is to connect conceptual explanations with reproducible hands-on work so that learners can understand, run, diagnose, and extend an end-to-end robot learning pipeline.

## Canonical Learning Path

The course follows a progressive path:

1. Genesis environment setup, scenes, physics, robot control, inverse kinematics, and cameras.
2. Grasping task scenes, demonstration acquisition, and data recording.
3. Dataset understanding, imitation learning, domain randomization, policy training, and closed-loop evaluation.

Keep prerequisites truthful. Do not jump into grasping before introducing control and inverse kinematics, or into policy training before explaining the data format. Do not treat training loss or open-loop playback as a substitute for closed-loop task performance.

Lectures and hands-on work form one learning path, not independent tracks. Readers should understand the mechanism needed for the current task before encountering alternatives and extensions.

## Repository Layout

- `docs/` — VitePress documentation source and course materials.
- `docs/.vitepress/config.mts` — site title, navigation, sidebar, links, and deployment base.
- `docs/public/` — static assets published as-is by VitePress.
- `package.json` / `package-lock.json` — documentation dependencies and commands.
- `.github/workflows/deploy.yml` — GitHub Pages build and deployment workflow.

When notebooks, Python source, generation scripts, or multilingual directories are added, document their responsibilities here. Do not assume that directories or commands mentioned only in the course plan are available.

## Editing Invariants

- Read the target section and its surrounding context before editing; match the established depth, terminology, and tone.
- Mirror structural and prose changes across EN/ZH unless told otherwise.
- Distinguish template placeholders, planned work, and completed content. Do not invent completion status, contributors, links, or experimental results.
- When pages are added, removed, renamed, or reordered, update `docs/.vitepress/config.mts` and all affected links in the same change.
- The README, homepage, course outline, and sidebar must describe the same course order and completion status.
- Explain a concept when it first becomes a required prerequisite; if it appears earlier, give only a brief preview.
- Commands, APIs, versions, hardware requirements, and outputs must agree with the repository implementation or reliable sources.
- Do not fabricate performance numbers, memory usage, training curves, success rates, terminal output, or citations.
- Attribute external text, images, datasets, and models, and confirm that their licenses permit the intended use.
- Use Mermaid only when prose cannot explain a relationship or process clearly; do not add diagrams for simple steps.
- Do not leave template instructions, empty links, or unexplained TODOs in content marked complete.

## Lectures, Notebooks, and Code

- Lectures provide the complete conceptual explanation; slide outlines and code comments are not substitutes for lecture content.
- Notebooks provide executable practice and must use the same terminology, interfaces, and expected results as the lectures.
- Put reusable implementations in clearly defined source modules. Notebooks must still expose the key logic for the lesson instead of acting only as black-box wrappers.
- If a file is generated, edit its source of truth and run the generator. Do not assume a generation relationship unless the repository defines one.
- Notebooks should run top to bottom from a clean kernel. Do not commit large outputs, caches, or machine-specific paths that do not help learners.
- Long-running or hardware-intensive exercises should provide a minimal verification path. Clearly disclose when the full experiment was not run.
- Datasets, checkpoints, training logs, and build artifacts stay out of Git unless repository policy explicitly requires them.

## Datawhale Requirements

- The README should state the project status, course overview, target audience, online reading link, real course progress, contributors, and contribution process.
- Contributor information must be accurate and identify the project lead. Remove example names inherited from the template.
- Update course status only from actual content and verification results; an empty directory or scaffold page is not complete.
- Use only confirmed information for the repository name, Pages URL, Datawhale brand assets, and license.
- Changes to licensing, contributor attribution, or brand content require confirmation from the project lead.

## Working Practices

- Run `git status --short` before starting and preserve existing changes made by the user or other contributors.
- Use `rg` / `rg --files` to locate files and references, and confirm actual call relationships before editing.
- Keep changes focused. Avoid unrelated refactors, bulk formatting, or file cleanup.
- When code behavior changes, update the corresponding course material. When commands in the course material change, verify them against the implementation.
- Do not commit secrets, private URLs, personal absolute paths, caches, debug dumps, or large generated files.
- Do not create commits, push changes, or publish external artifacts unless the user explicitly asks.

## Verification Workflow

Before handing off a change, run at least:

```sh
git diff --check
npm run docs:build
```

Also verify manually that every sidebar target and relative link resolves, the README agrees with the site content, generated files were not edited directly, and unrun experiments are not described as verified.

For notebook or Python changes, add the relevant syntax checks, unit tests, or smoke tests. If GPU work, long training runs, or external downloads cannot be exercised in the current environment, list the unrun checks and the reason in the handoff.

## Commands

Install dependencies with:
```sh
npm ci
```
Start the documentation site with:
```sh
npm run docs:dev
```
Build the documentation with:
```sh
npm run docs:build
```
Use `npm install <package>` only when intentionally adding or updating a dependency. Commit both `package.json` and `package-lock.json` when dependencies change.
