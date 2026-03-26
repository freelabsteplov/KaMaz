import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_unreal_math_library.json",
)


def main():
    result = {
        "has_MathLibrary": hasattr(unreal, "MathLibrary"),
        "has_KismetMathLibrary": hasattr(unreal, "KismetMathLibrary"),
        "math_library_look_methods": [],
        "kismet_math_library_look_methods": [],
        "error": "",
    }

    try:
        if hasattr(unreal, "MathLibrary"):
            result["math_library_look_methods"] = sorted(
                [name for name in dir(unreal.MathLibrary) if "look" in name.lower()]
            )
        if hasattr(unreal, "KismetMathLibrary"):
            result["kismet_math_library_look_methods"] = sorted(
                [name for name in dir(unreal.KismetMathLibrary) if "look" in name.lower()]
            )
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
