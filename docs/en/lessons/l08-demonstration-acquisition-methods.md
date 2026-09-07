# L08 · Demonstration Acquisition Methods

> **Part 1 of L08:** this page compares where robot demonstrations come from.
> Return to the [lesson overview](./l08-demonstration-acquisition-and-scripted-experts.md)
> or continue to the [scripted expert](./l08-scripted-pick-and-place-expert.md).

## A demonstration is produced, not merely found

A robot-learning demonstration is a time-ordered example of behavior for a
task. It usually connects observations, actions, task context, and an outcome,
but the device or process used to collect it may produce something quite
different. A teleoperator produces controller commands. Kinesthetic teaching
produces robot motion under physical guidance. A human video may contain no
robot action at all.

The important first question is therefore not “Which method makes the best
dataset?” It is:

> What signal does this method produce, what does it cost to collect, and what
> must happen before a robot can learn from it?

The routes below are complementary rather than mutually exclusive.

![Six demonstration sources pass through source-specific adapters before they share a task, observation, action, and outcome interface.](/diagrams/l08-acquisition-overview.svg)

*Course-authored schematic. The shared interface is a conceptual handoff to
L09, not a claim that the native sources already have one schema.*

## Compare native signals before formats

| Route | Who or what produces behavior? | Native signal | Necessary adaptation |
|---|---|---|---|
| Teleoperation | A person operates a leader arm, handheld device, VR interface, or other controller | Interface commands, robot state, and sensor observations | Calibrate the control mapping; synchronize commands and observations |
| Kinesthetic teaching | A person physically guides a robot | Joint or end-effector trajectory plus available sensor readings | Convert compliant teaching motion into a safe, replayable action representation |
| Scripted expert | A program selects targets and motion primitives from task state | Reproducible commands, simulator state, task identity, and computable outcome | Make phase logic, failure handling, and recorder hooks explicit |
| Privileged learned teacher | A learned controller acts with simulator-only state or rewards | Teacher actions and privileged simulation state | Restrict the learner's observations; distill or recollect executable actions |
| Automatic augmentation | A system transforms and replays seed demonstrations | Candidate trajectories under changed objects, poses, or scenes | Re-execute candidates and reject physically invalid or unsuccessful episodes |
| Human-video transfer | A person acts in ordinary or instrumented video | Images and estimated hand, body, or object motion | Recover geometry, map embodiments, infer robot actions, and test executability |

This separation prevents a common category error. A camera video, a Cartesian
leader trajectory, and a nine-joint command vector may all describe “the same
task,” but they cannot be concatenated into one training table without a
representation and alignment step.

## Six acquisition routes

### Teleoperation: direct human task knowledge

In teleoperation, a person closes the control loop through an interface. A
leader arm can make joint-space correspondence intuitive; VR, motion capture,
or handheld interfaces can reduce mechanical coupling; whole-body interfaces
can include base and bimanual motion. ALOHA and GELLO are well-known examples
of the lower-cost hardware direction, while Mobile ALOHA extends the idea to
mobile bimanual tasks.

The main advantage is behavioral relevance: the operator can react to contact,
recover from small mistakes, and demonstrate a strategy in the real task
environment. The main costs are operator time, calibration, fatigue, variable
skill, and the need to audit synchronization and failed demonstrations. A
better interface can improve collection quality, but it does not remove those
data-quality questions.

Use teleoperation when human judgment and contact-rich recovery matter more
than fully automatic scale, or when a small number of high-value examples can
seed later collection stages.

### Kinesthetic teaching: guide the robot itself

Kinesthetic teaching lets a person move a compliant or backdrivable robot
through the desired trajectory. It can be the shortest path from an idea to a
few robot-native trajectories because the teacher and learner share the same
embodiment.

That convenience brings constraints. The robot must support safe physical
guidance; the teacher may not reproduce the forces or velocities needed during
autonomous execution; and collecting many diverse episodes remains labor
intensive. It is strongest for quick trajectory teaching in a bounded
workspace, not as a universal path to internet-scale data.

### Scripted experts: encode task structure directly

A scripted expert converts known task state into a sequence of goals and
motion primitives. In simulation it is reproducible, easy to instrument, and
cheap to rerun after the script exists. Every phase can emit a label and every
episode can be checked by a programmatic success predicate.

