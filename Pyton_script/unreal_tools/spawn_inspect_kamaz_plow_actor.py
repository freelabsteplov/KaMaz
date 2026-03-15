import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
KAMAZ_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_BASENAME = "spawned_kamaz_plow_actor"


def _log(message: str) -> None:
    unreal.log(f"[spawn_inspect_kamaz_plow_actor] {message}")


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
        "child_actor_summary": _actor_summary(child_actor) if child_actor is not None else {},
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
                components.append(
                    {
                        "name": _object_name(component),
                        "path": _object_path(component),
                        "class": _object_path(component.get_class()),
                        "box_extent": _serialize_value(_safe_property(component, "box_extent")),
                        "relative_location": _serialize_value(_safe_property(component, "relative_location")),
                        "relative_rotation": _serialize_value(_safe_property(component, "relative_rotation")),
                        "relative_scale3d": _serialize_value(_safe_property(component, "relative_scale3d")),
                    }
                )
        except Exception:
            components = []

    return {
        "name": _object_name(actor),
        "path": _object_path(actor),
        "class": _object_path(actor.get_class()),
        "root_component": {
            "name": _object_name(root_component),
            "path": _object_path(root_component),
            "class": _object_path(root_component.get_class()) if root_component else "",
            "box_extent": _serialize_value(_safe_property(root_component, "box_extent")),
            "relative_location": _serialize_value(_safe_property(root_component, "relative_location")),
            "relative_rotation": _serialize_value(_safe_property(root_component, "relative_rotation")),
            "relative_scale3d": _serialize_value(_safe_property(root_component, "relative_scale3d")),
        },
        "components": components,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    bp_asset = unreal.EditorAssetLibrary.load_asset(KAMAZ_BP_PATH)
    generated_class = _safe_property(bp_asset, "generated_class")
    if callable(generated_class):
        generated_class = generated_class()
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for {KAMAZ_BP_PATH}")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    spawned_actor = actor_subsystem.spawn_actor_from_class(
        generated_class,
        unreal.Vector(0.0, 0.0, 300.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if spawned_actor is None:
        raise RuntimeError("Failed to spawn Kamaz actor")

    try:
        components = []
        for component in list(spawned_actor.get_components_by_class(unreal.ActorComponent) or []):
            name = _object_name(component)
            if "Plow" in name or "Hitch" in name or "Brush" in name:
                components.append(_component_summary(component))

        payload = {
            "map_path": MAP_PATH,
            "spawned_actor": _actor_summary(spawned_actor),
            "interesting_components": components,
        }
    finally:
        actor_subsystem.destroy_actor(spawned_actor)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
