import json
import os

import unreal


PHYSICS_ASSET_PATH = "/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset"
TARGET_BONES = {"WFL", "WFR", "WRL", "WRR"}
TARGET_RADIUS_CM = 30.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_try_save_kamaz_physicsasset_v2.json",
)


def _safe_get(obj, prop, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop)
        except Exception:
            pass
    return getattr(obj, prop, default)


def _safe_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def main():
    payload = {
        "physics_asset_path": PHYSICS_ASSET_PATH,
        "target_radius_cm": TARGET_RADIUS_CM,
        "updated_bodies": [],
        "save_loaded_asset_ok": False,
        "save_packages_ok": False,
        "package": "",
        "error": "",
    }

    try:
        physics_asset = unreal.EditorAssetLibrary.load_asset(PHYSICS_ASSET_PATH)
        if physics_asset is None:
            raise RuntimeError(f"Could not load {PHYSICS_ASSET_PATH}")

        package = physics_asset.get_outermost()
        payload["package"] = _safe_path(package)

        bodies = []
        iterator_cls = getattr(unreal, "ObjectIterator", None)
        if iterator_cls is None:
            raise RuntimeError("ObjectIterator unavailable")

        for obj in iterator_cls(unreal.BodySetup):
            path = _safe_path(obj)
            if "kamaz_ue5_PhysicsAsset" not in path:
                continue
            bone_name = str(_safe_get(obj, "bone_name", ""))
            if bone_name not in TARGET_BONES:
                continue
            bodies.append(obj)

        if not bodies:
            raise RuntimeError("No wheel BodySetup objects found")

        touched = False
        for body in bodies:
            body.modify()
            agg = _safe_get(body, "agg_geom")
            sphere_elems = list(_safe_get(agg, "sphere_elems", []) or [])
            before = []
            after = []
            for sphere in sphere_elems:
                before.append(float(_safe_get(sphere, "radius", 0.0)))
                setter = getattr(sphere, "set_editor_property", None)
                if callable(setter):
                    setter("radius", TARGET_RADIUS_CM)
                else:
                    sphere.radius = TARGET_RADIUS_CM
                after.append(float(_safe_get(sphere, "radius", 0.0)))
            if not sphere_elems:
                continue

            agg_setter = getattr(agg, "set_editor_property", None)
            if callable(agg_setter):
                agg_setter("sphere_elems", sphere_elems)

            body_setter = getattr(body, "set_editor_property", None)
            if callable(body_setter):
                body_setter("agg_geom", agg)

            invalidate = getattr(body, "invalidate_physics_data", None)
            if callable(invalidate):
                invalidate()

            create = getattr(body, "create_physics_meshes", None)
            if callable(create):
                create()

            mark_dirty = getattr(body, "mark_package_dirty", None)
            if callable(mark_dirty):
                mark_dirty()

            payload["updated_bodies"].append(
                {
                    "bone_name": str(_safe_get(body, "bone_name", "")),
                    "body_path": _safe_path(body),
                    "radii_before": before,
                    "radii_after": after,
                }
            )
            touched = True

        if not touched:
            raise RuntimeError("No sphere elements touched")

        physics_asset.modify()
        physics_mark_dirty = getattr(physics_asset, "mark_package_dirty", None)
        if callable(physics_mark_dirty):
            physics_mark_dirty()

        if package is not None:
            package_mark_dirty = getattr(package, "mark_package_dirty", None)
            if callable(package_mark_dirty):
                package_mark_dirty()

        asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        payload["save_loaded_asset_ok"] = bool(asset_subsystem.save_loaded_asset(physics_asset, False))

        if hasattr(unreal, "EditorLoadingAndSavingUtils") and package is not None:
            payload["save_packages_ok"] = bool(
                unreal.EditorLoadingAndSavingUtils.save_packages([package], False)
            )
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
