import json
import os

import unreal


OUTPUT_BASENAME = "material_editing_library_api"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_material_editing_library_api] Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    names = []
    for name in dir(unreal.MaterialEditingLibrary):
        if "param" in name.lower() or "default" in name.lower():
            names.append(name)
    payload = {"methods": sorted(names)}
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
