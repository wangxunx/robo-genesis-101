---
lesson: L11
slug: act-and-smolvla-policy-training
locale: en
title: "Training ACT and SmolVLA Policies"
duration_minutes: 150
hardware: gpu-required
status: gpu-verified
---

# L11 · Training ACT and SmolVLA Policies

> **Hardware contract:** the complete lab is GPU-required. The verified reference
> platform is Linux x86_64 with an AMD Radeon AI PRO R9700 and ROCm 7.2, but the
> concepts and commands remain platform-neutral. Learners who cannot train can
> still complete the data checks and command audit; that reduced route is not a
> substitute for the two GPU smoke runs.

## Where this lesson fits

[L09](/en/lessons/l09-dataset-anatomy-and-imitation-learning) established the
dataset schema, camera keys, behavior cloning, and the basic idea of action
chunking. [L10](/en/lessons/l10-domain-randomization) then asked how the training
distribution should vary. L11 now turns a versioned demonstration dataset into
two kinds of policy checkpoint:

```text
LeRobot dataset
  → validate one real sample
  → assemble the training command
  → ACT or SmolVLA optimization
  → checkpoint + saved preprocessing
  → reload on one real sample
  → closed-loop evaluation in L12
```

The last arrow matters. This lesson can prove that a training and loading path
works. It cannot prove that the learned policy completes a grasping task. That
claim requires the seeded simulator rollouts, success predicate, and reporting
protocol in [L12](/en/lessons/l12-closed-loop-evaluation-and-capstone).

Before starting, you should be able to:

- locate a local LeRobot dataset and identify its logical repository ID;
- read its feature schema, FPS, episode boundaries, and task table;
- explain why this course records two RGB views, a 9-D robot state, and a 9-D
  commanded action;
- distinguish behavior cloning from closed-loop task evaluation; and
- record which dataset version and domain-randomization configuration a run
  used.

## Learning objectives

By the end of L11, you should be able to:

1. validate the state, action, image, task, and timing contract of one real
   training sample before allocating a model;
2. explain the roles of ACT's visual backbone, conditional variational
   autoencoder (CVAE), Transformer, and action queries, including the difference
   between training and inference;
3. explain the roles of SmolVLA's vision-language backbone, task text, action
   expert, and flow-matching objective;
4. calculate the nominal prediction and execution horizons from dataset FPS,
   `chunk_size`, and `n_action_steps`, then reject an invalid configuration;
5. audit the generated ACT and SmolVLA `lerobot-train` commands, including their
   initialization mode, batch size, device, paths, and camera rename;
6. run one real GPU optimization step for each policy and identify the evidence
   for decoding, forward pass, finite loss, backward pass, optimizer update, and
   checkpoint save;
7. inspect and reload both checkpoints, then require a finite 9-D `float32`
   action from the same real dataset sample; and
8. state precisely why a dry-run, a finite loss, a loadable checkpoint, and one
   open-loop action still do not establish closed-loop task success.

## Start with the evidence boundary

The phrase "training worked" is too vague for a useful experiment report. L11
uses an evidence ladder instead:

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Dry-run command audit | the wrapper resolved paths and assembled the intended trainer arguments | that the dataset, model content, GPU, or optimizer can run |
| One-step smoke | one batch can be decoded and used for forward, backward, update, and save | convergence, generalization, or a useful policy |
| Finite training loss | the recorded scalar for that step is numerically defined | that the loss will decrease, or that another policy's loss is comparable |
| Checkpoint reload | weights, configuration, and processors can be reconstructed | that the policy acts sensibly in a changing environment |
| One open-loop action | the loaded model returns the required shape, dtype, and finite values | that executing the action is safe or completes the task |
| Closed-loop rollout | the policy interacts with the simulator under a defined protocol | population-level performance unless enough seeded episodes are reported |

Keep this table in view when reading logs. A tiny dataset can be memorized, and
a falling loss can accompany poor behavior under new poses or appearances. The
inverse is also possible over a short, noisy run: a non-monotonic loss trace is
not automatically a broken pipeline.

## The shared data-to-policy contract

ACT and SmolVLA use the same raw course dataset. They differ in how they
preprocess and model it.

| Field | Course meaning | Required check |
|---|---|---|
| `observation.state` | 9 joint positions: 7 arm plus 2 gripper joints | shape `(9,)`, `float32`, finite values, expected joint names |
| `action` | 9 commanded joint-position targets in the same joint order | shape `(9,)`, `float32`, finite values |
| `observation.images.world` | fixed global view | present, decodable RGB, consistent resolution |
| `observation.images.wrist` | eye-in-hand local view | present, decodable RGB, consistent resolution |
| `task` | non-empty language description of the episode | resolve and print one real task rather than inventing a placeholder |
| FPS | sampling rate shared by observations and actions | positive and consistent with video metadata |
| episode boundary | prevents a future-action target from crossing into another episode | metadata and padding behavior are readable |