Its weakness is the knowledge it assumes. A script may depend on object poses,
task-specific grasp profiles, or simulator state unavailable to a deployed
policy. Rules that work for a structured pick-and-place task can become brittle
under visual ambiguity, deformable objects, unmodeled contact, or long-horizon
recovery.

Use a scripted expert when geometry and success are explicit and the goal is a
clear, reproducible starting point. That is exactly the L08 setting.

### Privileged learned teachers: automate richer behavior

A reinforcement-learning or model-based teacher can use simulator state,
rewards, and many parallel trials to acquire behavior that would be awkward to
write as a fixed state machine. Once trained, the teacher can generate many
rollouts across controlled variations.

The automation is not free: reward and environment design, training compute,
teacher validation, and distribution coverage all become part of acquisition.
If the teacher sees privileged state, its action can supervise a student, but
the student must still act from the observations available at deployment.

This route is attractive when a fixed script is too brittle but simulation can
provide reliable state, objectives, and repeatable trials.

### Automatic augmentation: scale trusted seeds

Systems such as MimicGen transform pieces of successful demonstrations into
new scene configurations, then execute the generated trajectory in simulation
to obtain additional episodes. The important word is *execute*: a transformed
trajectory is only a candidate until contact and task outcome have been
checked.

Augmentation can expand object-pose and scene coverage without asking a human
to demonstrate every combination. Its coverage is still shaped by the seed
demonstrations, the transformation assumptions, and the task segments that can
be reused. Poor seeds or invalid transformations can scale failure just as
efficiently as success.

Use augmentation when a small set of demonstrations already captures the task
structure and the environment supports automatic replay and outcome checking.

### Human-video transfer: broad behavior, indirect control

Ordinary human video offers enormous diversity in objects, environments, and
task semantics. Instrumented first-person capture, as explored by work such as
UMI and EgoMimic, narrows the gap by estimating trajectories or using an
interface whose motion can be related to a robot end effector.

The remaining embodiment gap is fundamental. Pixels do not directly specify a
robot's joint command, gripper force, timing, or collision-free path. Viewpoint,
scale, occlusion, hand morphology, and contact all affect the conversion. A
retargeted motion must therefore be checked for robot reachability and physical
execution before it becomes a robot demonstration.

Human video is especially useful for task diversity, representation learning,
and high-level motion proposals. Robot-native data remains important for
grounding those proposals in an embodiment and control interface.

## Advantages, limits, and suitable uses

| Route | Main advantage | Main limitation | Strong fit |
|---|---|---|---|
| Teleoperation | Human strategy and online recovery in the real task | Hardware mapping and human collection cost | Complex, contact-rich real tasks |
| Kinesthetic teaching | Intuitive robot-native trajectories | Hardware and scale constraints | Quick teaching in a bounded workstation |
| Scripted expert | Reproducible, explainable, automatically checkable | Task-specific assumptions and privileged state | Structured simulation tasks |
| Privileged learned teacher | Automated behavior across richer variation | Teacher training, reward design, and transfer gap | Large simulation campaigns |
| Automatic augmentation | Expands coverage from a small seed set | Limited by seed quality and transform validity | Related tasks with replayable success checks |
| Human-video transfer | Broad task and scene diversity | Missing robot actions and physical correspondence | Semantic priors and cross-embodiment research |

Cost and quality are not single numbers. For example, a teleoperated episode
may be expensive in human time but valuable because it contains recovery. A
scripted episode may be inexpensive to repeat but narrow because every run
inherits the same task assumptions. The right comparison depends on what the
next learner needs.

## The recent direction is a mixture, not a winner

Recent systems increasingly combine acquisition routes instead of treating
one as a universal replacement for the others.

![A hybrid acquisition pipeline combines high-value human seeds, automated scaling, heterogeneous data, and quality gates.](/diagrams/l08-hybrid-acquisition.svg)

*Course-authored schematic based on the cited project and paper directions;
it is a conceptual map, not a chronology or performance ranking.*

Three developments make the combination especially useful:

1. **Lower-friction human collection.** Low-cost leader devices, mobile or
   bimanual rigs, portable end-effector interfaces, and immersive control aim
   to collect useful behavior outside one fixed laboratory setup.
2. **Scaling and aggregation.** Simulation experts and seed-based generation
   multiply controlled episodes, while projects such as DROID and Open
   X-Embodiment show why data from many scenes, institutions, tasks, or robot
   embodiments needs explicit normalization and metadata.
