import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
KAMAZ_LABEL = "Kamaz_SnowTest"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
TEMP_MI_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/MI_WheelProbeTemp_Runtime"
DEFAULT_BRUSH_LENGTH_CM = 220.0
DEFAULT_BRUSH_WIDTH_CM = 70.0
DEFAULT_BRUSH_STRENGTH = 1.0
DEFAULT_WHEEL_TRACK_FALLOFF = 1.6
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_snowtest_wheel_rt_writer.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _name(obj):
    if not obj:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _safe_get(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            return default
    return getattr(obj, property_name, default)


def _safe_set(obj, property_name, value):
    if obj is None:
        return False, "missing"
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(property_name, value)
            return True, ""
        except Exception as exc:
            return False, str(exc)
    try:
        setattr(obj, property_name, value)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Name):
        return str(value)
    path_name = _path(value)
    if path_name:
        return path_name
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _find_kamaz_actor():
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fallback = None
    for actor in list(actor_sub.get_all_level_actors() or []):
        label = ""
        try:
            label = actor.get_actor_label()
        except Exception:
            label = ""
        if label == KAMAZ_LABEL:
            return actor
        actor_name = _name(actor)
        actor_class = _name(actor.get_class()) if actor else ""
        if "Kamaz" in actor_name or "Kamaz" in actor_class:
            fallback = fallback or actor
    return fallback


def _find_wheel_component(kamaz_actor):
    if not kamaz_actor:
        return None
    fallback = None
    try:
        by_property = _safe_get(kamaz_actor, "SnowTraceComponent", None)
        if by_property is not None:
            return by_property
    except Exception:
        pass
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        component_name = _name(component)
        class_name = _name(component.get_class()) if component else ""
        if "BP_WheelSnowTrace_Component" in component_name or "BP_WheelSnowTrace_Component" in class_name:
            return component
        if "SnowTraceComponent" in component_name or "SnowTraceComponent" in class_name:
            return component
        if "WheelSnowTrace" in component_name or "WheelSnowTrace" in class_name:
            fallback = fallback or component
    return fallback


def _ensure_snowtest_loaded():
    kamaz_actor = _find_kamaz_actor()
    if kamaz_actor is not None:
        return kamaz_actor
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return _find_kamaz_actor()


def _find_skeletal_mesh_component(actor):
    if not actor:
        return None
    for component in list(actor.get_components_by_class(unreal.SkeletalMeshComponent) or []):
        return component
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if isinstance(component, unreal.SkeletalMeshComponent):
                return component
        except Exception:
            continue
    return None


def _get_socket_location(skeletal_mesh_component, socket_name):
    if skeletal_mesh_component is None:
        return None
    try:
        return skeletal_mesh_component.get_socket_location(socket_name)
    except Exception:
        pass
    try:
        return skeletal_mesh_component.get_bone_location_by_name(socket_name, unreal.BoneSpaces.WORLD_SPACE)
    except Exception:
        return None


def _capture_rt_stats(world, render_target):
    render_lib = unreal.RenderingLibrary
    payload = {
        "sample_count": 0,
        "non_black_samples": 0,
        "max_r": 0.0,
        "max_g": 0.0,
        "max_b": 0.0,
        "max_a": 0.0,
    }
    grid_size = 48
    for y_index in range(1, grid_size + 1):
        for x_index in range(1, grid_size + 1):
            u = float(x_index) / float(grid_size + 1)
            v = float(y_index) / float(grid_size + 1)
            sample = render_lib.read_render_target_raw_uv(world, render_target, u, v)
            r = float(getattr(sample, "r", 0.0))
            g = float(getattr(sample, "g", 0.0))
            b = float(getattr(sample, "b", 0.0))
            a = float(getattr(sample, "a", 0.0))
            payload["sample_count"] += 1
            payload["max_r"] = max(payload["max_r"], r)
            payload["max_g"] = max(payload["max_g"], g)
            payload["max_b"] = max(payload["max_b"], b)
            payload["max_a"] = max(payload["max_a"], a)
            if r > 0.0 or g > 0.0 or b > 0.0 or a > 0.0:
                payload["non_black_samples"] += 1
    return payload


def _load_mpc_bounds():
    collection = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
    if collection is None:
        return None, None

    bounds_min = None
    bounds_max = None
    for parameter in list(_safe_get(collection, "vector_parameters", []) or []):
        try:
            name = str(parameter.get_editor_property("parameter_name"))
            value = parameter.get_editor_property("default_value")
        except Exception:
            continue
        if name == "WorldBoundsMin":
            bounds_min = value
        elif name == "WorldBoundsMax":
            bounds_max = value
    return bounds_min, bounds_max


