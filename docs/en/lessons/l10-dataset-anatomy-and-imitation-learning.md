---
lesson: L10
slug: dataset-anatomy-and-imitation-learning
locale: en
title: "Dataset Anatomy and Imitation Learning 101"
duration_minutes: 90
hardware: gpu-recommended
status: planned
---

# L10 · Dataset Anatomy and Imitation Learning 101

> **Course status:** L10 remains `planned`; its bilingual content, companion
> notebook, and runtime evidence are not yet complete. The intended core path
> is read-only and CPU-capable: it opens a local dataset produced by L09,
> decodes a few stored frames, and constructs training targets without
> initializing Genesis, allocating a model, or starting training. No example
> dataset is downloaded implicitly. If the local input is missing, record it
> in L09 or point `RG101_L10_DATASET_ROOT` at a compatible copy.

## Where this lesson fits

[L09](./l09-synthetic-data-recording-and-throughput.md) produced persistent,
aligned episodes from the scripted expert. A readable dataset is necessary, but
it is not yet a training argument. Before choosing a policy, we need to know
what the files mean, what one returned sample contains, where episode
boundaries live, and how a future-action target stays inside one episode.

```text
L09: aligned frames + committed episodes + H.264/PyAV persistence
  ↓
L10: dataset anatomy + decoded samples + statistics + episode split
     + behavior-cloning targets + action chunks
  ↓
L11: controlled changes to the data distribution
  ↓
L12: ACT / SmolVLA training and checkpoint reload
  ↓
L13: closed-loop task evaluation
```

L10's output is not a trained model. It is an auditable dataset report, a
non-overlapping set of train/eval episode IDs, one real behavior-cloning sample,
and one future-action chunk with an explicit boundary mask.

Before starting, you should be able to:

- explain why L09 records `(observation_t, action_t)` before advancing the
  simulator;
- distinguish a commanded nine-dimensional joint target from measured robot
  state;
- identify the fixed `world` view and eye-in-hand `wrist` view; and
- locate the exact dataset directory created by L09.

### A focused 90-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–10 min | Input identity and evidence boundary | Resolve one exact local dataset and state what L10 can prove |
| 10–25 min | Metadata, tabular data, and media | Explain the three storage layers and locate logical episode boundaries |
| 25–40 min | Raw rows and decoded samples | Read one multimodal sample and distinguish HWC metadata from CHW tensors |
| 40–52 min | Statistics, units, and normalization | Diagnose channel ranges without treating statistics as proof of coverage |
| 52–64 min | Episode-level train/eval split | Produce disjoint episode IDs and recognize trajectory leakage |
| 64–78 min | Behavior cloning and action chunks | Construct a same-episode `(H, 9)` target with a padding mask |
| 78–86 min | ACT and SmolVLA data contracts | Explain task conditioning and the camera-key adapter |
| 86–90 min | Diagnostics and one-variable exercise | Separate data checks, offline loss, and closed-loop success |

## Learning objectives

By the end of L10, you should be able to:

1. explain how recorded robot demonstrations are organized into a dataset for
   imitation learning;
2. inspect a real dataset and summarize what has been verified—and what remains
   unknown—before training;
3. explain how behavior cloning turns expert demonstrations into learning
   targets while preserving trajectory structure; and
4. distinguish offline action-prediction quality from closed-loop task success.

## Start with the evidence boundary

The word "dataset" can hide several distinct claims. L10 keeps them separate:

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Metadata opens | schema, counts, path templates, task and episode records are readable | Parquet rows or videos are present and decodable |
| Numeric rows open | state, action, timestamps, and indices can be read | the camera streams match those rows |
| Two videos decode | selected `world` and `wrist` frames are visible | every frame is correct or the views are sufficient for learning |
| Statistics are finite | the stored aggregates can support diagnostics and preprocessing | broad coverage, absence of bias, or generalization |
| Train/eval IDs are disjoint | the split does not share whole episodes | enough data for stable model selection |
| One action chunk is valid | the reader respects its shape and episode boundary | a policy can learn or execute the chunk successfully |