The logical repository ID and the local root are separate inputs. For example,
`genesis/fruit_pick` can identify the dataset while `datasets/fruit_pick`
selects the local copy. A correct ID paired with the wrong directory is still a
bad experiment.

### Three representations of one image

Do not compare shapes without asking which layer they describe:

1. dataset metadata describes stored video frames as height × width × channel;
2. a decoded LeRobot sample normally exposes a channel-first tensor; and
3. a policy preprocessor may rename, resize, normalize, pad, or batch that
   tensor before the model sees it.

SmolVLA also tokenizes `task` and can pad short state/action vectors internally.
That is why a raw metadata key and an internal model feature need not have the
same spelling or shape. The correct test follows the complete preprocessor and
checks a real training and loading path; it does not compare two isolated JSON
fragments and guess.

### Behavior cloning predicts a sequence here

One-step behavior cloning can be summarized as
`policy(observation_t) → action_t`. Both policies in this lesson instead learn a
future sequence:

```text
policy(images_t, state_t, optional_task)
  → [action_t, action_t+1, ..., action_t+chunk_size-1]
```

The dataset loader therefore needs future action targets from the same episode.
Near the end of an episode it marks padded positions so the model loss can
ignore or mask them. A chunk is a coordinated prediction over time, not proof
that every action in it should be executed without observing the world again.

## ACT: a CVAE that predicts action chunks

ACT stands for **Action Chunking with Transformers**. In the pinned LeRobot
implementation, images and robot state condition a Transformer that predicts a
fixed-size action chunk.

### Training path

ACT contains two Transformer-based paths whose names are easy to confuse:

- The **CVAE encoder** sees robot state and the ground-truth action chunk during
  training. It produces the mean and log variance of a latent distribution.
- The main **Transformer encoder/decoder** consumes visual features, robot
  state, a sampled latent, and learned action queries. It predicts the complete
  action chunk and is the path retained for inference.

The information flow is:

```text
ground-truth action chunk + state
  → CVAE encoder → mean/log-variance → sampled latent

camera features + state + sampled latent + action queries
  → Transformer encoder/decoder → predicted action chunk
```

The current loss is the mean absolute action reconstruction error over valid,
non-padded targets plus `kl_weight` times the KL divergence between the learned
latent distribution and a standard normal prior. The reconstruction term asks
the predicted chunk to imitate the demonstration; the KL term regularizes the
latent space. A finite sum verifies one computation, not task competence.

### Inference path

At inference there is no ground-truth future action for the CVAE encoder to
read. The pinned LeRobot implementation uses a zero latent, runs the main
Transformer, and returns a chunk. `ACTPolicy.select_action()` queues up to
`n_action_steps` entries and queries the model again when that queue is empty.

This gives two distinct horizons:

- `chunk_size`: how many future actions the model predicts and the loader uses
  as its training target;
- `n_action_steps`: how many predicted actions the runtime consumes before it
  asks for a new chunk.

Changing `n_action_steps` does not shorten the training target. It changes how
often a deployed policy incorporates a new observation. Temporal ensembling is
another ACT execution mode, but it is disabled by default in this course's
LeRobot configuration and is not part of the minimum lab.

### "From configuration" is not the same as "every weight is random"

The project ACT preset emits `--policy.type=act`, so the policy structure is
created from configuration and adapted to the dataset features. However, the
LeRobot 0.6.0 ACT default allows a pretrained ImageNet ResNet18 visual backbone.
It is therefore inaccurate to claim that every default ACT weight is randomly
initialized.

The one-step smoke deliberately sets
`--policy.pretrained_backbone_weights=null`. That avoids a network download and,
together with a much smaller Transformer/CVAE, makes a deterministic pipeline
probe. The resulting checkpoint is a **smoke model**, not a representative ACT
training configuration.

## SmolVLA: language-conditioned flow matching

SmolVLA is a compact **vision-language-action (VLA)** policy. This course
fine-tunes `lerobot/smolvla_base`; it does not train the complete model from
scratch.

### Prefix context and action expert

The model separates two conceptual streams:

- a vision-language backbone embeds camera images and task tokens; and
- an action expert combines that context with robot state, a noisy action
  chunk, and a continuous time value.

Images, language, and state form the context prefix. The noisy actions and
their time embedding form an action suffix. Attention lets the action expert
condition its prediction on the task context without treating the task string
as an action label.

