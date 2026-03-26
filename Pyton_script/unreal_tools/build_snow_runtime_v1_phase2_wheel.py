import json
import os

import unreal


ROOT = "/Game/CityPark/SnowSystem/SnowRuntime_V1"
MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
CLONE_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"
BPC_WHEEL_PATH = f"{ROOT}/Blueprints/BPC_SnowWheelTelemetry_V1"
RT_A_PATH = f"{ROOT}/RenderTargets/RT_SnowState_A_V1"
RT_B_PATH = f"{ROOT}/RenderTargets/RT_SnowState_B_V1"
WHEEL_MATERIAL_PATH = f"{ROOT}/Materials/M_SnowState_Write_Wheel_V1"
STATE_MANAGER_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowStateManagerV1"
NATIVE_COMPONENT_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowWheelTelemetryV1Component"
COMPONENT_NAME = "SnowWheelTelemetryV1"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "build_snow_runtime_v1_phase2_wheel.json",
)

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
RENDER_LIB = unreal.RenderingLibrary


def _write_json(payload: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs), ""
    except Exception as exc:
        return None, str(exc)


def _load_asset(asset_path: str):
    return ASSET_LIB.load_asset(asset_path)


def _compile_blueprint(blueprint_asset) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None and hasattr(bridge, "compile_blueprint"):
        try:
            asset_path = blueprint_asset.get_path_name().split(".")[0]
            raw = bridge.compile_blueprint(asset_path)
            payload = ""
            summary = ""
            success = True
            if isinstance(raw, tuple):
                for item in raw:
                    if isinstance(item, bool):
                        success = bool(item)
                    elif isinstance(item, str) and not payload:
                        payload = item
                    elif isinstance(item, str):
                        summary = item
            elif isinstance(raw, bool):
                success = bool(raw)
            return {
                "success": success,
                "summary": summary or "Compiled via BlueprintAutomationPythonBridge.compile_blueprint",
                "payload": payload,
            }
        except Exception as exc:
            return {"success": False, "summary": f"bridge compile failed: {exc}"}

    try:
        unreal.KismetEditorUtilities.compile_blueprint(blueprint_asset)
        return {"success": True, "summary": "Compiled via KismetEditorUtilities.compile_blueprint"}
    except Exception as exc:
        return {"success": False, "summary": str(exc)}


def _create_or_load_component_blueprint(asset_path: str, parent_class_path: str):
    blueprint = _load_asset(asset_path)
    created = False
    if blueprint is None:
        package_path, asset_name = asset_path.rsplit("/", 1)
        parent_class = unreal.load_class(None, parent_class_path)
        if parent_class is None:
            raise RuntimeError(f"Could not load parent class: {parent_class_path}")
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent_class)
        blueprint = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.Blueprint, factory)
        if blueprint is None:
            raise RuntimeError(f"Failed to create component blueprint: {asset_path}")
        created = True

    ASSET_LIB.save_loaded_asset(blueprint, False)
    return blueprint, created


def _try_set_property(obj, candidate_names, value):
    for name in candidate_names:
        try:
            obj.set_editor_property(name, value)
            return {"success": True, "property_name": name, "value": value}
        except Exception:
            continue
    return {"success": False, "property_name": "", "value": value}


def _set_component_bp_defaults(component_blueprint):
    generated_class = component_blueprint.generated_class()
    cdo = generated_class.get_default_object()
    return {
        "capture_every_tick": _try_set_property(cdo, ["capture_every_tick", "bCaptureEveryTick"], True),
        "capture_interval_seconds": _try_set_property(cdo, ["capture_interval_seconds", "CaptureIntervalSeconds"], 0.05),
        "center_state_mapping_on_owner": _try_set_property(cdo, ["center_state_mapping_on_owner", "bCenterStateMappingOnOwner"], True),
        "auto_resolve_state_manager": _try_set_property(cdo, ["auto_resolve_state_manager", "bAutoResolveStateManager"], True),
        "remaining_snow_depth_scale": _try_set_property(cdo, ["remaining_snow_depth_scale", "RemainingSnowDepthScale"], 0.28),
        "compaction_rut_depth_scale": _try_set_property(cdo, ["compaction_rut_depth_scale", "CompactionRutDepthScale"], 0.42),
        "cleared_expose_road_scale": _try_set_property(cdo, ["cleared_expose_road_scale", "ClearedExposeRoadScale"], 0.18),
    }


def _subobject_subsystem():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _subobject_library():
    return unreal.SubobjectDataBlueprintFunctionLibrary


def _handle_is_valid(function_library, handle) -> bool:
    value, error = _safe_call(function_library.is_handle_valid, handle)
    return error == "" and bool(value)


