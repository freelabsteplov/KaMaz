import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import rebuild_visible_road_snow_receiver as rebuild_receiver
import stamp_debug_plow_trace as stamp_debug
import capture_road_receiver_after_stamp as capture_after_stamp


MAP_PATH = "/Game/Maps/MoscowEA5"
TARGET_ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
BOARD_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_LocalSnowBoard_TestZone"
BOARD_LABEL = "LocalSnowBoard_TestZone"
BOARD_BOUNDS_NAME = "BoardBounds"
SOURCE_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
LOCAL_BOARD_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowBoard_TestZone"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
RECEIVER_PARENT_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver"
RECEIVER_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"
BOARD_HALF_EXTENT_Z_CM = 500.0
OUTPUT_BASENAME = "build_local_snow_board_proof_chain"

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
BRIDGE = getattr(unreal, "BlueprintAutomationPythonBridge", None)


def _log(message: str) -> None:
    unreal.log(f"[build_local_snow_board_proof_chain] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[build_local_snow_board_proof_chain] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _normalize_bridge_result(raw_result, expected_string_count: int):
    if isinstance(raw_result, bool):
        return raw_result, [""] * expected_string_count

    if isinstance(raw_result, str):
        strings = [raw_result]
        while len(strings) < expected_string_count:
            strings.append("")
        return True, strings[:expected_string_count]

    if isinstance(raw_result, tuple):
        success = None
        strings = []
        for item in raw_result:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
        if success is None:
            success = False
        while len(strings) < expected_string_count:
            strings.append("")
        return success, strings[:expected_string_count]

    raise TypeError(f"Unexpected bridge result: {type(raw_result)!r}")


def _bridge_has_method(method_name: str) -> bool:
    return BRIDGE is not None and hasattr(BRIDGE, method_name)


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs), ""
    except Exception as exc:
        return None, str(exc)


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _resolve_generated_class(blueprint):
    generated_class = _safe_property(blueprint, "generated_class")
    if callable(generated_class):
        generated_class = generated_class()
    return generated_class


def _split_asset_path(asset_path: str) -> tuple[str, str]:
    package_path, asset_name = asset_path.rsplit("/", 1)
    return package_path, asset_name


def _resolve_class_from_path(class_path: str):
    if not class_path:
        return None

    class_object = unreal.load_object(None, class_path)
    if class_object is not None:
        return class_object

    if class_path == "/Script/Engine.Actor":
        return unreal.Actor
    if class_path == "/Script/Engine.BoxComponent":
        return unreal.BoxComponent
    if class_path == "/Script/Engine.SceneComponent":
        return unreal.SceneComponent
    return None


def _create_blueprint_if_needed(asset_path: str) -> dict:
    result = {
        "asset_path": asset_path,
        "created_or_loaded": False,
        "object_path": "",
        "summary": "",
    }

    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        blueprint = _load_asset(asset_path)
        result["created_or_loaded"] = True
        result["object_path"] = _object_path(blueprint)
        result["summary"] = "Blueprint already existed."
        return result

    if _bridge_has_method("create_blueprint_asset"):
        success, strings = _normalize_bridge_result(
            BRIDGE.create_blueprint_asset(asset_path, "/Script/Engine.Actor"),
            2,
        )
        object_path, summary = strings
        result["created_or_loaded"] = bool(success)
        result["object_path"] = object_path
        result["summary"] = summary
        if not success:
            raise RuntimeError(f"create_blueprint_asset failed for {asset_path}: {summary}")
        return result

    package_path, asset_name = _split_asset_path(asset_path)
    unreal.EditorAssetLibrary.make_directory(package_path)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    blueprint = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.Blueprint, factory)
    if blueprint is None:
        raise RuntimeError(f"Failed to create blueprint asset: {asset_path}")

    unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    result["created_or_loaded"] = True
    result["object_path"] = _object_path(blueprint)
    result["summary"] = "Blueprint created through BlueprintFactory."
    return result


