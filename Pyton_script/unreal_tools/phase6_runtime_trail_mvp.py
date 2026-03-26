import json
import os

import traceback

import unreal

MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
TRAIL_ACTOR_CLASS = "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeActor"
TRAIL_COMPONENT_CLASS = "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
BRIDGE_ACTOR_LABEL = "SnowHeightBridgeSurface_MVP"
RECEIVER_SET_TAG = "SnowMVPRuntimeTrail"
TARGET_RVT_ASSET = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.RVT_SnowMask_MVP"
KAMAZ_BRIDGE_RELOCATE_X_OFFSET_CM = -260.0
KAMAZ_BRIDGE_RELOCATE_Z_OFFSET_CM = 220.0
LANDSCAPE_ACTIVE_MAX_RELATIVE_Z = -0.5
DEFAULT_STAMP_SPACING_CM = 15.0

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "phase6_runtime_trail_mvp.json",
)


def _log(message: str):
    unreal.log(f"[phase6_runtime_trail_mvp] {message}")


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
        for prop_name in ("virtual_texture", "VirtualTexture"):
            getter = getattr(actor, "get_editor_property", None)
            if callable(getter):
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


def _maybe_relocate_kamaz_to_bridge_zone(kamaz, bridge, rvt_volume):
    result = {
        "kamaz_relocated_for_rvt_zone": False,
        "kamaz_inside_rvt_before": False,
        "kamaz_inside_rvt_after": False,
        "kamaz_location_before": "",
        "kamaz_location_after": "",
        "rvt_volume_path": rvt_volume.get_path_name() if rvt_volume else "",
        "rvt_bounds_center": "",
        "rvt_bounds_extent": "",
    }

    if not kamaz:
        return result

    kamaz_loc = kamaz.get_actor_location()
    result["kamaz_location_before"] = str(kamaz_loc)

    inside_before = False
    center = None
    extents = None
    if rvt_volume:
        center, extents = rvt_volume.get_actor_bounds(False)
        result["rvt_bounds_center"] = str(center)
        result["rvt_bounds_extent"] = str(extents)
        inside_before = _is_point_in_aabb(kamaz_loc, center, extents)
    result["kamaz_inside_rvt_before"] = inside_before

    bridge_loc = bridge.get_actor_location() if bridge else None
    far_from_bridge = False
    if bridge_loc:
        dx = float(kamaz_loc.x - bridge_loc.x)
        dy = float(kamaz_loc.y - bridge_loc.y)
        far_from_bridge = (dx * dx + dy * dy) > (1200.0 * 1200.0)

    should_relocate = (rvt_volume is not None and not inside_before) or far_from_bridge
    if should_relocate and bridge_loc:
        target_loc = unreal.Vector(
            float(bridge_loc.x + KAMAZ_BRIDGE_RELOCATE_X_OFFSET_CM),
            float(bridge_loc.y),
            float(bridge_loc.z + KAMAZ_BRIDGE_RELOCATE_Z_OFFSET_CM),
        )
        kamaz.set_actor_location(target_loc, False, False)
        result["kamaz_relocated_for_rvt_zone"] = True

    kamaz_loc_after = kamaz.get_actor_location()
    result["kamaz_location_after"] = str(kamaz_loc_after)

    if rvt_volume:
        center_after, extents_after = rvt_volume.get_actor_bounds(False)
        result["kamaz_inside_rvt_after"] = _is_point_in_aabb(kamaz_loc_after, center_after, extents_after)
    else:
        result["kamaz_inside_rvt_after"] = not far_from_bridge

    return result


def _ensure_trail_actor(location):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_actor_label() == TRAIL_ACTOR_LABEL:
            return actor, False

    actor_class = unreal.load_class(None, TRAIL_ACTOR_CLASS)
    if actor_class is None:
        raise RuntimeError(f"Trail actor class not found: {TRAIL_ACTOR_CLASS}")

    spawned = actor_sub.spawn_actor_from_class(actor_class, location, unreal.Rotator(0.0, 0.0, 0.0))
    if not spawned:
        raise RuntimeError("Failed to spawn trail actor.")
    spawned.set_actor_label(TRAIL_ACTOR_LABEL)
    return spawned, True


def _normalize_bridge_result(raw_result):
    if isinstance(raw_result, bool):
        return raw_result
    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                return item
    return False


def _configure_receiver_surface(actor):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    raw_result = None
    if bridge is not None:
        actor_path = actor.get_path_name()
        try:
            raw_result = bridge.ensure_snow_receiver_surfaces_on_actors(
                "",
                [actor_path],
                unreal.SnowReceiverSurfaceFamily.ROAD,
                100,
                RECEIVER_SET_TAG,
                False,
                False,
            )
        except Exception as exc:
            _log(f"ensure_snow_receiver_surfaces_on_actors failed: {exc}")

    receiver = actor.get_component_by_class(unreal.SnowReceiverSurfaceComponent)

    if receiver is None:
        return bool(_normalize_bridge_result(raw_result))

    receiver.set_editor_property("bParticipatesInPersistentSnowState", True)
    receiver.set_editor_property("SurfaceFamily", unreal.SnowReceiverSurfaceFamily.ROAD)
    receiver.set_editor_property("ReceiverPriority", 100)
    receiver.set_editor_property("ReceiverSetTag", RECEIVER_SET_TAG)
    return True


