import json
import os

import unreal


OUTPUT_BASENAME = "rendering_api"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_rendering_api] Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    names = sorted(name for name in dir(unreal) if "render" in name.lower() or "material" in name.lower())
    rendering_library_methods = []
    rendering_library = getattr(unreal, "RenderingLibrary", None)
    if rendering_library is not None:
        rendering_library_methods = sorted(name for name in dir(rendering_library) if not name.startswith("__"))
    payload = {
        "names": names,
        "rendering_library_methods": rendering_library_methods,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
