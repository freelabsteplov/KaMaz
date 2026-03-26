import json
import os

import unreal


OUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "_tmp_probe_menu_factory_details.json")


def list_editor_props(obj):
    names = []
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            obj.get_editor_property(name)
            names.append(name)
        except Exception:
            continue
    return sorted(set(names))


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    payload = {}

    wbf = unreal.WidgetBlueprintFactory()
    payload["WidgetBlueprintFactory.editor_properties"] = list_editor_props(wbf)

    daf = unreal.DataAssetFactory()
    payload["DataAssetFactory.editor_properties"] = list_editor_props(daf)

    if hasattr(unreal, "EditorLevelLibrary"):
        payload["EditorLevelLibrary.functions"] = sorted(
            [name for name in dir(unreal.EditorLevelLibrary) if not name.startswith("_")]
        )

    if hasattr(unreal, "EditorActorSubsystem"):
        payload["EditorActorSubsystem.exists"] = True

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(payload)


if __name__ == "__main__":
    main()
