import json
import os

import unreal


ASSET_PATH = "/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_probe_kamaz_physicsasset_api.json",
)


def _safe_get(obj, prop):
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return True, getter(prop), ""
        except Exception as exc:
            return False, None, str(exc)
    return False, None, "no get_editor_property"


def _safe_str(value):
    try:
        return str(value)
    except Exception:
        return "<unstringable>"


def main():
    payload = {"asset": ASSET_PATH, "dir": [], "props": {}, "error": ""}
    try:
        asset = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
        if asset is None:
            raise RuntimeError("asset load failed")
        payload["dir"] = sorted([name for name in dir(asset) if "body" in name.lower() or "constraint" in name.lower() or "skeleton" in name.lower() or "preview" in name.lower() or "setup" in name.lower() or "phys" in name.lower()])
        for prop in [
            "skeletal_body_setups",
            "skeletal_body_setup",
            "body_setup",
            "body_setups",
            "bounds_bodies",
            "constraint_setup",
            "constraint_setups",
            "preview_skeletal_mesh",
            "solver_settings",
            "physics_asset_solver_settings",
        ]:
            ok, value, err = _safe_get(asset, prop)
            payload["props"][prop] = {
                "ok": ok,
                "type": _safe_str(type(value)) if ok else "",
                "value": _safe_str(value) if ok else "",
                "error": err,
            }
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
