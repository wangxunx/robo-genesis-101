---
lesson: L03
slug: rigid-body-physics-and-stable-simulation
locale: en
title: "Rigid-Body Physics and Stable Simulation"
duration_minutes: 90
hardware: cpu-ok
status: planned
---

# L03 · Rigid-Body Physics and Stable Simulation

> **Course status:** L03 is still `planned`. The complete bilingual lesson and
> executable notebook have not been published yet.

## Where this lesson fits

L02 followed one Box through declaration, build, stepping, and observation. It
kept the physics configuration fixed so that the simulation lifecycle was the
only subject under test. L03 now changes selected parameters deliberately and
asks a harder question:

**When a rigid body falls onto or slides across a table, which observations come
from the physical model, which come from numerical discretization, and what
evidence supports a careful claim about stability?**

A plausible final image is not enough. A cube may end near the tabletop after
briefly penetrating it, losing contact, rebounding, or oscillating. Conversely,
a changing contact-point count need not mean that the cube visibly left the
surface. This lesson therefore treats trajectories and explicitly defined
metrics as the primary evidence.

Before starting, you should be able to:

- run the course notebooks from a clean kernel and identify the selected
  Genesis backend;
- read the sequence
  `gs.init → Scene → add_entity → build → step → state`;
- distinguish Morph, Material, and Surface configuration; and
- read an unbatched rigid body's position and linear velocity.

No robot model, inverse kinematics, dataset, or learning policy is required.
The experiments use only built-in Box primitives and run on CPU. A verified AMD
GPU can accelerate the same work, but it is not a prerequisite.

## Learning objectives

By the end of L03, you should be able to:

1. classify geometry, density, friction, `dt`, substeps, sampling rules, and
   color as physical, numerical, observational, or visual information;
2. calculate simulated duration, internal timestep, external sample count, and
   internal update count for a Genesis run;
3. design a controlled comparison that changes one factor while preserving the
   same scene, seed, initial state, and simulated duration;
4. interpret a falling-cube experiment using height, velocity, contacts,
   geometric clearance, a penetration proxy, and settling error together;
5. explain how Genesis 1.3.3 combines the two sides of a frictional contact and
   use position and velocity traces to compare stopping distance;
6. distinguish a measured observation from a solver-internal quantity or a
   universal physics claim; and
7. diagnose missing contact, non-finite state, unexpected penetration, failure
   to stop, and CPU/GPU disagreement in a systematic order.

## Four layers of an experiment

A controlled simulation experiment is easier to reason about when its inputs
and evidence are separated into four layers.

| Layer | Examples in L03 | Question it answers |
|---|---|---|
| Physical | geometry, `rho`, friction, gravity, initial pose and velocity | What physical system did we ask the engine to model? |
| Numerical | `dt`, substeps, internal timestep | How finely did the engine approximate its evolution? |
| Observational | external sample times, stopping threshold, hold interval, plot range | How did we turn discrete records into evidence? |
| Visual | Surface color, legend color, schematic style | How did we identify and present objects? |

The first three layers affect the conclusion or how strongly it is supported.
The visual layer helps a reader distinguish objects, but it does not change
their physical behavior. Painting a cube blue cannot make it more slippery.

`rho` belongs to the physical layer. For a primitive with fixed geometry it
affects mass and inertia. It does not imply that two objects with different
densities fall at different gravitational accelerations in this scene. Density
is held constant in the main comparisons so that it cannot confound contact or
friction effects.

A useful evidence chain is:

```text
physical configuration + numerical configuration
                       ↓
       fixed seed and equal simulated duration
                       ↓
    sampled state + contact + geometric evidence
                       ↓
        one-factor comparison with a bounded claim
```

If two cases change friction, timestep, and initial speed together, their
different outcomes cannot identify which change caused the difference.

## Time discretization: three quantities, three roles

Genesis exposes the outer simulation timestep and the number of internal
substeps through `SimOptions`:

