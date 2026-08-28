# Third-Party Notices and Asset Audit

This document records third-party material considered for RoboGenesis 101. It is
an audit ledger, not a replacement for the original license texts and not a
grant of rights by this project. M0.4 approved the audit, and M0.5 approved the
license boundary and dispositions reflected below.

Audit date: 2026-08-28.

Except for the two Datawhale template files identified below, none of the
third-party assets reviewed here has been copied into this repository. Approved
assets remain subject to their later migration step and original license.

## Audit summary

| Material | Location reviewed | License evidence | Approved disposition |
|---|---|---|---|
| ManiSkill-distributed YCB meshes and textures | `franka_fruit_pick_demo/assets/ycb/` at the recorded `course` baseline | ManiSkill identifies its assets as CC BY-NC 4.0 | Vendor only banana, lemon, plum, and bowl during the approved later asset step; include the original license and provenance |
| Franka Emika Panda MJCF model | `franka_fruit_pick_demo/assets/robots/franka/` at the recorded `course` baseline | Model README and MuJoCo Menagerie upstream identify the model as Apache-2.0 | Do not copy the incomplete source bundle; use the model bundled with the pinned Genesis version |
| Source-course renders and slide exports | Both source courses at their recorded baselines | Project lead confirmed on 2026-08-28 that the course code, lectures, and teaching content are original | Original portions use MIT after migration; preserve notices for depicted or embedded third-party material |
| Datawhale template media already in this repository | `docs/public/datawhale-logo.png`, `docs/public/learning.GIF` | Inherited template README declares CC BY-NC-SA 4.0 for the work; separate trademark permission was not found | Keep outside the project MIT boundary until Datawhale brand use is confirmed or the media is replaced |
| Datasets, checkpoints, and training/evaluation outputs | Local source worktrees only | No artifact-specific license or release metadata reviewed | Excluded by M0.2; any future release requires a separate M5 entry |

The course MIT License must not be presented as relicensing any item in this
table. Third-party terms continue to apply to third-party material.

## 1. YCB objects distributed by ManiSkill

### Reviewed scope

The source baseline
`wangxunx/franka_fruit_pick_demo@0de3ae0df2a91acbda7f4fb537c65d9e54190527`
contains these ten directories under `assets/ycb/`:

- `003_cracker_box`
- `006_mustard_bottle`
- `011_banana`
- `013_apple`
- `014_lemon`
- `016_pear`
- `017_orange`
- `018_plum`
- `024_bowl`
- `025_mug`

The reviewed tree contains 60 files and 11,255,029 bytes. Each object has an
OBJ render mesh, a PLY collision mesh, two material files, and two texture
images. The SHA-256 of the sorted per-file SHA-256 manifest, with paths relative
to `assets/ycb/`, is:

```text
40465c3b1f59c0b1e0c88ce507d0957b4b5ca4b29e637c80fb6d72611a8d9fa6
```

All ten directories are byte-for-byte identical to the corresponding
`models/<object>/` directories in a local ManiSkill 3.0.1 YCB download.

### Provenance

