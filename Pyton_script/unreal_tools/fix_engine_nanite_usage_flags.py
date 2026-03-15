import json
import os

import unreal


OUTPUT_BASENAME = "fix_engine_nanite_usage_flags"
ASSET_LIB = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary
TARGET_MATERIALS = [
    "/InterchangeAssets/gltf/M_Default.M_Default",
    "/Engine/VREditor/BasicMeshes/M_Floor_01.M_Floor_01",
]


def _log(message: str) -> None:
    unreal.log(f"[fix_engine_nanite_usage_flags] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _resolve_nanite_usage_enum():
    enum_type = getattr(unreal, "MaterialUsage", None)
    if not enum_type:
        return None

    for name in dir(enum_type):
        if name.lower() == "matusage_nanite":
            return getattr(enum_type, name)

    for name in dir(enum_type):
        if "nanite" in name.lower():
            return getattr(enum_type, name)

    return None


def _set_property_if_present(material, prop_name: str, value) -> bool:
    try:
        material.set_editor_property(prop_name, value)
        return True
    except Exception:
        return False


def _fix_material(asset_path: str, nanite_usage) -> dict:
    asset = ASSET_LIB.load_asset(asset_path)
    result = {
        "asset": asset_path,
        "found": bool(asset),
        "class": type(asset).__name__ if asset else None,
        "usage_set_result": None,
        "needs_recompile": None,
        "property_set": False,
        "recompiled": False,
        "saved": False,
        "errors": [],
    }

    if not asset:
        result["errors"].append("asset_not_found")
        return result

    if type(asset).__name__ != "Material":
        result["errors"].append(f"unexpected_class:{type(asset).__name__}")
        return result

    try:
        asset.modify()
    except Exception as exc:
        result["errors"].append(f"modify_failed:{exc}")

    if nanite_usage is not None:
        try:
            usage_response = MATERIAL_LIB.set_material_usage(asset, nanite_usage)
            if isinstance(usage_response, tuple):
                result["usage_set_result"] = bool(usage_response[0])
                result["needs_recompile"] = bool(usage_response[1])
            else:
                result["usage_set_result"] = bool(usage_response)
        except Exception as exc:
            result["errors"].append(f"set_material_usage_failed:{exc}")
    else:
        result["errors"].append("nanite_usage_enum_not_found")

    property_names = ("used_with_nanite", "b_used_with_nanite", "bUsedWithNanite")
    for prop_name in property_names:
        if _set_property_if_present(asset, prop_name, True):
            result["property_set"] = True
            break

    try:
        MATERIAL_LIB.recompile_material(asset)
        result["recompiled"] = True
    except Exception as exc:
        result["errors"].append(f"recompile_failed:{exc}")

    try:
        result["saved"] = bool(ASSET_LIB.save_loaded_asset(asset, False))
    except Exception as exc:
        result["errors"].append(f"save_failed:{exc}")

    return result


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    nanite_usage = _resolve_nanite_usage_enum()
    entries = [_fix_material(asset_path, nanite_usage) for asset_path in TARGET_MATERIALS]
    success = all(item["found"] and item["saved"] for item in entries)
    summary = (
        f"engine_nanite_usage fixed={sum(1 for item in entries if item['saved'])}/"
        f"{len(entries)}"
    )

    result = {
        "targets": TARGET_MATERIALS,
        "success": success,
        "summary": summary,
        "entries": entries,
        "notes": [
            "This touches only the reported engine/plugin materials.",
            "It explicitly applies Nanite material usage, recompiles, and saves.",
            "This does not modify project gameplay assets, Kamaz input, MOZA input, or snow receivers.",
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["result"]["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload["result"].get("success", False),
        "summary": payload["result"].get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