The normal path therefore checks metadata before paying video-decoding cost,
then samples visual evidence instead of decoding the whole dataset merely to
plot numeric features.

## A robot dataset is not a bag of independent images

An image classifier often treats examples as approximately interchangeable.
Here, neighboring rows belong to an ordered physical rollout:

```text
episode e:
  (observation_0, action_0),
  (observation_1, action_1),
  ...,
  (observation_T-1, action_T-1)
```

Each observation combines measured robot state, two synchronized camera views,
and a task context. The action is the expert command paired with that decision
time. Adjacent frames share scene geometry, object placement, camera content,
and most of their trajectory history. Treating them as independent rows would
lose the structure needed for honest splitting and future-action targets.

## Three layers of one LeRobot dataset

The on-disk dataset is easiest to reason about as three related layers:

| Layer | Typical contents | Question it answers |
|---|---|---|
| Metadata | `info.json`, `stats.json`, task rows, episode rows, path templates | What is this dataset, which fields exist, and where are its episodes? |
| Tabular data | Parquet columns for state, action, timestamps, and indices | What numerical values belong to each decision time? |
| Media | MP4 files for `world` and `wrist` | What did each camera see at that time? |

An abbreviated layout is:

```text
<dataset-root>/
├── meta/
│   ├── info.json
│   ├── stats.json
│   ├── tasks.parquet
│   └── episodes/.../*.parquet
├── data/.../*.parquet
└── videos/
    ├── observation.images.world/.../*.mp4
    └── observation.images.wrist/.../*.mp4
```

The ellipses matter. LeRobot may shard many logical episodes into storage
chunks. A Parquet or MP4 **file chunk is a storage unit**, while an **episode is
a task trajectory with index and timestamp boundaries**. Never infer episode
identity from filenames alone; use episode metadata and the row's
`episode_index`.

`LeRobotDatasetMetadata` can inspect the first layer without decoding video.
`LeRobotDataset` later joins a tabular row, the task lookup, and requested video
timestamps into a sample.

![Metadata, Parquet rows, and the two video streams join in the LeRobot reader to form a decoded behavior-cloning sample; a separate policy adapter then performs model-specific renaming, normalization, and batching.](/diagrams/l10-dataset-to-sample.svg)

*Course-created diagram. It separates persistent storage, the public decoded
sample, and model-specific preprocessing rather than treating them as one
representation.*

## Identity and schema come before values

### Resolve one exact local root

The logical repository ID and local filesystem root are different pieces of
identity. `local/l09_banana_demo` can describe the dataset while
`DATASETS_DIR / "l09_banana_demo"` selects a concrete local copy.

The companion notebook resolves its input in this order:

1. `RG101_L10_DATASET_ROOT`, when explicitly set;
2. otherwise `DATASETS_DIR / "l09_banana_demo"`;
3. no recursive search for another dataset; and
4. no implicit Hub download or fabricated fallback dataset.

It checks `meta/info.json` before constructing the LeRobot reader because the
library itself may try to fetch missing local content. Failing early makes a
mistyped path distinguishable from an unavailable network artifact.

After that explicit preflight, metadata-only inspection is small and direct:

```python
from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata

metadata = LeRobotDatasetMetadata(repo_id, root=dataset_root)
print(metadata.total_episodes, metadata.total_frames, metadata.fps)
print(metadata.features)
```

The first report should include the resolved root, logical repo ID,
`codebase_version`, FPS, episode/frame/task counts, and feature keys. A result
without this identity is hard to reproduce and easy to attribute to the wrong
dataset.

### Four user features, five automatic fields, and task lookup

L09 declared four user features:

| Key | Stored schema | Course meaning |
|---|---|---|
| `observation.state` | `float32`, `(9,)` | measured positions for seven arm and two finger joints |
| `action` | `float32`, `(9,)` | commanded joint-position targets in the same name order |
| `observation.images.world` | video, `(H, W, 3)` | fixed global view |
| `observation.images.wrist` | video, `(H, W, 3)` | moving eye-in-hand view |