The pinned base configuration freezes the vision encoder, primarily trains the
action expert, and trains the state projection. These choices define the
fine-tuning boundary and affect trainable parameters, memory, and learning
rate. Changing them creates a different experiment and must be recorded.

### The flow-matching target

During training, SmolVLA samples noise and a time value. It interpolates between
the demonstrated action chunk and noise, then asks the action expert to predict
the velocity that points along that path. In compact notation:

```text
noisy point x_t = t × noise + (1 - t) × demonstrated_actions
target velocity = noise - demonstrated_actions
loss = mean squared error(predicted_velocity, target_velocity)
```

At inference the model starts from noise and integrates the learned velocity
field back toward an action chunk. LeRobot 0.6.0 uses ten sampling steps by
default. This is why a single SmolVLA policy query is not simply one direct
linear regression from pixels to joints.

The description above is sufficient to reason about the lab. Deriving the full
flow-matching theory, tokenizer internals, or every attention layer is outside
this lesson's boundary.

### Language is real input, not decoration

The task must come from the dataset sample, for example a description of which
object to pick and where to place it. Replacing it with an unrelated hard-coded
sentence changes the conditioning signal. An ACT run can use the same dataset
without consuming language, but SmolVLA's training and reload probe must verify
that non-empty task text reaches the preprocessor.

Pretraining may provide reusable visual, language, and action priors. Whether
those priors improve this fruit-picking task is an experimental question. A
model name, parameter count, or one-step loss cannot answer it.

## Camera keys are part of the checkpoint contract

The course dataset names its views by their physical role:

```text
observation.images.world
observation.images.wrist
```

The SmolVLA base uses canonical pretraining names. The project preset therefore
adds this map:

```json
{
  "observation.images.world": "observation.images.camera1",
  "observation.images.wrist": "observation.images.camera2"
}
```

LeRobot writes the mapping into `train_config.json` and the saved
`rename_observations_processor`. The loader in
`robo_genesis.eval_policy.load_policy()` reads the map back so callers continue
to provide the meaningful raw keys `world` and `wrist`.

ACT created from this dataset adapts to its raw feature keys and does not need
this preset rename. That is a statement about this ACT initialization path, not
a universal promise that every pretrained ACT checkpoint accepts arbitrary
camera names.

Do not "fix" a feature mismatch by inventing a different evaluation-time map.
Training, checkpoint metadata, and evaluation must agree on the same
transformation.

## ACT and SmolVLA: compare contracts, not raw losses

| Question | ACT preset | SmolVLA preset |
|---|---|---|
| Trainer selection | `--policy.type=act` | `--policy.path=lerobot/smolvla_base` or a pinned local snapshot |
| Initialization | new ACT policy; visual backbone may use ImageNet weights unless overridden | fine-tune a pretrained SmolVLA base |
| Conditioning | two images and robot state | two images, robot state, and task text |
| Training objective | valid-action L1 reconstruction plus weighted KL | flow-matching velocity MSE |
| Current default chunk / execution steps | 100 / 100 | 50 / 50 |
| Wrapper default batch size | 8 | 4 |
| Camera rename in this course | none | `world/wrist → camera1/camera2` |
| Reload path | generic project loader and saved processors | same loader, including recovered rename and language processing |

The raw losses have different definitions and scales. Comparing `ACT loss <
SmolVLA loss` would not rank policy quality. Even within one policy, compare
runs only after checking that the dataset, preprocessing, initialization,
training budget, and reduction are the same.

## Reason about the training knobs

### `chunk_size` and dataset FPS

`chunk_size` counts action samples, not seconds. Its nominal time span is:

```text
prediction horizon in seconds = chunk_size / dataset_fps
```

For a 10 FPS dataset and `chunk_size=40`, one prediction contains 4 seconds of
action targets. That does not mean all 4 seconds must be executed open loop.

Longer chunks expose longer coordinated behavior but increase the output target
and the amount of padding near episode ends. Shorter chunks reduce that horizon
but do not automatically make behavior smoother or more successful.

### `n_action_steps` and replanning

The execution interval is nominally:

```text
replan interval in seconds = n_action_steps / dataset_fps
```

It must satisfy `1 <= n_action_steps <= chunk_size`. Smaller values incorporate
new observations more often but increase inference frequency. Larger values
reduce query frequency but commit to more actions before observing again. The
latency-versus-feedback trade-off must eventually be measured in L12.

### Batch size and memory

Batch size changes how many samples contribute to one optimizer update. Larger
batches normally require more activation memory and may improve throughput;
they also change gradient noise. Exact memory depends on policy, image count and
resolution, trainable modules, precision, and other processes on the GPU.

