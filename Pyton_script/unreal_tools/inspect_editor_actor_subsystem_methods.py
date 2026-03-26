import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_editor_actor_subsystem_methods.json",
)


def main():
    result = {
        "methods": [],
        "error": "",
    }
    try:
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for name in sorted(dir(subsystem)):
            lowered = name.lower()
            if "hidden" in lowered or "editor" in lowered or "visibility" in lowered:
                result["methods"].append(name)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
