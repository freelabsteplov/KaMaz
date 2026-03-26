import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"
COMPONENT_NAME = "KamazStartupHold"
COMPONENT_CLASS_PATH = "/Script/Kamaz_Cleaner.KamazStartupHoldComponent"
OUTPUT_BASENAME = "attach_kamaz_startup_hold_component"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs), ""
    except Exception as exc:
        return None, str(exc)


def _subobject_subsystem():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _subobject_library():
    return unreal.SubobjectDataBlueprintFunctionLibrary


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


def _gather_entries(blueprint):
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
                "object_name": obj.get_name() if obj else "",
                "object_path": obj.get_path_name() if obj else "",
                "object_class": obj.get_class().get_path_name() if obj else "",
            }
        )
    return entries


def _find_default_scene_root_entry(entries):
    for entry in entries:
        if "DefaultSceneRoot" in entry["display_name"] or entry["object_name"] == "DefaultSceneRoot":
            return entry
    return entries[0] if entries else None


def _find_component_entry(entries):
    for entry in entries:
        if entry["object_name"] == COMPONENT_NAME:
            return entry
        if entry["object_class"] == COMPONENT_CLASS_PATH and COMPONENT_NAME in entry["object_name"]:
            return entry
    return None


def _compile_blueprint(blueprint_asset) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None and hasattr(bridge, "compile_blueprint"):
        try:
            asset_path = blueprint_asset.get_path_name().split(".")[0]
            raw = bridge.compile_blueprint(asset_path)
            payload = ""
            summary = ""
            success = True
            if isinstance(raw, tuple):
                for item in raw:
                    if isinstance(item, bool):
                        success = bool(item)
                    elif isinstance(item, str) and not payload:
                        payload = item
                    elif isinstance(item, str):
                        summary = item
            elif isinstance(raw, bool):
                success = bool(raw)
            return {
                "success": success,
                "summary": summary or "Compiled via BlueprintAutomationPythonBridge.compile_blueprint",
                "payload": payload,
            }
        except Exception as exc:
            return {"success": False, "summary": f"bridge compile failed: {exc}"}

    try:
        unreal.KismetEditorUtilities.compile_blueprint(blueprint_asset)
        return {"success": True, "summary": "Compiled via KismetEditorUtilities.compile_blueprint"}
    except Exception as exc:
        return {"success": False, "summary": str(exc)}


def _try_set_property(obj, candidate_names, value):
    for name in candidate_names:
        try:
            obj.set_editor_property(name, value)
            return {"success": True, "property_name": name, "value": value}
        except Exception:
            continue
    return {"success": False, "property_name": "", "value": value}


def run(output_dir: str | None = None):
    output_dir = output_dir or _saved_output_dir()
    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "component_name": COMPONENT_NAME,
        "component_class_path": COMPONENT_CLASS_PATH,
        "component_added": False,
        "component_already_present": False,
        "component_object_path": "",
        "compile": {},
        "saved": False,
        "error": "",
    }

    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if not blueprint:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    entries = _gather_entries(blueprint)
    existing_entry = _find_component_entry(entries)
    if existing_entry:
        result["component_already_present"] = True
        result["component_object_path"] = existing_entry["object_path"]
        component_object = existing_entry["object"]
    else:
        root_entry = _find_default_scene_root_entry(entries)
        if root_entry is None:
            raise RuntimeError("Could not resolve root entry for blueprint subobjects.")

        component_class = unreal.load_class(None, COMPONENT_CLASS_PATH)
        if component_class is None:
            raise RuntimeError(f"Could not load component class: {COMPONENT_CLASS_PATH}")

        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", root_entry["handle"])
        params.set_editor_property("new_class", component_class)
        params.set_editor_property("blueprint_context", blueprint)

        subsystem = _subobject_subsystem()
        add_result, error = _safe_call(subsystem.add_new_subobject, params=params)
        if error != "":
            add_result, error = _safe_call(subsystem.add_new_subobject, params)
        if error != "":
            raise RuntimeError(f"add_new_subobject failed: {error}")

        if isinstance(add_result, tuple):
            new_handle = add_result[0]
        else:
            new_handle = add_result

        if not _handle_is_valid(_subobject_library(), new_handle):
            raise RuntimeError("add_new_subobject returned invalid handle.")

        component_object = _resolve_subobject_object(_subobject_library(), new_handle, blueprint)
        if component_object is None:
            raise RuntimeError("Could not resolve component object after creation.")

        rename_ok = False
        for rename_callable in (
            getattr(_subobject_library(), "rename_subobject", None),
            getattr(subsystem, "rename_subobject", None),
        ):
            if not callable(rename_callable):
                continue
            _, rename_error = _safe_call(rename_callable, new_handle, unreal.Text(COMPONENT_NAME))
            if rename_error == "":
                rename_ok = True
                break

        if not rename_ok:
            try:
                component_object.rename(COMPONENT_NAME)
            except Exception:
                pass

        result["component_added"] = True

        refreshed_entries = _gather_entries(blueprint)
        created_entry = _find_component_entry(refreshed_entries)
        if created_entry:
            result["component_object_path"] = created_entry["object_path"]
            component_object = created_entry["object"]

    if component_object is None:
        raise RuntimeError("Could not resolve startup hold component object.")

    property_sets = {
        "enable_startup_hold": _try_set_property(component_object, ["enable_startup_hold", "bEnableStartupHold", "b_enable_startup_hold"], True),
        "arm_on_begin_play": _try_set_property(component_object, ["arm_on_begin_play", "bArmOnBeginPlay", "b_arm_on_begin_play"], True),
        "arm_on_pawn_restarted": _try_set_property(component_object, ["arm_on_pawn_restarted", "bArmOnPawnRestarted", "b_arm_on_pawn_restarted"], True),
        "release_on_brake_input": _try_set_property(component_object, ["release_on_brake_input", "bReleaseOnBrakeInput", "b_release_on_brake_input"], False),
    }
    result["property_sets"] = property_sets

    result["compile"] = _compile_blueprint(blueprint)
    result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False))

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
