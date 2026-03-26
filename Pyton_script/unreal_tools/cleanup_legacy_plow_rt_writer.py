import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
KAMAZ_BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "cleanup_legacy_plow_rt_writer.json",
)


ASSET_LIB = unreal.EditorAssetLibrary


def _subobject_subsystem():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _subobject_library():
    return unreal.SubobjectDataBlueprintFunctionLibrary


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _obj_name(obj):
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _safe_get(obj, prop, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop)
        except Exception:
            pass
    return getattr(obj, prop, default)


def _safe_set(obj, prop, value):
    if obj is None:
        return False, "object is None"
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(prop, value)
            return True, ""
        except Exception as exc:
            return False, str(exc)
    try:
        setattr(obj, prop, value)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _resolve_generated_class(asset):
    candidate = getattr(asset, "generated_class", None)
    if callable(candidate):
        try:
            candidate = candidate()
        except Exception:
            candidate = None
    if candidate is None:
        try:
            candidate = asset.get_editor_property("generated_class")
        except Exception:
            candidate = None
    return candidate


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs), ""
    except Exception as exc:
        return None, str(exc)


def _handle_is_valid(function_library, handle) -> bool:
    value, error = _safe_call(function_library.is_handle_valid, handle)
    return error == "" and bool(value)


def _resolve_subobject_object(function_library, handle, blueprint):
    data, _ = _safe_call(function_library.get_data, handle)
    for args in ((handle,), (data,), (handle, blueprint), (data, blueprint)):
        value, error = _safe_call(function_library.get_object, *args)
        if error == "":
            return value
    for args in ((handle, blueprint), (data, blueprint), (blueprint, handle), (blueprint, data)):
        value, error = _safe_call(function_library.get_object_for_blueprint, *args)
        if error == "":
            return value
    return None


def _gather_subobject_entries(blueprint):
    subsystem = _subobject_subsystem()
    function_library = _subobject_library()
    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    entries = []
    for handle in handles:
        if not _handle_is_valid(function_library, handle):
            continue
        display_name, _ = _safe_call(function_library.get_display_name, handle)
        obj = _resolve_subobject_object(function_library, handle, blueprint)
        entries.append(
            {
                "handle": handle,
                "display_name": str(display_name),
                "object": obj,
                "object_name": _obj_name(obj),
                "object_path": _obj_path(obj),
                "object_class": _obj_path(obj.get_class()) if obj else "",
            }
        )
    return entries


def _decode_bridge_compile_result(raw_result):
    payload = {
        "compiled": False,
        "summary": "",
        "json": "",
    }
    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                payload["compiled"] = item
            elif isinstance(item, str):
                if not payload["json"]:
                    payload["json"] = item
                else:
                    payload["summary"] = item
        return payload
    if isinstance(raw_result, bool):
        payload["compiled"] = raw_result
        return payload
    payload["summary"] = str(raw_result)
    return payload


def _compile_and_save_blueprint(asset_path):
    result = {
        "asset_path": asset_path,
        "compiled": False,
        "compile_summary": "",
        "saved": False,
        "save_summary": "",
    }

    blueprint = ASSET_LIB.load_asset(asset_path)
    if blueprint is None:
        result["compile_summary"] = "missing blueprint"
        return result

    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None and hasattr(bridge, "compile_blueprint"):
        try:
            compile_payload = _decode_bridge_compile_result(bridge.compile_blueprint(asset_path))
            result["compiled"] = compile_payload["compiled"]
            result["compile_summary"] = compile_payload["summary"]
        except Exception as exc:
            result["compile_summary"] = f"bridge.compile_blueprint failed: {exc}"
    else:
        try:
            unreal.KismetEditorUtilities.compile_blueprint(blueprint)
            result["compiled"] = True
            result["compile_summary"] = "Compiled via KismetEditorUtilities"
        except Exception as exc:
            result["compile_summary"] = f"kismet compile failed: {exc}"

    try:
        blueprint.mark_package_dirty()
    except Exception:
        pass

    save_attempts = []
    try:
        save_attempts.append(
            {
                "method": "save_asset",
                "success": bool(ASSET_LIB.save_asset(asset_path, False)),
            }
        )
    except Exception as exc:
        save_attempts.append({"method": "save_asset", "success": False, "error": str(exc)})

    if not any(bool(item.get("success")) for item in save_attempts):
        try:
            save_attempts.append(
                {
                    "method": "save_loaded_asset",
                    "success": bool(ASSET_LIB.save_loaded_asset(blueprint, False)),
                }
            )
        except Exception as exc:
            save_attempts.append({"method": "save_loaded_asset", "success": False, "error": str(exc)})

    result["saved"] = any(bool(item.get("success")) for item in save_attempts)
    result["save_summary"] = json.dumps(save_attempts, ensure_ascii=False)

    return result


