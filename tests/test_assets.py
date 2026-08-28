from robo_genesis.setup_assets import REQUIRED_OBJECT_FILES, YCB_OBJECTS, setup_assets


def test_vendored_ycb_assets_are_complete_and_verified() -> None:
    models_dir = setup_assets()

    assert YCB_OBJECTS == ("011_banana", "014_lemon", "018_plum", "024_bowl")
    assert {path.name for path in models_dir.iterdir() if path.is_dir()} == set(YCB_OBJECTS)
    assert all(
        (models_dir / object_name / file_name).is_file()
        for object_name in YCB_OBJECTS
        for file_name in REQUIRED_OBJECT_FILES
    )
    assert not any(path.is_symlink() for path in models_dir.rglob("*"))
