# YCB assets

This directory contains the four YCB objects used by the RoboGenesis 101
manipulation lessons:

- `011_banana`
- `014_lemon`
- `018_plum`
- `024_bowl`

## Source and version

The files were copied byte-for-byte from
`wangxunx/franka_fruit_pick_demo@0de3ae0df2a91acbda7f4fb537c65d9e54190527`,
where they are stored under `assets/ycb/<object>/`. That reviewed tree is
byte-for-byte identical to the corresponding objects in the ManiSkill 3.0.1
YCB asset archive:

- Distributor: [ManiSkill](https://github.com/haosulab/ManiSkill)
- Archive: [mani_skill2_ycb.zip](https://huggingface.co/datasets/haosulab/ManiSkill2/resolve/main/data/mani_skill2_ycb.zip)
- Archive SHA-256: `1551724fd1ac7bad9807ebcf46dd4a788caed5c9499c1225b9bfa080ffbefcb3`
- Original collection: [YCB Object and Model Set](https://www.ycbbenchmarks.com/)

See the repository [NOTICE](../../../NOTICE.md) for the full provenance audit.

## License and attribution

ManiSkill identifies its assets as licensed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
These files are not covered by the repository's MIT License. The complete
license text is in [LICENSE-CC-BY-NC-4.0.txt](LICENSE-CC-BY-NC-4.0.txt).

Please cite:

> Calli et al. “Benchmarking in Manipulation Research: Using the
> Yale-CMU-Berkeley Object and Model Set.” IEEE Robotics & Automation Magazine,
> 2015.

Also see: [doi:10.1109/MRA.2015.2448951](https://doi.org/10.1109/MRA.2015.2448951).

## Modification record

No geometry, material, texture, scale, or file-format changes were made. The
course neither uses nor generates scaled variants of these objects.

`SHA256SUMS` covers all 24 files below `models/`. Verify them from this
directory with:

```sh
sha256sum --check SHA256SUMS
```
