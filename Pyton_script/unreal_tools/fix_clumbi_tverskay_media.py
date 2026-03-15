import json
import os

import unreal


MAP_PATH = "/Game/Maps/Clumbi_Tverskay"
EXPECTED_MEDIA_PLAYER_ASSET_PATH = "/Game/Movies/MediaPlane"
OPTIONAL_MEDIA_SOURCE_ASSET_PATH = "/Game/Movies/Seqence"


def _log(message: str) -> None:
    unreal.log(f"[fix_clumbi_tverskay_media] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[fix_clumbi_tverskay_media] {message}")


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
    return _safe_call(obj, "get_name") or str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    return _safe_call(obj, "get_path_name") or str(obj)


def _object_class_name(obj) -> str:
    if obj is None:
        return ""
    return _object_name(_safe_call(obj, "get_class"))


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(asset_path)
    except Exception:
        return None


def _load_map(map_path: str):
    loaders = [
        getattr(unreal, "EditorLoadingAndSavingUtils", None),
        getattr(unreal, "LevelEditorSubsystem", None),
    ]

    loading_utils = loaders[0]
    if loading_utils is not None:
        if _safe_call(loading_utils, "load_map", map_path):
            return True

    subsystem_cls = loaders[1]
    if subsystem_cls is not None:
        subsystem = unreal.get_editor_subsystem(subsystem_cls)
        if subsystem and _safe_call(subsystem, "load_level", map_path):
            return True

    return False


def _map_name_from_path(map_path: str) -> str:
    return map_path.rsplit("/", 1)[-1]


def _package_path_from_object_path(object_path: str) -> str:
    if not object_path:
        return ""
    return object_path.split(":", 1)[0].split(".", 1)[0]


def _load_level_blueprint_generated_class(map_path: str):
    editor_asset_library = getattr(unreal, "EditorAssetLibrary", None)
    if editor_asset_library is not None:
        class_obj = _safe_call(editor_asset_library, "load_blueprint_class", map_path)
        if class_obj is not None:
            return class_obj

    generated_class_path = f"{map_path}.{_map_name_from_path(map_path)}_C"

    load_object = getattr(unreal, "load_object", None)
    if load_object is not None:
        class_obj = _safe_call(unreal, "load_object", None, generated_class_path)
        if class_obj is not None:
            return class_obj

    load_class = getattr(unreal, "load_class", None)
    if load_class is not None:
        class_obj = _safe_call(unreal, "load_class", None, generated_class_path)
        if class_obj is not None:
            return class_obj

    return None


def _resolve_blueprint_for_class(class_obj):
    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is None or class_obj is None:
        return None

    getter = getattr(blueprint_editor_library, "get_blueprint_for_class", None)
    if getter is None:
        return None

    try:
        result = getter(class_obj)
    except TypeError:
        return None
    except Exception:
        return None

    if isinstance(result, tuple):
        if len(result) >= 2:
            blueprint, has_blueprint = result[0], bool(result[1])
            return blueprint if has_blueprint else None
        if len(result) == 1:
            return result[0]
        return None

    return result


def _get_class_default_object(class_obj):
    default_obj = _safe_call(class_obj, "get_default_object")
    if default_obj is not None and "blueprintgeneratedclass" not in _object_class_name(default_obj).lower():
        return default_obj

    getter = getattr(unreal, "get_default_object", None)
    if getter is not None:
        default_obj = _safe_call(unreal, "get_default_object", class_obj)
        if default_obj is not None and "blueprintgeneratedclass" not in _object_class_name(default_obj).lower():
            return default_obj

    class_name = _object_name(class_obj)
    package_path = _package_path_from_object_path(_object_path(class_obj))
    if class_name and package_path:
        explicit_cdo_path = f"{package_path}.Default__{class_name}"
        explicit_cdo = None

        load_object = getattr(unreal, "load_object", None)
        if load_object is not None:
            explicit_cdo = _safe_call(unreal, "load_object", None, explicit_cdo_path)
        if explicit_cdo is None:
            explicit_cdo = _load_asset(explicit_cdo_path)
        if explicit_cdo is not None and "blueprintgeneratedclass" not in _object_class_name(explicit_cdo).lower():
            return explicit_cdo

    return None


def _save_asset_by_path(asset_path: str) -> bool:
    editor_asset_library = getattr(unreal, "EditorAssetLibrary", None)
    if editor_asset_library is None:
        return False

    result = _safe_call(editor_asset_library, "save_asset", asset_path, False)
    if result is not None:
        return bool(result)
    return False