def _collect_component_state(component):
    return {
        "component_name": _obj_name(component),
        "component_path": _obj_path(component),
        "component_class": _obj_path(component.get_class()) if component else "",
        "RenderTargetGlobal": _obj_path(_safe_get(component, "RenderTargetGlobal", None)),
        "BrushMaterial": _obj_path(_safe_get(component, "BrushMaterial", None)),
        "BrushDMI": _obj_path(_safe_get(component, "BrushDMI", None)),
        "MPCSnowSystem": _obj_path(_safe_get(component, "MPCSnowSystem", None)),
        "bEnablePlowClearing": bool(_safe_get(component, "bEnablePlowClearing", False)),
        "PlowLiftHeight": _safe_get(component, "PlowLiftHeight", None),
    }


def _looks_like_plow_component(component):
    if component is None:
        return False
    class_path = _obj_path(component.get_class())
    name = _obj_name(component)
    return (
        "BP_PlowBrush_Component" in class_path
        or "BP_PlowBrush_Component" in name
        or "PlowBrush" in class_path
        or "PlowBrush" in name
    )


def _find_plow_components_on_object(obj):
    results = []
    if obj is None:
        return results
    get_components = getattr(obj, "get_components_by_class", None)
    if callable(get_components):
        try:
            for component in list(get_components(unreal.ActorComponent) or []):
                if _looks_like_plow_component(component):
                    results.append(component)
        except Exception:
            pass
    return results


def _disable_rt_on_component(component):
    before = _collect_component_state(component)
    rt_ok, rt_error = _safe_set(component, "RenderTargetGlobal", None)
    dmi_ok, dmi_error = _safe_set(component, "BrushDMI", None)
    after = _collect_component_state(component)
    return {
        "before": before,
        "after": after,
        "set_render_target_global": {"ok": rt_ok, "error": rt_error},
        "set_brush_dmi": {"ok": dmi_ok, "error": dmi_error},
    }


def _process_blueprint_default(asset_path):
    result = {
        "asset_path": asset_path,
        "default_object_path": "",
        "components": [],
        "compile_save": {},
        "error": "",
    }
    asset = ASSET_LIB.load_asset(asset_path)
    if asset is None:
        result["error"] = "asset missing"
        return result
    generated_class = _resolve_generated_class(asset)
    if generated_class is None:
        result["error"] = "generated class missing"
        return result
    default_object = unreal.get_default_object(generated_class)
    result["default_object_path"] = _obj_path(default_object)

    if "BP_PlowBrush_Component" in asset_path:
        result["components"].append(_disable_rt_on_component(default_object))
    else:
        direct_candidates = []
        for property_name in ("BP_PlowBrush_Component", "PlowBrush", "BP_PlowBrush_Component_GEN_VARIABLE"):
            candidate = _safe_get(default_object, property_name, None)
            if candidate is not None and _looks_like_plow_component(candidate):
                direct_candidates.append(candidate)

        subobject_candidates = []
        for entry in _gather_subobject_entries(asset):
            component = entry.get("object")
            if component is not None and _looks_like_plow_component(component):
                subobject_candidates.append(component)

        seen_paths = set()
        for component in direct_candidates + subobject_candidates + _find_plow_components_on_object(default_object):
            component_path = _obj_path(component)
            if not component_path or component_path in seen_paths:
                continue
            seen_paths.add(component_path)
            result["components"].append(_disable_rt_on_component(component))

    result["compile_save"] = _compile_and_save_blueprint(asset_path)
    return result


def _find_map_plow_components():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    components = []
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        actor_label = ""
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            actor_label = ""
        for component in _find_plow_components_on_object(actor):
            components.append(
                {
                    "actor_label": actor_label,
                    "actor_path": _obj_path(actor),
                    "component": component,
                }
            )
    return components


def _process_map_instances():
    result = {
        "map_path": MAP_PATH,
        "components": [],
        "saved_level": False,
        "error": "",
    }
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    for entry in _find_map_plow_components():
        component_result = _disable_rt_on_component(entry["component"])
        component_result["actor_label"] = entry["actor_label"]
        component_result["actor_path"] = entry["actor_path"]
        result["components"].append(component_result)

    try:
        result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        result["saved_level"] = False
        result["error"] = str(exc)
    return result


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def main():
    result = {
        "success": False,
        "plow_component_blueprint": {},
        "kamaz_blueprint": {},
        "map_instances": {},
        "error": "",
    }
    try:
        result["plow_component_blueprint"] = _process_blueprint_default(PLOW_BLUEPRINT_PATH)
        result["kamaz_blueprint"] = _process_blueprint_default(KAMAZ_BLUEPRINT_PATH)
        result["map_instances"] = _process_map_instances()
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