```python
from robo_genesis.course_utils import to_numpy

scene = gs.Scene(
    sim_options=gs.options.SimOptions(dt=0.01, substeps=2),
    rigid_options=gs.options.RigidOptions(enable_collision=True),
    show_viewer=False,
)
```

For this configuration:

```text
outer dt       = 0.01 s
substeps       = 2
internal dt    = dt / substeps = 0.005 s
```

The course uses `substep_dt` as a descriptive name for that internal timestep.
It is not a third independent input.

### `dt`: the external boundary

One call to `scene.step()` advances `dt` seconds of simulated time. State read
once after each call is therefore sampled every `dt` seconds. Later, when L04
adds joint control and L05 adds observations, `dt` will also determine how often
Python can update a target or read a sensor in the straightforward one-step
loop.

For `n_steps` outer calls:

```text
simulated_time = n_steps × dt
external_samples = n_steps              # when recording once after every step
```

This is why two timing configurations must be compared over equal simulated
duration, not merely equal step count. Running 100 steps at `dt=0.01` covers
1 second; 100 steps at `dt=0.02` covers 2 seconds.

### `substeps`: internal resolution

Within one outer step, Genesis 1.3.3 executes the configured number of internal
substeps. The internal timestep and update count are:

```text
substep_dt = dt / substeps
internal_updates = n_steps × substeps
```

Increasing substeps at fixed `dt` gives the solver a finer internal temporal
resolution while leaving the Python observation and command cadence unchanged.
It also requires more internal work. It is therefore a numerical tradeoff, not
a free guarantee that every stability diagnostic improves monotonically.

### Same internal timestep does not mean the same experiment interface

Consider two configurations:

| Case | `dt` | substeps | `substep_dt` | samples over 1.5 s |
|---|---:|---:|---:|---:|
| N1 | 0.01 s | 1 | 0.010 s | 150 |
| N4 | 0.02 s | 2 | 0.010 s | 75 |

They have the same internal timestep and the same number of internal updates
over 1.5 seconds. They do not have the same external sampling frequency. An N1
sample at 0.01 s has no N4 counterpart; trajectory differences should be
computed only at shared times such as 0.02, 0.04, and 0.06 s.

This distinction will matter even more once actions and sensor reads occur at
outer-step boundaries. L03 establishes the timing vocabulary; L04 applies it to
control.

## Contact is a numerical approximation

Two rigid meshes should not occupy the same physical space, but a discrete
solver does not observe and resolve every instant continuously. It advances a
finite timestep, detects contact, and applies constraints at its internal
resolution. A small measured overlap can therefore appear even in a useful
simulation.

That does not mean penetration should be ignored. It means the measurement and
its limits must be stated precisely.

### A geometry-based penetration proxy

The falling-cube experiment uses a level, fixed table and an initially aligned
cube. Its ideal resting center height is

```text
expected_center_z
    = table_center_z + table_height / 2 + cube_size / 2
```

From states sampled after each outer step, the notebook computes

```text
penetration_proxy
    = max(0, expected_center_z - minimum_sampled_center_z)
```

This value is useful for comparing the four controlled cases, but it is not the
solver's exact continuous-time penetration depth:

- the trajectory is observed only once per outer `dt`;
- the deepest event between samples may be missed;
- the formula assumes the cube remains close to the experiment's intended
  aligned orientation; and
- it is derived from center height rather than read from solver-internal contact
  data.

Call it a penetration proxy, not “the penetration.”

### Contact count is supporting evidence

The runner asks for contacts between the dynamic cube and the table:

```python
contacts = cube.get_contacts(with_entity=table)
contact_count = int(contacts["position"].shape[0])
```

Contact count describes the contact manifold reported at that sampled instant.
It may change as corners, faces, or solver contacts change. A zero count after
first contact is not sufficient proof that the cube left the table.

The experiment therefore also computes bottom clearance:

```text
clearance = cube_center_z - cube_size / 2 - table_top_z
```

A sample counts as observed geometric separation only when contact count is zero
and clearance is greater than a small declared tolerance. Even then, the
reported duration is quantized by the outer `dt`.