def _get_editor_world():
    editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
    if editor_level_library is not None:
        world = _safe_call(editor_level_library, "get_editor_world")
        if world:
            return world

    subsystem_cls = getattr(unreal, "LevelEditorSubsystem", None)
    if subsystem_cls is not None:
        subsystem = unreal.get_editor_subsystem(subsystem_cls)
        if subsystem is not None:
            world = _safe_call(subsystem, "get_editor_world")
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


def _get_all_level_actors() -> list:
    subsystem_cls = getattr(unreal, "EditorActorSubsystem", None)
    if subsystem_cls is None:
        return []

    subsystem = unreal.get_editor_subsystem(subsystem_cls)
    if subsystem is None:
        return []

    return list(_safe_call(subsystem, "get_all_level_actors") or [])


def _get_level_script_actor(level):
    actor = _safe_call(level, "get_level_script_actor")
    if actor:
        return actor
    actor = _safe_get_editor_property(level, "level_script_actor")
    if actor:
        return actor
    raise RuntimeError("Failed to resolve level script actor.")


def _find_level_script_actor_via_actor_subsystem() -> object | None:
    candidates = []
    for actor in _get_all_level_actors():
        actor_name = _object_name(actor)
        actor_path = _object_path(actor)
        class_name = _object_class_name(actor)
        if "clumbi_tverskay_c" in class_name.lower():
            return actor
        if "levelscriptactor" in class_name.lower():
            candidates.append(actor)
            continue
        if "clumbi_tverskay_c" in actor_name.lower():
            return actor
        if "persistentlevel.clumbi_tverskay_c" in actor_path.lower():
            return actor

    if len(candidates) == 1:
        return candidates[0]
    return None


def _resolve_level_script_actor(world):
    level = None
    level_error = None
    try:
        level = _get_persistent_level(world)
    except Exception as exc:
        level_error = str(exc)

    if level is not None:
        actor = _safe_call(level, "get_level_script_actor")
        if actor:
            return level, actor, level_error
        actor = _safe_get_editor_property(level, "level_script_actor")
        if actor:
            return level, actor, level_error

    actor = _find_level_script_actor_via_actor_subsystem()
    if actor is not None:
        actor_level = _safe_call(actor, "get_level")
        return actor_level, actor, level_error

    if level_error:
        raise RuntimeError(f"Failed to resolve level script actor. Initial level error: {level_error}")
    raise RuntimeError("Failed to resolve level script actor.")


def _save_current_level() -> bool:
    loading_utils = getattr(unreal, "EditorLoadingAndSavingUtils", None)
    if loading_utils is not None:
        result = _safe_call(loading_utils, "save_current_level")
        if result is not None:
            return bool(result)

    editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
    if editor_level_library is not None:
        result = _safe_call(editor_level_library, "save_current_level")
        if result is not None:
            return bool(result)

    return False


def _list_media_properties(actor) -> list[dict]:
    results = []
    for name in dir(actor):
        if "media" not in name.lower():
            continue
        if name.startswith("_"):
            continue
        value = _safe_get_editor_property(actor, name)
        results.append(
            {
                "name": name,
                "value_object_path": _object_path(value),
                "value_class_name": _object_class_name(value),
                "value_repr": str(value),
            }
        )
    return results


def _try_assign_optional_media_source(target_obj, media_source_asset) -> dict:
    result = {
        "attempted": False,
        "assigned": False,
        "property_name": "",
        "before_path": "",
        "after_path": "",
        "error": "",
    }
    if target_obj is None or media_source_asset is None:
        return result

    for property_name in ("MediaSource", "Source"):
        try:
            before_value = _safe_get_editor_property(target_obj, property_name, None)
            result["attempted"] = True
            result["property_name"] = property_name
            result["before_path"] = _object_path(before_value)
            if before_value is None or _object_path(before_value) != _object_path(media_source_asset):
                target_obj.set_editor_property(property_name, media_source_asset)
            after_value = _safe_get_editor_property(target_obj, property_name, None)
            result["after_path"] = _object_path(after_value)
            result["assigned"] = _object_path(after_value) == _object_path(media_source_asset)
            return result
        except Exception as exc:
            result["error"] = str(exc)

    return result


