import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import nanite_material_tools as nmt


OUTPUT_BASENAME = "fix_known_invalid_nanite_spam"
TARGET_ROOTS = [
    "/Game/Meshes/Clumba",
    "/Game/CitySampleVehicles/vehicle02_Car",
    "/Game/Datasmith/DS_StreetLight/Geometries",
    "/Game/Datasmith/DS_Police/Geometries",
    "/Game/Datasmith/Ostanovka_Cineware/Geometries",
]


def _log(message: str) -> None:
    unreal.log(f"[fix_known_invalid_nanite_spam] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _scan_and_fix_root(nanite_tools, root: str) -> dict:
    invalid_before = nanite_tools.scan_invalid_nanite_meshes(root)
    updated = nanite_tools.disable_nanite_for_invalid_meshes(root)
    invalid_after = nanite_tools.scan_invalid_nanite_meshes(root)

    return {
        "root": root,
        "success": len(invalid_after) == 0,
        "invalid_before_count": len(invalid_before),
        "updated_count": len(updated),
        "invalid_after_count": len(invalid_after),
        "updated_meshes": [entry.get("mesh", "") for entry in updated],
        "updated_entries": updated,
        "invalid_after_entries": invalid_after,
        "summary": (
            f"{root} invalid_before={len(invalid_before)} "
            f"updated={len(updated)} invalid_after={len(invalid_after)}"
        ),
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    nanite_tools = importlib.reload(nmt)

    root_results = []
    for root in TARGET_ROOTS:
        root_results.append(_scan_and_fix_root(nanite_tools, root))

    total_invalid_before = sum(item["invalid_before_count"] for item in root_results)
    total_updated = sum(item["updated_count"] for item in root_results)
    total_invalid_after = sum(item["invalid_after_count"] for item in root_results)

    result = {
        "target_roots": TARGET_ROOTS,
        "success": total_invalid_after == 0,
        "total_invalid_before_count": total_invalid_before,
        "total_updated_count": total_updated,
        "total_invalid_after_count": total_invalid_after,
        "root_results": root_results,
        "notes": [
            "This changes only StaticMesh assets under known spam-producing roots.",
            "It disables Nanite only where a non-opaque material is assigned.",
            "This is intended to stop repeated Nanite/translucent warning spam in the editor log.",
            "No Kamaz input, MOZA input, or snow materials are modified by this helper.",
        ],
        "summary": (
            f"known_invalid_nanite total_before={total_invalid_before} "
            f"updated={total_updated} total_after={total_invalid_after}"
        ),
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["result"]["summary"])
    for item in payload["result"]["root_results"]:
        _log(item["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload["result"].get("success", False),
        "summary": payload["result"].get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