def _compile_and_save_blueprint(asset_path: str) -> dict:
    compile_success = True
    compile_summary = ""
    compile_json = ""
    if _bridge_has_method("compile_blueprint"):
        compile_success, compile_strings = _normalize_bridge_result(
            BRIDGE.compile_blueprint(asset_path),
            2,
        )
        compile_json, compile_summary = compile_strings

    save_success = True
    save_summary = ""
    if _bridge_has_method("save_blueprint"):
        save_success, save_strings = _normalize_bridge_result(
            BRIDGE.save_blueprint(asset_path),
            1,
        )
        save_summary = save_strings[0]
    else:
        blueprint = _load_asset(asset_path)
        save_success = bool(unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False))
        save_summary = "Saved through EditorAssetLibrary."

    return {
        "compile_success": bool(compile_success),
        "compile_summary": compile_summary,
        "compile_json": compile_json,
        "save_success": bool(save_success),
        "save_summary": save_summary,
    }


def _subobject_subsystem():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _subobject_library():
    return unreal.SubobjectDataBlueprintFunctionLibrary


def _resolve_subobject_object(function_library, handle, blueprint):
    data, _ = _safe_call(function_library.get_data, handle)

    for args in ((handle,), (data,), (handle, blueprint), (data, blueprint)):
        value, error = _safe_call(function_library.get_associated_object, *args)
        if error == "":
            return value

    for args in ((handle,), (data,), (handle, blueprint), (data, blueprint)):
        value, error = _safe_call(function_library.get_object, *args)
        if error == "":
            return value

    for args in ((handle, blueprint), (data, blueprint), (blueprint, handle), (blueprint, data)):
        value, error = _safe_call(function_library.get_object_for_blueprint, *args)
        if error == "":
            return value

    return None


def _gather_blueprint_subobjects(blueprint) -> list[dict]:
    subsystem = _subobject_subsystem()
    function_library = _subobject_library()
    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    result = []
    for handle in handles:
        display_name, _ = _safe_call(function_library.get_display_name, handle)
        variable_name, _ = _safe_call(function_library.get_variable_name, handle)
        associated_object = _resolve_subobject_object(function_library, handle, blueprint)
        result.append(
            {
                "handle": handle,
                "display_name": str(display_name) if display_name is not None else "",
                "variable_name": str(variable_name) if variable_name is not None else "",
                "associated_object": associated_object,
                "class_path": _object_path(associated_object.get_class()) if associated_object else "",
                "object_path": _object_path(associated_object),
            }
        )
    return result


def _class_matches(obj, target_class) -> bool:
    if obj is None or target_class is None:
        return False
    try:
        return bool(obj.is_a(target_class))
    except Exception:
        return _object_path(obj.get_class()) == _object_path(target_class)


def _find_subobject_entry(blueprint, component_name: str = "", component_class=None):
    entries = _gather_blueprint_subobjects(blueprint)

    if component_name:
        target_name = component_name.lower()
        for entry in entries:
            haystack = " ".join(
                [
                    entry["display_name"],
                    entry["variable_name"],
                    entry["object_path"],
                ]
            ).lower()
            if target_name in haystack.replace(" ", "") or target_name in haystack:
                return entry

    if component_class is not None:
        class_token = str(getattr(component_class, "__name__", component_class)).lower()
        for entry in entries:
            if _class_matches(entry["associated_object"], component_class) or class_token in entry["class_path"].lower():
                return entry

    return None


def _find_default_scene_root_entry(blueprint):
    entries = _gather_blueprint_subobjects(blueprint)
    for entry in entries:
        associated_object = entry["associated_object"]
        if not _class_matches(associated_object, unreal.SceneComponent):
            continue
        display_name = entry["display_name"].lower()
        variable_name = entry["variable_name"].lower()
        if "defaultsceneroot" in display_name.replace(" ", "") or "defaultsceneroot" in variable_name.replace(" ", ""):
            return entry

    for entry in entries:
        associated_object = entry["associated_object"]
        if _class_matches(associated_object, unreal.SceneComponent) and not _class_matches(associated_object, unreal.BoxComponent):
            return entry

    return entries[1] if len(entries) > 1 else None


