import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_snowtest_plow_height_engagement.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_get(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            return default
    return getattr(obj, property_name, default)


def _safe_set(obj, property_name, value):
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(property_name, value)
            return True, ""
        except Exception as exc:
            return False, str(exc)
    try:
        setattr(obj, property_name, value)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _find_actor_by_label(label):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _find_trail_component(trail_actor):
    if not trail_actor:
        return None
    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    if component_class:
        component = trail_actor.get_component_by_class(component_class)
        if component:
            return component
    for component in list(trail_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if "SnowRuntimeTrailBridgeComponent" in component.get_class().get_name():
                return component
        except Exception:
            continue
    return None


def _find_plow_component(kamaz_actor):
    preferred = None
    fallback = None
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if not isinstance(component, unreal.SceneComponent):
                continue
        except Exception:
            continue

        name = component.get_name()
        class_name = component.get_class().get_name()
        if "BP_PlowBrush_Component" in name or "BP_PlowBrush_Component" in class_name:
            preferred = component
            break
        if ("PlowBrush" in name or "BP_PlowBrush" in name) and fallback is None:
            fallback = component
    return preferred or fallback


def _ensure_snowtest_loaded():
    kamaz_actor = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
    trail_actor = _find_actor_by_label(TRAIL_ACTOR_LABEL)
    if kamaz_actor and trail_actor:
        return kamaz_actor, trail_actor

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return _find_actor_by_label(KAMAZ_ACTOR_LABEL), _find_actor_by_label(TRAIL_ACTOR_LABEL)


def _capture_counts(trail_component):
    row = {
        "stamp_count": None,
        "visual_stamp_count": None,
    }
    try:
        row["stamp_count"] = int(trail_component.get_stamp_count())
    except Exception:
        row["stamp_count"] = None
    try:
        row["visual_stamp_count"] = int(trail_component.get_visual_stamp_count())
    except Exception:
        row["visual_stamp_count"] = None
    return row


def _move_kamaz(kamaz_actor, base_location, offset_x):
    location = unreal.Vector(
        float(base_location.x + offset_x),
        float(base_location.y),
        float(base_location.z),
    )
    kamaz_actor.set_actor_location(location, False, False)
    return location


def _write_output(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return OUTPUT_PATH


def main():
    payload = {
        "map": MAP_PATH,
        "kamaz_path": "",
        "trail_actor_path": "",
        "trail_component_path": "",
        "plow_source_path": "",
        "plow_owner_path": "",
        "settings_before": {},
        "owner_before": {},
        "source_before": {},
        "engaged_probe": {},
        "lifted_probe": {},
        "error": "",
    }

    kamaz_actor = None
    trail_component = None
    plow_source = None
    plow_owner = None
    start_location = None
    original_trail_props = {}
    original_owner_props = {}
    original_source_props = {}

    try:
        kamaz_actor, trail_actor = _ensure_snowtest_loaded()
        payload["kamaz_path"] = _path(kamaz_actor)
        payload["trail_actor_path"] = _path(trail_actor)
        if not kamaz_actor or not trail_actor:
            raise RuntimeError("Missing Kamaz_SnowTest or SnowRuntimeTrailBridgeActor")

        trail_component = _find_trail_component(trail_actor)
        payload["trail_component_path"] = _path(trail_component)
        if not trail_component:
            raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")

        plow_source = _find_plow_component(kamaz_actor)
        payload["plow_source_path"] = _path(plow_source)
        if not plow_source:
            raise RuntimeError("BP_PlowBrush_Component not found on Kamaz_SnowTest")
        plow_owner = plow_source.get_owner()
        payload["plow_owner_path"] = _path(plow_owner)

        start_location = kamaz_actor.get_actor_location()

        original_trail_props = {
            "bEnableRuntimeTrail": _safe_get(trail_component, "bEnableRuntimeTrail", True),
            "bUseSourceHeightGate": _safe_get(trail_component, "bUseSourceHeightGate", False),
            "SourceComponentOverride": _safe_get(trail_component, "SourceComponentOverride", None),
        }
        original_owner_props = {
            "PlowLiftHeight": _safe_get(plow_owner, "PlowLiftHeight", None),
            "TargetPlowHeight": _safe_get(plow_owner, "TargetPlowHeight", None),
        }
        original_source_props = {
            "bEnablePlowClearing": _safe_get(plow_source, "bEnablePlowClearing", True),
            "PlowLiftHeight": _safe_get(plow_source, "PlowLiftHeight", 0.0),
        }

        payload["settings_before"] = {
            "StampSpacingCm": _safe_get(trail_component, "StampSpacingCm", None),
            "MinStampEngagementToWrite": _safe_get(trail_component, "MinStampEngagementToWrite", None),
            "PlowLiftHeightForNoEffect": _safe_get(trail_component, "PlowLiftHeightForNoEffect", None),
            "bUseSourceHeightGate": original_trail_props["bUseSourceHeightGate"],
        }
        payload["source_before"] = {
            "bEnablePlowClearing": original_source_props["bEnablePlowClearing"],
            "PlowLiftHeight": original_source_props["PlowLiftHeight"],
        }
        payload["owner_before"] = {
            "PlowLiftHeight": original_owner_props["PlowLiftHeight"],
            "TargetPlowHeight": original_owner_props["TargetPlowHeight"],
        }

        _safe_set(trail_component, "bEnableRuntimeTrail", True)
        _safe_set(trail_component, "bUseSourceHeightGate", False)
        _safe_set(trail_component, "SourceComponentOverride", plow_source)
        _safe_set(plow_source, "bEnablePlowClearing", True)

        max_lift_height = float(_safe_get(trail_component, "PlowLiftHeightForNoEffect", 1.0) or 1.0)
        spacing_cm = float(_safe_get(trail_component, "StampSpacingCm", 10.0) or 10.0)
        move_delta = max(spacing_cm + 40.0, 120.0)

        _safe_set(plow_owner, "PlowLiftHeight", 0.0)
        _safe_set(plow_owner, "TargetPlowHeight", 0.0)
        _safe_set(plow_source, "PlowLiftHeight", 0.0)
        engaged_before = _capture_counts(trail_component)
        engaged_written = bool(trail_component.record_trail_stamp_now())
        engaged_after = _capture_counts(trail_component)
        payload["engaged_probe"] = {
            "applied_plow_lift_height": 0.0,
            "observed_owner_plow_lift_height": _safe_get(plow_owner, "PlowLiftHeight", None),
            "observed_owner_target_plow_height": _safe_get(plow_owner, "TargetPlowHeight", None),
            "observed_plow_lift_height": _safe_get(plow_source, "PlowLiftHeight", None),
            "observed_bEnablePlowClearing": _safe_get(plow_source, "bEnablePlowClearing", None),
            "counts_before": engaged_before,
            "record_trail_stamp_now": engaged_written,
            "counts_after": engaged_after,
        }

        _move_kamaz(kamaz_actor, start_location, move_delta)

        _safe_set(plow_owner, "PlowLiftHeight", max_lift_height)
        _safe_set(plow_owner, "TargetPlowHeight", max_lift_height)
        _safe_set(plow_source, "PlowLiftHeight", max_lift_height)
        lifted_before = _capture_counts(trail_component)
        lifted_written = bool(trail_component.record_trail_stamp_now())
        lifted_after = _capture_counts(trail_component)
        payload["lifted_probe"] = {
            "applied_plow_lift_height": max_lift_height,
            "observed_owner_plow_lift_height": _safe_get(plow_owner, "PlowLiftHeight", None),
            "observed_owner_target_plow_height": _safe_get(plow_owner, "TargetPlowHeight", None),
            "observed_plow_lift_height": _safe_get(plow_source, "PlowLiftHeight", None),
            "observed_bEnablePlowClearing": _safe_get(plow_source, "bEnablePlowClearing", None),
            "counts_before": lifted_before,
            "record_trail_stamp_now": lifted_written,
            "counts_after": lifted_after,
        }

        _move_kamaz(kamaz_actor, start_location, move_delta * 2.0)

        _safe_set(plow_source, "bEnablePlowClearing", False)
        _safe_set(plow_owner, "PlowLiftHeight", 0.0)
        _safe_set(plow_owner, "TargetPlowHeight", 0.0)
        _safe_set(plow_source, "PlowLiftHeight", 0.0)
        disabled_before = _capture_counts(trail_component)
        disabled_written = bool(trail_component.record_trail_stamp_now())
        disabled_after = _capture_counts(trail_component)
        payload["disabled_probe"] = {
            "applied_plow_lift_height": 0.0,
            "observed_owner_plow_lift_height": _safe_get(plow_owner, "PlowLiftHeight", None),
            "observed_owner_target_plow_height": _safe_get(plow_owner, "TargetPlowHeight", None),
            "observed_plow_lift_height": _safe_get(plow_source, "PlowLiftHeight", None),
            "observed_bEnablePlowClearing": _safe_get(plow_source, "bEnablePlowClearing", None),
            "counts_before": disabled_before,
            "record_trail_stamp_now": disabled_written,
            "counts_after": disabled_after,
        }
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        if plow_source:
            _safe_set(plow_source, "bEnablePlowClearing", original_source_props.get("bEnablePlowClearing", True))
            _safe_set(plow_source, "PlowLiftHeight", original_source_props.get("PlowLiftHeight", 0.0))
        if plow_owner:
            if original_owner_props.get("PlowLiftHeight", None) is not None:
                _safe_set(plow_owner, "PlowLiftHeight", original_owner_props.get("PlowLiftHeight"))
            if original_owner_props.get("TargetPlowHeight", None) is not None:
                _safe_set(plow_owner, "TargetPlowHeight", original_owner_props.get("TargetPlowHeight"))
        if trail_component:
            _safe_set(trail_component, "bEnableRuntimeTrail", original_trail_props.get("bEnableRuntimeTrail", True))
            _safe_set(trail_component, "bUseSourceHeightGate", original_trail_props.get("bUseSourceHeightGate", False))
            _safe_set(trail_component, "SourceComponentOverride", original_trail_props.get("SourceComponentOverride", None))
        if kamaz_actor and start_location is not None:
            kamaz_actor.set_actor_location(start_location, False, False)
        payload["output_path"] = _write_output(payload)


if __name__ == "__main__":
    main()