If an otherwise valid run is out of memory, first confirm the intended device
and current GPU occupancy, then reduce `--batch-size`. Do not silently change
the policy architecture or action horizon and continue calling it the same
experiment.

### Steps are not episodes or convergence

`--steps` counts optimizer updates. It is not the number of demonstrations, the
number of epochs, or evidence of convergence. Record dataset frames/episodes,
batch size, steps, seed, and checkpoint cadence together. Values such as 20,000
or 200,000 are budgets to justify for a particular run, not "paper-grade"
settings that guarantee quality.

### Seed and determinism

The wrapper records a seed for model initialization and sampling paths handled
by the trainer. Reusing it improves traceability but does not promise bitwise
identical results across different hardware, kernels, or dependency versions.

## The project wrapper stays thin

`python -m robo_genesis.train_policy` does not reimplement optimization. It
resolves course paths and translates a small, reviewable interface into
LeRobot's trainer arguments.

The wrapper currently controls:

- the `act` or `smolvla` preset;
- logical repo ID and local dataset root;
- job name and output directory;
- steps, batch size, checkpoint/log frequency, workers, seed, and device;
- PyAV as the default video backend;
- optional W&B and Hub publishing, both off by default; and
- the SmolVLA camera rename and optional pinned local base/VLM snapshots.

Arguments after a standalone `--` are forwarded to `lerobot-train`, for example:

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id genesis/fruit_pick \
  --dataset-root datasets/fruit_pick \
  --dry-run -- \
  --policy.chunk_size=40 \
  --policy.n_action_steps=10 \
  --policy.optimizer_lr=1e-5
```

Forwarding is powerful and easy to misuse. Every override belongs in the run
record; a hidden command-line change is a changed experiment.

## Before allocating the GPU

### Install and identify the actual runtime

The complete course environment is installed from the lock file:

```sh
uv sync --locked --all-extras
```

That portable resolution does not by itself install or verify the course's AMD
ROCm wheels. Follow the
[compatibility matrix](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
for the reference AMD environment.

Record at least:

- Python, LeRobot, and PyTorch versions;
- `torch.version.hip` and `torch.version.cuda` as applicable;
- `torch.cuda.is_available()`, visible device count, and actual device name; and
- whether the model content came from an existing cache or a network fetch.

PyTorch intentionally exposes ROCm devices through the `torch.cuda` API. On the
verified AMD environment, LeRobot's correct device value is therefore
`--device cuda`, not `rocm`. The device name and HIP runtime provide the evidence
that the underlying platform is AMD. If LeRobot falls back to CPU, the GPU smoke
has failed.

### Validate the dataset before the model

Fail before training if any of these checks fails:

- the resolved dataset directory and `meta/info.json` exist;
- metadata and one sample can be read with `video_backend="pyav"`;
- state/action are finite 9-D `float32` values with matching joint order;
- both expected image keys decode with consistent dimensions;
- FPS and episode/frame counts are positive; and
- the sample resolves to non-empty task text.

This ordering separates a data error from a model or GPU error and avoids an
expensive download before discovering a missing camera.

### Pin the SmolVLA model content

A Hub repository name can move. The verified reference content is:

| Repository | Verified revision |
|---|---|
| `lerobot/smolvla_base` | `c83c3163b8ca9b7e67c509fffd9121e66cb96205` |
| `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` | `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |

Before a reproducible run, resolve both repositories to those commits or use a
pre-provisioned local snapshot whose provenance records them. The current
wrapper's bare `lerobot/smolvla_base` default is convenient for command
discovery but does not, by itself, freeze content. A cache hit also does not
prove that a clean-cache download path was tested.

For an auditable local run, pass the base snapshot through `--policy-path` and
the VLM snapshot through `--smolvla-vlm-path`. The wrapper accepts an exact
Hugging Face `snapshots/<40-hex-commit>` directory, or a copied directory with a
`robo_genesis_snapshot.json` provenance record. It verifies both revisions and
required files locally, then forwards the VLM directory as
`policy.vlm_model_name`. No model is downloaded by this audit.

## Level 1 lab: audit both dry-run commands

Choose the dataset that you produced and inspected in the preceding lessons:

```sh
RG101_REPO_ID=genesis/fruit_pick
RG101_DATASET_ROOT=datasets/fruit_pick
```

First ask the wrapper to print the ACT command:

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-act-dry-run \
  --output-dir outputs/train/l11-act-dry-run \
  --steps 1 --save-freq 1 --log-freq 1 --num-workers 0 \
  --seed 1000 --device cuda --video-backend pyav \
  --dry-run
