import json
import os

import unreal


OUTPUT_BASENAME = "spawn_road_only_carrier_for_road2"
TARGET_ACTOR_LABEL = "Road2"
TARGET_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
TARGET_MAP_PATH = "/Game/Maps/MoscowEA5"
CARRIER_ACTOR_LABEL = "SnowRoadCarrier_Road2"
STALE_OVERLAY_LABEL = "SnowOverlay_Road2"

DENSE_CARRIER_MESH_PATH = "/Engine/EditorMeshes/PlanarReflectionPlane.PlanarReflectionPlane"
FALLBACK_CARRIER_MESH_PATH = "/Engine/BasicShapes/Plane.Plane"

PREFERRED_MATERIAL_PATHS = [
    "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP",
]

CARRIER_LENGTH_MULTIPLIER = 0.98
CARRIER_WIDTH_MULTIPLIER = 0.72
CARRIER_Z_OFFSET_CM = 4.0
RECEIVER_PRIORITY = 110
RECEIVER_SET_TAG = "RoadOnlyCarrier"


def _log(message: str) -> None:
    unreal.log(f"[spawn_road_only_carrier_for_road2] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _all_level_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def _find_actor_by_label(label: str):
    for actor in _all_level_actors():
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _find_actor_by_path(actor_path: str):
    for actor in _all_level_actors():
        try:
            if actor.get_path_name() == actor_path:
                return actor
        except Exception:
            continue
    return None


def _selected_mesh_actor():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected = list(actor_subsystem.get_selected_level_actors() or [])
    for actor in selected:
        if _first_static_mesh_component(actor) is not None:
            return actor
    return None


def _resolve_target_actor():
    target_actor = _find_actor_by_label(TARGET_ACTOR_LABEL)
    if target_actor is not None:
        return target_actor, "label"

    target_actor = _find_actor_by_path(TARGET_ACTOR_PATH)
    if target_actor is not None:
        return target_actor, "path"

    selected_actor = _selected_mesh_actor()
    if selected_actor is not None:
        return selected_actor, "selection"

    loaded = False
    try:
        loaded = bool(unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP_PATH))
    except Exception:
        loaded = False

    if loaded:
        target_actor = _find_actor_by_label(TARGET_ACTOR_LABEL)
        if target_actor is not None:
            return target_actor, "label_after_load"

        target_actor = _find_actor_by_path(TARGET_ACTOR_PATH)
        if target_actor is not None:
            return target_actor, "path_after_load"

    raise RuntimeError(
        f"Could not resolve target road actor. Tried label='{TARGET_ACTOR_LABEL}', "
        f"path='{TARGET_ACTOR_PATH}', current selection, and loading {TARGET_MAP_PATH}."
    )


def _destroy_actor_if_present(label: str) -> bool:
    actor = _find_actor_by_label(label)
    if actor is None:
        return False
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    try:
        return bool(actor_subsystem.destroy_actor(actor))
    except Exception:
        return False


def _load_first_existing_asset(asset_paths: list[str]):
    for asset_path in asset_paths:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is not None:
            return asset, asset_path
    raise RuntimeError(f"Could not load any candidate asset from: {asset_paths}")


def _first_static_mesh_component(actor):
    if actor is None:
        return None
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def _get_target_surface_size_cm(actor) -> tuple[float, float, float]:
    component = _first_static_mesh_component(actor)
    if component is None:
        raise RuntimeError(f"Target actor has no StaticMeshComponent: {_object_path(actor)}")

    static_mesh = component.get_editor_property("static_mesh")
    if static_mesh is None:
        raise RuntimeError(f"Target actor has no static mesh assigned: {_object_path(component)}")

    mesh_bounds = static_mesh.get_bounds()
    scale = component.get_component_scale()

    size_x = abs(float(mesh_bounds.box_extent.x) * 2.0 * float(scale.x))
    size_y = abs(float(mesh_bounds.box_extent.y) * 2.0 * float(scale.y))
    size_z = abs(float(mesh_bounds.box_extent.z) * 2.0 * float(scale.z))

    length_cm = max(size_x, size_y)
    width_cm = min(size_x, size_y)
    return length_cm, width_cm, size_z


def _get_mesh_base_size_cm(static_mesh) -> tuple[float, float]:
    mesh_bounds = static_mesh.get_bounds()
    base_x = max(abs(float(mesh_bounds.box_extent.x) * 2.0), 1.0)
    base_y = max(abs(float(mesh_bounds.box_extent.y) * 2.0), 1.0)
    return base_x, base_y


def _ensure_carrier_actor(location: unreal.Vector, rotation: unreal.Rotator):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = _find_actor_by_label(CARRIER_ACTOR_LABEL)
    created = False
    if actor is None:
        actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        if actor is None:
            raise RuntimeError("Failed to spawn road-only carrier actor.")
        actor.set_actor_label(CARRIER_ACTOR_LABEL)
        created = True
    else:
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, False)
    return actor, created


