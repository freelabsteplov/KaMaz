import math
import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
TARGET_LABEL = "SnowTestGround"


def _find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _safe(value, default=None):
    try:
        return value()
    except Exception:
        return default


def main():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor = _find_actor_by_label(TARGET_LABEL)
    if actor is None:
        raise RuntimeError(f"Actor not found: {TARGET_LABEL}")

    sm_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if sm_comp is None:
        raise RuntimeError("StaticMeshComponent missing")

    sm = sm_comp.get_editor_property("static_mesh")
    if sm is None:
        raise RuntimeError("Static mesh missing on component")

    sm_subsys = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    lod_count = _safe(lambda: sm_subsys.get_lod_count(sm), 0)
    lod0_verts = _safe(lambda: sm_subsys.get_number_verts(sm, 0), -1)

    origin, box_extent = actor.get_actor_bounds(False)
    world_size_x = float(box_extent.x) * 2.0
    world_size_y = float(box_extent.y) * 2.0
    area_xy = max(1.0, world_size_x * world_size_y)

    # Rough average spacing proxy for a grid-like surface.
    spacing_estimate = math.sqrt(area_xy / max(1.0, float(lod0_verts)))

    # MVP heuristic: < ~75 uu average spacing typically gives readable local WPO for debug stamp.
    wpo_viable = bool(lod0_verts >= 500 and spacing_estimate <= 75.0)

    print(f"world={unreal.EditorLevelLibrary.get_editor_world().get_name()}")
    print(f"actor_path={actor.get_path_name()}")
    print(f"component_path={sm_comp.get_path_name()}")
    print(f"static_mesh={sm.get_path_name()}")
    print(f"lod_count={lod_count}")
    print(f"lod0_verts={lod0_verts}")
    print(f"world_size_x={world_size_x:.3f}")
    print(f"world_size_y={world_size_y:.3f}")
    print(f"area_xy={area_xy:.3f}")
    print(f"spacing_estimate={spacing_estimate:.3f}")
    print(f"SNOWTESTGROUND_WPO_VIABLE={'YES' if wpo_viable else 'NO'}")


if __name__ == "__main__":
    main()
