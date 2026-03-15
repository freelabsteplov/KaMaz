import json
import os

import unreal


CANDIDATE_MEDIA_ASSETS = [
    "/Game/Movies/MediaPlane",
    "/Game/Movies/MediaPlane_Video",
    "/Game/Movies/MediaPlane_Video_Mat",
    "/Game/Movies/Seqence",
]


def _log(message: str) -> None:
    unreal.log(f"[level_media_diagnostics] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[level_media_diagnostics] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_call(obj, method_name: str, *args, **kwargs):
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _safe_get_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)

    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _object_name(obj) -> str:
    if obj is None:
        return ""
    name = _safe_call(obj, "get_name")
    return name or str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    path = _safe_call(obj, "get_path_name")
    return path or str(obj)


def _object_class_name(obj) -> str:
    if obj is None:
        return ""
    obj_class = _safe_call(obj, "get_class")
    return _object_name(obj_class)


def _load_asset(asset_path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(asset_path)
    except Exception:
        return None


def _get_editor_world():
    editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
    if editor_level_library is None:
        raise RuntimeError("EditorLevelLibrary is not available.")

    world = _safe_call(editor_level_library, "get_editor_world")
    if world:
        return world

    raise RuntimeError("Failed to resolve editor world.")


def _get_persistent_level(world):
    level = _safe_call(world, "get_current_level")
    if level:
        return level

    level = _safe_get_editor_property(world, "persistent_level")
    if level:
        return level

    raise RuntimeError("Failed to resolve persistent level.")


def _get_level_script_actor(level):
    actor = _safe_call(level, "get_level_script_actor")
    if actor:
        return actor

    actor = _safe_get_editor_property(level, "level_script_actor")
    if actor:
        return actor

    raise RuntimeError("Failed to resolve level script actor.")


def _get_level_blueprint(level_script_actor):
    actor_class = _safe_call(level_script_actor, "get_class")
    if not actor_class:
        return None

    blueprint = _safe_get_editor_property(actor_class, "class_generated_by")
    if blueprint:
        return blueprint

    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is not None:
        blueprint = _safe_call(blueprint_editor_library, "get_blueprint_for_class", actor_class)
        if blueprint:
            return blueprint

    return None


def _find_event_graph(blueprint):
    if blueprint is None:
        return None

    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is not None:
        graph = _safe_call(blueprint_editor_library, "find_event_graph", blueprint)
        if graph:
            return graph

    for graph in _safe_get_editor_property(blueprint, "ubergraph_pages", []) or []:
        if _object_name(graph) == "EventGraph":
            return graph

    return None


def _serialize_pin_link(linked_pin) -> dict:
    owning_node = _safe_call(linked_pin, "get_owning_node")
    return {
        "node_name": _object_name(owning_node),
        "node_path": _object_path(owning_node),
        "pin_name": str(getattr(linked_pin, "pin_name", "") or _object_name(linked_pin)),
    }


def _serialize_node(node) -> dict:
    pins = []
    for pin in _safe_get_editor_property(node, "pins", []) or []:
        pins.append(
            {
                "name": str(getattr(pin, "pin_name", "") or _object_name(pin)),
                "default_value": str(getattr(pin, "default_value", "") or ""),
                "default_object": _object_path(getattr(pin, "default_object", None)),
                "linked_to": [_serialize_pin_link(linked_pin) for linked_pin in getattr(pin, "linked_to", []) or []],
            }
        )

    return {
        "name": _object_name(node),
        "path": _object_path(node),
        "class_name": _object_class_name(node),
        "title": str(_safe_call(node, "get_node_title") or _object_name(node)),
        "comment": str(_safe_get_editor_property(node, "node_comment", "") or ""),
        "pins": pins,
    }


def _collect_relevant_event_nodes(graph):
    if graph is None:
        return []

    relevant = []
    for node in _safe_get_editor_property(graph, "nodes", []) or []:
        title = str(_safe_call(node, "get_node_title") or _object_name(node))
        node_name = _object_name(node)
        lower = f"{title} {node_name}".lower()
        if "open source" in lower or "media" in lower or "play" in lower:
            relevant.append(_serialize_node(node))
    return relevant


def _collect_media_properties(level_script_actor):
    results = []
    for name in dir(level_script_actor):
        if "media" not in name.lower():
            continue
        if name.startswith("_"):
            continue

        value = None
        try:
            value = _safe_get_editor_property(level_script_actor, name)
        except Exception:
            value = getattr(level_script_actor, name, None)

        results.append(
            {
                "name": name,
                "value_object_path": _object_path(value),
                "value_class_name": _object_class_name(value),
                "value_repr": str(value),
            }
        )

    return results


def _candidate_media_assets():
    results = []
    for asset_path in CANDIDATE_MEDIA_ASSETS:
        asset = _load_asset(asset_path)
        results.append(
            {
                "asset_path": asset_path,
                "exists": asset is not None,
                "object_path": _object_path(asset),
                "class_name": _object_class_name(asset),
            }
        )
    return results


def inspect_current_level_media_context(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    world = _get_editor_world()
    level = _get_persistent_level(world)
    level_script_actor = _get_level_script_actor(level)
    blueprint = _get_level_blueprint(level_script_actor)
    event_graph = _find_event_graph(blueprint)

    result = {
        "world_path": _object_path(world),
        "level_path": _object_path(level),
        "level_name": _object_name(level),
        "level_script_actor_path": _object_path(level_script_actor),
        "level_script_actor_class": _object_class_name(level_script_actor),
        "level_blueprint_path": _object_path(blueprint),
        "event_graph_path": _object_path(event_graph),
        "media_properties": _collect_media_properties(level_script_actor),
        "candidate_media_assets": _candidate_media_assets(),
        "relevant_event_nodes": _collect_relevant_event_nodes(event_graph),
    }

    file_prefix = f"{_object_name(level) or 'current_level'}_media_diagnostics"
    output_path = os.path.join(output_dir, f"{file_prefix}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path

    return result


if __name__ == "__main__":
    _log("Loaded level_media_diagnostics.py")
