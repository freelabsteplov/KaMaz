import json
import os

import unreal


RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "increase_rt_snowtest_wheeltracks_resolution.json",
)


def main():
    payload = {
        "rt_path": RT_PATH,
        "before": {},
        "after": {},
        "saved": False,
        "error": "",
    }

    try:
        rt = unreal.EditorAssetLibrary.load_asset(RT_PATH)
        if not rt:
            raise RuntimeError(f"Missing render target: {RT_PATH}")

        before_x = int(rt.get_editor_property("size_x"))
        before_y = int(rt.get_editor_property("size_y"))
        new_size = max(before_x, before_y) * 2

        payload["before"] = {
            "size_x": before_x,
            "size_y": before_y,
            "render_target_format": str(rt.get_editor_property("render_target_format")),
        }

        rt.set_editor_property("size_x", new_size)
        rt.set_editor_property("size_y", new_size)

        post_edit_change = getattr(rt, "post_edit_change", None)
        if callable(post_edit_change):
            post_edit_change()

        payload["after"] = {
            "size_x": int(rt.get_editor_property("size_x")),
            "size_y": int(rt.get_editor_property("size_y")),
            "render_target_format": str(rt.get_editor_property("render_target_format")),
        }

        if payload["after"]["size_x"] != new_size or payload["after"]["size_y"] != new_size:
            raise RuntimeError("Render target size did not update to the requested value.")

        payload["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(rt, False))
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
