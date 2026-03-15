import json
import os

import unreal


OUTPUT_BASENAME = "fix_clumba_spruce_nanite"
TARGET_MESHES = [
    "/Game/Meshes/Clumba/1_Cube_007.1_Cube_007",
    "/Game/Meshes/Clumba/1_Cube_012.1_Cube_012",
    "/Game/Meshes/Clumba/Cube_009.Cube_009",
]


def _log(message: str) -> None:
    unreal.log(f"[fix_clumba_spruce_nanite] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _disable_nanite(mesh_path: str) -> dict:
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not mesh or type(mesh).__name__ != "StaticMesh":
        return {"mesh": mesh_path, "found": False, "updated": False, "saved": False}

    nanite = mesh.get_editor_property("nanite_settings")
    was_enabled = nanite.get_editor_property("enabled")
    if not was_enabled:
        return {"mesh": mesh_path, "found": True, "updated": False, "saved": False}

    mesh.modify()
    nanite.set_editor_property("enabled", False)
    mesh.set_editor_property("nanite_settings", nanite)
    saved = unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
    return {"mesh": mesh_path, "found": True, "updated": True, "saved": saved}


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    entries = [_disable_nanite(mesh_path) for mesh_path in TARGET_MESHES]
    updated_count = sum(1 for item in entries if item["updated"])
    success = all(item["found"] for item in entries) and all(
        item["saved"] or not item["updated"] for item in entries
    )

    result = {
        "target_meshes": TARGET_MESHES,
        "success": success,
        "updated_count": updated_count,
        "entries": entries,
        "summary": f"clumba_spruce updated={updated_count}/{len(TARGET_MESHES)}",
        "notes": [
            "This changes only the three Clumba spruce meshes that dominate the Nanite/translucent warning spam.",
            "It only disables Nanite on these StaticMesh assets.",
            "A level/editor reload may be required before the warning spam fully stops.",
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
