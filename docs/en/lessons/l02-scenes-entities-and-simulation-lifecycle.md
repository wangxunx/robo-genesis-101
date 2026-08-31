---
lesson: L02
slug: scenes-entities-and-simulation-lifecycle
locale: en
title: "Scenes, Entities, and the Simulation Lifecycle"
duration_minutes: 90
hardware: cpu-ok
status: planned
---

# L02 · Scenes, Entities, and the Simulation Lifecycle

> **Course status:** the lecture content is available, but the companion
> executable notebook and its clean-kernel verification are not yet published.
> L02 therefore remains `planned`.

## Where this lesson fits

L01 established that a working installation is not a single yes/no property: a
machine can support documentation, core simulation, rendering, or the complete
training workflow to different degrees. L02 now asks the first structural
question that appears in every later simulation program:

**When does a Python scene description become simulation state that can be
stepped and measured?**

The answer is the Genesis lifecycle:

```text
gs.init
  → configure Scene
  → add entities and cameras
  → scene.build()
  → scene.step()
  → read state and render observations
```

This pattern will reappear when the course adds rigid-body experiments in L03,
an articulated robot in L04, inverse kinematics and cameras in L05, and the
complete grasping scene in L06. Here we deliberately use only built-in Plane and
Box primitives. A small scene makes the lifecycle visible without hiding it
behind a task-specific helper.

Before starting, you should be able to:

- run a notebook from a clean kernel;
- identify the backend selected by your environment;
- recognize that `gs.init()` is process-wide initialization; and
- distinguish "the call returned" from "the result has been verified."

## Learning objectives

By the end of L02, you should be able to:

1. label initialization, topology declaration, build, and runtime operations in
   a Genesis program, then identify an invalid call order;
2. classify arguments to `scene.add_entity(...)` as Morph, Material, or Surface
   configuration and explain the responsibility of each;
3. explain the rigid-body hierarchy
   `Scene → RigidEntity → RigidLink → RigidGeom` and inspect it on a primitive;
4. build and step a minimal scene on an automatically selected verified backend,
   read position, quaternion, and linear velocity, and report their shape,
   device, finiteness, and observed change;
5. use controlled expected exceptions as evidence for the `build()` boundary;
   and
6. validate an offscreen RGB observation when rendering is enabled, or report an
   explicit rendering `SKIP` and use a state-derived schematic for the core lab.

## From configuration to runtime state

A useful first reading strategy is to divide simulation code into three phases.

| Phase | Main question | Typical operations |
|---|---|---|
| Declaration | What belongs in this world? | construct `Scene`, add entities, add cameras |
| Build | How does the description become executable state? | `scene.build()` |
| Runtime | What happens, and what can we observe? | `scene.step()`, state getters, camera render |

The declaration phase contains ordinary Python objects that describe a scene.
For example, calling `scene.add_entity(...)` returns an entity handle, but that
does not mean all runtime state already exists. Solver buffers and compiled
kernels are established at the build boundary.

After a successful build, runtime operations can advance and inspect that state.
The distinction explains two otherwise surprising errors:

- reading a rigid entity's position before build raises an "is not built yet"
  error; and
- adding another entity after build raises "Scene is already built."

These are lifecycle invariants, not arbitrary restrictions. Genesis needs the
scene topology when it allocates solver state and prepares the kernels that will
operate on that state.

## Scene and Entity

### What a Scene owns

`gs.Scene` is the top-level container for one simulation world. It brings
together several kinds of configuration:

- simulation timing such as `dt` and `substeps`;
- solver-specific options;
- entities and their physical representations;
- cameras and visualization configuration; and
- the runtime state advanced by `scene.step()` after build.

L02 uses timing options only to create a concrete scene. L03 will investigate
how timestep, substeps, contact, and friction change physical results. Do not
infer those effects from this lesson's one trajectory.

### What an Entity is

An Entity is the runtime-facing object returned by `scene.add_entity(...)`.
Code keeps that handle so it can later inspect or modify the represented object:

```python
box = scene.add_entity(
    morph=gs.morphs.Box(
        size=(0.10, 0.10, 0.10),
        pos=(0.0, 0.0, 0.50),
    ),
    material=gs.materials.Rigid(rho=500.0),
    surface=gs.surfaces.Default(color=(0.20, 0.60, 0.90, 1.0)),
    name="falling_box",
)
```

The assignment does not copy a position into a standalone Python structure.
`box` refers to an object owned by `scene`; after build, its getters read the
scene's current solver state.

## The rigid-body hierarchy

"Entity" is a general Genesis concept. This lesson narrows the discussion to a
rigid entity, because the lab's Box uses `gs.materials.Rigid`.

```text
Scene
└── RigidEntity
    └── RigidLink
        └── RigidGeom
```

The levels have different responsibilities:

- A `RigidEntity` is the object-level handle returned to the user.
- A `RigidLink` is one rigid body within that entity.
- A `RigidGeom` is collision geometry belonging to a link.

A Box primitive normally produces one rigid entity with one link and one
collision geom. An articulated robot is still one entity but contains multiple
links and joints. L04 will explain that articulated structure, joint state, and
degrees of freedom; L02 only establishes the container hierarchy.

Use the API rather than trusting a diagram:

```python
print(type(box).__name__)
print(box.n_links, len(box.links))
print(box.n_geoms, len(box.geoms))
```

For the pinned Genesis 1.3.3 primitive used in this lesson, the expected counts
are one link and one collision geom. That observation is specific to this
primitive. It is not a universal rule for every entity or imported asset.

Visual geometry and collision geometry also need not be identical. That
distinction becomes important for imported robot and object assets, but a deeper
visual-geom discussion would distract from the lifecycle and is deferred.

## Morph, Material, and Surface

`scene.add_entity(...)` combines three categories of configuration. Keeping
them separate makes both code review and debugging much easier.

| Input | Responsibility in L02 | Example | Common confusion |
|---|---|---|---|
| Morph | shape, size, initial pose, import flags such as `fixed` | `gs.morphs.Box(size=..., pos=...)` | a Morph is a creation description, not the runtime Entity |
| Material | physical model and physical parameters | `gs.materials.Rigid(rho=...)` | "material" here is not the object's visible color |
| Surface | rendered appearance such as color and texture | `gs.surfaces.Default(color=...)` | a red object is not automatically more or less slippery |

### Morph describes what is created

A Morph tells Genesis how to create geometry and where to place it initially.
Primitive Morphs include Plane, Box, and Sphere. File-backed Morphs can describe
meshes and articulated assets, which later lessons will use.

Some flags that affect how an object enters the simulation also belong to the
Morph. For example, `fixed=True` anchors a primitive instead of allowing it to
move freely. This does not turn the Morph into runtime state: the Entity returned
by `add_entity` is the object that exposes runtime methods.

### Material selects physical behavior

A Material selects the physical model used for the entity. In this lesson,
`gs.materials.Rigid(...)` selects the rigid solver path and supplies a density.
Rigid materials can also carry friction and other physical parameters.

L02 uses one fixed set of values so that the category is visible in code. It
does not use density or friction changes to draw physical conclusions. L03 will
vary physics parameters under controlled conditions and measure their effects.

### Surface selects appearance

A Surface describes how an entity is rendered. The RGBA tuple in
`gs.surfaces.Default(color=...)` changes appearance, not contact friction. If a
learner wants "the blue box to become slippery," changing its color is the
wrong intervention; the relevant physical parameter belongs to the Material.

This separation is an important debugging habit: first decide whether a problem
is about geometry, physics, or appearance, then inspect the corresponding input.

## The build boundary

### What build does conceptually

Call `scene.build()` only after the entities and any cameras required for the run
have been declared. In the pinned Genesis 1.3.3 implementation, build prepares
the scene for execution by finalizing the declared structure, allocating solver
state, preparing the selected environment layout, compiling required simulation
kernels, resetting the initial state, and building visualization components.