### A multi-evidence definition of stability

L03 does not reduce “stable simulation” to one threshold. Read these signals
together:

| Evidence | What it measures | What it cannot prove alone |
|---|---|---|
| finite `z` and `vz` histories | the recorded state remains numerically usable | correct contact behavior |
| penetration proxy | lowest sampled center relative to ideal rest height | exact continuous penetration |
| contact presence | whether a contact was reported at an outer sample | true separation or rebound |
| geometric separation | no contact plus positive bottom clearance | events shorter than `dt` |
| upward velocity | upward motion after contact | separation without clearance evidence |
| tail settling error | mean final-height bias over a declared window | absence of oscillation hidden by the mean |
| full trajectory | transient penetration, rebound, and settling pattern | behavior outside the simulated duration |

A credible conclusion states which of these were observed and over what time
window. “The final frame looked fine” is not such a conclusion.

## Part A: a 2×2 contact experiment

Part A drops the same cube onto the same fixed table for 1.5 seconds. Geometry,
density, friction, gravity, initial pose, seed, and precision stay fixed. Only
`dt` and substeps vary:

| Case | `dt` | substeps | `substep_dt` | Purpose |
|---|---:|---:|---:|---|
| N1 | 0.01 s | 1 | 0.010 s | finer outer cadence, baseline internal resolution |
| N2 | 0.01 s | 2 | 0.005 s | isolate more substeps at fixed `dt` |
| N3 | 0.02 s | 1 | 0.020 s | coarsest internal resolution |
| N4 | 0.02 s | 2 | 0.010 s | isolate more substeps and match N1 internal resolution |

Before running the experiment, predict:

1. Which cases have 150 outer samples, and which have 75?
2. At fixed `dt`, what direction do you expect the penetration proxy to move
   when substeps increase?
3. Should N1 and N4 have similar state at their shared sample times?
4. Would equal `substep_dt` make their full arrays the same length?
5. If one case has a smaller penetration proxy but a brief geometric separation,
   can one number decide which case is “more stable”?

### The relevant Genesis operations

The reusable runner owns scene construction and stepping. Its essential
physical path is intentionally small:

```python
scene = gs.Scene(
    sim_options=gs.options.SimOptions(dt=dt, substeps=substeps),
    rigid_options=gs.options.RigidOptions(enable_collision=True),
    show_viewer=False,
)

table = scene.add_entity(
    gs.morphs.Box(size=(0.9, 0.6, 0.05), pos=(0.35, 0.0, 0.70), fixed=True),
    material=gs.materials.Rigid(friction=0.8),
)
cube = scene.add_entity(
    gs.morphs.Box(size=(0.08, 0.08, 0.08), pos=(0.35, 0.0, 1.0)),
    material=gs.materials.Rigid(rho=500.0, friction=0.5),
)

scene.build()
for sample_index in range(n_steps):
    scene.step()
    z[sample_index] = float(to_numpy(cube.get_pos()).reshape(-1)[2])
    vz[sample_index] = float(to_numpy(cube.get_vel()).reshape(-1)[2])
    contact_count[sample_index] = int(cube.get_contacts(
        with_entity=table
    )["position"].shape[0])
```

The notebook exposes every case specification, subprocess command, saved field,
metric calculation, and plot. The package keeps one reusable copy of scene
construction so the English and Chinese notebooks cannot drift into different
physics implementations.

### Reading the comparison in the right order

Use this sequence after all four cases finish:

1. Verify the actual backend, `dt`, substeps, `substep_dt`, duration, and sample
   count recorded for every case.
2. Check array shapes and finite values before interpreting any plot.
3. Compare N1 with N2 and N3 with N4. Each pair fixes the outer `dt` and changes
   only internal resolution.
4. Compare N1 with N4 only at shared sample times. Their equal `substep_dt`
   tests whether the uncontrolled rigid-body trajectory agrees while their
   different outer sampling remains visible.
