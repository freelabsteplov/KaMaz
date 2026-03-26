import json
import os

import unreal


MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_m_snowreceiver_lerp_inputs.json",
)


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _obj_name(obj):
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
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


def _serialize_input(input_struct):
    if input_struct is None:
        return {"expression": "", "expression_path": "", "output_name": ""}
    expression = _safe_get(input_struct, "expression", None)
    output_name = _safe_get(input_struct, "output_name", "")
    return {
        "expression": _obj_name(expression),
        "expression_path": _obj_path(expression),
        "output_name": str(output_name),
    }


def _serialize_root_input(material, prop_name):
    input_struct = _safe_get(material, prop_name, None)
    return _serialize_input(input_struct)


def main():
    result = {
        "success": False,
        "material_path": MATERIAL_PATH,
        "root_inputs": {},
        "lerps": [],
        "error": "",
    }

    try:
        material = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
        if material is None:
            raise RuntimeError(f"Could not load material: {MATERIAL_PATH}")

        root_props = (
            "base_color",
            "roughness",
            "normal",
            "world_position_offset",
            "opacity_mask",
            "emissive_color",
        )
        for prop in root_props:
            result["root_inputs"][prop] = _serialize_root_input(material, prop)

        expressions = list(_safe_get(material, "expressions", []) or [])
        for expr in expressions:
            class_name = _obj_name(expr.get_class())
            if class_name != "MaterialExpressionLinearInterpolate":
                continue
            entry = {
                "name": _obj_name(expr),
                "path": _obj_path(expr),
                "const_a": _safe_get(expr, "const_a", None),
                "const_b": _safe_get(expr, "const_b", None),
                "const_alpha": _safe_get(expr, "const_alpha", None),
                "a": _serialize_input(_safe_get(expr, "a", None)),
                "b": _serialize_input(_safe_get(expr, "b", None)),
                "alpha": _serialize_input(_safe_get(expr, "alpha", None)),
            }
            result["lerps"].append(entry)

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