Those implementation details explain why the first build can cost more than a
single later step. They are not permission to depend on private attributes or an
exact internal call order; the public contract is simpler:

- declare topology before build;
- build once; and
- step, control, read state, and render afterward.

### What "topology is fixed" does and does not mean

Genesis 1.3.3 guards `add_entity`, `add_camera`, and `build` with an unbuilt-scene
precondition. Once the scene is built, those topology-changing calls are closed
for that scene.

This does **not** mean every value is immutable after build. Runtime APIs can
change supported state, control targets, and camera poses. Later lessons will do
exactly that. The precise rule is: do not add new scene members through the
pre-build declaration API after build.

### Controlled failure before build

An entity handle exists immediately after `add_entity`, but its dynamic state is
not ready. The lab tests that claim explicitly:

```python
try:
    box.get_pos()
except gs.GenesisException as exc:
    if "not built yet" not in str(exc).lower():
        raise
    print("PASS — state is unavailable before build")
else:
    raise AssertionError("get_pos unexpectedly succeeded before scene.build()")
```

This is a successful test only when the expected Genesis exception and message
are observed. A different exception is an unexpected failure and must propagate.

### Controlled failure after build

The inverse test runs after `scene.build()`:

```python
try:
    scene.add_entity(gs.morphs.Sphere(radius=0.05))
except gs.GenesisException as exc:
    if "already built" not in str(exc).lower():
        raise
    print("PASS — topology declaration is closed after build")
else:
    raise AssertionError("add_entity unexpectedly succeeded after scene.build()")
```

Do not write a broad `except Exception` around either test. Broad exception
handling can make a typo, import problem, or unrelated engine failure look like
evidence for the lifecycle.

## Step, state, and evidence

After build, `scene.step()` advances the simulation by one outer timestep. With
`SimOptions(dt=0.01, substeps=2)`, twenty calls represent twenty outer steps;
substeps are internal subdivisions rather than extra Python calls. L03 will
explain why that distinction matters for stability.

For a single, unbatched rigid entity, the getters used here return PyTorch
tensors with these shapes:

| Getter | Meaning | Unbatched shape |
|---|---|---:|
| `box.get_pos()` | base-link position | `(3,)` |
| `box.get_quat()` | base-link orientation in `(w, x, y, z)` order | `(4,)` |
| `box.get_vel()` | base-link linear velocity | `(3,)` |

The returned device follows the runtime backend. A ROCm-backed PyTorch build can
display an AMD device through PyTorch's CUDA-compatible namespace, so inspect
both the selected Genesis backend and `tensor.device`; do not infer the hardware
from the word `cuda` alone.

For every state used as evidence, check at least:

1. the Python or tensor type;
2. the expected shape;
3. the device;
4. whether all values are finite; and
5. whether the observed change matches the qualitative prediction.

The L02 Box starts above a Plane. After a fixed number of steps, the core check
requires its final height to be below its initial height. It deliberately does
not require one exact final number: absolute contact results can depend on the
pinned engine configuration and are not the concept under test here.

An image can help a human understand the scene, but it does not replace state
checks. Conversely, a plausible state tensor does not prove that a requested
camera image was rendered correctly. Each claim needs evidence of the same kind.

## Backend selection and rendering capability

Two choices that are often conflated are independent:

- the **simulation backend** executes physics and compiled kernels; and
- the **rendering path** produces camera observations.

### Simulation backend modes

The lab uses two backend modes:

- `auto` is the learner-facing default. The current course helper prefers the
  verified AMD ROCm path and selects `gs.amdgpu` when it is available; otherwise
  it selects `gs.cpu`.
- `cpu` explicitly selects `gs.cpu`. It supports learners without a verified
  accelerator and provides the regression path for the lesson's `cpu-ok` claim.

On the reference AMD Radeon AI PRO R9700 machine, `auto` is expected to select
`gs.amdgpu`; the course does not force that machine to use CPU. The `cpu-ok`
label also requires the core lab to pass in a separate forced-CPU clean kernel.