def _resolve_subobject_object(function_library, handle, blueprint):
    data, _ = _safe_call(function_library.get_data, handle)
    for args in ((handle,), (data,), (handle, blueprint), (data, blueprint)):
        value, error = _safe_call(function_library.get_object, *args)
        if error == "":
            return value
    for args in ((handle, blueprint), (data, blueprint), (blueprint, handle), (blueprint, data)):
        value, error = _safe_call(function_library.get_object_for_blueprint, *args)
        if error == "":
            return value
    return None


def _gather_entries(blueprint):
    subsystem = _subobject_subsystem()
    function_library = _subobject_library()
    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    entries = []
    for handle in handles:
        if not _handle_is_valid(function_library, handle):
            continue
        display_name, _ = _safe_call(function_library.get_display_name, handle)
        obj = _resolve_subobject_object(function_library, handle, blueprint)
        entries.append(
            {
                "handle": handle,
                "display_name": str(display_name),
                "object": obj,
                "object_name": obj.get_name() if obj else "",
                "object_path": obj.get_path_name() if obj else "",
                "object_class": obj.get_class().get_path_name() if obj else "",
            }
        )
    return entries


def _find_default_scene_root_entry(entries):
    for entry in entries:
        if "DefaultSceneRoot" in entry["display_name"] or entry["object_name"] == "DefaultSceneRoot":
            return entry
    return entries[0] if entries else None


def _find_component_entry(entries, generated_component_class_path: str):
    for entry in entries:
        if entry["object_name"] == COMPONENT_NAME:
            return entry
        if entry["object_class"] == generated_component_class_path:
            return entry
    return None


def _attach_component_blueprint_to_clone(clone_blueprint, component_blueprint):
    result = {
        "component_added": False,
        "component_already_present": False,
        "component_object_path": "",
        "property_sets": {},
    }

    generated_class = component_blueprint.generated_class()
    generated_class_path = generated_class.get_path_name()
    entries = _gather_entries(clone_blueprint)
    existing_entry = _find_component_entry(entries, generated_class_path)
    if existing_entry:
        result["component_already_present"] = True
        result["component_object_path"] = existing_entry["object_path"]
        component_object = existing_entry["object"]
    else:
        root_entry = _find_default_scene_root_entry(entries)
        if root_entry is None:
            raise RuntimeError("Could not resolve clone blueprint root entry.")

        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", root_entry["handle"])
        params.set_editor_property("new_class", generated_class)
        params.set_editor_property("blueprint_context", clone_blueprint)

        subsystem = _subobject_subsystem()
        add_result, error = _safe_call(subsystem.add_new_subobject, params=params)
        if error != "":
            add_result, error = _safe_call(subsystem.add_new_subobject, params)
        if error != "":
            raise RuntimeError(f"add_new_subobject failed: {error}")

        new_handle = add_result[0] if isinstance(add_result, tuple) else add_result
        if not _handle_is_valid(_subobject_library(), new_handle):
            raise RuntimeError("Component add returned invalid handle.")

        component_object = _resolve_subobject_object(_subobject_library(), new_handle, clone_blueprint)
        if component_object is None:
            raise RuntimeError("Could not resolve attached wheel telemetry component object.")

        rename_ok = False
        for rename_callable in (
            getattr(_subobject_library(), "rename_subobject", None),
            getattr(subsystem, "rename_subobject", None),
        ):
            if not callable(rename_callable):
                continue
            _, rename_error = _safe_call(rename_callable, new_handle, unreal.Text(COMPONENT_NAME))
            if rename_error == "":
                rename_ok = True
                break
        if not rename_ok:
            try:
                component_object.rename(COMPONENT_NAME)
            except Exception:
                pass

        refreshed_entries = _gather_entries(clone_blueprint)
        created_entry = _find_component_entry(refreshed_entries, generated_class_path)
        if created_entry:
            component_object = created_entry["object"]
            result["component_object_path"] = created_entry["object_path"]

        result["component_added"] = True

    if component_object is None:
        raise RuntimeError("Attached component object could not be resolved.")

    result["property_sets"] = {
        "capture_every_tick": _try_set_property(component_object, ["capture_every_tick", "bCaptureEveryTick"], True),
        "center_state_mapping_on_owner": _try_set_property(component_object, ["center_state_mapping_on_owner", "bCenterStateMappingOnOwner"], True),
        "auto_resolve_state_manager": _try_set_property(component_object, ["auto_resolve_state_manager", "bAutoResolveStateManager"], True),
        "capture_interval_seconds": _try_set_property(component_object, ["capture_interval_seconds", "CaptureIntervalSeconds"], 0.05),
    }

    if not result["component_object_path"]:
        result["component_object_path"] = component_object.get_path_name()
    return result


def _world_to_uv(world_location, origin, extent):
    extent_x = max(float(extent.x), 1.0)
    extent_y = max(float(extent.y), 1.0)
    u = ((float(world_location.x) - float(origin.x)) / (extent_x * 2.0)) + 0.5
    v = ((float(world_location.y) - float(origin.y)) / (extent_y * 2.0)) + 0.5
    return max(0.0, min(1.0, u)), max(0.0, min(1.0, v))