LeRobot owns five bookkeeping fields:

| Key | Meaning |
|---|---|
| `timestamp` | logical time within the episode |
| `frame_index` | zero-based position within that episode |
| `episode_index` | logical episode identity |
| `index` | global row identity across the dataset |
| `task_index` | integer reference into the task table |

The writer receives task text alongside each frame, but the tabular row stores
`task_index`. On read, LeRobot looks up that integer in `meta/tasks.parquet` and
adds a Python `task` string to the sample. `task` is therefore part of the
learner-visible sample without being a fifth user-declared tensor feature.

For this course, state and action names must match the shared
`robo_genesis.record_dataset.JOINT_NAMES` order. Shape `(9,)` alone is not
enough: swapping two joints produces a shape-correct but semantically wrong
training target.

## Raw row, decoded sample, and policy input are different

The same camera observation has at least three useful representations:

| Boundary | Example representation | Intended use |
|---|---|---|
| Metadata | video shape `(120, 160, 3)` in HWC order | describe stored frame geometry |
| Decoded sample | `torch.float32` tensor `(3, 120, 160)` in CHW order | inspect or pass through the data pipeline |
| Policy adapter | renamed/resized/normalized/batched tensor | satisfy one policy's internal contract |

HWC and CHW are not contradictory shapes; they describe different layers.
For display, a decoded CHW tensor can be moved to CPU and transposed back to
HWC. That display conversion is not a substitute for the policy's saved
preprocessor.

The distinction also determines how to read efficiently:

- use the Parquet-backed table for whole-episode state/action curves;
- use `ds[i]` only for the samples whose video frames you need;
- use `with_format(None)` before constructing NumPy arrays from Hugging Face
  columns; and
- if a returned value is already a tensor, use
  `value.detach().cpu().numpy()` rather than assuming it lives on the CPU.

Calling `ds[i]` across every frame just to collect state vectors would also
decode both videos at every index. The result may be numerically correct, but
it hides unnecessary work and confuses tabular access with multimodal sample
assembly.