5. Read height, velocity, contact, clearance, and tail metrics together.
6. State the result as an observation from this scene and pinned engine version,
   not as a theorem that more substeps always fix every contact problem.

## Friction belongs to a contact pair

`gs.materials.Rigid(friction=...)` assigns a friction coefficient to an
entity's rigid geometry. Motion at a contact depends on both geometries, not on
the moving object in isolation.

For the rigid-contact implementation pinned by this course, Genesis 1.3.3 uses
the larger of the two geometry-side sliding-friction values after any runtime
friction ratios have been applied. With the default ratio of one, the rule in
this experiment is:

```text
effective_pair_friction = max(table_friction, cube_friction)
```

This is a Genesis 1.3.3 implementation rule, not a universal law shared by every
physics engine. If the engine version changes, the rule must be checked again.
L10 will later use runtime friction ratios for domain randomization; the same
pair rule explains why changing only one contact surface may have no effect.

The baseline values make that behavior testable:

| Lane | table friction | cube friction | effective pair value |
|---|---:|---:|---:|
| low-friction cube | 0.50 | 0.10 | 0.50 |
| high-friction cube | 0.50 | 0.80 | 0.80 |

If the table is changed from 0.50 to 0.30 while both cubes remain unchanged:

| Lane | modified table | cube friction | effective pair value |
|---|---:|---:|---:|
| low-friction cube | 0.30 | 0.10 | 0.30 |
| high-friction cube | 0.30 | 0.80 | 0.80 |

The low-friction lane should therefore change, while the high-friction lane is
a useful near-unchanged control. The experiment tests that directional
prediction; it does not require one hard-coded stopping distance on every
supported machine.

Surface color remains outside this calculation. Orange and blue identify the
lanes in plots. Swapping those colors must not swap their physical results.

## Part B: friction and sustained stopping distance

Part B uses one table and two equal cubes. It fixes geometry, density, pose,
`dt=0.01`, substeps=2, initial horizontal speed, and measurement duration. The
only baseline difference is the two cube-side friction values.

### Settle before starting the measurement

The cubes begin at their geometric resting height, but the solver still needs
to establish a contact manifold. The runner advances a short settling interval
before defining measurement time zero. Only then does it give both free bodies
the same horizontal velocity:

```python
for _ in range(settle_steps):
    scene.step()

initial_velocity = np.array([2.0, 0.0, 0.0, 0.0, 0.0, 0.0])
cube_low.set_dofs_velocity(initial_velocity)
cube_high.set_dofs_velocity(initial_velocity)
```

Without the settling phase, an initial contact transient would be mixed into
the sliding comparison.

### Define “stopped” before inspecting the result

A single velocity sample close to zero may be a crossing, oscillation, or
numerical fluctuation. The lab therefore declares a speed threshold and a hold
interval before running. A cube is considered stopped at the first sample that
starts a complete interval satisfying

```text
abs(vx) < stop_speed
```

for the entire hold duration. If no such interval exists, stop time and stop
distance remain unavailable rather than being invented from the final sample.

For a detected stop at index `i`:

```text
stop_time = time[i]
stop_distance = x[i] - x[0]
```

The runner also records angular velocity. A free cube can convert translational
motion into rotation as friction acts at the contact. Consequently, stop time
and stopping distance need not rank two cases in the same intuitive order. Read
the full `x(t)`, `vx(t)`, and angular-velocity histories, and use stopping
distance as the main comparison requested by this experiment.

Do not invert a textbook point-mass stopping formula to estimate Genesis's
friction coefficient from this one trajectory. The simulated object is a free
rigid body with rotational dynamics and a discrete contact solver.

### The one-factor table modification

After the baseline, the hands-on comparison changes only table friction from
0.50 to 0.30. Before running it, predict:

- which lane's effective pair value changes;
- which cube should travel farther;
- which lane should remain nearly unchanged; and
- why changing color alone would affect neither result.

The comparison is valid only if cube properties, numerical settings, settling
duration, initial velocity, seed, and measurement duration remain fixed.