```

Then print the SmolVLA command:

```sh
uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-smolvla-dry-run \
  --output-dir outputs/train/l11-smolvla-dry-run \
  --steps 1 --save-freq 1 --log-freq 1 --num-workers 0 \
  --seed 1000 --device cuda --video-backend pyav \
  --dry-run
```

Audit the generated command rather than accepting a zero exit code:

| Check | ACT | SmolVLA |
|---|---|---|
| policy selector | `--policy.type=act` | `--policy.path=lerobot/smolvla_base` |
| wrapper default batch | `--batch_size=8` | `--batch_size=4` |
| data | resolved ID/root and PyAV | same |
| device | `--policy.device=cuda` | same |
| external publishing | Hub and W&B false | same |
| camera map | absent | JSON map from `world/wrist` to `camera1/camera2` |

Dry-run does not open the dataset, load a policy, allocate a GPU tensor, or
write a checkpoint. Stop calling the result a "training smoke" at this level.

## Level 2 lab: one real step for each policy

Run these only after the environment, data, and model-content gates pass. Use
different output directories so one policy cannot overwrite the other.

### ACT pipeline-only smoke

```sh
uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name l11-act-smoke \
  --output-dir outputs/train/l11-act-smoke \
  --steps 1 --batch-size 1 --save-freq 1 --log-freq 1 \
  --num-workers 0 --seed 1000 --device cuda --video-backend pyav -- \
  --policy.pretrained_backbone_weights=null \
  --policy.chunk_size=10 \
  --policy.n_action_steps=10 \
  --policy.dim_model=64 \
  --policy.n_heads=4 \
  --policy.dim_feedforward=128 \
  --policy.n_encoder_layers=1 \
  --policy.n_decoder_layers=1 \
  --policy.n_vae_encoder_layers=1 \
  --policy.latent_dim=8
```

These architecture reductions exist only to exercise the pipeline cheaply.
The checkpoint must be labelled `pipeline-only`; it is not an ACT baseline for
task evaluation.

### SmolVLA fine-tuning smoke

Point both policy components at the verified local snapshots prepared during
the revision gate. Replace `/path/to/huggingface/hub` with the cache root on
your machine:

```sh
RG101_SMOLVLA_BASE_SNAPSHOT=/path/to/huggingface/hub/models--lerobot--smolvla_base/snapshots/c83c3163b8ca9b7e67c509fffd9121e66cb96205
RG101_SMOLVLA_VLM_SNAPSHOT=/path/to/huggingface/hub/models--HuggingFaceTB--SmolVLM2-500M-Video-Instruct/snapshots/7b375e1b73b11138ff12fe22c8f2822d8fe03467

uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --policy-path "$RG101_SMOLVLA_BASE_SNAPSHOT" \
  --smolvla-vlm-path "$RG101_SMOLVLA_VLM_SNAPSHOT" \
  --name l11-smolvla-smoke \
  --output-dir outputs/train/l11-smolvla-smoke \
  --steps 1 --batch-size 1 --save-freq 1 --log-freq 1 \
  --num-workers 0 --seed 1000 --device cuda --video-backend pyav
```

Model snapshots are local generated content and must not be committed. The
wrapper rejects a directory name that merely resembles a revision: it requires
an exact cache path or a matching provenance record and checks both complete
commit IDs. Using `--policy-path` does not disable the SmolVLA preset's camera
rename.

### What a passing one-step smoke contains

For each policy, record rather than hard-code:

- the complete command and return code;
- actual GPU identity and software versions;
- dataset episode/frame/FPS and one sample's feature checks;
- resolved model revisions where applicable;
- a finite loss and finite gradient norm;
- evidence that one optimizer step completed;
- numeric checkpoint directory and the `last` target;
- elapsed time and peak memory as observations for this run only; and
- every unrun item, especially long training and closed-loop evaluation.

Do not require one exact loss, gradient norm, time, or memory value. Those are
environment- and sample-dependent. With one log point there is no loss trend to
plot.

## Inspect the checkpoint as a package

LeRobot writes a numeric step directory and updates `last` to point to the
newest one:

```text
outputs/train/l11-act-smoke/
└── checkpoints/
    ├── 000001/
    │   └── pretrained_model/
    │       ├── config.json
    │       ├── train_config.json
    │       ├── model.safetensors
    │       ├── policy_preprocessor.json
    │       ├── policy_postprocessor.json
    │       └── processor state files required by those JSON configs
    └── last -> 000001
