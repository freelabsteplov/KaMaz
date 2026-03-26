import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
MOVE_DELTA_CM = 900.0
TARGET_RVT_ASSET = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.RVT_SnowMask_MVP"
DEFAULT_STAMP_SPACING_CM = 15.0

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "phase6_runtime_trail_binary_probe.json",
)


def _log(message: str):
    unreal.log(f"[phase6_runtime_trail_binary_probe] {message}")


def _write_output(payload: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote output: {OUTPUT_PATH}")
    return OUTPUT_PATH


def _find_actor_by_label(label: str):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _is_point_in_aabb(point, center, extents):
    dx = abs(float(point.x - center.x))
    dy = abs(float(point.y - center.y))
    dz = abs(float(point.z - center.z))
    return (
        dx <= float(extents.x)
        and dy <= float(extents.y)
        and dz <= float(extents.z)
    )


def _find_target_rvt_volume(target_rvt):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fallback_volume = None
    for actor in actor_sub.get_all_level_actors():
        if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
            continue
        if fallback_volume is None:
            fallback_volume = actor

        volume_rvt = None
        getter = getattr(actor, "get_editor_property", None)
        if callable(getter):
            for prop_name in ("virtual_texture", "VirtualTexture"):
                try:
                    volume_rvt = getter(prop_name)
                except Exception:
                    volume_rvt = None
                if volume_rvt is not None:
                    break

        if volume_rvt is None:
            for comp in list(actor.get_components_by_class(unreal.ActorComponent) or []):
                getter = getattr(comp, "get_editor_property", None)
                if not callable(getter):
                    continue
                for prop_name in ("virtual_texture", "VirtualTexture", "RuntimeVirtualTexture"):
                    try:
                        volume_rvt = getter(prop_name)
                    except Exception:
                        volume_rvt = None
                    if volume_rvt is not None:
                        break
                if volume_rvt is not None:
                    break

        if target_rvt is None:
            return actor
        if volume_rvt == target_rvt:
            return actor
    return fallback_volume


def _serialize_cell_id(cell_id):
    return {"x": int(cell_id.x), "y": int(cell_id.y)}


def _serialize_snapshot(snapshot):
    return {
        "cell_id": _serialize_cell_id(snapshot.cell_id),
        "is_dirty": bool(snapshot.is_dirty),
        "pending_write_count": int(snapshot.pending_write_count),
        "dominant_surface_family": str(snapshot.dominant_surface_family),
        "save_relative_path": str(snapshot.save_relative_path),
    }


def _get_world_subsystem(world):
    subsystem_lib = getattr(unreal, "SubsystemBlueprintLibrary", None)
    if subsystem_lib is not None:
        getter = getattr(subsystem_lib, "get_world_subsystem", None)
        if callable(getter):
            return getter(world, unreal.SnowStateWorldSubsystem)

    direct_getter = getattr(world, "get_subsystem", None)
    if callable(direct_getter):
        try:
            return direct_getter(unreal.SnowStateWorldSubsystem)
        except Exception:
            return None
    return None


def _find_scene_plow_component(kamaz_actor):
    fallback = None
    for comp in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        if not isinstance(comp, unreal.SceneComponent):
            continue
        name = comp.get_name()
        if "BP_PlowBrush_Component" in name:
            return comp
        if ("PlowBrush" in name or "BP_PlowBrush" in name) and fallback is None:
            fallback = comp
    return fallback


def main():
    payload = {
        "map_path": MAP_PATH,
        "kamaz_path": "",
        "trail_actor_path": "",
        "target_rvt_path": "",
        "rvt_volume_path": "",
        "rvt_bounds_center": "",
        "rvt_bounds_extent": "",
        "kamaz_inside_rvt_before": False,
        "kamaz_inside_rvt_after_move": False,
        "trail_component_found": False,
        "source_component_path": "",
        "source_component_class": "",
        "stamp_count_before": 0,
        "stamp_count_after": 0,
        "visual_stamp_count_before": 0,
        "visual_stamp_count_after": 0,
        "mark_call_1": False,
        "mark_call_2": False,
        "active_cells_before": [],
        "active_cells_after": [],
        "flush_count": 0,
        "flushed_cells": [],
        "moving_clean_trail_marked": False,
        "trail_persists_after_move_proxy": False,
        "error": "",
    }

    start_location = None
    kamaz = None
    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

        kamaz = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
        trail_actor = _find_actor_by_label(TRAIL_ACTOR_LABEL)
        payload["kamaz_path"] = kamaz.get_path_name() if kamaz else ""
        payload["trail_actor_path"] = trail_actor.get_path_name() if trail_actor else ""

        if not kamaz or not trail_actor:
            payload["error"] = "Missing Kamaz_SnowTest or SnowRuntimeTrailBridgeActor"
            return payload

        component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
        trail_component = (
            trail_actor.get_component_by_class(component_class) if component_class else None
        )
        payload["trail_component_found"] = bool(trail_component)
        if not trail_component:
            payload["error"] = "SnowRuntimeTrailBridgeComponent not found"
            return payload

        plow_source = _find_scene_plow_component(kamaz)
        if not plow_source:
            payload["error"] = "Scene PlowBrush component not found on Kamaz"
            return payload

        payload["source_component_path"] = plow_source.get_path_name()
        payload["source_component_class"] = plow_source.get_class().get_name()

        target_rvt = unreal.load_asset(TARGET_RVT_ASSET)
        payload["target_rvt_path"] = target_rvt.get_path_name() if target_rvt else ""
        rvt_volume = _find_target_rvt_volume(target_rvt)
        payload["rvt_volume_path"] = rvt_volume.get_path_name() if rvt_volume else ""
        if rvt_volume:
            center, extents = rvt_volume.get_actor_bounds(False)
            payload["rvt_bounds_center"] = str(center)
            payload["rvt_bounds_extent"] = str(extents)
            payload["kamaz_inside_rvt_before"] = _is_point_in_aabb(kamaz.get_actor_location(), center, extents)

        trail_component.set_editor_property("bEnableRuntimeTrail", True)
        trail_component.set_editor_property("bMarkPersistentSnowState", True)
        trail_component.set_editor_property("StampSpacingCm", DEFAULT_STAMP_SPACING_CM)
        trail_component.set_editor_property("PersistentPlowLengthCm", 120.0)
        trail_component.set_editor_property("PersistentPlowWidthCm", 320.0)
        trail_component.set_editor_property("PersistentSurfaceFamily", unreal.SnowReceiverSurfaceFamily.LANDSCAPE)
        trail_component.set_editor_property("bUseSourceHeightGate", True)
        trail_component.set_editor_property("SourceActiveMaxRelativeZ", -0.5)
        trail_component.set_editor_property("RuntimeHeightAmplitudeWhenActive", -100.0)
        trail_component.set_editor_property("RuntimeHeightAmplitudeWhenInactive", 0.0)
        trail_component.set_editor_property("SourceComponentOverride", plow_source)
        trail_component.set_editor_property("bEnableRvtVisualStamp", True)
        if target_rvt:
            trail_component.set_editor_property("TargetRvt", target_rvt)

        settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
        if settings:
            settings.set_editor_property("bEnablePersistentSnowStateV1", True)

        world = unreal.EditorLevelLibrary.get_editor_world()
        subsystem = _get_world_subsystem(world)
        if subsystem:
            payload["active_cells_before"] = [
                _serialize_cell_id(cell_id)
                for cell_id in list(subsystem.get_active_cell_ids() or [])
            ]

        start_location = kamaz.get_actor_location()

        payload["stamp_count_before"] = int(trail_component.get_stamp_count())
        if hasattr(trail_component, "get_visual_stamp_count"):
            payload["visual_stamp_count_before"] = int(trail_component.get_visual_stamp_count())
        payload["mark_call_1"] = bool(trail_component.record_trail_stamp_now())

        moved_location = unreal.Vector(
            float(start_location.x + MOVE_DELTA_CM),
            float(start_location.y),
            float(start_location.z),
        )
        kamaz.set_actor_location(moved_location, False, False)
        if rvt_volume:
            center_after, extents_after = rvt_volume.get_actor_bounds(False)
            payload["kamaz_inside_rvt_after_move"] = _is_point_in_aabb(moved_location, center_after, extents_after)

        payload["mark_call_2"] = bool(trail_component.record_trail_stamp_now())
        payload["stamp_count_after"] = int(trail_component.get_stamp_count())
        if hasattr(trail_component, "get_visual_stamp_count"):
            payload["visual_stamp_count_after"] = int(trail_component.get_visual_stamp_count())

        flushed = list(unreal.SnowStateBlueprintLibrary.flush_persistent_snow_state(kamaz) or [])
        payload["flush_count"] = len(flushed)
        payload["flushed_cells"] = [_serialize_snapshot(snapshot) for snapshot in flushed]

        if subsystem:
            payload["active_cells_after"] = [
                _serialize_cell_id(cell_id)
                for cell_id in list(subsystem.get_active_cell_ids() or [])
            ]

        payload["moving_clean_trail_marked"] = (
            payload["mark_call_1"]
            or payload["mark_call_2"]
            or (payload["stamp_count_after"] > payload["stamp_count_before"])
            or (payload["visual_stamp_count_after"] > payload["visual_stamp_count_before"])
        )
        payload["trail_persists_after_move_proxy"] = (
            payload["flush_count"] > 0
            or len(payload["active_cells_after"]) > len(payload["active_cells_before"])
        )
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        if kamaz and start_location is not None:
            kamaz.set_actor_location(start_location, False, False)
        payload["output_path"] = _write_output(payload)
        return payload


if __name__ == "__main__":
    main()