## Companion notebook workflow

The companion notebook, when published, follows this sequence:

1. report versions, requested backend mode, actual child-process backend, and
   output directory;
2. display the N1–N4 configurations and collect predictions;
3. run each contact configuration in an isolated process;
4. validate and load the structured `.npz` results;
5. display a metric table and aligned height, velocity, and contact plots;
6. run the baseline two-lane friction experiment;
7. compare displacement, velocity, angular velocity, and sustained stopping;
8. change only table friction to 0.30 and repeat the comparison; and
9. print either `L03 CHECK: PASSED` or the specific failed condition.

Genesis initialization is process-wide. Separate processes allow multiple
`dt`/substeps configurations to run from one notebook without asking you to
restart the kernel between cases. This is an execution detail, not the subject
of the lesson: focus on the configuration passed to each process and the
evidence returned from it.

The core path is state-based and does not require camera rendering. Initial and
final schematics are drawn from measured positions, while trajectory plots use
the saved arrays. They must be labelled as state-derived figures, not Genesis
camera images.

The learner-facing default uses the verified AMD backend when it is available
and otherwise uses CPU. The explicit CPU mode provides the course's `cpu-ok`
path. If an AMD run is selected and fails, the failure must remain visible; a
silent retry on CPU would invalidate the backend claim.

## How to know the lab worked

The lab's final result should establish all of the following without relying on
one exact set of floating-point values:

- every child process reports its requested mode and actual backend and exits
  successfully;
- all required arrays have the expected length and contain finite values;
- every contact case covers 1.5 seconds, so sample count changes with `dt`;
- computed `substep_dt` and internal update counts match the case table;
- the cube contacts the table in every case and does not pass through it;
- at fixed `dt`, the finer internal timestep reduces the penetration proxy for
  this pinned scene;
- N1 and N4 agree within the reviewed tolerance at shared sample times while
  retaining different external sample counts;
- the interpretation uses trajectory, contact, clearance, and settling evidence
  rather than declaring one metric to be “stability”;
- in the baseline friction run, the low-effective-friction lane travels farther
  before sustained stopping than the high-effective-friction lane;
- lowering table friction changes the low-friction lane in the predicted
  direction while leaving the high-friction lane nearly unchanged; and
- generated `.npz` files and figures stay in the configured output directory,
  outside version control.

CPU and AMD results may differ slightly. A tolerance must describe an accepted
numerical range; it must not be widened after seeing a failure simply to make
the check pass. Preserve the configuration and evidence before investigating a
backend discrepancy.

## Common failures and diagnosis

### The cases cover different simulated durations

Check `n_steps × dt`, not just `n_steps`. Recompute the step count from one
shared duration and require the product to match it.

### Too many inputs changed at once

Print the full case dictionaries and compare them field by field. For N1→N2 or
N3→N4, only substeps should change. For the table-friction exercise, only table
friction should change.

### `substep_dt` matches, but array lengths do not

This is expected for N1 and N4. Their internal timestep matches, while their
outer `dt` values and sample counts differ. Align common timestamps before
computing a trajectory difference.

### No contact is reported

First check the table top, cube bottom, initial height, gravity, total duration,
and `enable_collision=True`. Then inspect the height trajectory to determine
whether the cube reached the table. Do not immediately increase tolerances.

### Contact count briefly becomes zero

Inspect bottom clearance and vertical velocity at the same sample. Count it as
observed separation only when both the contact condition and geometric
condition support that interpretation.

### State becomes non-finite or the cube passes through the table

Find the first bad sample, record its case and backend, then compare its
`substep_dt` with the successful cases. Preserve stdout and stderr from the
child process. Do not catch the failure and substitute a successful case.

### A cube never satisfies the stop rule

Check the measurement duration, speed threshold, hold duration, contact
presence, and complete velocity trace. Report “not stopped within the measured
window” instead of using final displacement as a fabricated stop distance.

### Changing one friction value has no effect

