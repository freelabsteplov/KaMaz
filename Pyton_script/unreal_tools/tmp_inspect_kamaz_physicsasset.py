import json
import os

import unreal


PHYSICS_ASSET_PATH = "/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset"
SKELETAL_MESH_PATH = "/Game/CityPark/Kamaz/model/kamaz_ue5"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_inspect_kamaz_physicsasset.json",
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


def _safe_name(obj):
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _vec(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _sphere_elem(elem):
    return {
        "center": _vec(_safe_get(elem, "center")),
        "radius": float(_safe_get(elem, "radius", 0.0)),
        "rotation": _rot(_safe_get(elem, "rotation")),
    }


def _box_elem(elem):
    return {
        "center": _vec(_safe_get(elem, "center")),
        "rotation": _rot(_safe_get(elem, "rotation")),
        "x": float(_safe_get(elem, "x", 0.0)),
        "y": float(_safe_get(elem, "y", 0.0)),
        "z": float(_safe_get(elem, "z", 0.0)),
    }


def _sphyl_elem(elem):
    return {
        "center": _vec(_safe_get(elem, "center")),
        "rotation": _rot(_safe_get(elem, "rotation")),
        "radius": float(_safe_get(elem, "radius", 0.0)),
        "length": float(_safe_get(elem, "length", 0.0)),
    }


def _capsule_min_z(capsule):
    center = capsule.get("center") or {"z": 0.0}
    radius = float(capsule.get("radius") or 0.0)
    length = float(capsule.get("length") or 0.0)
    half_height = radius + max(length * 0.5, 0.0)
    return float(center["z"] - half_height)


def _box_min_z(box):
    center = box.get("center") or {"z": 0.0}
    half_z = float(box.get("z") or 0.0) * 0.5
    return float(center["z"] - half_z)


def _sphere_min_z(sphere):
    center = sphere.get("center") or {"z": 0.0}
    radius = float(sphere.get("radius") or 0.0)
    return float(center["z"] - radius)


def main():
    result = {
        "physics_asset_path": PHYSICS_ASSET_PATH,
        "skeletal_mesh_path": SKELETAL_MESH_PATH,
        "preview_mesh": "",
        "body_count": 0,
        "bodies": [],
        "lowest_shapes": [],
        "error": "",
    }

    try:
        physics_asset = unreal.EditorAssetLibrary.load_asset(PHYSICS_ASSET_PATH)
        if physics_asset is None:
            raise RuntimeError(f"Could not load {PHYSICS_ASSET_PATH}")

        skeletal_mesh = unreal.EditorAssetLibrary.load_asset(SKELETAL_MESH_PATH)
        if skeletal_mesh is None:
            raise RuntimeError(f"Could not load {SKELETAL_MESH_PATH}")

        result["preview_mesh"] = _safe_path(_safe_get(physics_asset, "preview_skeletal_mesh"))
        result["assigned_physics_asset_on_mesh"] = _safe_path(_safe_get(skeletal_mesh, "physics_asset"))

        bodies = []
        iterator_cls = getattr(unreal, "ObjectIterator", None)
        if iterator_cls is not None:
            try:
                for obj in iterator_cls(unreal.BodySetup):
                    path = _safe_path(obj)
                    if "kamaz_ue5_PhysicsAsset" not in path:
                        continue
                    bodies.append(obj)
            except Exception:
                pass

        result["body_count"] = len(bodies)

        lowest_shapes = []
        for body in bodies:
            agg = _safe_get(body, "agg_geom")
            spheres = [_sphere_elem(elem) for elem in list(_safe_get(agg, "sphere_elems", []) or [])]
            boxes = [_box_elem(elem) for elem in list(_safe_get(agg, "box_elems", []) or [])]
            sphyls = [_sphyl_elem(elem) for elem in list(_safe_get(agg, "sphyl_elems", []) or [])]

            body_entry = {
                "body_name": _safe_name(body),
                "bone_name": str(_safe_get(body, "bone_name", "")),
                "physics_type": str(_safe_get(body, "physics_type", "")),
                "collision_trace_flag": str(_safe_get(body, "collision_trace_flag", "")),
                "spheres": spheres,
                "boxes": boxes,
                "sphyls": sphyls,
            }
            result["bodies"].append(body_entry)

            for idx, sphere in enumerate(spheres):
                lowest_shapes.append(
                    {
                        "bone_name": body_entry["bone_name"],
                        "shape_type": "sphere",
                        "shape_index": idx,
                        "min_z": _sphere_min_z(sphere),
                        "data": sphere,
                    }
                )
            for idx, box in enumerate(boxes):
                lowest_shapes.append(
                    {
                        "bone_name": body_entry["bone_name"],
                        "shape_type": "box",
                        "shape_index": idx,
                        "min_z": _box_min_z(box),
                        "data": box,
                    }
                )
            for idx, sphyl in enumerate(sphyls):
                lowest_shapes.append(
                    {
                        "bone_name": body_entry["bone_name"],
                        "shape_type": "sphyl",
                        "shape_index": idx,
                        "min_z": _capsule_min_z(sphyl),
                        "data": sphyl,
                    }
                )

        lowest_shapes.sort(key=lambda item: item["min_z"])
        result["lowest_shapes"] = lowest_shapes[:20]
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
