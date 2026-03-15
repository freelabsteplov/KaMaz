import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import rebuild_visible_road_snow_receiver as rr


OUTPUT_BASENAME = "spawn_direct_rt_debug_overlay_for_road2"
TARGET_ACTOR_LABEL = "Road2"
PLANE_MESH_PATH = "/Engine/BasicShapes/Plane.Plane"
OVERLAY_Z_OFFSET_CM = 2.0
PLANE_BASE_SIZE_CM = 100.0
OVERLAY_TEST_LENGTH_CM = 25000.0
OVERLAY_TEST_WIDTH_CM = 2600.0
DEBUG_EMISSIVE_MULTIPLIER = 80.0


def _log(message: str) -> None:
    unreal.log(f"[spawn_direct_rt_debug_overlay_for_road2] {message}")


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


def _find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = []
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            actor_label = ""
        if actor_label == label:
            matches.append(actor)
    if not matches:
        raise RuntimeError(f"Could not find actor with label '{label}'.")
    return matches[0]


def _find_overlay_actor(target_label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == target_label:
                return actor
        except Exception:
            continue
    return None


def _delete_stale_overlay_actors(keep_label: str) -> list[str]:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    removed = []
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            continue
        if not actor_label.startswith("SnowOverlay_"):
            continue
        if actor_label == keep_label:
            continue
        try:
            if actor_subsystem.destroy_actor(actor):
                removed.append(actor_label)
        except Exception:
            continue
    return removed


def _get_actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return origin, extent


def _ensure_overlay_actor(target_label: str, location: unreal.Vector, rotation: unreal.Rotator):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    overlay_actor = _find_overlay_actor(target_label)
    if overlay_actor is None:
        overlay_actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        if overlay_actor is None:
            raise RuntimeError("Failed to spawn overlay actor.")
        overlay_actor.set_actor_label(target_label)
    else:
        overlay_actor.set_actor_location(location, False, False)
        overlay_actor.set_actor_rotation(rotation, False)
    return overlay_actor


def _configure_overlay_component(overlay_actor, static_mesh, material_asset, scale: unreal.Vector):
    component = overlay_actor.get_component_by_class(unreal.StaticMeshComponent)
    if component is None:
        raise RuntimeError(f"Overlay actor has no StaticMeshComponent: {_object_path(overlay_actor)}")

    component.set_static_mesh(static_mesh)
    component.set_material(0, material_asset)
    component.set_relative_scale3d(scale)
    component.set_editor_property("cast_shadow", False)
    component.set_editor_property("affect_distance_field_lighting", False)
    component.set_editor_property("visible_in_ray_tracing", False)
    component.set_editor_property("receives_decals", False)
    component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return component


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    module = importlib.reload(rr)
    module.DEBUG_DIRECT_RT_VIS = True
    module.DEBUG_FORCE_SOLID_COLOR = False
    module.DEBUG_DIRECT_TEXCOORD_RT_VIS = False
    module.DEBUG_USE_TEXCOORD_CLEAR_MASK = False
    module.DEBUG_EMISSIVE_MULTIPLIER = DEBUG_EMISSIVE_MULTIPLIER

    rebuild_result = module.run(output_dir)
    material_asset = unreal.EditorAssetLibrary.load_asset(module.RECEIVER_INSTANCE_PATH)
    if material_asset is None:
        raise RuntimeError(f"Could not load receiver instance: {module.RECEIVER_INSTANCE_PATH}")

    plane_mesh = unreal.EditorAssetLibrary.load_asset(PLANE_MESH_PATH)
    if plane_mesh is None:
        raise RuntimeError(f"Could not load plane mesh: {PLANE_MESH_PATH}")

    target_actor = _find_actor_by_label(TARGET_ACTOR_LABEL)
    origin, extent = _get_actor_bounds(target_actor)
    rotation = target_actor.get_actor_rotation()

    overlay_location = unreal.Vector(float(origin.x), float(origin.y), float(origin.z + extent.z + OVERLAY_Z_OFFSET_CM))
    overlay_scale = unreal.Vector(
        max(float(OVERLAY_TEST_LENGTH_CM / PLANE_BASE_SIZE_CM), 0.01),
        max(float(OVERLAY_TEST_WIDTH_CM / PLANE_BASE_SIZE_CM), 0.01),
        1.0,
    )

    overlay_label = f"SnowOverlay_{TARGET_ACTOR_LABEL}"
    removed_overlay_labels = _delete_stale_overlay_actors(overlay_label)
    overlay_actor = _ensure_overlay_actor(overlay_label, overlay_location, rotation)
    overlay_component = _configure_overlay_component(overlay_actor, plane_mesh, material_asset, overlay_scale)

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(rebuild_result.get("success", False)),
        "summary": rebuild_result.get("summary", ""),
        "target_actor_label": TARGET_ACTOR_LABEL,
        "target_actor_name": _object_name(target_actor),
        "target_actor_path": _object_path(target_actor),
        "overlay_actor_name": _object_name(overlay_actor),
        "overlay_actor_path": _object_path(overlay_actor),
        "overlay_component_path": _object_path(overlay_component),
        "overlay_material_path": _object_path(material_asset),
        "overlay_location": {
            "x": overlay_location.x,
            "y": overlay_location.y,
            "z": overlay_location.z,
        },
        "overlay_scale": {
            "x": overlay_scale.x,
            "y": overlay_scale.y,
            "z": overlay_scale.z,
        },
        "removed_overlay_labels": removed_overlay_labels,
        "debug_emissive_multiplier": DEBUG_EMISSIVE_MULTIPLIER,
        "save_result": save_result,
        "rebuild_output_path": rebuild_result.get("output_path", ""),
        "notes": [
            "Applies a world-space RT debug material to the overlay plane above Road2.",
            "Use it to verify that plow writes reach the overlay through world mapping before tuning visible snow again.",
        ],
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