def _ensure_settings():
    settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
    if settings:
        settings.set_editor_property("bEnablePersistentSnowStateV1", True)
        save_config = getattr(settings, "save_config", None)
        if callable(save_config):
            save_config()
    return bool(settings)


def main():
    payload = {
        "map_path": MAP_PATH,
        "runtime_component_attached": False,
        "receiver_configured": False,
        "settings_enabled": False,
        "source_component_bound": False,
        "source_component_path": "",
        "source_component_class": "",
        "kamaz_path": "",
        "bridge_path": "",
        "target_rvt_path": "",
        "rvt_volume_path": "",
        "rvt_bounds_center": "",
        "rvt_bounds_extent": "",
        "kamaz_location_before": "",
        "kamaz_location_after": "",
        "kamaz_inside_rvt_before": False,
        "kamaz_inside_rvt_after": False,
        "kamaz_relocated_for_rvt_zone": False,
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        kamaz = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
        bridge = _find_actor_by_label(BRIDGE_ACTOR_LABEL)
        payload["kamaz_path"] = kamaz.get_path_name() if kamaz else ""
        payload["bridge_path"] = bridge.get_path_name() if bridge else ""

        if not kamaz or not bridge:
            payload["error"] = "Missing Kamaz or bridge actor"
            return payload

        target_rvt = unreal.load_asset(TARGET_RVT_ASSET)
        payload["target_rvt_path"] = target_rvt.get_path_name() if target_rvt else ""
        rvt_volume = _find_target_rvt_volume(target_rvt)

        relocate = _maybe_relocate_kamaz_to_bridge_zone(kamaz, bridge, rvt_volume)
        payload.update(relocate)

        trail_actor, created = _ensure_trail_actor(kamaz.get_actor_location())
        payload["runtime_component_attached"] = True
        payload["runtime_component_created"] = created

        payload["rvt_volume_path"] = rvt_volume.get_path_name() if rvt_volume else ""

        component_class = unreal.load_class(None, TRAIL_COMPONENT_CLASS)
        trail_component = (
            trail_actor.get_component_by_class(component_class) if component_class else None
        )
        if trail_component:
            trail_component.set_editor_property("StampSpacingCm", DEFAULT_STAMP_SPACING_CM)
            trail_component.set_editor_property("PersistentPlowLengthCm", 120.0)
            trail_component.set_editor_property("PersistentPlowWidthCm", 320.0)
            trail_component.set_editor_property("bEnableRuntimeTrail", True)
            trail_component.set_editor_property("bMarkPersistentSnowState", True)
            trail_component.set_editor_property("bEnableRvtVisualStamp", True)
            trail_component.set_editor_property("bUseSourceHeightGate", True)
            trail_component.set_editor_property("SourceActiveMaxRelativeZ", LANDSCAPE_ACTIVE_MAX_RELATIVE_Z)
            trail_component.set_editor_property("PersistentSurfaceFamily", unreal.SnowReceiverSurfaceFamily.LANDSCAPE)
            trail_component.set_editor_property("RuntimeHeightAmplitudeWhenActive", -100.0)
            trail_component.set_editor_property("RuntimeHeightAmplitudeWhenInactive", 0.0)
            if target_rvt:
                trail_component.set_editor_property("TargetRvt", target_rvt)

        plow_source = None
        fallback_plow = None
        for comp in list(kamaz.get_components_by_class(unreal.ActorComponent) or []):
            comp_name = comp.get_name()
            is_scene_component = isinstance(comp, unreal.SceneComponent)
            if not is_scene_component:
                continue
            if "BP_PlowBrush_Component" in comp_name:
                plow_source = comp
                break
            if ("PlowBrush" in comp_name or "BP_PlowBrush" in comp_name) and fallback_plow is None:
                fallback_plow = comp
        if plow_source is None:
            plow_source = fallback_plow
        if trail_component and plow_source:
            trail_component.set_editor_property("SourceComponentOverride", plow_source)
            payload["source_component_bound"] = True
            payload["source_component_path"] = plow_source.get_path_name()
            payload["source_component_class"] = plow_source.get_class().get_name()
            trail_actor.set_actor_location(kamaz.get_actor_location(), False, False)

        payload["receiver_configured"] = _configure_receiver_surface(bridge)
        payload["settings_enabled"] = _ensure_settings()
        unreal.EditorLoadingAndSavingUtils.save_current_level()
    except Exception as exc:
        payload["error"] = str(exc)
        unreal.log_error(f"[phase6_runtime_trail_mvp] Exception: {exc}\n{traceback.format_exc()}")
    finally:
        payload["output_path"] = _write_output(payload)
        return payload


if __name__ == "__main__":
    main()
