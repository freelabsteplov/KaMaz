import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "persist_snowtest_rvt_bounds_to_mpc_asset.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _vec_to_dict(value):
    if value is None:
        return None
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _color_to_dict(value):
    if value is None:
        return None
    return {
        "r": float(value.r),
        "g": float(value.g),
        "b": float(value.b),
        "a": float(value.a),
    }


def _to_linear_color(vector_value):
    return unreal.LinearColor(float(vector_value.x), float(vector_value.y), float(vector_value.z), 0.0)


def _get_actor_bounds(actor):
    try:
        return actor.get_actor_bounds(True)
    except Exception:
        return None, None


def _resolve_bounds_from_transform(actor):
    try:
        location = actor.get_actor_location()
        scale = actor.get_actor_scale3d()
    except Exception:
        return None, None

    if scale is None:
        return None, None

    if abs(float(scale.x)) <= 0.001 and abs(float(scale.y)) <= 0.001 and abs(float(scale.z)) <= 0.001:
        return None, None

    extent = unreal.Vector(float(scale.x) * 0.5, float(scale.y) * 0.5, float(scale.z) * 0.5)
    return location, extent


def _find_snow_rvt_volume():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if actor_subsystem is None:
        return None

    fallback = None
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            class_name = actor.get_class().get_name()
        except Exception:
            class_name = ""
        if "RuntimeVirtualTextureVolume" not in class_name:
            continue
        fallback = fallback or actor
        try:
            label = actor.get_actor_label()
        except Exception:
            label = ""
        if "Snow" in label or "RVT" in label:
            return actor
    return fallback


def _ensure_map_ready():
    actor = _find_snow_rvt_volume()
    if actor is not None:
        return actor
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return _find_snow_rvt_volume()


def _ensure_vector_parameter(parameters, parameter_name, default_value):
    for parameter in parameters:
        try:
            if str(parameter.get_editor_property("parameter_name")) == parameter_name:
                parameter.set_editor_property("default_value", default_value)
                return "updated"
        except Exception:
            continue

    parameter = unreal.CollectionVectorParameter()
    parameter.set_editor_property("parameter_name", parameter_name)
    parameter.set_editor_property("default_value", default_value)
    parameters.append(parameter)
    return "created"


def main():
    result = {
        "map": MAP_PATH,
        "mpc_path": MPC_PATH,
        "rvt_volume_path": "",
        "origin": None,
        "extent": None,
        "world_bounds_min": None,
        "world_bounds_max": None,
        "parameter_results": {},
        "saved": False,
        "error": "",
    }

    try:
        actor = _ensure_map_ready()
        if actor is None:
            raise RuntimeError("Could not find RuntimeVirtualTextureVolume on SnowTest_Level")

        used_transform_fallback = False
        origin, extent = _get_actor_bounds(actor)
        if origin is None or extent is None or (
            abs(float(extent.x)) <= 0.001 and abs(float(extent.y)) <= 0.001 and abs(float(extent.z)) <= 0.001
        ):
            origin, extent = _resolve_bounds_from_transform(actor)
            used_transform_fallback = True
        if origin is None or extent is None:
            raise RuntimeError("Could not read SnowTest RVT volume bounds")

        world_bounds_min = unreal.Vector(
            float(origin.x - extent.x),
            float(origin.y - extent.y),
            float(origin.z - extent.z),
        )
        world_bounds_max = unreal.Vector(
            float(origin.x + extent.x),
            float(origin.y + extent.y),
            float(origin.z + extent.z),
        )

        collection = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
        if collection is None:
            raise RuntimeError(f"Missing MPC asset {MPC_PATH}")

        vector_parameters = list(collection.get_editor_property("vector_parameters") or [])
        collection.modify(True)
        result["parameter_results"]["WorldBoundsMin"] = _ensure_vector_parameter(
            vector_parameters,
            "WorldBoundsMin",
            _to_linear_color(world_bounds_min),
        )
        result["parameter_results"]["WorldBoundsMax"] = _ensure_vector_parameter(
            vector_parameters,
            "WorldBoundsMax",
            _to_linear_color(world_bounds_max),
        )
        result["parameter_results"]["BrushUV"] = _ensure_vector_parameter(
            vector_parameters,
            "BrushUV",
            unreal.LinearColor(0.0, 0.0, 0.0, 0.0),
        )
        collection.set_editor_property("vector_parameters", vector_parameters)
        if callable(getattr(collection, "mark_package_dirty", None)):
            collection.mark_package_dirty()
        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(collection, False))
        result["bounds_source"] = "actor_transform_fallback" if used_transform_fallback else "actor_bounds"

        result["rvt_volume_path"] = _path(actor)
        result["origin"] = _vec_to_dict(origin)
        result["extent"] = _vec_to_dict(extent)
        result["world_bounds_min"] = _vec_to_dict(world_bounds_min)
        result["world_bounds_max"] = _vec_to_dict(world_bounds_max)
        result["saved_parameters"] = []
        for parameter in list(collection.get_editor_property("vector_parameters") or []):
            try:
                name = str(parameter.get_editor_property("parameter_name"))
            except Exception:
                continue
            if name not in ("WorldBoundsMin", "WorldBoundsMax", "BrushUV"):
                continue
            result["saved_parameters"].append(
                {
                    "parameter_name": name,
                    "default_value": _color_to_dict(parameter.get_editor_property("default_value")),
                }
            )
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
