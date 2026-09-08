---
lesson: L08
slug: demonstration-acquisition-and-scripted-experts
locale: en
title: "Demonstration Acquisition and Scripted Experts"
duration_minutes: 120
hardware: gpu-recommended
status: planned
---

# L08 · Demonstration Acquisition and Scripted Experts

> **Course status:** the English lecture is complete. The Chinese adaptation,
> companion notebook, and clean-kernel evidence are still pending, so L08
> remains `planned`.

## Where this lesson fits

L07 produced a settled tabletop scene with named handles for Franka, a banana,
and a bowl. L08 now gives that scene an expert that can carry out one complete
pick-and-place task. The result is a rollout with a clear task outcome and a
time-ordered stream of commanded actions and measured robot states.

The lesson follows one chain:

```text
demonstration source
  → task and grasp contract
  → seven-phase scripted expert
  → commanded-action / measured-state trace
  → bowl-containment result
```

This is the bridge from a task scene to data generation. L09 will define
sampling, time alignment, image encoding, the LeRobot schema, and persistent
episodes. L11 will introduce domain randomization. Those mechanisms are not
part of the L08 rollout.

Before starting, you should be able to:

- identify Franka's seven arm DOFs and two finger DOFs;
- distinguish a joint-position target from measured joint state;
- read a world-frame end-effector position and quaternion;
- explain what IK returns and why the result still has to be executed through
  control and simulation steps;
- inspect object positions and axis-aligned bounding boxes (AABBs); and
- build the fixed L07 task scene through `build_scene()`.

## Learning objectives

By the end of L08, you should be able to:

1. compare common demonstration-acquisition routes by cost, scale, task
   coverage, native signal, and adaptation needs, then explain why this task
   uses a scripted expert;
2. express the banana-to-bowl task with a `TaskSpec`, a `GraspProfile`, and a
   seven-phase sequence of end-effector targets, gripper commands, and motion
   primitives;
3. explain the roles of arm position control, finger force control, and bounded
   joint-target increments, while distinguishing commanded action from
   measured state; and
4. execute one scripted rollout, interpret its action/state trace, and use the
   bowl-containment test to decide whether the task completed.

## A focused 120-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–25 min | Acquisition methods and recent hybrid directions | Compare six routes and justify a source for a task |
| 25–45 min | `TaskSpec`, `GraspProfile`, and grasp geometry | Turn a task into explicit object, target, pose, and grip parameters |
| 45–75 min | Seven-phase expert and control roles | Explain each phase, primitive, and controller role |
| 75–105 min | One fixed banana-to-bowl rollout | Produce an in-memory action/state trace and optional phase views |
| 105–120 min | Outcome diagnosis, one-variable exercise, and L09 handoff | Interpret containment and the joint-target schedule |

The acquisition survey is deliberately longer than a list of method names. It
shows why modern data pipelines often combine human collection, simulation,
automatic augmentation, and heterogeneous datasets. The remainder of the
lesson then studies one route deeply enough to execute and inspect it.

## Read the lesson in two parts

### Part 1 — choose a demonstration source

[Demonstration Acquisition Methods](./l08-demonstration-acquisition-methods.md)
compares:

- teleoperation;
- kinesthetic teaching;
- scripted experts;
- learned teachers with privileged simulation state;
- automatic augmentation from seed demonstrations; and
- human-video transfer and retargeting.

The comparison separates each route's native signal from the adapter needed
to produce robot-learning demonstrations. It then connects recent work in
lower-cost interfaces, in-the-wild collection, cross-embodiment aggregation,
simulation scaling, and egocentric video without pretending that these sources
are interchangeable.

### Part 2 — build and inspect one scripted expert

[The Scripted Pick-and-Place Expert](./l08-scripted-pick-and-place-expert.md)
develops the concrete expert used in this repository:

```text
pregrasp → descend → grasp → lift → transport → release → retreat
```

It connects `TaskSpec` and `GraspProfile` to top-down grasp geometry, explains
why the arm and fingers use different control modes, derives the bounded
joint-target schedule used while carrying an object, and finishes with a
two-part containment check.

## The experiment contract

The companion notebook will build one fixed `011_banana → 024_bowl` task and
call the shared expert once. It will keep two aligned arrays in memory:

```text
measured robot state : (T, 9)
commanded action     : (T, 9)
```

The first seven values describe the arm joints and the final two values the
fingers. The two arrays have the same width, but they answer different
questions: the action is what the expert requested; the state is what the
simulated robot had reached when that sample was observed.

The notebook defaults to `ROBO_GENESIS_RENDER=1`, so the normal learning path
creates a world camera and shows a start image plus one image after each expert
phase. Learners without a working rendering stack can explicitly set the value
to `0`; the full rollout, numerical plots, trace, and containment checks still
run without a camera.

## One task, one result

L08 intentionally avoids a large benchmark. The core experiment answers a
smaller, useful question:

> Did this fixed expert rollout carry the banana into the bowl, and can we
> explain that answer from its commands, measured state, and final geometry?

The outcome check combines horizontal placement within the bowl opening with
the banana's AABB bottom lying below the bowl rim. A single successful rollout
is one completed demonstration; a success-rate claim would require a separate
multi-seed protocol.

## Continue

Start with [Demonstration Acquisition Methods](./l08-demonstration-acquisition-methods.md),
then continue to [The Scripted Pick-and-Place Expert](./l08-scripted-pick-and-place-expert.md).