def _handle_is_valid(handle) -> bool:
    function_library = _subobject_library()
    valid, error = _safe_call(function_library.is_handle_valid, handle)
    if error == "":
        return bool(valid)
    return handle is not None


def _add_box_component_python(blueprint_asset_path: str, component_name: str) -> dict:
    blueprint = _load_asset(blueprint_asset_path)

    existing_entry = _find_subobject_entry(blueprint, component_name, unreal.BoxComponent)
    if existing_entry is None:
        existing_entry = _find_subobject_entry(blueprint, component_class=unreal.BoxComponent)
    if existing_entry is not None:
        return {
            "success": True,
            "component_object_path": existing_entry["object_path"],
            "summary": f"Component already exists: {component_name}",
        }

    root_entry = _find_default_scene_root_entry(blueprint)
    if root_entry is None:
        raise RuntimeError(f"Could not resolve default scene root in {blueprint_asset_path}")

    params = unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", root_entry["handle"])
    params.set_editor_property("new_class", unreal.BoxComponent)
    params.set_editor_property("blueprint_context", blueprint)

    subsystem = _subobject_subsystem()
    add_result, error = _safe_call(subsystem.add_new_subobject, params=params)
    if error != "":
        add_result, error = _safe_call(subsystem.add_new_subobject, params)
    if error != "":
        raise RuntimeError(f"add_new_subobject failed for {component_name}: {error}")

    if isinstance(add_result, tuple):
        new_handle = add_result[0]
        fail_reason = str(add_result[1]) if len(add_result) > 1 else ""
    else:
        new_handle = add_result
        fail_reason = ""

    if not _handle_is_valid(new_handle):
        raise RuntimeError(f"add_new_subobject returned invalid handle for {component_name}: {fail_reason}")

    compile_save = _compile_and_save_blueprint(blueprint_asset_path)
    blueprint = _load_asset(blueprint_asset_path)
    resolved_entry = _find_subobject_entry(blueprint, component_name, unreal.BoxComponent)
    if resolved_entry is None:
        resolved_entry = _find_subobject_entry(blueprint, component_class=unreal.BoxComponent)

    return {
        "success": True,
        "component_object_path": resolved_entry["object_path"] if resolved_entry else "",
        "summary": "BoxComponent added through SubobjectDataSubsystem.",
        **compile_save,
    }


def _ensure_blueprint_component(
    blueprint_asset_path: str,
    component_class_path: str,
    component_name: str,
    attach_parent_name: str = "",
    make_root_if_missing: bool = True,
) -> dict:
    if _bridge_has_method("add_blueprint_component"):
        success, strings = _normalize_bridge_result(
            BRIDGE.add_blueprint_component(
                blueprint_asset_path,
                component_class_path,
                component_name,
                attach_parent_name,
                make_root_if_missing,
            ),
            2,
        )
        component_object_path, summary = strings
        payload = {
            "success": bool(success),
            "component_object_path": component_object_path,
            "summary": summary,
        }
        if not success:
            raise RuntimeError(
                f"add_blueprint_component failed for {blueprint_asset_path}:{component_name}: {summary}"
            )
        return payload

    class_token = (component_class_path or "").replace(" ", "").lower()
    if "boxcomponent" not in class_token:
        raise RuntimeError(f"Python-only fallback only supports BoxComponent. Requested: {component_class_path}")
    return _add_box_component_python(blueprint_asset_path, component_name)


def _find_scs_node(blueprint, component_name: str):
    scs = _safe_property(blueprint, "simple_construction_script")
    if scs is None:
        return None
    for node in list(scs.get_all_nodes() or []):
        if str(node.get_variable_name()) == component_name:
            return node
    return None