def _world_to_uv(location, bounds_min, bounds_max):
    if location is None or bounds_min is None or bounds_max is None:
        return None, None

    span_x = max(float(bounds_max.r) - float(bounds_min.r), 1.0)
    span_y = max(float(bounds_max.g) - float(bounds_min.g), 1.0)
    u = (float(location.x) - float(bounds_min.r)) / span_x
    v = (float(location.y) - float(bounds_min.g)) / span_y
    return max(0.0, min(1.0, u)), max(0.0, min(1.0, v))


def _sample_rt_points(world, render_target, positions):
    bounds_min, bounds_max = _load_mpc_bounds()
    samples = []
    for item in positions:
        location_values = item.get("location", [])
        if len(location_values) != 3:
            continue
        location = unreal.Vector(float(location_values[0]), float(location_values[1]), float(location_values[2]))
        u, v = _world_to_uv(location, bounds_min, bounds_max)
        if u is None or v is None:
            continue
        sample = unreal.RenderingLibrary.read_render_target_raw_uv(world, render_target, float(u), float(v))
        samples.append(
            {
                "wheel": item.get("wheel", ""),
                "uv": [float(u), float(v)],
                "rgba": [
                    float(getattr(sample, "r", 0.0)),
                    float(getattr(sample, "g", 0.0)),
                    float(getattr(sample, "b", 0.0)),
                    float(getattr(sample, "a", 0.0)),
                ],
            }
        )
    return samples


def _get_mpc_vector_default(collection, parameter_name):
    if collection is None:
        return None
    for parameter in list(_safe_get(collection, "vector_parameters", []) or []):
        try:
            if str(parameter.get_editor_property("parameter_name")) == parameter_name:
                return parameter.get_editor_property("default_value")
        except Exception:
            continue
    return None


def _set_mpc_vector_default(collection, parameter_name, value):
    if collection is None:
        return False
    vector_parameters = list(_safe_get(collection, "vector_parameters", []) or [])
    for parameter in vector_parameters:
        try:
            if str(parameter.get_editor_property("parameter_name")) != parameter_name:
                continue
            parameter.set_editor_property("default_value", value)
            collection.set_editor_property("vector_parameters", vector_parameters)
            return True
        except Exception:
            continue
    return False


def _set_mpc_vector_runtime(world, collection, parameter_name, value):
    if world is None or collection is None:
        return False
    library = getattr(unreal, "KismetMaterialLibrary", None)
    if library is None:
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


def _try_call_by_name_with_arguments(obj, function_name):
    results = []
    method = getattr(obj, "call_function_by_name_with_arguments", None)
    if not callable(method):
        return results

    output_device = None
    output_device_cls = getattr(unreal, "OutputDeviceNull", None)
    if output_device_cls is not None:
        try:
            output_device = output_device_cls()
        except Exception:
            output_device = None

    attempts = [
        ("cmd_only", (function_name,), {}),
        ("cmd_force", (function_name,), {"b_force_call_with_non_exec": True}),
        ("cmd_output_executor_force", (function_name, output_device, obj, True), {}),
        ("cmd_output_none_force", (function_name, output_device, None, True), {}),
        ("cmd_output_executor", (function_name, output_device, obj), {}),
        ("cmd_output_none", (function_name, output_device, None), {}),
    ]
    for label, args, kwargs in attempts:
        result = {
            "path": f"call_function_by_name_with_arguments:{label}",
            "called": False,
            "return_value": None,
            "error": "",
        }
        try:
            return_value = method(*args, **kwargs)
            result["called"] = bool(return_value) or return_value is None
            result["return_value"] = _serialize_value(return_value)
        except Exception as exc:
            result["error"] = str(exc)
        results.append(result)
        if result["called"]:
            break
    return results


def _call_draw_wheel_traces(component):
    for method_name in ("draw_wheel_traces", "DrawWheelTraces"):
        method = getattr(component, method_name, None)
        if callable(method):
            method()
            return {"method_name": method_name, "path": "python_direct", "called": True, "error": ""}
        fallback_results = _try_call_by_name_with_arguments(component, method_name)
        for item in fallback_results:
            if item.get("called"):
                return {
                    "method_name": method_name,
                    "path": item.get("path", ""),
                    "called": True,
                    "error": "",
                }
    raise RuntimeError("DrawWheelTraces method not found on wheel component")


def _set_scalar_parameter(material_object, parameter_name, value):
    if material_object is None:
        return False
    setter = getattr(material_object, "set_scalar_parameter_value", None)
    if callable(setter):
        try:
            setter(parameter_name, float(value))
            return True
        except Exception:
            pass
    try:
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            material_object,
            parameter_name,
            float(value),
        )
        unreal.MaterialEditingLibrary.update_material_instance(material_object)
        return True
    except Exception:
        return False


