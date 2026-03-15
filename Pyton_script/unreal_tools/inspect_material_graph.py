import json
import os

import unreal


OUTPUT_BASENAME = "material_graph"


def _log(message: str) -> None:
    unreal.log(f"[inspect_material_graph] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


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


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _safe_get(obj, property_name: str, default=None):
    try:
        return obj.get_editor_property(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _expression_entry(expr):
    entry = {
        "name": _object_name(expr),
        "class": _object_path(expr.get_class()),
        "path": _object_path(expr),
    }

    for property_name in (
        "parameter_name",
        "material_expression_editor_x",
        "material_expression_editor_y",
        "desc",
    ):
        value = _safe_get(expr, property_name, None)
        if value not in (None, ""):
            entry[property_name] = str(value)

    texture = _safe_get(expr, "texture", None)
    if texture is not None:
        entry["texture_path"] = _object_path(texture)

    material_function = _safe_get(expr, "material_function", None)
    if material_function is not None:
        entry["material_function_path"] = _object_path(material_function)

    collection = _safe_get(expr, "collection", None)
    if collection is not None:
        entry["collection_path"] = _object_path(collection)

    return entry


def inspect_material_graph(asset_path: str, output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = _load_asset(asset_path)

    expressions = _safe_get(material, "expressions", []) or []
    expression_entries = [_expression_entry(expr) for expr in expressions]

    result = {
        "asset_path": asset_path,
        "resolved_asset_name": _object_name(material),
        "resolved_asset_path": _object_path(material),
        "resolved_asset_class": _object_path(material.get_class()),
        "num_expressions": len(expression_entries),
        "expressions": expression_entries,
    }

    safe_name = _object_name(material) or "material"
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}_{safe_name}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(
        inspect_material_graph(
            "/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1"
        )
    )
