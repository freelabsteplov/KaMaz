import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
KAMAZ_LABEL = "Kamaz_SnowTest"
ROAD_LABEL_TOKEN = "SnowSplineRoad"
ROAD_CLASS_TOKEN = "SnowSplineRoadActor"
BOUNDS_MARGIN_XY_CM = 4000.0
BOUNDS_MARGIN_Z_CM = 500.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "persist_snowtest_wheel_rt_bounds_to_mpc_asset.json",
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


def _safe_label(actor):
    if actor is None:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        try:
            return actor.get_name()
        except Exception:
            return ""


def _safe_class_name(actor):
    if actor is None:
        return ""
    try:
        return actor.get_class().get_name()
    except Exception:
        return ""


def _get_actor_bounds(actor):
    try:
        origin, extent = actor.get_actor_bounds(False)
        if extent is not None and (
            abs(float(extent.x)) > 0.001 or abs(float(extent.y)) > 0.001 or abs(float(extent.z)) > 0.001
        ):
            return origin, extent
    except Exception:
        pass

    try:
        primitive_components = list(actor.get_components_by_class(unreal.PrimitiveComponent) or [])
    except Exception:
        primitive_components = []

    aggregate_min = None
    aggregate_max = None
    for component in primitive_components:
        try:
            bounds = component.get_editor_property("bounds")
            origin = bounds.origin
            extent = bounds.box_extent
        except Exception:
            continue

        component_min = unreal.Vector(
            float(origin.x - extent.x),
            float(origin.y - extent.y),
            float(origin.z - extent.z),
        )
        component_max = unreal.Vector(
            float(origin.x + extent.x),
            float(origin.y + extent.y),
            float(origin.z + extent.z),
        )
        if aggregate_min is None:
            aggregate_min = component_min
            aggregate_max = component_max
        else:
            aggregate_min = unreal.Vector(
                min(float(aggregate_min.x), float(component_min.x)),
                min(float(aggregate_min.y), float(component_min.y)),
                min(float(aggregate_min.z), float(component_min.z)),
            )
            aggregate_max = unreal.Vector(
                max(float(aggregate_max.x), float(component_max.x)),
                max(float(aggregate_max.y), float(component_max.y)),
                max(float(aggregate_max.z), float(component_max.z)),
            )

    if aggregate_min is None or aggregate_max is None:
        return None, None

    origin = unreal.Vector(
        float((aggregate_min.x + aggregate_max.x) * 0.5),
        float((aggregate_min.y + aggregate_max.y) * 0.5),
        float((aggregate_min.z + aggregate_max.z) * 0.5),
    )
    extent = unreal.Vector(
        float((aggregate_max.x - aggregate_min.x) * 0.5),
        float((aggregate_max.y - aggregate_min.y) * 0.5),
        float((aggregate_max.z - aggregate_min.z) * 0.5),
    )
    return origin, extent


def _ensure_map_ready():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors() or [])
    if actors:
        return actors
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return list(actor_subsystem.get_all_level_actors() or [])


def _is_relevant_actor(actor):
    label = _safe_label(actor)
    class_name = _safe_class_name(actor)
    if label == KAMAZ_LABEL:
        return True
    if ROAD_LABEL_TOKEN in label or ROAD_CLASS_TOKEN in class_name:
        return True
    return False


def _actor_role(actor):
    label = _safe_label(actor)
    if label == KAMAZ_LABEL:
        return "kamaz"
    return "road"


def _accumulate_bounds(bounds_min, bounds_max, origin, extent):
    actor_min = unreal.Vector(
        float(origin.x - extent.x),
        float(origin.y - extent.y),
        float(origin.z - extent.z),
    )
    actor_max = unreal.Vector(
        float(origin.x + extent.x),
        float(origin.y + extent.y),
        float(origin.z + extent.z),
    )
    if bounds_min is None:
        return actor_min, actor_max

    return (
        unreal.Vector(
            min(float(bounds_min.x), float(actor_min.x)),
            min(float(bounds_min.y), float(actor_min.y)),
            min(float(bounds_min.z), float(actor_min.z)),
        ),
        unreal.Vector(
            max(float(bounds_max.x), float(actor_max.x)),
            max(float(bounds_max.y), float(actor_max.y)),
            max(float(bounds_max.z), float(actor_max.z)),
        ),
    )


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