- Immediate distributor: [ManiSkill](https://github.com/haosulab/ManiSkill).
- Download used by ManiSkill 3.0.1:
  [mani_skill2_ycb.zip](https://huggingface.co/datasets/haosulab/ManiSkill2/resolve/main/data/mani_skill2_ycb.zip).
- SHA-256 declared by ManiSkill 3.0.1 for that archive:
  `1551724fd1ac7bad9807ebcf46dd4a788caed5c9499c1225b9bfa080ffbefcb3`.
- Original collection: [YCB Object and Model Set](https://www.ycbbenchmarks.com/).
- Recommended scholarly citation: Calli et al., “Benchmarking in Manipulation
  Research: Using the Yale-CMU-Berkeley Object and Model Set,” IEEE Robotics &
  Automation Magazine, 2015,
  [doi:10.1109/MRA.2015.2448951](https://doi.org/10.1109/MRA.2015.2448951).

The source repository README names ManiSkill and YCB, and its asset setup code
names a local ManiSkill dataset as the fallback source. The extracted asset
directories themselves contain no README, license, or citation file.

### License evidence and obligations

The ManiSkill 3.0.1 package metadata and the official ManiSkill README both
state: “The assets are licensed under CC BY-NC 4.0.” The applicable license is
[Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/legalcode).
The YCB website returned HTTP 500 during this audit, so no separate original-YCB
license statement was confirmed there. This ledger therefore uses the explicit,
more restrictive ManiSkill asset license for the reviewed copies.

If these files are distributed with RoboGenesis 101, at minimum the project
must retain the CC BY-NC 4.0 terms, credit ManiSkill and the YCB Object and Model
Set, link the license and sources, indicate modifications, and avoid presenting
the assets as covered by the course's own content or code license. The
noncommercial restriction must remain visible to downstream users.

M0.5 approved vendoring only the four objects used by the course mainline:
`011_banana`, `014_lemon`, `018_plum`, and `024_bowl`. Their later migration
must include the CC BY-NC 4.0 license, source and archive checksum, object list,
and modification record. The other six audited objects remain excluded unless
a later lesson requests and separately reviews them.

### Apparent scaling discrepancy

`setup_assets.py` in the source course says that `013_apple` and `017_orange`
come from scaled copies. That statement does not describe the reviewed Git
baseline: both committed directories are byte-for-byte identical to the
ManiSkill download, including `textured.obj` and `collision.ply`. The separate
local `mani_skill_dataset_scaled` files are different and are not part of the
approved migration baseline.

Therefore the reviewed apple and orange files must be treated as unmodified
ManiSkill assets. A future scaling operation would create modified assets and
must be recorded as such. The stale fallback description must be corrected when
the asset setup interface is redesigned after this audit.

## 2. Franka Emika Panda MJCF model

### Reviewed scope

The source baseline contains 77 files under `assets/robots/franka/`: one README,
eight MJCF/XML files, one PNG, 59 OBJ meshes, and eight STL meshes. Its size is
36,562,008 bytes. The SHA-256 of the sorted per-file SHA-256 manifest, with paths
relative to `assets/robots/franka/`, is:

```text
b8924c554f16fd318af3a3afaf9637e884221393e220740dfbdbae5f9da29fc0
```

The tree is byte-for-byte identical to
`wangxunx/genesis-world@20d07d7447b27540dcd8869960f58dac4301cd0f`
under `genesis/assets/xml/franka_emika_panda/`, which is the immediate source
named by the source course's setup code.

### Provenance

- Immediate source: the Genesis `franka_emika_panda` asset directory.
- Model upstream: [MuJoCo Menagerie — Franka Emika Panda](https://github.com/google-deepmind/mujoco_menagerie/tree/main/franka_emika_panda).
- Earlier robot-description source named by the model README:
  [franka_ros/franka_description](https://github.com/frankaemika/franka_ros/tree/develop/franka_description).

The model README documents the URDF-to-MJCF conversion and subsequent model
changes. “Franka” and “Panda” are used only to identify the source robot/model;
the Apache license does not grant trademark rights.

### License evidence and missing file

Both the reviewed model README and the official MuJoCo Menagerie README identify
the model as Apache License 2.0. The official upstream supplies the referenced
[model-level LICENSE](https://github.com/google-deepmind/mujoco_menagerie/blob/main/franka_emika_panda/LICENSE).

However, neither the copied source-course directory nor its immediate Genesis
directory contains the `LICENSE` file linked by its README. A repository-level
Genesis Apache-2.0 license exists, but it does not repair the missing
model-level distribution record by itself.

M0.5 approved using `xml/franka_emika_panda/panda.xml` from the pinned Genesis
installation instead of copying the incomplete source-course folder. The
course must retain Genesis, MuJoCo Menagerie, and Franka attribution here and
must not hard-code a developer-machine `site-packages` path. If that bundled
model later proves incompatible, a new reviewed proposal must select an exact
MuJoCo Menagerie commit, include the model-level Apache-2.0 license, and record
any modifications before vendoring it.

## 3. Source-course media and exports

The Franka source repository contains 30 PNG/GIF paths in its bilingual course
tree plus three copies in top-level documentation. Together they represent five
unique simulation outputs: world-camera and wrist-camera frames, a
scripted-pick GIF, a domain-randomization montage, and its baseline montage.
Git history records Xun Wang as the author who added them. On 2026-08-28, the
project lead additionally confirmed that the source-course code, lectures, and
teaching content are original. The renders nevertheless depict the YCB and
Franka assets audited above, whose separate terms continue to apply.

The same source contains 14 PPTX exports and one PDF export. The Genesis
foundations source contains six SVG flow diagrams and twelve PPTX exports. No
separate stored third-party paper figures were identified by the static file and
link inventory, but exported presentations were not treated as proof of rights
for their embedded content.

These files are not part of the M1.3 code migration. During M2-M4, each selected
media file must receive one of these dispositions before import:

- record it as original source-course material under MIT;
- retain the YCB/Franka notices when those assets appear in a rendering;
- replace it with a reproducibly generated equivalent; or
- separately audit or omit any newly discovered external material.

Generated PPTX/PDF files must be regenerated from their reviewed source rather
than treated as the source of truth.

## 4. Existing Datawhale template media

Two files predate this audit and already exist in RoboGenesis 101:

| File | SHA-256 | Evidence and open question |
|---|---|---|
| `docs/public/datawhale-logo.png` | `137d2d2aac7109f8630b5afb8ec3d4e117d2bb53373eaf1e77a3754441498857` | Inherited from the Datawhale repository template; brand-use approval is not recorded locally |
| `docs/public/learning.GIF` | `95985ee9642522feb498b6b6cad99655d03b32dcf04ab4cd9a9747833cfa7802` | Inherited from the same template; original creator and asset-specific license are not recorded locally |

The inherited template README points to
[`datawhalechina/repo-template`](https://github.com/datawhalechina/repo-template)
and declares the template work under CC BY-NC-SA 4.0. That statement is recorded
as evidence, but it does not by itself establish trademark permission for the
Datawhale logo. M0.5 therefore kept both files outside the project MIT boundary;
brand-use confirmation or replacement remains required before publication. No
brand asset was changed in M0.4 or M1.1.

The current README also embeds a remote Datawhale QR-code image from
`datawhalechina/pumpkin-book`. It is linked rather than stored, but its source
and permission must be confirmed or the link removed when the README is
rewritten in M1.10.

## 5. Datasets, checkpoints, models, and dependencies

M0.2 excluded all local datasets, checkpoints, evaluation outputs, videos,
frames, logs, and caches from migration. They receive no redistribution
approval from this audit.

If M5 publishes a dataset or checkpoint, add a separate entry here containing
its creator, source data, model provenance, license, immutable version,
checksum, hosting URL, and citation. A model name or Hugging Face repository
link in lesson text is not sufficient evidence of redistribution rights.

Genesis, ManiSkill, LeRobot, PyTorch, and other installable software packages
are dependencies rather than vendored source in the current plan. Their exact
versions and installation sources belong to M0.6-M0.7; any code later copied
from them must first receive a file-level license review and a new entry here.

## 6. Approved decisions and remaining review

The project lead approved the following M0.5 decisions on 2026-08-28:

1. vendor only the four selected YCB objects under CC BY-NC 4.0;
2. use the Franka model bundled with the pinned Genesis version instead of
   copying the incomplete source directory;
3. release original source-course material under MIT while preserving the
   notices for depicted or embedded third-party material; and
4. keep datasets, checkpoints, and pretrained models outside the repository-wide
   license until each artifact is reviewed for M5.

Datawhale trademark and template-media authorization remains to be confirmed.
Until then, those materials are not covered by the project MIT License.

M1.1 copies no third-party asset. The approved YCB files and their license are
added only in the later asset migration step.
