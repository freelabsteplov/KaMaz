import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_apply_landscape_runtime_bridge_fix.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    try:
        return actor.get_actor_label()
    except Exception:
        return ""


def _find_actor(world, label):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    for actor in actors:
        if _label(actor) == label:
            return actor
    return None


def _find_plow_component(actor):
    if not actor:
        return None
    try:
        components = actor.get_components_by_class(unreal.SceneComponent)
    except Exception:
        components = []
    for component in components:
        name = component.get_name()
        if "BP_PlowBrush_Component" in name:
            return component
    for component in components:
        name = component.get_name()
        if "PlowBrush" in name or "BP_PlowBrush" in name:
            return component
    return None


result = {
    "map_path": MAP_PATH,
    "landscape_actor_path": "",
    "landscape_material_before": "",
    "trail_actor_path": "",
    "trail_component_path": "",
    "plow_component_path": "",
    "trail_component_values_after": {},
    "persistent_snow_enabled_after": None,
    "saved_level": False,
    "saved_packages": False,
    "error": "",
}

try:
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    landscape = _find_actor(world, "Landscape")
    trail_actor = _find_actor(world, "SnowRuntimeTrailBridgeActor")
    kamaz = _find_actor(world, "Kamaz_SnowTest")
    if not landscape:
        raise RuntimeError("Landscape actor not found")
    if not trail_actor:
        raise RuntimeError("SnowRuntimeTrailBridgeActor not found")
    if not kamaz:
        raise RuntimeError("Kamaz_SnowTest not found")

    result["landscape_actor_path"] = _path(landscape)
    result["trail_actor_path"] = _path(trail_actor)
    result["landscape_material_before"] = _path(landscape.get_editor_property("landscape_material"))

    plow_component = _find_plow_component(kamaz)
    if not plow_component:
        raise RuntimeError("Plow component not found on Kamaz_SnowTest")
    result["plow_component_path"] = _path(plow_component)

    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    trail_component = trail_actor.get_component_by_class(component_class) if component_class else None
    if not trail_component:
        raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")
    result["trail_component_path"] = _path(trail_component)

    trail_actor.modify()
    trail_component.modify()

    updates = {
        "bEnableRuntimeTrail": True,
        "StampSpacingCm": 20.0,
        "bMarkPersistentSnowState": True,
        "PersistentPlowLengthCm": 120.0,
        "PersistentPlowWidthCm": 320.0,
        "PersistentSurfaceFamily": unreal.SnowReceiverSurfaceFamily.LANDSCAPE,
        "SourceComponentOverride": plow_component,
        "bEnableRvtVisualStamp": True,
        "RuntimeHeightAmplitudeWhenActive": -100.0,
        "RuntimeHeightAmplitudeWhenInactive": 0.0,
        "bUseSourceHeightGate": True,
        "SourceActiveMaxRelativeZ": -0.5,
    }

    for name, value in updates.items():
        trail_component.set_editor_property(name, value)

    if callable(getattr(trail_component, "post_edit_change", None)):
        trail_component.post_edit_change()
    if callable(getattr(trail_actor, "post_edit_change", None)):
        trail_actor.post_edit_change()
    if callable(getattr(trail_actor, "mark_package_dirty", None)):
        trail_actor.mark_package_dirty()

    for name in updates.keys():
        value = trail_component.get_editor_property(name)
        result["trail_component_values_after"][name] = _path(value) if hasattr(value, "get_path_name") else str(value)

    settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
    if settings:
        settings.set_editor_property("bEnablePersistentSnowStateV1", True)
        if callable(getattr(settings, "save_config", None)):
            settings.save_config()
        result["persistent_snow_enabled_after"] = bool(
            settings.get_editor_property("bEnablePersistentSnowStateV1")
        )

    result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    result["saved_packages"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))