```

SmolVLA uses the same roles but can have different processor-state filenames.
Validate roles and references rather than assuming one numbered filename is a
cross-policy API.

At minimum, check:

- `model.safetensors` exists and is non-empty;
- `config.json` records the expected policy type, chunk, execution steps, and
  9-D action output;
- `train_config.json` records dataset identity, seed, output, and training
  options;
- the preprocessor and postprocessor configurations reference their required
  state files; and
- SmolVLA records the exact camera rename in both the training configuration
  and rename processor.

The numeric directory is the durable evidence. `last` is a convenient pointer;
confirm that it resolves to the numeric checkpoint rather than checking only
that the string path exists.

## Reload on a real sample

The next check uses `robo_genesis.eval_policy.load_policy()` with the same repo
ID and local dataset metadata used for training. The loader reconstructs the
policy and pre/postprocessors. For SmolVLA it also recovers the camera map from
`train_config.json`.

Use the same real dataset sample for both policies. The probe must report:

```text
policy type
actual device
raw image keys
task text present (SmolVLA)
action shape: (9,)
action dtype: float32
all action values finite: true
```

The dataset sample's decoded images may need conversion back to the raw HWC
observation format expected by the project inference helper. In the companion
notebook, perform and assert that conversion explicitly. Do not replace the
sample with random tensors merely to make the call return.

This remains an **open-loop single-sample probe**. It does not build Genesis,
apply the action, observe the next state, or check task success.

## Level 3 lab: design a full run before starting it

A full training job is take-home work. It is opt-in and must not start merely
because a notebook was run top to bottom. First fill in a run record:

| Decision | Record before launch |
|---|---|
| Data | repo ID, local root, artifact/version, episodes, frames, FPS, domain-randomization provenance |
| Initialization | policy type or pinned base/VLM revisions; ACT backbone-weight choice |
| Horizon | explicit `chunk_size` and `n_action_steps`, plus their duration at dataset FPS |
| Optimization | steps, batch, learning rate overrides, seed, workers, log/save frequency |
| Resources | actual GPU/software, free memory, model cache, output storage |
| Evaluation handoff | numeric checkpoint path and the L12 protocol that will consume it |

After choosing values, a complete ACT command has this form:

```sh
# Set every ALL_CAPS value from the run record before executing.
RG101_ACT_STEPS=CHOOSE_INTEGER
RG101_ACT_BATCH=CHOOSE_INTEGER
RG101_ACT_CHUNK=CHOOSE_INTEGER
RG101_ACT_EXECUTION_STEPS=CHOOSE_INTEGER
RG101_ACT_LR=CHOOSE_FLOAT
RG101_ACT_BACKBONE_WEIGHTS=CHOOSE_IMAGENET_IDENTIFIER_OR_NULL
RG101_SAVE_FREQ=CHOOSE_INTEGER
RG101_LOG_FREQ=CHOOSE_INTEGER
RG101_SEED=CHOOSE_INTEGER

uv run python -m robo_genesis.train_policy act \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --name act-fruit-pick \
  --output-dir outputs/train/act-fruit-pick \
  --steps "$RG101_ACT_STEPS" \
  --batch-size "$RG101_ACT_BATCH" \
  --save-freq "$RG101_SAVE_FREQ" \
  --log-freq "$RG101_LOG_FREQ" \
  --num-workers 4 --seed "$RG101_SEED" \
  --device cuda --video-backend pyav -- \
  --policy.pretrained_backbone_weights="$RG101_ACT_BACKBONE_WEIGHTS" \
  --policy.chunk_size="$RG101_ACT_CHUNK" \
  --policy.n_action_steps="$RG101_ACT_EXECUTION_STEPS" \
  --policy.optimizer_lr="$RG101_ACT_LR"
```

The corresponding SmolVLA template uses the pinned snapshot and records its
fine-tuning boundary:

```sh
# Set every ALL_CAPS value from the run record before executing.
RG101_SMOLVLA_BASE_SNAPSHOT=CHOOSE_PINNED_BASE_SNAPSHOT
RG101_SMOLVLA_VLM_SNAPSHOT=CHOOSE_PINNED_VLM_SNAPSHOT
RG101_SMOLVLA_STEPS=CHOOSE_INTEGER
RG101_SMOLVLA_BATCH=CHOOSE_INTEGER
RG101_SMOLVLA_CHUNK=CHOOSE_INTEGER
RG101_SMOLVLA_EXECUTION_STEPS=CHOOSE_INTEGER
RG101_SMOLVLA_LR=CHOOSE_FLOAT
RG101_SMOLVLA_FREEZE_VISION=CHOOSE_TRUE_OR_FALSE
RG101_SMOLVLA_TRAIN_EXPERT_ONLY=CHOOSE_TRUE_OR_FALSE
RG101_SMOLVLA_TRAIN_STATE_PROJ=CHOOSE_TRUE_OR_FALSE
RG101_SAVE_FREQ=CHOOSE_INTEGER
RG101_LOG_FREQ=CHOOSE_INTEGER
RG101_SEED=CHOOSE_INTEGER

