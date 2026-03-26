import json
import os

import unreal


PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "reparent_landscape_runtimefix_mi_to_clean_parent.json",
)


def main():
    result = {
        "parent_path": PARENT_PATH,
        "mi_path": MI_PATH,
        "saved": False,
        "error": "",
    }

    try:
        parent = unreal.EditorAssetLibrary.load_asset(PARENT_PATH)
        mi = unreal.EditorAssetLibrary.load_asset(MI_PATH)
        if parent is None:
            raise RuntimeError(f"Missing parent: {PARENT_PATH}")
        if mi is None:
            raise RuntimeError(f"Missing MI: {MI_PATH}")

        mi.set_editor_property("parent", parent)
        unreal.MaterialEditingLibrary.update_material_instance(mi)
        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mi, False))
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