Compute both effective pair values using the Genesis 1.3.3 `max` rule. The
unchanged side of the pair may already dominate. This is why the experiment
changes table friction from 0.50 to 0.30 rather than assuming every single-side
edit must alter motion.

### A requested AMD run reports CPU

Inspect PyTorch's HIP build information, device visibility, the requested mode,
and the backend printed by the child process. Do not accept CPU output as proof
of an AMD run. Remember that ROCm devices appear through PyTorch's `cuda`
namespace; the namespace alone does not identify NVIDIA hardware.

### Results differ slightly between CPU and AMD

Confirm that seed, precision, engine version, case configuration, and duration
match. Compare relationships and reviewed tolerances before comparing printed
decimal strings. If the qualitative relation changes, keep both result sets and
investigate rather than hiding one.

## Checkpoints and exercises

### Concept checkpoints

Answer these before looking back at the tables:

1. With `dt=0.02` and substeps=2, what are `substep_dt`, the number of outer
   samples over 1.5 seconds, and the number of internal updates?
2. Why is it invalid to run every timing case for the same number of outer
   steps?
3. Why should N1 and N4 be compared only at shared sample times?
4. Can `contact_count == 0` alone prove that the cube rebounded?
5. With table friction 0.50 and cube friction 0.10, what pair value does Genesis
   1.3.3 use in this experiment?
6. Why does lowering the table to 0.30 affect the low-friction lane but not the
   high-friction cube whose coefficient is 0.80?
7. Why does swapping orange and blue Surface colors leave the trajectories
   unchanged?
8. Why does one velocity sample below the threshold not establish sustained
   stopping?

### Hands-on exercise

Run the baseline friction comparison, then change only table friction from 0.50
to 0.30. Before the second run, write down the predicted effective pair values
and the expected direction of each stopping-distance change. Afterward:

1. verify from the printed configuration that no other input changed;
2. compare the full `vx(t)` curves, not only their final values;
3. report the sustained stop distance for each lane, or explicitly report that
   a lane did not stop within the measurement window;
4. explain whether each prediction was supported; and
5. state the engine version and parameter range to which your conclusion
   applies.

As an extension, add a fifth contact case with `dt=0.01` and substeps=4. Keep
the 1.5-second duration and every physical parameter unchanged. Predict what
may improve, what is not guaranteed to improve, and what extra computational
work the configuration requires. Treat the result as one additional data point,
not a universal convergence proof.

## Summary and connections

- Physical parameters describe the modeled system; numerical parameters define
  its time discretization; observation rules define the evidence; visual
  parameters only affect presentation.
- `dt` is the outer simulation, command, and sampling boundary. Substeps refine
  the work inside that boundary, with `substep_dt = dt / substeps`.
- Fair numerical comparisons use equal simulated duration and align trajectories
  at shared sample times.
- Contact stability requires multiple signals. Penetration proxies, contact
  counts, clearance, velocity, settling error, and complete trajectories each
  have limits.
- Genesis 1.3.3 uses the larger side of a rigid contact pair for sliding
  friction after runtime ratios. This behavior is version-specific.
- A sustained stop needs a declared speed threshold and hold interval. A free
  cube can rotate, so read position, linear velocity, and angular velocity
  together.
- Conclusions should name the scene, engine version, backend, configuration,
  and measurement window that support them.

L04 will connect the outer timestep to joint-command cadence and compare target
state with actual robot motion. L06 will apply pairwise contact reasoning to the
table, object, and gripper. L10 will revisit friction through runtime domain
randomization and show why all relevant contact surfaces must be considered.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `SimOptions` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/options/solvers.py)
  — definitions of `dt` and substeps used for the timing contract.
- [Genesis 1.3.3 rigid-entity friction API](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — the documented maximum rule for the two sides of a contact.
- [Genesis 1.3.3 rigid-contact implementation](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/solvers/rigid/collider/contact.py)
  — the version-pinned implementation that applies friction ratios and forms
  the contact-pair value.
