import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
KAMAZ_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_BASENAME = "runtime_kamaz_plow_actor"


def _log(message: str) -> None:
    unreal.log(f"[inspect_runtime_kamaz_plow_actor] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _vec_to_dict(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot_to_dict(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Name):
        return str(value)
    if isinstance(value, unreal.Vector):
        return _vec_to_dict(value)
    if isinstance(value, unreal.Rotator):
        return _rot_to_dict(value)
    if isinstance(value, unreal.Array):
        return [_serialize_value(item) for item in value]
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    path_name = _object_path(value)
    if path_name:
        return path_name
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _component_summary(component) -> dict:
    if component is None:
        return {}

    child_actor = None
    get_child_actor = getattr(component, "get_child_actor", None)
    if callable(get_child_actor):
        try:
            child_actor = get_child_actor()
        except Exception:
            child_actor = None

    return {
        "name": _object_name(component),
        "path": _object_path(component),
        "class": _object_path(component.get_class()),
        "relative_location": _serialize_value(_safe_property(component, "relative_location")),
        "relative_rotation": _serialize_value(_safe_property(component, "relative_rotation")),
        "relative_scale3d": _serialize_value(_safe_property(component, "relative_scale3d")),
        "world_location": _serialize_value(component.get_component_location()) if hasattr(component, "get_component_location") else None,
        "world_rotation": _serialize_value(component.get_component_rotation()) if hasattr(component, "get_component_rotation") else None,
        "world_scale3d": _serialize_value(component.get_component_scale()) if hasattr(component, "get_component_scale") else None,
        "box_extent": _serialize_value(_safe_property(component, "box_extent")),
        "child_actor_class": _serialize_value(_safe_property(component, "child_actor_class")),
        "child_actor": _object_path(child_actor),
    }


def _actor_summary(actor) -> dict:
    if actor is None:
        return {}

    root_component = _safe_property(actor, "root_component")
    components = []
    get_components = getattr(actor, "get_components_by_class", None)
    if callable(get_components):
        try:
            for component in list(get_components(unreal.ActorComponent) or []):
                components.append(_component_summary(component))
        except Exception:
            components = []

    return {
        "name": _object_name(actor),
        "path": _object_path(actor),
        "class": _object_path(actor.get_class()),
        "root_component": _component_summary(root_component),
        "components": components,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError(f"Map asset does not exist: {MAP_PATH}")

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    bp_asset = unreal.EditorAssetLibrary.load_asset(KAMAZ_BP_PATH)
    generated_class = _safe_property(bp_asset, "generated_class")
    if callable(generated_class):
        generated_class = generated_class()

    actors = []
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        actor_class = actor.get_class()
        class_path = _object_path(actor_class)
        actor_path = _object_path(actor)
        actor_name = _object_name(actor)
        if generated_class and actor_class == generated_class:
            actors.append(actor)
            continue
        if "KamazBP_C" in class_path or "Kamaz" in actor_name or "Kamaz" in actor_path:
            actors.append(actor)

    payload = {
        "map_path": MAP_PATH,
        "kamaz_actor_count": len(actors),
        "actors": [_actor_summary(actor) for actor in actors[:5]],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