def _sample_rt_at_world_location(world, rt_asset, world_location, origin, extent):
    u, v = _world_to_uv(world_location, origin, extent)
    sample = RENDER_LIB.read_render_target_raw_uv(world, rt_asset, u, v)
    return {
        "u": float(u),
        "v": float(v),
        "r": float(getattr(sample, "r", 0.0)),
        "g": float(getattr(sample, "g", 0.0)),
        "b": float(getattr(sample, "b", 0.0)),
        "a": float(getattr(sample, "a", 0.0)),
    }


def _get_world():
    return unreal.EditorLevelLibrary.get_editor_world()


def _find_vehicle_actor(world, clone_generated_class):
    gameplay_statics = getattr(unreal, "GameplayStatics", None)
    if gameplay_statics is not None:
        try:
            actors = list(gameplay_statics.get_all_actors_of_class(world, clone_generated_class) or [])
            if actors:
                return actors[0]
        except Exception:
            pass

        try:
            generic_actors = list(gameplay_statics.get_all_actors_of_class(world, unreal.WheeledVehiclePawn) or [])
            for actor in generic_actors:
                try:
                    if actor.get_actor_label() == "Kamaz_SnowTest":
                        return actor
                except Exception:
                    continue
        except Exception:
            pass

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        try:
            if actor.is_a(clone_generated_class):
                return actor
            if actor.get_actor_label() == "Kamaz_SnowTest":
                return actor
        except Exception:
            continue
    return None


def _find_component_by_class(actor, component_class):
    try:
        component = actor.get_component_by_class(component_class)
        if component is not None:
            return component
    except Exception:
        pass

    try:
        for component in list(actor.get_components_by_class(component_class) or []):
            if component is not None:
                return component
    except Exception:
        pass
    return None