Use the full reader only when the task lookup or images are required:

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset(
    repo_id,
    root=dataset_root,
    episodes=[0],
    video_backend="pyav",
)
sample = dataset[0]  # joins the row, task text, and requested camera frames
```

### Read both views at matched moments

The camera names encode physical roles:

- `world` is fixed, so it preserves global robot–object–bowl layout;
- `wrist` moves with the hand, so it provides local evidence near approach,
  grasp, lift, and release.

The lab decodes start, middle, and end samples from one episode and presents a
2×3 montage. Each column must use the same episode, frame, and timestamp for
both cameras. This checks synchronization and view identity better than one
undated screenshot.

Visible progress across the montage proves that those stored frames can be
read and interpreted. It does not prove that a policy will attend to the right
view, that either camera covers every failure mode, or that the episode is
sufficient training data.

::: warning Read the actual codec and backend metadata
The verified L09 dataset uses H.264 video and is reopened through PyAV. Do not
copy an older slide's AV1 claim or confuse a codec with the decoder backend.
Inspect the current dataset, then pass `video_backend="pyav"` on this course's
explicit read path.
:::

## Statistics connect physical units to model coordinates

`meta/stats.json` stores per-feature aggregates. For each state/action channel,
the current dataset format can expose `min`, `max`, `mean`, `std`, `count`, and
quantiles `q01`, `q10`, `q50`, `q90`, and `q99`.

The shapes are aggregation shapes, not sample shapes:

| Feature | Sample shape | Typical statistics shape | Interpretation |
|---|---:|---:|---|
| state or action | `(9,)` | `(9,)` | one value per joint channel |
| RGB image | `(3,H,W)` after decode | `(3,1,1)` | per-channel value that can broadcast spatially |
| `count` | not a feature value | aggregate sample count | how much data entered the aggregate |

The first seven state/action channels are revolute arm joints measured in
radians. The last two are prismatic finger joints measured in metres. Plotting
all nine on one unlabeled axis can make a physically important finger change
look negligible or imply that incomparable values share a unit. The lab keeps
arm and finger panels separate.

### Use statistics for diagnosis before training

Statistics can reveal questions worth investigating:

- non-finite values indicate a corrupt numerical path;
- an implausible minimum or maximum suggests a unit, order, or recording error;
- near-zero standard deviation can reveal a stationary channel or inadequate
  task coverage;
- a large gap between an extreme value and `q01`/`q99` suggests an outlier; and
- counts that disagree with the intended dataset scope indicate that the
  aggregate may describe different data than expected.

They do not prove diversity, lack of bias, task relevance, or generalization.
A perfectly finite dataset can contain two nearly identical trajectories.

### Normalization is a reversible interface

Different units create different numerical scales. A common teaching example
is per-channel standardization:

```text
x_norm = (x - mean) / max(std, epsilon)
x      = x_norm * std + mean
```

The forward transform keeps arbitrary physical units from silently setting
the relative scale seen by the optimizer. The inverse transform is equally
important: a predicted action must return to the joint-target coordinates that
the controller expects.

The notebook applies this equation to one arm channel only as a sanity check.
It does **not** implement a second production preprocessor. In LeRobot 0.6.0,
the policy configuration chooses the normalization mode, dataset statistics
are passed into the policy processor, and the output processor unnormalizes an
action. Training, checkpoint reload, and evaluation must preserve that same
processor state.

::: warning Avoid dividing blindly by a tiny standard deviation
A constant or almost constant channel makes a naïve z-score unstable. Inspect
the channel and use the policy's formal processor behavior. An `epsilon` makes
a classroom calculation finite; it does not repair missing motion or bad data.
:::

## Split whole episodes, not neighboring frames

Suppose one trajectory contributes 100 neighboring frames. A random 80/20 row
split can put frame 40 in training and frame 41 in evaluation. Those samples
share almost the same scene, object pose, camera image, and history. A low
held-out loss then partly measures near-duplicate interpolation rather than
performance on an independent trajectory. This is **trajectory leakage**.

L10 therefore splits complete episode IDs. In the pinned LeRobot 0.6.0 factory,
the relevant procedure is:

```text
selected episode IDs
  → group episodes by task
  → within each task, hold out the last ceil(n_task × eval_split) episodes
  → construct train and eval readers with the same temporal-window contract
```

This rule is deterministic, but deterministic does not automatically mean
representative. If collection order follows seed, object pose, lighting, or a
domain-randomization schedule, "last episodes" can select a systematically
different group. Freeze the split rule and the collection conditions before a
formal experiment, and record the exact episode IDs.

The two-episode L09 dataset gives one train and one eval episode for its single
task under a nonzero split such as 20%. That is useful for demonstrating the
mechanics, but it is far too small for a stable model-selection or
generalization claim. A task also needs enough episodes to leave training data
after its holdout.

![Whole episodes are assigned to train or evaluation without sharing frames. Future-action windows stay inside one episode; boundary copies are marked by action_is_pad and excluded from valid targets.](/diagrams/l10-episode-split-and-chunk.svg)

*Course-created diagram. The upper half protects evaluation identity; the
lower half protects temporal targets at the end of an episode.*

## Behavior cloning turns aligned rows into supervision

Behavior cloning (BC) treats expert demonstrations as supervised examples. For
the single-step case:

```text
observation_t = {state_t, world_t, wrist_t, optional task_t}
expert target = action_t
policy_theta(observation_t) ≈ action_t
```

In compact notation:

```text
min_theta  E_(observation_t, action_t)∼D
           [ loss(policy_theta(observation_t), action_t) ]
