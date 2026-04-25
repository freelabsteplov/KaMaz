import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_probe_unreal_bodysetup_api.json",
)


def _safe_str(value):
    try:
        return str(value)
    except Exception:
        return "<unstringable>"


def main():
    payload = {
        "has_BodySetup": hasattr(unreal, "BodySetup"),
        "has_get_objects_of_class": hasattr(unreal, "get_objects_of_class"),
        "has_ObjectIterator": hasattr(unreal, "ObjectIterator"),
        "BodySetup_dir": [],
        "sample_paths": [],
        "error": "",
    }
    try:
        if hasattr(unreal, "BodySetup"):
            payload["BodySetup_dir"] = sorted([name for name in dir(unreal.BodySetup) if "geom" in name.lower() or "agg" in name.lower() or "bone" in name.lower() or "elem" in name.lower() or "box" in name.lower() or "sphere" in name.lower() or "sphyl" in name.lower()])
        if hasattr(unreal, "get_objects_of_class") and hasattr(unreal, "BodySetup"):
            try:
                objs = unreal.get_objects_of_class(unreal.BodySetup)
            except TypeError:
                objs = unreal.get_objects_of_class(unreal.BodySetup.static_class())
            payload["sample_paths"] = [_safe_str(getattr(obj, "get_path_name", lambda: obj)()) for obj in list(objs or [])[:20]]
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