If `auto` selects the verified AMD backend and initialization or execution then
fails, the notebook must expose that failure. Silently retrying on CPU would
hide a compatibility regression. NVIDIA CUDA and other accelerators remain
unverified in the current compatibility record, so device presence alone is not
enough to claim that those paths are supported.

### Rendering is a separate switch

A camera must be added before build, so the notebook decides whether to include
one before creating the final topology:

```python
camera = None
if render_enabled:
    camera = scene.add_camera(
        res=(640, 360),
        pos=(1.1, -1.1, 0.8),
        lookat=(0.0, 0.0, 0.25),
        fov=40,
        GUI=False,
    )
```

When rendering is enabled, camera creation, build, render, and RGB validation
form one test. A rendering exception must fail that test; it must not trigger a
silent fallback.

When rendering is disabled before the run, the notebook prints an explicit
`SKIP: rendering disabled for this run` and draws a simple side view from the
measured initial and final positions. That plot is a state-derived schematic,
not a Genesis camera image. It lets the CPU core path remain useful without
making a false rendering claim.

Selecting `gs.cpu` does not by itself prove rendering is unavailable, and
selecting `gs.amdgpu` does not prove rendering works. The course verifies the
two capabilities separately.

## Lab: one box, one lifecycle

The companion executable notebook is not yet published. This section defines
how to read the experiment and what evidence it must produce without claiming
that the experiment has already run.

### Phase 1 — initialize once

The notebook imports the installed `robo_genesis` package without modifying
`sys.path`, selects `auto` or forced `cpu` mode, reports the actual backend, and
calls `gs.init()` exactly once. Rerun the complete notebook from a clean kernel
when changing its backend or rendering mode.

### Phase 2 — declare the scene

The scene contains:

- one Plane;
- one named dynamic Box with explicit Morph, Material, and Surface; and
- one offscreen camera only when rendering was enabled before build.

At this point `scene.is_built` must be false. The Box handle and its declared
structure can be inspected, while dynamic state getters must reject the
pre-build access.

### Phase 3 — cross the boundary once

The notebook calls `scene.build()` once and verifies that `scene.is_built` is
true. It then inspects the primitive hierarchy and reads the first valid state.

### Phase 4 — step and compare

The notebook records initial position, quaternion, and linear velocity, advances
twenty steps, and records the final state. It verifies shapes and finite values,
then checks the directional prediction `final_z < initial_z` without asserting a
fabricated absolute coordinate.

### Phase 5 — observe honestly

With rendering enabled, the notebook validates the returned RGB array: it must
have image height and width dimensions, three or four channels as supported by
the selected renderer, finite values, and a sensible numeric range for its
dtype. With rendering disabled, it produces only the clearly labelled
state-derived schematic.

### Phase 6 — prove the closed topology

Finally, the notebook attempts one post-build `add_entity` call and accepts only
the expected `GenesisException` containing `already built`.

## Acceptance evidence

The core lab passes only if all of the following are true:

- the installed Genesis version and actual backend are reported;
- no source repository, absolute developer path, or `sys.path` injection is used;
- `scene.is_built` changes from false to true across one build;
- pre-build state access produces the expected, narrowly checked failure;
- the primitive has one link and one collision geom under pinned Genesis 1.3.3;
- position, quaternion, and velocity have the expected unbatched shapes and
  finite values;
- twenty steps produce an observed decrease in Box height;
- post-build topology addition produces the expected, narrowly checked failure;
  and
- the enabled rendering branch validates RGB data, or the disabled branch is
  reported as an explicit skip and produces only a labelled schematic.

Before L02 is marked verified, the same notebook must pass in two clean kernels
on the reference machine: default `auto` must select `gs.amdgpu`, and forced
`cpu` must select `gs.cpu`. The rendering-enabled reference run is additional
evidence and does not turn a GPU into a prerequisite for the core lesson.

## Common failures and diagnosis

### `Genesis hasn't been initialized`

