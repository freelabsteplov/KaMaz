import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
TRAIL_LABEL = "SnowRuntimeTrailBridgeActor"
KAMAZ_LABEL = "Kamaz_SnowTest"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_snowtest_plow_sources.json",
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


def _safe_get(obj, prop, default=None):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return getattr(obj, prop, default)


def _vec_to_dict(value):
    if value is None:
        return None
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _component_row(component):
    relative_location = _safe_get(component, "relative_location", None)
    component_to_world = _safe_get(component, "component_to_world", None)
    world_location = getattr(component_to_world, "translation", None) if component_to_world else None
    return {
        "name": component.get_name(),
        "path": _path(component),
        "class": component.get_class().get_name(),
        "relative_location": _vec_to_dict(relative_location),
        "world_location": _vec_to_dict(world_location),
        "bEnablePlowClearing": _safe_get(component, "bEnablePlowClearing", None),
        "PlowLiftHeight": _safe_get(component, "PlowLiftHeight", None),
    }


def main():
    payload = {
        "map": MAP_PATH,
        "trail_actor": "",
        "trail_component": "",
        "source_override": "",
        "plow_candidates": [],
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = list(actor_subsystem.get_all_level_actors() or [])

        trail_actor = None
        kamaz_actor = None
        for actor in actors:
            label = _label(actor)
            if label == TRAIL_LABEL:
                trail_actor = actor
            elif label == KAMAZ_LABEL:
                kamaz_actor = actor

        if trail_actor:
            payload["trail_actor"] = _path(trail_actor)
            comp_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
            trail_component = trail_actor.get_component_by_class(comp_class) if comp_class else None
            if trail_component:
                payload["trail_component"] = _path(trail_component)
                payload["source_override"] = _path(_safe_get(trail_component, "SourceComponentOverride", None))

        if kamaz_actor:
            for component in list(kamaz_actor.get_components_by_class(unreal.SceneComponent) or []):
                name = component.get_name()
                if "PlowBrush" not in name and "BP_PlowBrush" not in name:
                    continue
                payload["plow_candidates"].append(_component_row(component))
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
