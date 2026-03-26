import json
import os

import unreal


RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_rt_python_api.json",
)


def main():
    payload = {
        "rt_path": RT_PATH,
        "class_name": "",
        "candidate_names": [],
        "interesting_values": {},
        "error": "",
    }

    try:
        rt = unreal.EditorAssetLibrary.load_asset(RT_PATH)
        if not rt:
            raise RuntimeError(f"Missing render target: {RT_PATH}")

        payload["class_name"] = rt.get_class().get_name()
        payload["candidate_names"] = sorted(
            [
                name
                for name in dir(rt)
                if any(token in name.lower() for token in ("size", "resize", "init", "target", "format", "render"))
            ]
        )
        for prop_name in (
            "size_x",
            "size_y",
            "max_texture_size",
            "resize_during_build_x",
            "resize_during_build_y",
            "render_target_format",
        ):
            try:
                payload["interesting_values"][prop_name] = str(rt.get_editor_property(prop_name))
            except Exception as exc:
                payload["interesting_values"][prop_name] = f"<error: {exc}>"
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
