import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_probe_kamaz_bodysetup_save_methods.json",
)


def _safe_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_outer(obj):
    if obj is None:
        return ""
    try:
        return str(obj.get_outer())
    except Exception:
        return ""


def main():
    payload = {
        "body_path": "",
        "body_outer": "",
        "body_class": "",
        "body_methods": [],
        "package_path": "",
        "save_packages_doc": "",
        "save_loaded_asset_doc": "",
        "error": "",
    }

    try:
        iterator_cls = getattr(unreal, "ObjectIterator", None)
        if iterator_cls is None:
            raise RuntimeError("ObjectIterator unavailable")

        body = None
        for obj in iterator_cls(unreal.BodySetup):
            path = _safe_path(obj)
            if "kamaz_ue5_PhysicsAsset:WFL" in path:
                body = obj
                break

        if body is None:
            raise RuntimeError("Could not find WFL body setup")

        payload["body_path"] = _safe_path(body)
        payload["body_outer"] = _safe_outer(body)
        payload["body_class"] = body.get_class().get_name()
        payload["body_methods"] = sorted(
            name
            for name in dir(body)
            if any(token in name.lower() for token in ("save", "edit", "dirty", "physics", "cook", "create", "invalidate"))
        )

        physics_asset = unreal.EditorAssetLibrary.load_asset("/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset")
        payload["package_path"] = _safe_outer(physics_asset)

        if hasattr(unreal, "EditorLoadingAndSavingUtils"):
            payload["save_packages_doc"] = str(getattr(unreal.EditorLoadingAndSavingUtils.save_packages, "__doc__", ""))

        asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        payload["save_loaded_asset_doc"] = str(getattr(asset_subsystem.save_loaded_asset, "__doc__", ""))
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
