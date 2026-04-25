import json
import os
import shutil
import gc

import unreal


SNOWMAP_SOURCE_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
SNOWMAP_SOURCE_BUILDDATA_PATH = "/Game/LandscapeDeformation/Maps/SnowMap_BuiltData"
MOSCOW_MAP_PATH = "/Game/Maps/MoscowEA5"
TARGET_MAP_PATH = "/Game/Maps/SnowMap_MoscowEA5"
TARGET_BUILDDATA_PATH = "/Game/Maps/SnowMap_MoscowEA5_BuiltData"

LANDSCAPE_LABEL = "Landscape"
RVT_HEIGHT_LABEL = "RVT_SnowHeight"
RVT_MATERIAL_LABEL = "RVT_SnowMaterial"
VHM_LABEL = "VirtualHeightfieldMesh1"
BP_CAPTURE_LABEL = "BP_Capture"
TEST_SPHERE_LABELS = {"Sphere", "Cube"}

ROAD_SCALE_MARGIN = 1.2
ROAD_MESH_PATH_TOKEN = "/game/snappyroads/meshes/road/"
ROAD_MESH_NAME_TOKENS = (
    "sm_road_nocollision",
    "sm_1lane_road",
    "sm_1lane_intersection",
)
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "create_snowmap_moscowea5_sublevel_map.json",
)


def _asset_to_filename(asset_path):
    relative = asset_path.replace("/Game/", "").replace("/", os.sep)
    if asset_path.endswith("_BuiltData"):
        return os.path.join(unreal.Paths.project_content_dir(), relative + ".uasset")
    return os.path.join(unreal.Paths.project_content_dir(), relative + ".umap")


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        try:
            return actor.get_name()
        except Exception:
            return ""


