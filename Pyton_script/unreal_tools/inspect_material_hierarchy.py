import json
import os

import unreal


OUTPUT_BASENAME = "material_hierarchy"


def _log(message: str) -> None:
    unreal.log(f"[inspect_material_hierarchy] {message}")


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


def _get_parent(material):
    for property_name in ("parent", "Parent", "ParentEditorOnly"):
        try:
            parent = material.get_editor_property(property_name)
            if parent is not None:
                return parent
        except Exception:
            continue
    return None


def _collect_parent_chain(material):
    chain = []
    seen = set()
    current = material

    while current is not None:
        current_path = _object_path(current)
        if current_path in seen:
            break
        seen.add(current_path)
        chain.append(
            {
                "asset_name": _object_name(current),
                "asset_path": current_path,
                "asset_class": _object_path(current.get_class()),
            }
        )
        current = _get_parent(current)

    return chain


def _try_get_texture_parameter_values(material):
    values = []
    library = getattr(unreal, "MaterialEditingLibrary", None)
    if library is None:
        return values

    getter = getattr(library, "get_texture_parameter_names", None)
    value_getter = getattr(library, "get_material_instance_texture_parameter_value", None)
    if getter is None or value_getter is None:
        return values

    try:
        parameter_names = getter(material) or []
    except Exception:
        parameter_names = []

    for parameter_name in parameter_names:
        try:
            texture = value_getter(material, parameter_name)
        except Exception:
            texture = None

        values.append(
            {
                "parameter_name": str(parameter_name),
                "texture_name": _object_name(texture),
                "texture_path": _object_path(texture),
            }
        )

    return values


def inspect_material_hierarchy(asset_path: str, output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = _load_asset(asset_path)

    result = {
        "requested_asset_path": asset_path,
        "resolved_asset_name": _object_name(material),
        "resolved_asset_path": _object_path(material),
        "resolved_asset_class": _object_path(material.get_class()),
        "parent_chain": _collect_parent_chain(material),
        "texture_parameters": _try_get_texture_parameter_values(material),
    }

    safe_name = _object_name(material) or "material"
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}_{safe_name}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(
        inspect_material_hierarchy(
            "/Game/SnappyRoads/Materials/Old/M_SR_RoadSection001_Inst"
        )
    )