def fix_clumbi_tverskay_media(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "expected_media_player_asset_path": EXPECTED_MEDIA_PLAYER_ASSET_PATH,
        "optional_media_source_asset_path": OPTIONAL_MEDIA_SOURCE_ASSET_PATH,
        "loaded_map": False,
        "saved": False,
    }
    expected_media = _load_asset(EXPECTED_MEDIA_PLAYER_ASSET_PATH)
    if expected_media is None:
        raise RuntimeError(f"Failed to load expected media player asset {EXPECTED_MEDIA_PLAYER_ASSET_PATH}.")
    optional_media_source = _load_asset(OPTIONAL_MEDIA_SOURCE_ASSET_PATH)

    result["expected_media_class"] = _object_class_name(expected_media)
    result["optional_media_source_class"] = _object_class_name(optional_media_source)

    class_obj = _load_level_blueprint_generated_class(MAP_PATH)
    result["generated_class_path"] = _object_path(class_obj)
    result["generated_class_name"] = _object_class_name(class_obj)

    if class_obj is None:
        _warn("Failed to load generated class directly; falling back to map load/editor world path.")
        if not _load_map(MAP_PATH):
            raise RuntimeError(f"Failed to load map {MAP_PATH}.")
        result["loaded_map"] = True

        world = _get_editor_world()
        level, actor, level_error = _resolve_level_script_actor(world)
        before_media = _safe_get_editor_property(actor, "Media", None)
        result["world_path"] = _object_path(world)
        result["level_path"] = _object_path(level)
        result["level_resolution_warning"] = level_error or ""
        result["level_script_actor_path"] = _object_path(actor)
        result["level_script_actor_class"] = _object_class_name(actor)
        result["before_media_path"] = _object_path(before_media)
        result["media_properties_before"] = _list_media_properties(actor)

        if before_media is None or _object_path(before_media) != _object_path(expected_media):
            actor.set_editor_property("Media", expected_media)
            result["media_assigned"] = True
        else:
            result["media_assigned"] = False

        result["saved"] = _save_current_level()
        result["optional_media_source_assignment"] = _try_assign_optional_media_source(actor, optional_media_source)

        after_media = _safe_get_editor_property(actor, "Media", None)
        result["after_media_path"] = _object_path(after_media)
        result["media_properties_after"] = _list_media_properties(actor)
        result["success"] = _object_path(after_media) == _object_path(expected_media)
    else:
        blueprint = _resolve_blueprint_for_class(class_obj)
        default_object = _get_class_default_object(class_obj)
        if default_object is None:
            raise RuntimeError("Failed to resolve level blueprint class default object.")

        result["level_blueprint_path"] = _object_path(blueprint)
        result["default_object_path"] = _object_path(default_object)
        result["default_object_class"] = _object_class_name(default_object)

        before_media = _safe_get_editor_property(default_object, "Media", None)
        result["before_media_path"] = _object_path(before_media)
        result["media_properties_before"] = _list_media_properties(default_object)

        if before_media is None or _object_path(before_media) != _object_path(expected_media):
            default_object.set_editor_property("Media", expected_media)
            result["media_assigned"] = True
        else:
            result["media_assigned"] = False
        result["optional_media_source_assignment"] = _try_assign_optional_media_source(default_object, optional_media_source)

        compiled = False
        blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
        if blueprint_editor_library is not None and blueprint is not None:
            compiled_result = _safe_call(blueprint_editor_library, "compile_blueprint", blueprint)
            compiled = compiled_result is None or bool(compiled_result)
        result["compiled"] = compiled

        save_map = _save_asset_by_path(MAP_PATH)
        save_bp = _save_asset_by_path(_object_path(blueprint)) if blueprint is not None else False
        result["saved_map_asset"] = save_map
        result["saved_blueprint_asset"] = save_bp
        result["saved"] = bool(save_map or save_bp)

        after_media = _safe_get_editor_property(default_object, "Media", None)
        result["after_media_path"] = _object_path(after_media)
        result["media_properties_after"] = _list_media_properties(default_object)
        result["success"] = _object_path(after_media) == _object_path(expected_media)

    output_path = os.path.join(output_dir, "fix_clumbi_tverskay_media.json")
    result["output_path"] = _write_json(output_path, result)
    return result


def print_summary() -> str:
    result = fix_clumbi_tverskay_media()
    summary = (
        f"Clumbi_Tverskay Media fixed={result['success']} "
        f"before={result.get('before_media_path') or '<none>'} "
        f"after={result.get('after_media_path') or '<none>'} "
        f"saved={result['saved']}"
    )
    _log(summary)
    _log(f"summary_path={result['output_path']}")
    return summary


if __name__ == "__main__":
    _log("Loaded fix_clumbi_tverskay_media.py")