uv run python -m robo_genesis.train_policy smolvla \
  --repo-id "$RG101_REPO_ID" \
  --dataset-root "$RG101_DATASET_ROOT" \
  --policy-path "$RG101_SMOLVLA_BASE_SNAPSHOT" \
  --smolvla-vlm-path "$RG101_SMOLVLA_VLM_SNAPSHOT" \
  --name smolvla-fruit-pick \
  --output-dir outputs/train/smolvla-fruit-pick \
  --steps "$RG101_SMOLVLA_STEPS" \
  --batch-size "$RG101_SMOLVLA_BATCH" \
  --save-freq "$RG101_SAVE_FREQ" \
  --log-freq "$RG101_LOG_FREQ" \
  --num-workers 4 --seed "$RG101_SEED" \
  --device cuda --video-backend pyav -- \
  --policy.chunk_size="$RG101_SMOLVLA_CHUNK" \
  --policy.n_action_steps="$RG101_SMOLVLA_EXECUTION_STEPS" \
  --policy.optimizer_lr="$RG101_SMOLVLA_LR" \
  --policy.freeze_vision_encoder="$RG101_SMOLVLA_FREEZE_VISION" \
  --policy.train_expert_only="$RG101_SMOLVLA_TRAIN_EXPERT_ONLY" \
  --policy.train_state_proj="$RG101_SMOLVLA_TRAIN_STATE_PROJ"