def _apply_runtime_mpc_vector(collection, parameter_name, value):
    world = unreal.EditorLevelLibrary.get_editor_world()
    library = getattr(unreal, "KismetMaterialLibrary", None)
    if world is None or library is None:
        return False

    for setter_name in ("set_vector_parameter_value", "set_vector_parameter_value_by_name"):
        setter = getattr(library, setter_name, None)
        if setter is None:
            continue
        try:
            setter(world, collection, parameter_name, value)
            return True
        except TypeError:
            try:
                setter(collection, parameter_name, value)
                return True
            except Exception:
                continue
        except Exception:
            continue
    return False


def main():
    result = {
        "map": MAP_PATH,
        "mpc_path": MPC_PATH,
        "sources": [],
        "bounds_source": "road_zone_with_kamaz_margin",
        "base_world_bounds_min": None,
        "base_world_bounds_max": None,
        "world_bounds_min": None,
        "world_bounds_max": None,
        "parameter_results": {},
        "runtime_parameter_results": {},
        "saved": False,
        "error": "",
    }

    try:
        actors = _ensure_map_ready()
        relevant_actors = [actor for actor in actors if _is_relevant_actor(actor)]
        if not relevant_actors:
            raise RuntimeError("Could not find SnowTest road actors or Kamaz for wheel RT bounds.")

        bounds_min = None
        bounds_max = None
        for actor in relevant_actors:
            origin, extent = _get_actor_bounds(actor)
            if origin is None or extent is None:
                continue
            bounds_min, bounds_max = _accumulate_bounds(bounds_min, bounds_max, origin, extent)
            result["sources"].append(
                {
                    "role": _actor_role(actor),
                    "label": _safe_label(actor),
                    "path": _path(actor),
                    "bounds_origin": _vec_to_dict(origin),
                    "bounds_extent": _vec_to_dict(extent),
                }
            )

        if bounds_min is None or bounds_max is None:
            raise RuntimeError("Failed to resolve combined wheel RT bounds from SnowTest road zone.")

        result["base_world_bounds_min"] = _vec_to_dict(bounds_min)
        result["base_world_bounds_max"] = _vec_to_dict(bounds_max)

        padded_min = unreal.Vector(
            float(bounds_min.x - BOUNDS_MARGIN_XY_CM),
            float(bounds_min.y - BOUNDS_MARGIN_XY_CM),
            float(bounds_min.z - BOUNDS_MARGIN_Z_CM),
        )
        padded_max = unreal.Vector(
            float(bounds_max.x + BOUNDS_MARGIN_XY_CM),
            float(bounds_max.y + BOUNDS_MARGIN_XY_CM),
            float(bounds_max.z + BOUNDS_MARGIN_Z_CM),
        )

        collection = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
        if collection is None:
            raise RuntimeError(f"Missing MPC asset {MPC_PATH}")

        vector_parameters = list(collection.get_editor_property("vector_parameters") or [])
        collection.modify(True)
        result["parameter_results"]["WorldBoundsMin"] = _ensure_vector_parameter(
            vector_parameters,
            "WorldBoundsMin",
            _to_linear_color(padded_min),
        )
        result["parameter_results"]["WorldBoundsMax"] = _ensure_vector_parameter(
            vector_parameters,
            "WorldBoundsMax",
            _to_linear_color(padded_max),
        )
        result["parameter_results"]["BrushUV"] = _ensure_vector_parameter(
            vector_parameters,
            "BrushUV",
            unreal.LinearColor(0.5, 0.5, 0.0, 0.0),
        )
        collection.set_editor_property("vector_parameters", vector_parameters)
        if callable(getattr(collection, "mark_package_dirty", None)):
            collection.mark_package_dirty()
        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(collection, False))

        result["runtime_parameter_results"]["WorldBoundsMin"] = bool(
            _apply_runtime_mpc_vector(collection, "WorldBoundsMin", _to_linear_color(padded_min))
        )
        result["runtime_parameter_results"]["WorldBoundsMax"] = bool(
            _apply_runtime_mpc_vector(collection, "WorldBoundsMax", _to_linear_color(padded_max))
        )
        result["runtime_parameter_results"]["BrushUV"] = bool(
            _apply_runtime_mpc_vector(collection, "BrushUV", unreal.LinearColor(0.5, 0.5, 0.0, 0.0))
        )

        result["world_bounds_min"] = _vec_to_dict(padded_min)
        result["world_bounds_max"] = _vec_to_dict(padded_max)
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