def _configure_mesh_component(component, static_mesh, material_asset, scale: unreal.Vector) -> None:
    component.set_static_mesh(static_mesh)
    component.set_material(0, material_asset)
    component.set_relative_scale3d(scale)
    component.set_editor_property("cast_shadow", False)
    component.set_editor_property("affect_distance_field_lighting", False)
    component.set_editor_property("visible_in_ray_tracing", False)
    component.set_editor_property("receives_decals", False)
    component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.modify()


def _ensure_receiver_surface(actor) -> tuple[bool, str]:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return False, "BlueprintAutomationPythonBridge missing"

    raw_result = None
    try:
        raw_result = bridge.ensure_snow_receiver_surfaces_on_actors(
            "",
            [actor.get_path_name()],
            unreal.SnowReceiverSurfaceFamily.ROAD,
            RECEIVER_PRIORITY,
            RECEIVER_SET_TAG,
            False,
            False,
        )
    except Exception as exc:
        return False, str(exc)

    receiver = actor.get_component_by_class(unreal.SnowReceiverSurfaceComponent)
    if receiver is None:
        return bool(raw_result), "SnowReceiverSurfaceComponent missing after bridge call"

    receiver.set_editor_property("bParticipatesInPersistentSnowState", True)
    receiver.set_editor_property("SurfaceFamily", unreal.SnowReceiverSurfaceFamily.ROAD)
    receiver.set_editor_property("ReceiverPriority", RECEIVER_PRIORITY)
    receiver.set_editor_property("ReceiverSetTag", RECEIVER_SET_TAG)
    receiver.modify()
    return True, ""


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    target_actor, target_resolution = _resolve_target_actor()

    material_asset, material_path = _load_first_existing_asset(PREFERRED_MATERIAL_PATHS)
    dense_mesh, dense_mesh_path = _load_first_existing_asset([DENSE_CARRIER_MESH_PATH, FALLBACK_CARRIER_MESH_PATH])

    length_cm, width_cm, target_height_cm = _get_target_surface_size_cm(target_actor)
    desired_length_cm = max(length_cm * CARRIER_LENGTH_MULTIPLIER, 100.0)
    desired_width_cm = max(width_cm * CARRIER_WIDTH_MULTIPLIER, 100.0)

    base_x_cm, base_y_cm = _get_mesh_base_size_cm(dense_mesh)
    scale = unreal.Vector(
        float(desired_length_cm / base_x_cm),
        float(desired_width_cm / base_y_cm),
        1.0,
    )

    origin, extent = target_actor.get_actor_bounds(False)
    rotation = target_actor.get_actor_rotation()
    carrier_location = unreal.Vector(
        float(origin.x),
        float(origin.y),
        float(origin.z + extent.z + CARRIER_Z_OFFSET_CM),
    )

    removed_stale_overlay = _destroy_actor_if_present(STALE_OVERLAY_LABEL)
    carrier_actor, created = _ensure_carrier_actor(carrier_location, rotation)
    component = _first_static_mesh_component(carrier_actor)
    if component is None:
        raise RuntimeError(f"Carrier actor has no StaticMeshComponent: {_object_path(carrier_actor)}")

    _configure_mesh_component(component, dense_mesh, material_asset, scale)
    receiver_ok, receiver_error = _ensure_receiver_surface(carrier_actor)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    try:
        actor_subsystem.set_selected_level_actors([carrier_actor])
    except Exception:
        pass

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(receiver_ok),
        "summary": (
            f"Configured road-only carrier for {_object_name(target_actor)}: "
            f"carrier={_object_path(carrier_actor)} material={material_path}"
        ),
        "target_actor_label": getattr(target_actor, "get_actor_label", lambda: "")(),
        "target_actor_name": _object_name(target_actor),
        "target_actor_path": _object_path(target_actor),
        "target_resolution": target_resolution,
        "target_height_cm": target_height_cm,
        "carrier_actor_name": _object_name(carrier_actor),
        "carrier_actor_path": _object_path(carrier_actor),
        "carrier_component_path": _object_path(component),
        "carrier_created": created,
        "carrier_mesh_path": dense_mesh_path,
        "carrier_material_path": material_path,
        "carrier_location": {
            "x": carrier_location.x,
            "y": carrier_location.y,
            "z": carrier_location.z,
        },
        "carrier_scale": {
            "x": scale.x,
            "y": scale.y,
            "z": scale.z,
        },
        "desired_length_cm": desired_length_cm,
        "desired_width_cm": desired_width_cm,
        "removed_stale_overlay": removed_stale_overlay,
        "receiver_configured": receiver_ok,
        "receiver_error": receiver_error,
        "save_result": save_result,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": payload.get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