3. **Broader visual experience.** Egocentric and other human video can add
   task and scene diversity, but robot-native execution and outcome checks are
   still needed to bridge from visual behavior to controllable action.

A practical hybrid pipeline might collect a small set of careful human
demonstrations, expand suitable parts in simulation, reject failures with task
checks, and mix the accepted data with broader robot datasets. Human video can
inform representation or task understanding without being mislabeled as
joint-level supervision.

This lesson stops at acquisition logic. L09 will define the concrete temporal
and storage contract. L12 will later explain how a policy consumes a prepared
dataset.

## Choose with a task-first decision frame

For any proposed source, ask:

1. **Native signal:** does it provide robot actions, measured states, images,
   object motion, or only a task-level example?
2. **Environment:** is it collected on the target robot, another embodiment,
   in simulation, or from human activity?
3. **Scale and coverage:** what human time, hardware, simulation, or training
   cost is paid for each additional task variation?
4. **Physical validity:** is the motion executed on a robot or simulator, or
   must it still be retargeted and replayed?
5. **Outcome:** can success be labelled automatically, or does it require
   review or another model?
6. **Adapter:** what calibration, action conversion, synchronization, or
   filtering is required before recording?

These questions lead directly to the L08 choice. The banana-to-bowl task has
known object poses, a configured Franka, available IK and path planning, and a
computable containment result. A scripted expert therefore provides a small,
transparent starting point whose phases can be inspected before L09 records
many episodes.

## Checkpoints

1. Why is an RGB video not already equivalent to a robot action trajectory?
2. Which route offers the clearest automatic success labels in the current
   simulated task, and what assumptions make that possible?
3. Why must an automatically augmented trajectory be replayed rather than
   accepted solely because its geometric transform succeeded?
4. What does cross-embodiment aggregation add, and which differences still
   require normalization?
5. Give one task for which teleoperation is a better starting point than a
   scripted expert, and explain the trade-off.

## Summary

- Demonstration sources differ first in their native signals, not merely in
  file format.
- Human-guided methods contribute task judgment and recovery but require
  hardware, calibration, and collection effort.
- Scripted and learned simulation experts scale repeatable behavior but depend
  on task structure, privileged state, and reliable outcome checks.
- Automatic augmentation scales seeds only after physical replay and success
  filtering.
- Human video broadens task coverage but needs embodiment mapping and robot
  execution evidence.
- Current data strategies increasingly combine these strengths. L08 chooses a
  scripted expert because the current task is structured, observable, and
  automatically checkable.

Continue to [The Scripted Pick-and-Place Expert](./l08-scripted-pick-and-place-expert.md).

## Sources

- Argall et al., [“A Survey of Robot Learning from
  Demonstration”](https://doi.org/10.1016/j.robot.2008.10.024), *Robotics and
  Autonomous Systems*, 2009 — foundational terminology and demonstration
  interfaces.
- Zhao et al., [“Learning Fine-Grained Bimanual Manipulation with Low-Cost
  Hardware”](https://arxiv.org/abs/2304.13705), 2023 — ALOHA and low-cost
  bimanual teleoperation.
- Wu et al., [“GELLO: A General, Low-Cost, and Intuitive Teleoperation
  Framework for Robot Manipulators”](https://arxiv.org/abs/2309.13037), 2023.
- Fu et al., [“Mobile ALOHA: Learning Bimanual Mobile Manipulation with
  Low-Cost Whole-Body Teleoperation”](https://arxiv.org/abs/2401.02117), 2024.
- Chi et al., [“Universal Manipulation Interface: In-The-Wild Robot Teaching
  Without In-The-Wild Robots”](https://arxiv.org/abs/2402.10329), 2024.
- Khazatsky et al., [“DROID: A Large-Scale In-The-Wild Robot Manipulation
  Dataset”](https://arxiv.org/abs/2403.12945), 2024.
- Open X-Embodiment Collaboration, [“Open X-Embodiment: Robotic Learning
  Datasets and RT-X Models”](https://arxiv.org/abs/2310.08864), 2023.
- Mandlekar et al., [“MimicGen: A Data Generation System for Scalable Robot
  Learning using Human Demonstrations”](https://arxiv.org/abs/2310.17596),
  2023.
- Kareer et al., [“EgoMimic: Scaling Imitation Learning via Egocentric
  Video”](https://arxiv.org/abs/2410.24221), 2024.
