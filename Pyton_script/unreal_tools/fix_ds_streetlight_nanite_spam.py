import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import nanite_material_tools as nmt


OUTPUT_BASENAME = "fix_ds_streetlight_nanite_spam"
DS_STREETLIGHT_ROOT = "/Game/Datasmith/DS_StreetLight/Geometries"


def _log(message: str) -> None:
    unreal.log(f"[fix_ds_streetlight_nanite_spam] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    nanite_tools = importlib.reload(nmt)

    invalid_before = nanite_tools.scan_invalid_nanite_meshes(DS_STREETLIGHT_ROOT)
    updated = nanite_tools.disable_nanite_for_invalid_meshes(DS_STREETLIGHT_ROOT)
    invalid_after = nanite_tools.scan_invalid_nanite_meshes(DS_STREETLIGHT_ROOT)

    result = {
        "root": DS_STREETLIGHT_ROOT,
        "success": len(invalid_after) == 0,
        "invalid_before_count": len(invalid_before),
        "updated_count": len(updated),
        "invalid_after_count": len(invalid_after),
        "updated_meshes": [entry.get("mesh", "") for entry in updated],
        "updated_entries": updated,
        "notes": [
            "This changes only StaticMesh assets under /Game/Datasmith/DS_StreetLight/Geometries.",
            "It disables Nanite only where a non-opaque material is assigned.",
            "This is intended to stop repeated Nanite/translucent warning spam in the editor log.",
        ],
        "summary": (
            f"DS_StreetLight invalid_nanite_before={len(invalid_before)} "
            f"updated={len(updated)} invalid_after={len(invalid_after)}"
        ),
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
