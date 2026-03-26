import json
import os

import unreal


MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_m_snowreceiver_root_chains.json",
)

INPUT_FIELDS = [
    "a",
    "b",
    "alpha",
    "input",
    "base",
    "exponent",
    "coordinates",
    "uvs",
    "height",
    "x",
    "y",
]


def _safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def _expr_name(expr):
    if expr is None:
        return ""
    try:
        return expr.get_name()
    except Exception:
        return str(expr)


def _expr_path(expr):
    if expr is None:
        return ""
    try:
        return expr.get_path_name()
    except Exception:
        return str(expr)


def _input_expr(input_struct):
    if input_struct is None:
        return None
    try:
        return input_struct.expression
    except Exception:
        return None


def _param_name(expr):
    for prop_name in ("parameter_name",):
        value = _safe_get(expr, prop_name, None)
        if value is not None:
            return str(value)
    return ""


def _walk(expr, visited):
    if expr is None:
        return None
    path = _expr_path(expr)
    if path in visited:
        return {"name": _expr_name(expr), "path": path, "recursive": True}

    visited.add(path)
    node = {
        "name": _expr_name(expr),
        "path": path,
        "class": expr.get_class().get_name(),
        "parameter_name": _param_name(expr),
        "inputs": [],
    }

    for field_name in INPUT_FIELDS:
        input_struct = _safe_get(expr, field_name, None)
        if input_struct is None:
            continue
        input_expr = _input_expr(input_struct)
        if input_expr is None:
            continue
        node["inputs"].append(
            {
                "pin": field_name,
                "source": _walk(input_expr, visited),
            }
        )

    return node


def _root(material, mat_prop):
    expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, mat_prop)
    out_name = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, mat_prop)
    return expr, str(out_name)


def main():
    result = {
        "success": False,
        "material_path": MATERIAL_PATH,
        "roots": {},
        "error": "",
    }
    try:
        material = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
        if material is None:
            raise RuntimeError(f"Material not found: {MATERIAL_PATH}")

        root_map = {
            "base_color": unreal.MaterialProperty.MP_BASE_COLOR,
            "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
            "normal": unreal.MaterialProperty.MP_NORMAL,
            "opacity_mask": unreal.MaterialProperty.MP_OPACITY_MASK,
            "wpo": unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET,
        }
        for label, prop in root_map.items():
            expr, out_name = _root(material, prop)
            result["roots"][label] = {
                "root_expr_name": _expr_name(expr),
                "root_expr_path": _expr_path(expr),
                "output_name": out_name,
                "chain": _walk(expr, set()),
            }

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