def _manual_draw_wheel_traces(world, kamaz_actor, wheel_component, render_target, collection):
    skeletal_mesh = _find_skeletal_mesh_component(kamaz_actor)
    if skeletal_mesh is None:
        raise RuntimeError("SkeletalMeshComponent not found on Kamaz actor")

    brush_material = _safe_get(wheel_component, "BrushMaterial", None)
    if brush_material is None:
        raise RuntimeError("Wheel component has no BrushMaterial")

    wheel_bone_names = list(_safe_get(wheel_component, "WheelBoneNames", []) or [])
    if not wheel_bone_names:
        raise RuntimeError("Wheel component has no WheelBoneNames")

    bounds_min, bounds_max = _load_mpc_bounds()
    if bounds_min is None or bounds_max is None:
        raise RuntimeError("MPC_SnowSystem is missing WorldBoundsMin/WorldBoundsMax")

    dynamic_material = None
    creator = getattr(unreal, "KismetMaterialLibrary", None)
    if creator is not None:
        attempts = [
            (kamaz_actor, brush_material),
            (world, brush_material),
            (kamaz_actor, brush_material, None),
            (world, brush_material, None),
            (kamaz_actor, brush_material, "WheelProbeMID"),
            (world, brush_material, "WheelProbeMID"),
        ]
        for args in attempts:
            try:
                dynamic_material = creator.create_dynamic_material_instance(*args)
                if dynamic_material is not None:
                    break
            except Exception:
                continue
    temp_instance_path = ""
    if dynamic_material is None:
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        temp_instance_path = TEMP_MI_PATH
        if unreal.EditorAssetLibrary.does_asset_exist(temp_instance_path):
            unreal.EditorAssetLibrary.delete_asset(temp_instance_path)
        package_path, asset_name = temp_instance_path.rsplit("/", 1)
        dynamic_material = asset_tools.create_asset(
            asset_name,
            package_path,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
        if dynamic_material is None:
            raise RuntimeError("Failed to create dynamic wheel brush material")
        dynamic_material.set_editor_property("parent", brush_material)
        unreal.MaterialEditingLibrary.update_material_instance(dynamic_material)
        unreal.EditorAssetLibrary.save_loaded_asset(dynamic_material, False)

    for parameter_name, parameter_value in (
        ("BrushLengthCm", DEFAULT_BRUSH_LENGTH_CM),
        ("BrushWidthCm", DEFAULT_BRUSH_WIDTH_CM),
        ("BrushStrength", DEFAULT_BRUSH_STRENGTH),
        ("WheelTrackFalloff", DEFAULT_WHEEL_TRACK_FALLOFF),
    ):
        _set_scalar_parameter(dynamic_material, parameter_name, parameter_value)

    drawn_positions = []
    try:
        for wheel_bone_name in wheel_bone_names:
            socket_name = str(wheel_bone_name)
            location = _get_socket_location(skeletal_mesh, socket_name)
            if location is None:
                continue

            u, v = _world_to_uv(location, bounds_min, bounds_max)
            if u is None or v is None:
                continue
            brush_uv_value = unreal.LinearColor(float(u), float(v), 0.0, 0.0)
            runtime_applied = _set_mpc_vector_runtime(world, collection, "BrushUV", brush_uv_value)
            if not runtime_applied:
                _set_mpc_vector_default(collection, "BrushUV", brush_uv_value)

            unreal.RenderingLibrary.draw_material_to_render_target(world, render_target, dynamic_material)
            drawn_positions.append(
                {
                    "wheel": socket_name,
                    "location": [float(location.x), float(location.y), float(location.z)],
                    "uv": [float(u), float(v)],
                }
            )

        if not drawn_positions:
            raise RuntimeError("Could not resolve any wheel socket positions for manual RT draw")
        return drawn_positions
    finally:
        if temp_instance_path and unreal.EditorAssetLibrary.does_asset_exist(temp_instance_path):
            unreal.EditorAssetLibrary.delete_asset(temp_instance_path)


def main():
    payload = {
        "map": MAP_PATH,
        "kamaz_path": "",
        "wheel_component_path": "",
        "rt_path": "",
        "writer_before": {},
        "before_stats": {},
        "after_stats": {},
        "draw_method": "",
        "delta_detected": False,
        "error": "",
    }

    world = None
    kamaz_actor = None
    wheel_component = None
    render_target = None
    collection = None
    original_owner_vehicle = None
    original_enable_traces = None
    original_rt = None
    original_brush_uv = None

    try:
        kamaz_actor = _ensure_snowtest_loaded()
        world = unreal.EditorLevelLibrary.get_editor_world()
        payload["kamaz_path"] = _path(kamaz_actor)
        if not kamaz_actor:
            raise RuntimeError("Kamaz actor not found on SnowTest_Level")

        wheel_component = _find_wheel_component(kamaz_actor)
        payload["wheel_component_path"] = _path(wheel_component)
        if not wheel_component:
            raise RuntimeError("BP_WheelSnowTrace_Component not found on Kamaz actor")

        render_target = unreal.EditorAssetLibrary.load_asset(RT_PATH)
        payload["rt_path"] = _path(render_target)
        if not render_target:
            raise RuntimeError(f"Missing RT asset: {RT_PATH}")

        collection = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
        if collection is None:
            raise RuntimeError(f"Missing MPC asset: {MPC_PATH}")

        original_owner_vehicle = _safe_get(wheel_component, "OwnerVehicle", None)
        original_enable_traces = _safe_get(wheel_component, "bEnableSnowTraces", True)
        original_rt = _safe_get(wheel_component, "RenderTargetGlobal", None)
        original_brush_uv = _get_mpc_vector_default(collection, "BrushUV")

        _safe_set(wheel_component, "OwnerVehicle", kamaz_actor)
        _safe_set(wheel_component, "bEnableSnowTraces", True)
        _safe_set(wheel_component, "RenderTargetGlobal", render_target)

        payload["writer_before"] = {
            "OwnerVehicle": _path(original_owner_vehicle),
            "RenderTargetGlobal": _path(original_rt),
            "bEnableSnowTraces": bool(original_enable_traces),
            "WheelBoneNames": [str(x) for x in list(_safe_get(wheel_component, "WheelBoneNames", []) or [])],
            "BrushMaterial": _path(_safe_get(wheel_component, "BrushMaterial", None)),
            "WorldBoundsMin": _serialize_value(_get_mpc_vector_default(collection, "WorldBoundsMin")),
            "WorldBoundsMax": _serialize_value(_get_mpc_vector_default(collection, "WorldBoundsMax")),
            "BrushUV": _serialize_value(original_brush_uv),
        }

        unreal.RenderingLibrary.clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
        payload["before_stats"] = _capture_rt_stats(world, render_target)

        try:
            draw_result = _call_draw_wheel_traces(wheel_component)
            payload["draw_method"] = draw_result.get("method_name", "")
            payload["draw_call_path"] = draw_result.get("path", "")
        except Exception as exc:
            payload["draw_method"] = ""
            payload["draw_call_path"] = ""
            payload["draw_error"] = str(exc)

        payload["after_stats"] = _capture_rt_stats(world, render_target)
        payload["delta_detected"] = (
            payload["after_stats"]["non_black_samples"] > payload["before_stats"]["non_black_samples"]
            or payload["after_stats"]["max_r"] > payload["before_stats"]["max_r"]
            or payload["after_stats"]["max_g"] > payload["before_stats"]["max_g"]
            or payload["after_stats"]["max_b"] > payload["before_stats"]["max_b"]
            or payload["after_stats"]["max_a"] > payload["before_stats"]["max_a"]
        )
        if not payload["delta_detected"]:
            manual_positions = _manual_draw_wheel_traces(world, kamaz_actor, wheel_component, render_target, collection)
            payload["manual_draw_positions"] = manual_positions
            payload["after_stats"] = _capture_rt_stats(world, render_target)
            payload["manual_targeted_samples"] = _sample_rt_points(world, render_target, manual_positions)
            payload["delta_detected"] = (
                payload["after_stats"]["non_black_samples"] > payload["before_stats"]["non_black_samples"]
                or payload["after_stats"]["max_r"] > payload["before_stats"]["max_r"]
                or payload["after_stats"]["max_g"] > payload["before_stats"]["max_g"]
                or payload["after_stats"]["max_b"] > payload["before_stats"]["max_b"]
                or payload["after_stats"]["max_a"] > payload["before_stats"]["max_a"]
                or any((sample["rgba"][0] > 0.0 or sample["rgba"][1] > 0.0 or sample["rgba"][2] > 0.0) for sample in payload["manual_targeted_samples"])
            )
            if payload["delta_detected"]:
                payload["draw_method"] = "manual_draw"
                payload["draw_call_path"] = "python_manual_fallback"
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        if wheel_component:
            _safe_set(wheel_component, "OwnerVehicle", original_owner_vehicle)
            if original_enable_traces is not None:
                _safe_set(wheel_component, "bEnableSnowTraces", original_enable_traces)
            if original_rt is not None:
                _safe_set(wheel_component, "RenderTargetGlobal", original_rt)
        if collection is not None and original_brush_uv is not None:
            _set_mpc_vector_runtime(world, collection, "BrushUV", original_brush_uv)
            _set_mpc_vector_default(collection, "BrushUV", original_brush_uv)

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