def run():
    result = {
        "map_path": MAP_PATH,
        "clone_blueprint_path": CLONE_BP_PATH,
        "component_blueprint_path": BPC_WHEEL_PATH,
        "created_assets": [],
        "compile": {},
        "attach": {},
        "validation": {
            "actor_found": False,
            "movement_found": False,
            "telemetry_component_found": False,
            "resolved_wheel_count": 0,
            "in_contact_wheel_count": 0,
            "queued_stamp_count": 0,
            "flush_succeeded": False,
            "authoritative_rt_path": "",
            "authoritative_rt_sample": {},
            "wheel_samples": [],
            "result": False,
        },
        "original_kamaz_untouched": True,
        "error": "",
    }

    try:
        component_bp, created_component_bp = _create_or_load_component_blueprint(BPC_WHEEL_PATH, NATIVE_COMPONENT_CLASS_PATH)
        if created_component_bp:
            result["created_assets"].append(BPC_WHEEL_PATH)
        result["component_bp_default_sets"] = _set_component_bp_defaults(component_bp)
        result["component_bp_compile"] = _compile_blueprint(component_bp)
        ASSET_LIB.save_loaded_asset(component_bp, False)

        clone_blueprint = _load_asset(CLONE_BP_PATH)
        if clone_blueprint is None:
            raise RuntimeError(f"Could not load clone blueprint: {CLONE_BP_PATH}")

        result["attach"] = _attach_component_blueprint_to_clone(clone_blueprint, component_bp)
        result["compile"] = _compile_blueprint(clone_blueprint)
        ASSET_LIB.save_loaded_asset(clone_blueprint, False)

        rt_a = _load_asset(RT_A_PATH)
        rt_b = _load_asset(RT_B_PATH)
        wheel_material = _load_asset(WHEEL_MATERIAL_PATH)
        if rt_a is None or rt_b is None or wheel_material is None:
            raise RuntimeError("Phase 1 assets missing: render targets or wheel write material could not be loaded.")

        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = _get_world()
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        state_manager_class = unreal.load_class(None, STATE_MANAGER_CLASS_PATH)
        native_component_class = unreal.load_class(None, NATIVE_COMPONENT_CLASS_PATH)
        clone_generated_class = clone_blueprint.generated_class()
        if state_manager_class is None or native_component_class is None or clone_generated_class is None:
            raise RuntimeError("Could not resolve state manager class, wheel telemetry class, or clone generated class.")

        vehicle_actor = _find_vehicle_actor(world, clone_generated_class)
        result["validation"]["actor_found"] = vehicle_actor is not None
        if vehicle_actor is None:
            raise RuntimeError("No clone KamAZ actor was found on the loaded map for phase 2 validation.")

        movement = vehicle_actor.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
        result["validation"]["movement_found"] = movement is not None
        if movement is None:
            raise RuntimeError("ChaosWheeledVehicleMovementComponent not found on clone KamAZ actor.")

        telemetry_component = _find_component_by_class(vehicle_actor, native_component_class)
        result["validation"]["telemetry_component_found"] = telemetry_component is not None
        if telemetry_component is None:
            raise RuntimeError("SnowWheelTelemetryV1Component was not found on the clone KamAZ actor instance.")

        manager = actor_subsystem.spawn_actor_from_class(
            state_manager_class,
            unreal.Vector(float(vehicle_actor.get_actor_location().x), float(vehicle_actor.get_actor_location().y), float(vehicle_actor.get_actor_location().z + 120.0)),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if manager is None:
            raise RuntimeError("Could not spawn temporary SnowStateManagerV1 for validation.")

        mapping_origin = vehicle_actor.get_actor_location()
        mapping_origin = unreal.Vector(float(mapping_origin.x), float(mapping_origin.y), 0.0)
        mapping_extent = unreal.Vector2D(900.0, 900.0)
        manager.set_editor_property("state_render_target_a", rt_a)
        manager.set_editor_property("state_render_target_b", rt_b)
        manager.set_editor_property("wheel_write_material", wheel_material)
        manager.set_editor_property("plow_write_material", wheel_material)
        manager.set_editor_property("world_mapping_origin", mapping_origin)
        manager.set_editor_property("world_mapping_extent_cm", mapping_extent)
        manager.reset_state_render_targets(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))

        telemetry_component.set_editor_property("state_manager_actor", manager)
        queued = int(telemetry_component.capture_wheel_telemetry_and_queue_stamps(True))
        result["validation"]["resolved_wheel_count"] = int(getattr(telemetry_component, "last_resolved_wheel_count", 0))
        result["validation"]["in_contact_wheel_count"] = int(getattr(telemetry_component, "last_in_contact_wheel_count", 0))
        result["validation"]["queued_stamp_count"] = queued
        result["validation"]["flush_succeeded"] = bool(getattr(telemetry_component, "b_last_flush_succeeded", False) or getattr(telemetry_component, "last_flush_succeeded", False))

        authoritative_rt = manager.get_authoritative_state_render_target()
        result["validation"]["authoritative_rt_path"] = authoritative_rt.get_path_name() if authoritative_rt else ""

        wheel_samples_payload = []
        primary_sample_dict = None
        last_samples = list(getattr(telemetry_component, "last_wheel_samples", []) or [])
        for sample in last_samples:
            item = {
                "wheel_index": int(getattr(sample, "wheel_index", -1)),
                "b_valid": bool(getattr(sample, "b_valid", False)),
                "b_in_contact": bool(getattr(sample, "b_in_contact", False)),
                "contact_point": str(getattr(sample, "contact_point", "")),
                "spring_force": float(getattr(sample, "spring_force", 0.0)),
                "slip_magnitude": float(getattr(sample, "slip_magnitude", 0.0)),
                "skid_magnitude": float(getattr(sample, "skid_magnitude", 0.0)),
                "speed_cm_per_sec": float(getattr(sample, "speed_cm_per_sec", 0.0)),
                "surface_family": str(getattr(sample, "surface_family", "")),
                "phys_material_path": str(getattr(sample, "phys_material_path", "")),
                "remaining_snow_depth_delta": float(getattr(sample, "remaining_snow_depth_delta", 0.0)),
                "compaction_rut_depth_delta": float(getattr(sample, "compaction_rut_depth_delta", 0.0)),
                "cleared_expose_road_delta": float(getattr(sample, "cleared_expose_road_delta", 0.0)),
            }
            contact_point = getattr(sample, "contact_point", None)
            if authoritative_rt is not None and contact_point is not None:
                item["rt_sample_at_contact"] = _sample_rt_at_world_location(world, authoritative_rt, contact_point, mapping_origin, mapping_extent)
                if primary_sample_dict is None:
                    primary_sample_dict = item["rt_sample_at_contact"]
            wheel_samples_payload.append(item)
        result["validation"]["wheel_samples"] = wheel_samples_payload[:4]
        result["validation"]["authoritative_rt_sample"] = primary_sample_dict or {}

        result["validation"]["result"] = bool(
            result["validation"]["movement_found"]
            and result["validation"]["telemetry_component_found"]
            and result["validation"]["in_contact_wheel_count"] > 0
            and result["validation"]["queued_stamp_count"] > 0
            and result["validation"]["flush_succeeded"]
            and (
                result["validation"]["authoritative_rt_sample"].get("r", 0.0) > 0.001
                or result["validation"]["authoritative_rt_sample"].get("g", 0.0) > 0.001
                or result["validation"]["authoritative_rt_sample"].get("b", 0.0) > 0.001
            )
        )

        actor_subsystem.destroy_actor(manager)

    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    return result


if __name__ == "__main__":
    print(run())
