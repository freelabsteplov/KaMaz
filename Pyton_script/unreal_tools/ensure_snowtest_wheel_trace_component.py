import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"
WHEEL_COMPONENT_CLASS_PATH = "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component.BP_WheelSnowTrace_Component_C"
WHEEL_COMPONENT_NAME = "WheelSnowTraceRuntimeComponent"
WHEEL_BRUSH_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush"
WHEEL_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
DEFAULT_WHEEL_BONE_NAMES = ["WFL", "WFR", "WRL", "WRR"]
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "ensure_snowtest_wheel_trace_component.json",
)


ASSET_LIB = unreal.EditorAssetLibrary


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs), ""
    except Exception as exc:
        return None, str(exc)


def _compile_blueprint(blueprint):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None and hasattr(bridge, "compile_blueprint"):
        try:
            raw = bridge.compile_blueprint(blueprint.get_path_name())
            return {"success": True, "raw": raw}
        except Exception as exc:
            return {"success": False, "raw": str(exc)}
    try:
        unreal.KismetEditorUtilities.compile_blueprint(blueprint)
        return {"success": True, "raw": "Compiled via KismetEditorUtilities"}
    except Exception as exc:
        return {"success": False, "raw": str(exc)}


def _subobject_subsystem():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _subobject_library():
    return unreal.SubobjectDataBlueprintFunctionLibrary


def _handle_valid(library, handle):
    value, error = _safe_call(library.is_handle_valid, handle)
    return error == "" and bool(value)


def _resolve_subobject_object(library, handle, blueprint):
    data, _ = _safe_call(library.get_data, handle)
    for args in ((handle,), (data,), (handle, blueprint), (data, blueprint)):
        value, error = _safe_call(library.get_object, *args)
        if error == "":
            return value
    for args in ((handle, blueprint), (data, blueprint), (blueprint, handle), (blueprint, data)):
        value, error = _safe_call(library.get_object_for_blueprint, *args)
        if error == "":
            return value
    return None


def _gather_entries(blueprint):
    subsystem = _subobject_subsystem()
    library = _subobject_library()
    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    entries = []
    for handle in handles:
        if not _handle_valid(library, handle):
            continue
        display_name, _ = _safe_call(library.get_display_name, handle)
        obj = _resolve_subobject_object(library, handle, blueprint)
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


def _find_parent_entry(entries):
    for entry in entries:
        if entry["object_name"] == "VehicleMesh" or "VehicleMesh" in entry["display_name"]:
            return entry
    for entry in entries:
        if "DefaultSceneRoot" in entry["display_name"] or entry["object_name"] == "DefaultSceneRoot":
            return entry
    return entries[0] if entries else None


def _find_component_entry(entries, class_path):
    fallback = None
    for entry in entries:
        if entry["object_name"] == WHEEL_COMPONENT_NAME:
            return entry
        if entry["object_name"] == "BP_WheelSnowTrace_Component":
            return entry
        if "WheelSnowTrace" in entry["object_name"] or "WheelSnowTrace" in entry["display_name"]:
            fallback = fallback or entry
        if entry["object_class"] == class_path:
            fallback = fallback or entry
    return fallback


def ensure_component():
    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "component_added": False,
        "component_already_present": False,
        "component_path": "",
        "component_class": "",
        "property_updates": {},
        "compile": {},
        "saved": False,
        "error": "",
    }

    try:
        blueprint = ASSET_LIB.load_asset(BLUEPRINT_PATH)
        if blueprint is None:
            raise RuntimeError(f"Missing blueprint: {BLUEPRINT_PATH}")

        component_class = unreal.load_class(None, WHEEL_COMPONENT_CLASS_PATH)
        if component_class is None:
            raise RuntimeError(f"Missing wheel component class: {WHEEL_COMPONENT_CLASS_PATH}")

        wheel_brush = ASSET_LIB.load_asset(WHEEL_BRUSH_PATH)
        wheel_rt = ASSET_LIB.load_asset(WHEEL_RT_PATH)
        if wheel_brush is None or wheel_rt is None:
            raise RuntimeError("Wheel brush material or render target is missing")

        entries = _gather_entries(blueprint)
        component_entry = _find_component_entry(entries, component_class.get_path_name())
        component_object = component_entry["object"] if component_entry else None

        if component_object is not None:
            result["component_already_present"] = True
        else:
            parent_entry = _find_parent_entry(entries)
            if parent_entry is None:
                raise RuntimeError("Could not resolve a parent entry for the wheel component")

            params = unreal.AddNewSubobjectParams()
            params.set_editor_property("parent_handle", parent_entry["handle"])
            params.set_editor_property("new_class", component_class)
            params.set_editor_property("blueprint_context", blueprint)

            add_result, add_error = _safe_call(_subobject_subsystem().add_new_subobject, params=params)
            if add_error != "":
                add_result, add_error = _safe_call(_subobject_subsystem().add_new_subobject, params)
            if add_error != "":
                raise RuntimeError(f"add_new_subobject failed: {add_error}")

            new_handle = add_result[0] if isinstance(add_result, tuple) else add_result
            component_object = _resolve_subobject_object(_subobject_library(), new_handle, blueprint)
            if component_object is None:
                raise RuntimeError("Could not resolve new wheel component object")

            result["component_added"] = True

        try:
            component_object.rename(WHEEL_COMPONENT_NAME)
        except Exception:
            pass

        property_updates = {}
        for prop_name, prop_value in (
            ("BrushMaterial", wheel_brush),
            ("RenderTargetGlobal", wheel_rt),
            ("bEnableSnowTraces", True),
            ("WheelBoneNames", [unreal.Name(name) for name in DEFAULT_WHEEL_BONE_NAMES]),
        ):
            try:
                component_object.set_editor_property(prop_name, prop_value)
                property_updates[prop_name] = True
            except Exception as exc:
                property_updates[prop_name] = str(exc)

        try:
            generated_class = blueprint.generated_class()
        except Exception:
            generated_class = getattr(blueprint, "generated_class", None)
        if callable(generated_class):
            generated_class = generated_class()
        cdo = unreal.get_default_object(generated_class) if generated_class else None
        if cdo is not None:
            try:
                cdo.set_editor_property("SnowTraceComponent", component_object)
                property_updates["SnowTraceComponent"] = True
            except Exception as exc:
                property_updates["SnowTraceComponent"] = str(exc)

        result["property_updates"] = property_updates
        result["component_path"] = component_object.get_path_name() if component_object else ""
        result["component_class"] = component_object.get_class().get_path_name() if component_object else ""
        result["compile"] = _compile_blueprint(blueprint)
        result["saved"] = bool(ASSET_LIB.save_loaded_asset(blueprint, False))
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    ensure_component()