The Scene or another Genesis object was created before `gs.init()`. Restart the
kernel, run initialization once, and then execute cells in order.

### `... is not built yet`

A runtime operation such as a state getter or `scene.step()` ran before
`scene.build()`. Locate the build call; do not suppress the error or invent
placeholder state.

The one pre-build getter in the lab is a controlled negative test. It should be
surrounded only by the narrow assertion shown earlier.

### `Scene is already built`

An entity, camera, or second build was requested after the topology boundary.
Move the declaration before the single build and rerun from a clean kernel.

The one post-build `add_entity` call in the lab is again a controlled negative
test, not an example of normal scene construction.

### Unexpected state shape

First print the getter name, type, shape, and device. This lesson uses the
default unbatched scene, so a leading environment dimension is unexpected. L08
will deliberately introduce batched environments and explain their shapes.

### Non-finite or implausible state

Check that initialization and build succeeded, inspect the first state before
stepping, then locate the first step that becomes non-finite. Do not diagnose
the problem from the final image alone. L03 will add physics-focused diagnostics
for contact and stability.

### Rendering failure

Confirm whether rendering was enabled before build. If it was disabled, the
absence of a camera image is an explicit skip. If it was enabled, preserve the
actual exception and environment details; do not catch it broadly and relabel it
as a successful fallback.

### Rerunning `gs.init()` in one kernel

Backend and rendering mode changes require a fresh process-level initialization.
Restart the kernel and run the notebook top to bottom instead of executing the
initialization cell repeatedly in hidden state.

## Checkpoints and exercises

### Concept checkpoints

Answer these before looking back at the tables:

1. Which side of `scene.build()` should `scene.add_camera(...)` appear on, and
   why?
2. To make a blue box slippery, should you change its Surface color or its
   Material configuration?
3. Why can an entity handle exist while `get_pos()` is still invalid?
4. Does "topology is fixed after build" mean that no runtime state can change?
5. If a tensor displays `cuda:0` on a ROCm system, what additional evidence tells
   you which backend is actually active?

### Hands-on exercise

Add a fixed marker before the build call:

```python
marker = scene.add_entity(
    morph=gs.morphs.Box(
        size=(0.06, 0.06, 0.06),
        pos=(0.18, 0.0, 0.03),
        fixed=True,
    ),
    surface=gs.surfaces.Default(color=(0.20, 0.80, 0.35, 1.0)),
    name="fixed_marker",
)
```

Then restart the kernel and rerun the entire notebook. Verify the marker through
object inspection and, when rendering is enabled, through the image. Explain
which arguments belong to the Morph and which belong to the Surface.

As a code-reading extension, open `src/robo_genesis/build_scene.py` and locate
the Scene construction, entity declarations, camera declarations, build call,
and post-build configuration. Do not run the full grasping scene yet; the goal
is only to recognize the lifecycle pattern that L06 will use.

## Summary and connection to L03

- A Scene description becomes executable runtime state at `scene.build()`.
- Entities and cameras are declared before build; stepping, state reads, and
  rendering happen afterward.
- A rigid primitive exposes the hierarchy
  `RigidEntity → RigidLink → RigidGeom`.
- Morph, Material, and Surface separate geometry and initial pose, physical
  behavior, and rendered appearance.
- State shape, device, finiteness, and change are stronger debugging evidence
  than "no exception" or a plausible-looking image.
- `cpu-ok` guarantees a CPU fallback; it does not force a verified AMD machine
  to abandon `gs.amdgpu`.
- Simulation backend and rendering capability are verified independently.

L02 kept the physics configuration fixed so that lifecycle was the only subject
under test. L03 will deliberately vary timestep, substeps, contact, and friction
and measure how those choices affect stable rigid-body simulation.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the version pinned by this course.
- [Genesis World official repository](https://github.com/Genesis-Embodied-AI/genesis-world)
  — implementation source for `Scene`, entity, Morph, Material, Surface, and
  camera behavior. API claims in this lesson were checked against the pinned
  1.3.3 package rather than inferred from an unpinned branch.
