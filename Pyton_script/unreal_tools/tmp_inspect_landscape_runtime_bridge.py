import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_inspect_landscape_runtime_bridge.json",
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
    "landscape_material": "",
    "trail_actor_path": "",
    "trail_component_path": "",
    "trail_component_values": {},
    "kamaz_actor_path": "",
    "plow_component_path": "",
    "persistent_snow_enabled": None,
    "error": "",
}

try:
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    landscape = _find_actor(world, "Landscape")
    trail_actor = _find_actor(world, "SnowRuntimeTrailBridgeActor")
    kamaz = _find_actor(world, "Kamaz_SnowTest")

    if landscape:
        result["landscape_actor_path"] = _path(landscape)
        material = landscape.get_editor_property("landscape_material")
        result["landscape_material"] = _path(material)

    if trail_actor:
        result["trail_actor_path"] = _path(trail_actor)
        component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
        trail_component = trail_actor.get_component_by_class(component_class) if component_class else None
        if trail_component:
            result["trail_component_path"] = _path(trail_component)
            for name in (
                "bEnableRuntimeTrail",
                "StampSpacingCm",
                "bMarkPersistentSnowState",
                "PersistentPlowLengthCm",
                "PersistentPlowWidthCm",
                "PersistentSurfaceFamily",
                "SourceComponentOverride",
                "bEnableRvtVisualStamp",
                "RuntimeHeightAmplitudeWhenActive",
                "RuntimeHeightAmplitudeWhenInactive",
                "bUseSourceHeightGate",
                "SourceActiveMaxRelativeZ",
            ):
                value = trail_component.get_editor_property(name)
                result["trail_component_values"][name] = _path(value) if hasattr(value, "get_path_name") else str(value)

    if kamaz:
        result["kamaz_actor_path"] = _path(kamaz)
        result["plow_component_path"] = _path(_find_plow_component(kamaz))

    settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
    if settings:
        result["persistent_snow_enabled"] = bool(settings.get_editor_property("bEnablePersistentSnowStateV1"))
except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))