def _find_first_box_node(blueprint):
    scs = _safe_property(blueprint, "simple_construction_script")
    if scs is None:
        return None
    for node in list(scs.get_all_nodes() or []):
        component_template = _safe_property(node, "component_template")
        if component_template is not None and _class_matches(component_template, unreal.BoxComponent):
            return node
    return None


def _find_box_component_template(blueprint):
    entry = _find_subobject_entry(blueprint, BOARD_BOUNDS_NAME, unreal.BoxComponent)
    if entry is None:
        entry = _find_subobject_entry(blueprint, component_class=unreal.BoxComponent)
    if entry is None:
        return None
    return entry["associated_object"]


def _configure_board_blueprint(asset_path: str, square_half_extent_xy_cm: float) -> dict:
    blueprint = _load_asset(asset_path)
    bounds_template = _find_box_component_template(blueprint)
    if bounds_template is None:
        bounds_node = _find_scs_node(blueprint, BOARD_BOUNDS_NAME) or _find_first_box_node(blueprint)
        bounds_template = _safe_property(bounds_node, "component_template") if bounds_node is not None else None
    if bounds_template is None:
        raise RuntimeError(f"Board blueprint is missing a BoxComponent: {asset_path}")

    extent = unreal.Vector(
        float(square_half_extent_xy_cm),
        float(square_half_extent_xy_cm),
        float(BOARD_HALF_EXTENT_Z_CM),
    )
    bounds_template.set_editor_property("box_extent", extent)

    collision_enum = getattr(unreal.CollisionEnabled, "NO_COLLISION", None)
    if collision_enum is not None:
        try:
            bounds_template.set_editor_property("collision_enabled", collision_enum)
        except Exception:
            pass

    try:
        bounds_template.set_editor_property("hidden_in_game", True)
    except Exception:
        pass

    try:
        bounds_template.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    compile_save = _compile_and_save_blueprint(asset_path)
    return {
        "blueprint_path": asset_path,
        "box_extent_cm": {
            "x": float(extent.x),
            "y": float(extent.y),
            "z": float(extent.z),
        },
        **compile_save,
    }


def _describe_root_component(asset_path: str) -> dict:
    blueprint = _load_asset(asset_path)
    entry = _find_default_scene_root_entry(blueprint)
    if entry is None:
        return {
            "success": False,
            "component_object_path": "",
            "summary": "Default scene root not found.",
        }
    return {
        "success": True,
        "component_object_path": entry["object_path"],
        "summary": "Using blueprint default scene root.",
    }


def _ensure_local_rt(source_rt_path: str, target_rt_path: str) -> dict:
    result = {
        "source_rt_path": source_rt_path,
        "target_rt_path": target_rt_path,
        "created": False,
        "saved": False,
    }

    if unreal.EditorAssetLibrary.does_asset_exist(target_rt_path):
        rt_asset = _load_asset(target_rt_path)
    else:
        unreal.EditorAssetLibrary.make_directory(_split_asset_path(target_rt_path)[0])
        duplicated = unreal.EditorAssetLibrary.duplicate_asset(source_rt_path, target_rt_path)
        if not duplicated:
            raise RuntimeError(f"Failed to duplicate RT asset to {target_rt_path}")
        result["created"] = True
        rt_asset = _load_asset(target_rt_path)

    source_rt = _load_asset(source_rt_path)
    size_x = int(_safe_property(source_rt, "size_x", 2048) or 2048)
    size_y = int(_safe_property(source_rt, "size_y", 2048) or 2048)
    square_size = max(size_x, size_y)
    rt_asset.set_editor_property("size_x", square_size)
    rt_asset.set_editor_property("size_y", square_size)
    result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(rt_asset, False))
    result["resolved_rt_path"] = _object_path(rt_asset)
    result["size_x"] = int(_safe_property(rt_asset, "size_x", square_size) or square_size)
    result["size_y"] = int(_safe_property(rt_asset, "size_y", square_size) or square_size)
    return result