```

L10 intentionally leaves `loss` abstract. ACT and SmolVLA use different model
structures and objectives, which L12 explains. The shared requirement is the
data meaning: observations and expert targets must be aligned, finite, ordered,
and transformed consistently.

Although optimization looks like supervised learning, deployment is
sequential. The expert generated the states in the dataset, while a deployed
policy generates its own future states through its actions. A small mistake can
move the robot to observations that were rare or absent in the demonstrations,
and later errors can compound. This distribution shift is why training loss or
open-loop prediction cannot replace closed-loop evaluation.

### Offline and closed-loop evaluation measure different things

Offline evaluation compares policy actions against held-out expert actions and
reports metrics such as behavior-cloning action loss. It does not execute the
predicted actions in the simulator, so the policy cannot affect future
observations or demonstrate whether it can recover from its own mistakes.

Closed-loop evaluation executes the policy step by step in Genesis. Each
predicted action changes the robot state and the next observation, so errors can
accumulate and the policy may encounter states outside the expert
demonstrations. The policy then has an opportunity to react and potentially
recover. The final result is measured using a task-level success criterion,
such as whether the object was placed successfully in the target after release
and settling.

Therefore:

```text
held-out behavior-cloning loss ≠ closed-loop task success
offline evaluation             ≠ closed-loop evaluation
```

A reliable evaluation protocol first splits data by complete episode or
trajectory to prevent train/eval leakage, then uses closed-loop rollouts to
measure actual task performance.

## Extend one target into an action chunk

Many robot policies predict a sequence of future actions at once. For a chunk
size `H`, L10 asks the reader for offsets aligned to dataset FPS:

```python
H = 4
delta_timestamps = {
    "action": [i / fps for i in range(H)],
}
```

At frame `t`, the action value changes from shape `(9,)` to `(H, 9)`:

```text
[action_t, action_t+1, action_t+2, action_t+3]
```

At 5 FPS, four samples represent a nominal four-sample horizon of
`H / fps = 0.8 s`; the final sampled target is offset by
`(H - 1) / fps = 0.6 s` from the current frame. These are related but different
quantities.

### A chunk must stop at its episode boundary

Near the final frame, future indices do not exist. The LeRobot reader clamps
them to the episode boundary so the tensor keeps a fixed shape, and returns
`action_is_pad`:

```text
last-frame action rows: [a_last, a_last, a_last, a_last]
action_is_pad:          [ false,   true,   true,   true]
```

The copied values are padding, not three additional demonstrations. A training
loss must ignore the marked rows. Crossing into the next episode would be
worse: it would teach a physically impossible future that jumps through an
environment reset.

The middle of an episode should produce `(4,9)` with four false mask entries;
the final frame should produce the same shape with only its first row valid.
Those two probes test both the normal and boundary cases.

`chunk_size` defines the training/prediction target length. How many predicted
actions are executed before replanning is `n_action_steps`, a policy and
closed-loop trade-off introduced in L12 rather than decided here.

## One raw dataset, two policy-facing contracts

ACT and SmolVLA consume the same course dataset, but their preprocessors do not
have identical internal contracts:

| Question | ACT path in this course | SmolVLA path in this course |
|---|---|---|
| Raw observations | state, `world`, and `wrist` | state, `world`, `wrist`, and task text |
| Training target | action chunk from the same episode | action chunk from the same episode |
| Raw camera-key handling | new ACT configuration adapts to dataset keys | preset renames keys expected by the pretrained base |
| Rename | none for this from-configuration path | `world → camera1`, `wrist → camera2` |
| L10 responsibility | validate fields, shapes, task availability, chunk, and adapter map | same |
| Deferred to L12 | CVAE, Transformer, KL/reconstruction loss, optimization, checkpoint | VLM/action expert, flow matching, fine-tuning, checkpoint |

The project preset expresses the SmolVLA mapping as:

```json
{
  "observation.images.world": "observation.images.camera1",
  "observation.images.wrist": "observation.images.camera2"
}
```

This is a schema adapter, not a request to rename files on disk. The training
pipeline saves the adapter with the preprocessor, and evaluation continues to
provide meaningful raw keys `world` and `wrist`. Inventing a new mapping only
at evaluation would break the training/checkpoint contract.

Neither a common schema nor an adapter makes all policies interchangeable.
Model-specific resizing, normalization, language tokenization, padding, and
batching remain real and must travel with the checkpoint.

## Companion lab: produce an auditable read report

Reuse the environment that completed L09; it already contains the required
reader stack. The repository's `data` extra declares LeRobot, PyArrow, and the
video dependencies, but installation still follows the platform-specific setup
in the project README and compatibility record. In particular, do not run a
generic PyPI sync over the verified AMD environment because it can replace the
pinned ROCm PyTorch wheels.

The notebook follows eight checks, each with a visible output:

1. **Resolve input:** print the exact local root and repo ID; stop with direct
   recovery instructions if required files are absent.
2. **Audit metadata:** report version, FPS, counts, tasks, feature names, joint
   names, episode bounds, path templates, and actual video information.
3. **Read one episode:** compare a raw numeric row with a decoded sample, then
   decode the start/middle/end `world` and `wrist` montage.
4. **Inspect numbers:** read complete state/action columns without video,
   separate arm radians from finger metres, and compare them with statistics.
5. **Plan the split:** list train/eval episode IDs, task, lengths, and frame
   totals; assert disjointness and full coverage.
6. **Construct `H=4`:** inspect a middle and final action chunk and visualize
   `action_is_pad`.
7. **Compare consumers:** read the project's ACT and SmolVLA preset contracts
   without creating either model.
8. **Summarize evidence:** require every data check to pass while explicitly
   reporting that no training, checkpoint, Genesis rollout, or success rate was
   produced.

The expected L09 input has at least two non-empty episodes, one task, 5 FPS,
nine-dimensional state/action features, and decodable `world` and `wrist`
videos. Actual episode lengths and numerical ranges are observations from your
copy, not constants to copy from this page.

## Diagnose failures by layer

1. **Dataset not found:** print the exact resolved root and check
   `meta/info.json`. Run L09 or set `RG101_L10_DATASET_ROOT`; do not scan random
   directories or silently download another dataset.
2. **Version mismatch:** compare the stored `codebase_version` with the pinned
   LeRobot 0.6.0 reader. Do not edit metadata merely to suppress a compatibility
   error.
3. **Metadata opens but rows fail:** inspect the data path template, episode
   records, and referenced Parquet files. Metadata-only success is not a full
   dataset read.
4. **Rows open but video fails:** check both referenced MP4 paths, codec
   information, and the explicit PyAV backend.
5. **Images look transposed or dark:** distinguish stored HWC from decoded CHW,
   then inspect dtype and value range before transposing or scaling.
6. **A numeric plot is unexpectedly slow:** verify that it reads table columns
   rather than calling `ds[i]` and decoding two videos at every frame.
7. **Statistics look shape-incompatible:** expect vector aggregates `(D,)` and
   RGB aggregates `(C,1,1)`, not the full sample shape.
8. **Eval looks implausibly good:** look for random frame splitting, neighboring
   trajectory leakage, and collection-order correlation before interpreting a
   loss.
9. **The final chunk repeats values:** inspect `action_is_pad`. Boundary copies
   must be masked rather than treated as future expert targets.
10. **SmolVLA cannot find cameras:** compare raw `world`/`wrist` keys with the
    saved or preset `camera1`/`camera2` rename; do not mutate the dataset schema.

## Checkpoints and one-variable exercise

### Concept checkpoints

1. Why can one Parquet or MP4 chunk contain data from more than one episode?
2. Why are HWC in metadata and CHW from `ds[i]` both correct?
3. Why should a whole-episode state/action plot avoid indexing every decoded
   sample?
4. Why should arm and finger curves not share an unlabeled numerical axis?
5. How does a random frame split leak trajectory information?
6. Why is a repeated boundary action invalid as a future target unless its mask
   is respected?
7. Why does this SmolVLA path need a camera-key adapter while the current ACT
   configuration does not?
8. Why do a decodable sample, finite action values, and a low offline loss all
   fall short of closed-loop success?

### One-variable exercise: change only `H`

Keep the dataset root, selected episode, FPS, feature schema, and split fixed.
Evaluate `H = 2`, `4`, and `8`.

Before running, predict for each value:

- the action tensor shape;
- `H / fps`, the nominal number-of-samples horizon;
- `(H - 1) / fps`, the final target offset; and
- which positions are padded when the current row is the episode's last frame.

Then construct each reader window, compare the actual masks with your
prediction, and count only unmasked targets. This exercise changes data-window
semantics; it does not train three policies or predict which horizon will have
the best task success.

## Evidence boundary and connection to L11/L12

Completing L10 can establish that one local dataset has coherent identity,
schema, numerical values, representative decoded frames, statistics, episode
boundaries, split IDs, and action-window behavior. It cannot establish:

- enough demonstrations or domain coverage for learning;
- a benefit from domain randomization;
- finite training loss, convergence, or checkpoint quality;
- open-loop policy accuracy; or
- closed-loop grasp success or sim-to-real transfer.

[L11](./l11-domain-randomization.md) next asks how appearance, object pose,
camera, and dynamics variation change the data distribution without destroying
task meaning. [L12](./l12-act-and-smolvla-policy-training.md) then consumes the
dataset contract here to train ACT and SmolVLA and reload their saved
processors. [L13](./l13-closed-loop-evaluation-and-capstone.md) finally places a
loaded policy back in the control loop.

## Summary

- A LeRobot dataset has metadata, tabular, and media layers; a storage file
  chunk is not an episode.
- Metadata describes stored video as HWC, while a decoded sample normally
  exposes CHW tensors. Policy preprocessing is a third representation.
- `world` and `wrist` provide synchronized global and local evidence; inspect
  matched moments from the actual input dataset.
- Per-channel statistics support diagnostics and reversible normalization, but
  do not prove coverage or generalization.
- Split complete episodes to avoid leaking near-duplicate trajectory frames.
- Behavior cloning maps aligned observations to expert targets, but deployment
  introduces policy-generated states and possible compounding error.
- Action chunks use FPS-aligned offsets, fixed shapes, and padding masks so a
  target never crosses an episode reset.
- ACT and SmolVLA share the raw dataset while retaining different task,
  camera-key, and preprocessing contracts.

## Sources

- [LeRobot 0.6.0 dataset metadata source](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/dataset_metadata.py)
  — version-pinned loading of `info.json`, statistics, tasks, episodes, and
  file-path resolution.
- [LeRobot 0.6.0 dataset reader source](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/dataset_reader.py)
  — version-pinned Parquet access, task lookup, on-demand video decoding,
  temporal queries, boundary clamping, and padding masks.
- [LeRobot 0.6.0 dataset factory source](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/datasets/factory.py)
  — action-offset resolution and task-grouped episode-level train/eval split.
- [LeRobot 0.6.0 normalization processor source](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/processor/normalize_processor.py)
  and [ACT processor source](https://github.com/huggingface/lerobot/blob/v0.6.0/src/lerobot/policies/act/processor_act.py)
  — policy-facing normalization and action unnormalization behavior.
- [A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://proceedings.mlr.press/v15/ross11a.html)
  — formal treatment of the sequential distribution-shift and compounding-error
  problem that motivates closed-loop evaluation beyond supervised BC loss.
- [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)
  — the ACT paper and source for action chunking.
- [SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics](https://arxiv.org/abs/2506.01844)
  — the SmolVLA architecture and language-conditioned policy context used for
  the data-contract comparison.
- [RoboGenesis 101 recorder](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/record_dataset.py),
  [training wrapper](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/train_policy.py),
  and [compatibility record](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
  — the current nine-joint schema, policy presets, and verified runtime boundary
  used by this course.