def _vec_dict(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot_dict(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _transform_dict(value):
    if value is None:
        return None
    return {
        "location": _vec_dict(value.translation),
        "rotation": _rot_dict(value.rotation.rotator()),
        "scale": _vec_dict(value.scale3d),
    }


def _ensure_map_exists():
    target_map_file = _asset_to_filename(TARGET_MAP_PATH)
    if not os.path.exists(target_map_file):
        source_map_file = _asset_to_filename(SNOWMAP_SOURCE_PATH)
        os.makedirs(os.path.dirname(target_map_file), exist_ok=True)
        shutil.copy2(source_map_file, target_map_file)

    source_builtdata_file = _asset_to_filename(SNOWMAP_SOURCE_BUILDDATA_PATH)
    target_builtdata_file = _asset_to_filename(TARGET_BUILDDATA_PATH)
    if os.path.exists(source_builtdata_file) and not os.path.exists(target_builtdata_file):
        shutil.copy2(source_builtdata_file, target_builtdata_file)


def _release_uobject_refs():
    gc.collect()
    try:
        unreal.SystemLibrary.collect_garbage()
    except Exception:
        pass


def _load_map(map_path):
    world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
    if not world:
        raise RuntimeError(f"Could not load map: {map_path}")
    return world


def _actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def _find_actor_by_label(target_label):
    for actor in _actors():
        if _label(actor) == target_label:
            return actor
    return None


def _find_player_starts():
    result = []
    for actor in _actors():
        if actor.get_class().get_name() == "PlayerStart":
            result.append(actor)
    return result


def _first_player_start():
    starts = _find_player_starts()
    if not starts:
        raise RuntimeError("No PlayerStart found")
    starts.sort(key=lambda actor: _path(actor))
    return starts[0]


def _landscape_bounds():
    landscape = _find_actor_by_label(LANDSCAPE_LABEL)
    if landscape is None:
        raise RuntimeError(f"Landscape actor '{LANDSCAPE_LABEL}' not found")
    origin, extent = landscape.get_actor_bounds(False)
    return landscape, origin, extent


def _get_static_mesh(actor):
    try:
        smc = actor.get_component_by_class(unreal.StaticMeshComponent)
    except Exception:
        smc = None
    if smc is None:
        return None
    try:
        return smc.get_editor_property("static_mesh")
    except Exception:
        return None


def _road_actor_match(actor):
    mesh = _get_static_mesh(actor)
    if mesh is None:
        return False
    mesh_path = _path(mesh).lower()
    mesh_name = mesh.get_name().lower() if mesh else ""
    if ROAD_MESH_PATH_TOKEN in mesh_path:
        return True
    return any(mesh_name.startswith(token) for token in ROAD_MESH_NAME_TOKENS)


def _accumulate_bounds(current_min, current_max, origin, extent):
    actor_min = unreal.Vector(origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
    actor_max = unreal.Vector(origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)
    if current_min is None:
        return actor_min, actor_max
    return (
        unreal.Vector(
            min(float(current_min.x), float(actor_min.x)),
            min(float(current_min.y), float(actor_min.y)),
            min(float(current_min.z), float(actor_min.z)),
        ),
        unreal.Vector(
            max(float(current_max.x), float(actor_max.x)),
            max(float(current_max.y), float(actor_max.y)),
            max(float(current_max.z), float(actor_max.z)),
        ),
    )


def _compute_moscow_road_bounds():
    road_min = None
    road_max = None
    matches = []
    for actor in _actors():
        if not _road_actor_match(actor):
            continue
        origin, extent = actor.get_actor_bounds(False)
        road_min, road_max = _accumulate_bounds(road_min, road_max, origin, extent)
        matches.append(
            {
                "actor_label": _label(actor),
                "actor_path": _path(actor),
                "origin": _vec_dict(origin),
                "extent": _vec_dict(extent),
                "mesh_path": _path(_get_static_mesh(actor)),
            }
        )
    if road_min is None or road_max is None:
        raise RuntimeError("Could not compute MoscowEA5 road bounds from SnappyRoads meshes")
    return road_min, road_max, matches


def _streaming_levels(world):
    try:
        return list(world.get_editor_property("streaming_levels") or [])
    except Exception:
        return []


def _streaming_level_package(level):
    getter = getattr(level, "get_world_asset_package_name", None)
    if callable(getter):
        try:
            value = getter()
            if value:
                return str(value)
        except Exception:
            pass
    for property_name in ("world_asset_package_name", "package_name_to_load", "package_name"):
        try:
            value = level.get_editor_property(property_name)
            if value:
                return str(value)
        except Exception:
            continue
    return ""


def _remove_existing_streaming_levels(world, map_path):
    removed = []
    for level in _streaming_levels(world):
        package_name = _streaming_level_package(level)
        if map_path not in package_name:
            continue
        try:
            unreal.EditorLevelUtils.remove_level_from_world(level)
            removed.append(package_name)
        except Exception:
            continue
    return removed


def _add_sublevel(world, map_path, offset):
    transform = unreal.Transform(offset, unreal.Rotator(0.0, 0.0, 0.0), unreal.Vector(1.0, 1.0, 1.0))
    attempts = []
    classes = []
    if hasattr(unreal, "LevelStreamingAlwaysLoaded"):
        classes.append(unreal.LevelStreamingAlwaysLoaded)
        try:
            classes.append(unreal.LevelStreamingAlwaysLoaded.static_class())
        except Exception:
            pass
    for streaming_class in classes:
        try:
            level = unreal.EditorLevelUtils.add_level_to_world_with_transform(world, map_path, streaming_class, transform)
            if level:
                for property_name in ("should_be_loaded", "should_be_visible"):
                    try:
                        level.set_editor_property(property_name, True)
                    except Exception:
                        continue
                return level, "add_level_to_world_with_transform", transform
        except Exception as exc:
            attempts.append(f"with_transform:{streaming_class}:{exc}")
        try:
            level = unreal.EditorLevelUtils.add_level_to_world(world, map_path, streaming_class)
            if level:
                for property_name in ("level_transform", "editor_transform", "transform"):
                    try:
                        level.set_editor_property(property_name, transform)
                        break
                    except Exception:
                        continue
                for property_name in ("should_be_loaded", "should_be_visible"):
                    try:
                        level.set_editor_property(property_name, True)
                    except Exception:
                        continue
                return level, "add_level_to_world", transform
        except Exception as exc:
            attempts.append(f"add_level:{streaming_class}:{exc}")
    raise RuntimeError("Failed to add MoscowEA5 sublevel: " + " | ".join(attempts))


def _delete_persistent_test_actors(target_map_token):
    deleted = []
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in _actors():
        actor_path = _path(actor)
        if target_map_token not in actor_path or ":PersistentLevel." not in actor_path:
            continue
        label = _label(actor)
        class_name = actor.get_class().get_name()
        if class_name == "PlayerStart" or label in TEST_SPHERE_LABELS:
            actor_subsystem.destroy_actor(actor)
            deleted.append(actor_path)
    return deleted


def _move_and_scale_snow_receiver(target_center, scale_ratio):
    landscape = _find_actor_by_label(LANDSCAPE_LABEL)
    rvt_height = _find_actor_by_label(RVT_HEIGHT_LABEL)
    rvt_material = _find_actor_by_label(RVT_MATERIAL_LABEL)
    vhm = _find_actor_by_label(VHM_LABEL)
    bp_capture = _find_actor_by_label(BP_CAPTURE_LABEL)

    if landscape is None or rvt_height is None or rvt_material is None or vhm is None:
        raise RuntimeError("Missing one or more SnowMap receiver actors (Landscape/RVT/VHM)")

    landscape_before_origin, landscape_before_extent = landscape.get_actor_bounds(False)
    landscape_before_scale = landscape.get_actor_scale3d()
    landscape_location = landscape.get_actor_location()
    landscape_location.x = float(target_center.x)
    landscape_location.y = float(target_center.y)
    landscape.set_actor_location(landscape_location, False, False)
    landscape_scale = unreal.Vector(
        float(landscape_before_scale.x) * float(scale_ratio),
        float(landscape_before_scale.y) * float(scale_ratio),
        float(landscape_before_scale.z),
    )
    landscape.set_actor_scale3d(landscape_scale)

    height_location = rvt_height.get_actor_location()
    height_scale = rvt_height.get_actor_scale3d()
    height_rotation = rvt_height.get_actor_rotation()
    height_location.x = float(target_center.x)
    height_location.y = float(target_center.y)
    rvt_height.set_actor_location(height_location, False, False)
    rvt_height.set_actor_scale3d(
        unreal.Vector(
            float(height_scale.x) * float(scale_ratio),
            float(height_scale.y) * float(scale_ratio),
            float(height_scale.z),
        )
    )

    synced_location = rvt_height.get_actor_location()
    synced_rotation = rvt_height.get_actor_rotation()
    synced_scale = rvt_height.get_actor_scale3d()
    for actor in (rvt_material, vhm):
        actor.set_actor_location(synced_location, False, False)
        actor.set_actor_rotation(synced_rotation, False)
        actor.set_actor_scale3d(synced_scale)

    if bp_capture is not None:
        capture_location = bp_capture.get_actor_location()
        capture_location.x = float(target_center.x)
        capture_location.y = float(target_center.y)
        bp_capture.set_actor_location(capture_location, False, False)

    landscape_after_origin, landscape_after_extent = landscape.get_actor_bounds(False)
    return {
        "landscape_path": _path(landscape),
        "landscape_before_origin": _vec_dict(landscape_before_origin),
        "landscape_before_extent": _vec_dict(landscape_before_extent),
        "landscape_before_scale": _vec_dict(landscape_before_scale),
        "landscape_after_origin": _vec_dict(landscape_after_origin),
        "landscape_after_extent": _vec_dict(landscape_after_extent),
        "landscape_after_scale": _vec_dict(landscape.get_actor_scale3d()),
        "rvt_height_path": _path(rvt_height),
        "rvt_material_path": _path(rvt_material),
        "vhm_path": _path(vhm),
        "receiver_location": _vec_dict(synced_location),
        "receiver_rotation": _rot_dict(synced_rotation),
        "receiver_scale": _vec_dict(synced_scale),
        "bp_capture_path": _path(bp_capture),
        "bp_capture_location": _vec_dict(bp_capture.get_actor_location()) if bp_capture else None,
        "scale_ratio": float(scale_ratio),
    }


def main():
    payload = {
        "snowmap_source_path": SNOWMAP_SOURCE_PATH,
        "moscow_map_path": MOSCOW_MAP_PATH,
        "target_map_path": TARGET_MAP_PATH,
        "target_builtdata_path": TARGET_BUILDDATA_PATH,
        "moved_receiver": {},
        "sublevel_added": {},
        "deleted_persistent_actors": [],
        "removed_existing_sublevels": [],
        "save_ok": False,
        "error": "",
    }

    try:
        _ensure_map_exists()

        _load_map(MOSCOW_MAP_PATH)
        moscow_player_start = _first_player_start()
        road_min, road_max, road_matches = _compute_moscow_road_bounds()
        moscow_player_start_location = moscow_player_start.get_actor_location()
        payload["moscow_player_start"] = {
            "path": _path(moscow_player_start),
            "location": _vec_dict(moscow_player_start_location),
        }
        payload["moscow_road_bounds"] = {
            "min": _vec_dict(road_min),
            "max": _vec_dict(road_max),
            "matches": road_matches[:10],
            "match_count": len(road_matches),
        }
        del moscow_player_start
        _release_uobject_refs()

        world = _load_map(TARGET_MAP_PATH)
        snow_player_start = _first_player_start()
        snow_player_start_location = snow_player_start.get_actor_location()
        payload["snowmap_player_start_before"] = {
            "path": _path(snow_player_start),
            "location": _vec_dict(snow_player_start_location),
        }

        removed_existing = _remove_existing_streaming_levels(world, MOSCOW_MAP_PATH)
        payload["removed_existing_sublevels"] = removed_existing

        offset = unreal.Vector(
            float(snow_player_start_location.x - moscow_player_start_location.x),
            float(snow_player_start_location.y - moscow_player_start_location.y),
            float(snow_player_start_location.z - moscow_player_start_location.z),
        )
        added_level, add_method, level_transform = _add_sublevel(world, MOSCOW_MAP_PATH, offset)
        payload["sublevel_added"] = {
            "streaming_level_path": _path(added_level),
            "streaming_level_package": _streaming_level_package(added_level),
            "world_asset": _path(added_level.get_editor_property("world_asset")) if added_level else "",
            "method": add_method,
            "offset": _vec_dict(offset),
            "transform": _transform_dict(level_transform),
        }

        transformed_road_min = unreal.Vector(
            float(road_min.x + offset.x),
            float(road_min.y + offset.y),
            float(road_min.z + offset.z),
        )
        transformed_road_max = unreal.Vector(
            float(road_max.x + offset.x),
            float(road_max.y + offset.y),
            float(road_max.z + offset.z),
        )
        road_span_x = float(transformed_road_max.x - transformed_road_min.x)
        road_span_y = float(transformed_road_max.y - transformed_road_min.y)
        target_square_span = max(road_span_x, road_span_y) * ROAD_SCALE_MARGIN

        landscape, landscape_origin, landscape_extent = _landscape_bounds()
        current_square_span = max(float(landscape_extent.x) * 2.0, float(landscape_extent.y) * 2.0)
        scale_ratio = max(float(target_square_span / current_square_span), 1.0)
        target_center = unreal.Vector(
            (float(transformed_road_min.x) + float(transformed_road_max.x)) * 0.5,
            (float(transformed_road_min.y) + float(transformed_road_max.y)) * 0.5,
            float(landscape_origin.z),
        )

        payload["transformed_road_bounds"] = {
            "min": _vec_dict(transformed_road_min),
            "max": _vec_dict(transformed_road_max),
            "span_x": road_span_x,
            "span_y": road_span_y,
            "target_square_span_with_margin": float(target_square_span),
            "target_center": _vec_dict(target_center),
        }
        payload["moved_receiver"] = _move_and_scale_snow_receiver(target_center, scale_ratio)

        deleted = _delete_persistent_test_actors(TARGET_MAP_PATH)
        payload["deleted_persistent_actors"] = deleted

        payload["save_ok"] = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP_PATH))
        payload["final_streaming_levels"] = [
            {
                "path": _path(level),
                "package": _streaming_level_package(level),
            }
            for level in _streaming_levels(world)
        ]
        payload["final_player_starts"] = [
            {
                "path": _path(actor),
                "location": _vec_dict(actor.get_actor_location()),
            }
            for actor in _find_player_starts()
        ]
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