```

The `CHOOSE_...` values are deliberate stop signs, not suggested settings. The
training CLI will reject them until you replace them. For the ACT backbone,
record either an exact torchvision weight identifier or `null`; for the three
SmolVLA booleans, record the intended fine-tuning boundary explicitly. This
prevents a course-wide constant or hidden default from being mistaken for a
universally sufficient configuration. If the long job was not run, write **not
run**; do not invent its curve, duration, memory use, or checkpoint quality.

Learners without training hardware can still complete the conceptual checks,
dataset gate, and dry-run. If a versioned course checkpoint is published, it can
provide the handoff to L12, but do not assume that artifact exists until its
metadata and download instructions are available. Using one must be reported as
using a provided artifact, not as completing the L11 GPU training lab.

## Diagnose failures in layers

### The run used CPU unexpectedly

Check PyTorch and LeRobot versions, `torch.cuda.is_available()`, visible device
count, the actual device name, and HIP/CUDA runtime before inspecting model
code. On a multi-GPU AMD host, follow the compatibility matrix's visibility
rules. A LeRobot warning followed by CPU execution is a failed GPU smoke, not a
successful fallback.

### SmolVLA cannot load offline

Confirm both model revisions and whether the Hugging Face cache visible to the
process contains them. Changing `XDG_CACHE_HOME` can hide an otherwise valid
model cache. Conversely, finding files in an old cache does not prove that the
recorded revision or a clean download is correct.

### The dataset cannot decode video

Verify the local root, `meta/info.json`, video metadata, and
`--video-backend pyav`. A `torchcodec`/FFmpeg shared-library error belongs to a
different decoder path; do not diagnose it as a policy architecture failure.

### SmolVLA reports missing camera features

Inspect the generated command for `--rename_map`, then inspect the saved
`train_config.json` and rename processor. Keep the raw dataset keys as
`world/wrist`; do not rename files or add a conflicting evaluation-only map.

### Training is out of memory

Confirm the intended GPU and competing processes, then lower batch size. If the
failure is in ACT smoke, verify that all reduced-model overrides were forwarded
after `--`. Do not claim equivalence after quietly changing architecture,
precision, or trainable modules.

### Loss or gradient is non-finite

Return to the first real sample and dataset statistics. Check finiteness,
normalization, task/image alignment, learning-rate overrides, and any optional
mixed precision. Preserve the first failing step and actual log instead of
replacing it with a fabricated expected value.

### No checkpoint appeared

Check the subprocess return code, output directory, `steps`, `save_freq`, and
available storage. A created run directory is not evidence that
`model.safetensors` was written.

### Reload reports a feature mismatch

Use the training dataset metadata, numeric checkpoint directory, and saved
processors together. For SmolVLA, verify the persisted rename. For both models,
check the 9-D action contract before blaming the GPU.

### The action is finite but the grasp fails

The reload probe has passed and the evidence boundary has been reached. Move to
L12's closed-loop diagnostics: observation timing, execution horizon, control
application, task predicate, seed, and distribution split.

## Checkpoints and exercises

### Concept checkpoints

1. Why can ACT's CVAE encoder use the demonstrated future action during
   training but not during inference?
2. At 10 FPS, what prediction and replanning intervals result from
   `chunk_size=40` and `n_action_steps=8`?
3. Why does lowering `n_action_steps` not reduce ACT's training target from 40
   actions?
4. Why is a lower ACT loss not evidence that ACT is better than SmolVLA?
5. Which files prove that SmolVLA's camera rename survives checkpoint reload?
6. On a ROCm machine, why can `device=cuda` be correct, and what evidence shows
   that the actual device is AMD?
7. Which parts of a one-step smoke would still pass for a policy that has learned
   no useful grasping behavior?

### Command-audit exercise

Generate both dry-run commands with your own dataset root. Annotate each final
trainer argument as one of:

- dataset identity and decoding;
- policy initialization;
- optimization budget;
- output/logging;
- device/runtime; or
- preprocessing compatibility.

Then remove the SmolVLA rename from a copied command **without running training**
and explain which raw and canonical feature names no longer agree.

### Experiment-design exercise

Write two run records that differ only in `n_action_steps`. Keep dataset,
checkpoint, `chunk_size`, seed set, and L12 protocol fixed. Predict the trade-off
in replanning frequency and inference cost. Do not predict a success-rate number;
that value must come from the later rollouts.

### Artifact-audit exercise

Given a numeric checkpoint directory, produce a short report containing:

- policy type and initialization source;
- dataset ID/root and seed;
- chunk and execution horizons;
- expected raw camera keys and any rename;
- weight and processor files present;
- one-sample action shape/dtype/finiteness; and
- the strongest justified claim about the artifact.

## Summary and connection to L12

- Both policies consume the same two-view, 9-D state/action course dataset, but
  their internal preprocessing and objectives differ.
- ACT uses a training-only CVAE encoder and a Transformer to reconstruct action
  chunks; the current preset can still use pretrained visual-backbone weights.
- SmolVLA conditions an action expert on vision, language, and state, then uses
  flow matching to generate an action chunk from noise.
- `chunk_size` defines the prediction target; `n_action_steps` defines how much
  of that target is consumed before replanning.
- Dry-run, one-step smoke, checkpoint reload, and one open-loop action are four
  distinct evidence levels.
- Model revisions, camera rename, pre/postprocessors, data identity, and the
  numeric checkpoint must travel together for reproducibility.
- Full training is an explicit, recorded take-home experiment. A fixed step
  count is not a universal quality guarantee.

L12 will load one of these checkpoints into the Genesis control loop, apply its
actions over time, evaluate the task predicate across seeded episodes, and
report success counts with uncertainty. That is where policy quality becomes a
closed-loop claim.

## Sources

- [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)
  — the ACT paper; source for action chunking, the CVAE formulation, and temporal
  ensembling.
- [Official ACT implementation](https://github.com/tonyzhaozh/act) — the
  reference implementation associated with the paper.
- [SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics](https://arxiv.org/abs/2506.01844)
  — the SmolVLA paper and architecture description.
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) —
  background for the conditional flow-matching objective used by SmolVLA.
- [LeRobot 0.6.0 ACT source](https://github.com/huggingface/lerobot/tree/v0.6.0/src/lerobot/policies/act)
  and [SmolVLA source](https://github.com/huggingface/lerobot/tree/v0.6.0/src/lerobot/policies/smolvla)
  — implementation source for the configuration defaults, loss, action queue,
  saved processors, and sampling behavior described here.
- [`lerobot/smolvla_base` at the verified revision](https://huggingface.co/lerobot/smolvla_base/tree/c83c3163b8ca9b7e67c509fffd9121e66cb96205)
  and [`SmolVLM2-500M-Video-Instruct` at the verified revision](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct/tree/7b375e1b73b11138ff12fe22c8f2822d8fe03467)
  — model content used by the reference compatibility run.
- [PyTorch HIP semantics](https://docs.pytorch.org/docs/stable/notes/hip.html)
  — official explanation of the shared `torch.cuda` interface on ROCm.
- [RoboGenesis 101 training wrapper](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/train_policy.py),
  [policy loader](https://github.com/wangxunx/robo-genesis-101/blob/main/src/robo_genesis/eval_policy.py),
  and [compatibility record](https://github.com/wangxunx/robo-genesis-101/blob/main/COMPATIBILITY.md)
  — the project interfaces and verification boundary used by this lesson.