def _set_blueprint_default_object_property(
    blueprint_asset_path: str,
    property_name: str,
    asset_path: str,
    persist_changes: bool = True,
) -> dict:
    blueprint = _load_asset(blueprint_asset_path)
    generated_class = _resolve_generated_class(blueprint)
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for {blueprint_asset_path}")

    target_asset = _load_asset(asset_path)
    default_object = unreal.get_default_object(generated_class)
    before = _safe_property(default_object, property_name)
    default_object.set_editor_property(property_name, target_asset)
    after = _safe_property(default_object, property_name)
    compile_save = {
        "compile_success": True,
        "compile_summary": "Skipped compile for in-memory proof update.",
        "compile_json": "",
        "save_success": True,
        "save_summary": "Skipped save for in-memory proof update.",
    }
    if persist_changes:
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
        compile_save = _compile_and_save_blueprint(blueprint_asset_path)
    return {
        "blueprint_path": blueprint_asset_path,
        "property_name": property_name,
        "before": _object_path(before),
        "after": _object_path(after),
        "persist_changes": bool(persist_changes),
        **compile_save,
    }


def _find_actor_by_object_path(actor_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _find_board_actor(generated_class_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if actor.get_actor_label() == BOARD_LABEL:
            return actor
        if _object_path(actor.get_class()) == generated_class_path:
            return actor
    return None


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(True)
    return origin, extent


def _ensure_board_actor(board_blueprint_path: str, target_road_actor_path: str) -> dict:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    road_actor = _find_actor_by_object_path(target_road_actor_path)
    if road_actor is None:
        raise RuntimeError(f"Could not find target road actor: {target_road_actor_path}")

    board_blueprint = _load_asset(board_blueprint_path)
    generated_class = _resolve_generated_class(board_blueprint)
    generated_class_path = _object_path(generated_class)
    board_actor = _find_board_actor(generated_class_path)

    road_origin, road_extent = _actor_bounds(road_actor)
    square_half_extent_xy_cm = max(float(road_extent.x), float(road_extent.y))

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    created = False
    if board_actor is None:
        board_actor = actor_subsystem.spawn_actor_from_class(
            generated_class,
            unreal.Vector(float(road_origin.x), float(road_origin.y), float(road_origin.z)),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if board_actor is None:
            raise RuntimeError("Failed to spawn board actor")
        created = True

    board_actor.set_actor_label(BOARD_LABEL)
    board_actor.set_actor_location(unreal.Vector(float(road_origin.x), float(road_origin.y), float(road_origin.z)), False, False)
    board_actor.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)

    unreal.EditorLoadingAndSavingUtils.save_current_level()

    board_origin, board_extent = _actor_bounds(board_actor)
    return {
        "created": created,
        "board_actor_path": _object_path(board_actor),
        "board_actor_label": board_actor.get_actor_label(),
        "board_origin": {"x": float(board_origin.x), "y": float(board_origin.y), "z": float(board_origin.z)},
        "board_extent": {"x": float(board_extent.x), "y": float(board_extent.y), "z": float(board_extent.z)},
        "square_half_extent_xy_cm": float(square_half_extent_xy_cm),
        "generated_class_path": generated_class_path,
    }


def _set_mpc_vector_param(mpc_asset, param_name: str, value) -> str:
    vector_parameters = list(_safe_property(mpc_asset, "vector_parameters", []) or [])
    for entry in vector_parameters:
        if str(_safe_property(entry, "parameter_name")) != param_name:
            continue
        entry.set_editor_property("default_value", value)
        mpc_asset.set_editor_property("vector_parameters", vector_parameters)
        return "updated"

    new_param = unreal.CollectionVectorParameter()
    new_param.set_editor_property("parameter_name", param_name)
    new_param.set_editor_property("default_value", value)
    vector_parameters.append(new_param)
    mpc_asset.set_editor_property("vector_parameters", vector_parameters)
    return "created"


def _apply_board_bounds_to_mpc(board_actor_path: str) -> dict:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    board_actor = _find_actor_by_object_path(board_actor_path)
    if board_actor is None:
        raise RuntimeError(f"Could not find board actor: {board_actor_path}")

    origin, extent = _actor_bounds(board_actor)
    target_min = unreal.Vector(origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
    target_max = unreal.Vector(origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)

    mpc = _load_asset(MPC_PATH)
    mpc.modify(True)
    min_status = _set_mpc_vector_param(
        mpc,
        "WorldBoundsMin",
        unreal.LinearColor(float(target_min.x), float(target_min.y), float(target_min.z), 0.0),
    )
    max_status = _set_mpc_vector_param(
        mpc,
        "WorldBoundsMax",
        unreal.LinearColor(float(target_max.x), float(target_max.y), float(target_max.z), 0.0),
    )
    brush_uv_status = _set_mpc_vector_param(
        mpc,
        "BrushUV",
        unreal.LinearColor(0.5, 0.5, 0.0, 0.0),
    )
    mark_dirty = getattr(mpc, "mark_package_dirty", None)
    if callable(mark_dirty):
        mark_dirty()
    saved = False

    return {
        "mpc_path": _object_path(mpc),
        "target_world_bounds_min": {"x": float(target_min.x), "y": float(target_min.y), "z": float(target_min.z)},
        "target_world_bounds_max": {"x": float(target_max.x), "y": float(target_max.y), "z": float(target_max.z)},
        "parameter_results": {
            "WorldBoundsMin": min_status,
            "WorldBoundsMax": max_status,
            "BrushUV": brush_uv_status,
        },
        "saved": saved,
    }


def _set_vector_parameter_default_in_memory(mpc_asset, parameter_name: str, value) -> bool:
    vector_parameters = list(_safe_property(mpc_asset, "vector_parameters", []) or [])
    for entry in vector_parameters:
        if str(_safe_property(entry, "parameter_name")) != parameter_name:
            continue
        entry.set_editor_property("default_value", value)
        mpc_asset.set_editor_property("vector_parameters", vector_parameters)
        mark_dirty = getattr(mpc_asset, "mark_package_dirty", None)
        if callable(mark_dirty):
            mark_dirty()
        return False
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _rebuild_receiver_for_local_rt(output_dir: str) -> dict:
    global rebuild_receiver
    rebuild_receiver = importlib.reload(rebuild_receiver)
    rebuild_receiver.SNOW_RT_PATH = LOCAL_BOARD_RT_PATH
    rebuild_receiver.TEST_ACTOR_PATH = TARGET_ROAD_ACTOR_PATH
    rebuild_receiver.DEBUG_DIRECT_RT_VIS = True
    rebuild_receiver.DEBUG_FORCE_SOLID_COLOR = False
    rebuild_receiver.RECEIVER_PARENT_PATH = RECEIVER_PARENT_PATH
    rebuild_receiver.RECEIVER_INSTANCE_PATH = RECEIVER_INSTANCE_PATH
    return rebuild_receiver.run(output_dir)


def _proof_stamp_and_capture(output_dir: str) -> dict:
    global stamp_debug, capture_after_stamp
    stamp_debug = importlib.reload(stamp_debug)
    capture_after_stamp = importlib.reload(capture_after_stamp)

    stamp_debug.RT_PATH = LOCAL_BOARD_RT_PATH
    stamp_debug.TEST_ACTOR_PATH = TARGET_ROAD_ACTOR_PATH
    stamp_debug._set_vector_parameter_default = _set_vector_parameter_default_in_memory
    capture_after_stamp.SNOW_RT_PATH = LOCAL_BOARD_RT_PATH
    capture_after_stamp.TEST_ACTOR_PATH = TARGET_ROAD_ACTOR_PATH
    capture_after_stamp._set_vector_parameter_default = _set_vector_parameter_default_in_memory

    stamp_result = stamp_debug.run(output_dir)
    capture_result = capture_after_stamp.run(output_dir)

    sampled_color = stamp_result.get("sampled_color_at_brush_uv", {}) or {}
    stamped_signal_nonzero = any(float(sampled_color.get(channel, 0.0)) > 0.001 for channel in ("r", "g", "b", "a"))
    captures_differ = not bool(capture_result.get("capture_exports_equal", True))
    signal_visible = bool(stamped_signal_nonzero and captures_differ)

    return {
        "stamp_result": stamp_result,
        "capture_result": capture_result,
        "stamped_signal_nonzero": stamped_signal_nonzero,
        "captures_differ": captures_differ,
        "local_board_signal_visible": signal_visible,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    road_actor = _find_actor_by_object_path(TARGET_ROAD_ACTOR_PATH)
    if road_actor is None:
        raise RuntimeError(f"Could not find target road actor: {TARGET_ROAD_ACTOR_PATH}")

    road_origin, road_extent = _actor_bounds(road_actor)
    square_half_extent_xy_cm = max(float(road_extent.x), float(road_extent.y))

    blueprint_result = _create_blueprint_if_needed(BOARD_BLUEPRINT_PATH)
    root_result = _describe_root_component(BOARD_BLUEPRINT_PATH)
    box_result = _ensure_blueprint_component(
        BOARD_BLUEPRINT_PATH,
        "/Script/Engine.BoxComponent",
        BOARD_BOUNDS_NAME,
        "",
        False,
    )
    board_config_result = _configure_board_blueprint(BOARD_BLUEPRINT_PATH, square_half_extent_xy_cm)
    board_actor_result = _ensure_board_actor(BOARD_BLUEPRINT_PATH, TARGET_ROAD_ACTOR_PATH)
    local_rt_result = _ensure_local_rt(SOURCE_RT_PATH, LOCAL_BOARD_RT_PATH)
    plow_rt_result = _set_blueprint_default_object_property(
        PLOW_BLUEPRINT_PATH,
        "RenderTargetGlobal",
        LOCAL_BOARD_RT_PATH,
        False,
    )
    mpc_result = _apply_board_bounds_to_mpc(board_actor_result["board_actor_path"])
    receiver_result = _rebuild_receiver_for_local_rt(output_dir)
    proof_result = _proof_stamp_and_capture(output_dir)

    result = {
        "success": bool(proof_result.get("local_board_signal_visible", False)),
        "map_path": MAP_PATH,
        "target_road_actor_path": TARGET_ROAD_ACTOR_PATH,
        "reference_target_extent": {
            "x": float(road_extent.x),
            "y": float(road_extent.y),
            "z": float(road_extent.z),
        },
        "square_half_extent_xy_cm": float(square_half_extent_xy_cm),
        "board_blueprint": blueprint_result,
        "board_root_component": root_result,
        "board_bounds_component": box_result,
        "board_blueprint_config": board_config_result,
        "board_actor": board_actor_result,
        "local_rt": local_rt_result,
        "plow_rt_alignment": plow_rt_result,
        "mpc_bounds": mpc_result,
        "receiver_rebuild": receiver_result,
        "proof": proof_result,
        "notes": [
            "This proof chain is intentionally local and single-surface only.",
            "The board actor is fixed over StaticMeshActor_208 and uses square XY bounds with zero yaw.",
            "Plow writes into RT_SnowBoard_TestZone; the isolated road receiver reads that RT in direct debug mode.",
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary(output_dir: str | None = None) -> str:
    result = run(output_dir)
    summary = (
        f"local_board_signal_visible={result.get('proof', {}).get('local_board_signal_visible')} "
        f"board_actor={result.get('board_actor', {}).get('board_actor_path', '')} "
        f"local_rt={result.get('local_rt', {}).get('resolved_rt_path', '')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print_summary()
