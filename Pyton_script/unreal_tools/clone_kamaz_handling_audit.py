import json
import os
from typing import Any

import unreal


SOURCE_KAMAZ_BP = "/Game/CityPark/Kamaz/model/KamazBP"
CLONE_KAMAZ_BP = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"

SOURCE_FRONT_WHEEL_BP = "/Game/CityPark/Kamaz/model/Front_wheels"
CLONE_FRONT_WHEEL_BP = "/Game/CityPark/Kamaz/model/Front_wheels_HandlingAudit"

SOURCE_REAR_WHEEL_BP = "/Game/CityPark/Kamaz/model/Rear_wheels"
CLONE_REAR_WHEEL_BP = "/Game/CityPark/Kamaz/model/Rear_wheels_HandlingAudit"

MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
TARGET_ACTOR_LABEL = "Kamaz_SnowTest"

OUTPUT_BASENAME = "clone_kamaz_handling_audit"


def _log(message: str) -> None:
    unreal.log(f"[clone_kamaz_handling_audit] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[clone_kamaz_handling_audit] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload: dict[str, Any]) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _normalize_bridge_result(raw_result, expected_string_count: int):
    if raw_result is None:
        strings = [""]
        while len(strings) < expected_string_count:
            strings.append("")
        return False, strings[:expected_string_count]

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
            success = True
        while len(strings) < expected_string_count:
            strings.append("")
        return success, strings[:expected_string_count]

    raise TypeError(f"Unexpected bridge result: {type(raw_result)!r} {raw_result!r}")


def _decode_json(payload: str):
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def _load_asset(asset_path: str):
    return unreal.EditorAssetLibrary.load_asset(asset_path)


def _duplicate_asset_if_missing(source_path: str, target_path: str) -> tuple[object, bool]:
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        asset = _load_asset(target_path)
        if not asset:
            raise RuntimeError(f"Asset exists but failed to load: {target_path}")
        return asset, False

    target_dir = os.path.dirname(target_path)
    if target_dir and not unreal.EditorAssetLibrary.does_directory_exist(target_dir):
        unreal.EditorAssetLibrary.make_directory(target_dir)

    duplicated = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    if not duplicated:
        raise RuntimeError(f"Failed to duplicate asset: {source_path} -> {target_path}")

    asset = _load_asset(target_path)
    if not asset:
        raise RuntimeError(f"Duplicated asset but could not load: {target_path}")
    return asset, True


def _generated_class(blueprint_asset):
    generated = getattr(blueprint_asset, "generated_class", None)
    if callable(generated):
        generated = generated()
    if generated is None:
        raise RuntimeError(f"Could not resolve generated class for {blueprint_asset.get_path_name()}")
    return generated


def _compile_blueprint(blueprint_asset) -> dict[str, Any]:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    blueprint_path = blueprint_asset.get_path_name().split(".")[0]

    if bridge is not None and hasattr(bridge, "compile_blueprint"):
        raw = bridge.compile_blueprint(blueprint_path)
        success, strings = _normalize_bridge_result(raw, 2)
        payload = _decode_json(strings[0])
        compile_ok = bool(success)
        if isinstance(payload, dict):
            num_errors = payload.get("num_errors")
            status = str(payload.get("status", "")).lower()
            try:
                if int(num_errors or 0) > 0:
                    compile_ok = False
            except Exception:
                pass
            if status == "error":
                compile_ok = False
        return {
            "success": bool(compile_ok),
            "summary": strings[1],
            "payload": payload,
            "path": blueprint_path,
            "method": "bridge.compile_blueprint",
        }

    try:
        unreal.KismetEditorUtilities.compile_blueprint(blueprint_asset)
        return {
            "success": True,
            "summary": "Compiled via KismetEditorUtilities.compile_blueprint",
            "payload": None,
            "path": blueprint_path,
            "method": "kismet.compile_blueprint",
        }
    except Exception as exc:
        return {
            "success": False,
            "summary": f"compile failed: {exc}",
            "payload": None,
            "path": blueprint_path,
            "method": "kismet.compile_blueprint",
        }


def _save_asset(asset) -> bool:
    try:
        return bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
    except Exception:
        return False


def _set_prop(obj, prop_name: str, value, changes: dict[str, Any]) -> None:
    try:
        old_value = obj.get_editor_property(prop_name)
        obj.set_editor_property(prop_name, value)
        changes[prop_name] = {"old": str(old_value), "new": str(value)}
    except Exception as exc:
        changes[prop_name] = {"error": str(exc)}


def _tune_wheel_blueprint(blueprint_asset, tuning: dict[str, Any]) -> dict[str, Any]:
    result = {
        "asset": blueprint_asset.get_path_name(),
        "class": "",
        "property_changes": {},
        "compile": {},
        "saved": False,
    }

    cls = _generated_class(blueprint_asset)
    result["class"] = cls.get_path_name()
    cdo = unreal.get_default_object(cls)

    for key, value in tuning.items():
        _set_prop(cdo, key, value, result["property_changes"])

    result["compile"] = _compile_blueprint(blueprint_asset)
    result["saved"] = _save_asset(blueprint_asset)
    return result


def _find_vehicle_movement_component(cdo):
    for component in list(cdo.get_components_by_class(unreal.ActorComponent) or []):
        class_path = component.get_class().get_path_name()
        if "ChaosWheeledVehicleMovementComponent" in class_path or "ChaosVehicleMovementComponent" in class_path:
            return component
    return None


def _tune_kamaz_clone(blueprint_asset, front_wheel_class, rear_wheel_class) -> dict[str, Any]:
    result = {
        "asset": blueprint_asset.get_path_name(),
        "class": "",
        "movement_component_path": "",
        "property_changes": {},
        "wheel_setup_changes": [],
        "compile": {},
        "saved": False,
    }

    cls = _generated_class(blueprint_asset)
    result["class"] = cls.get_path_name()
    cdo = unreal.get_default_object(cls)
    movement = _find_vehicle_movement_component(cdo)
    if movement is None:
        raise RuntimeError("Could not find Chaos vehicle movement component on clone CDO.")

    result["movement_component_path"] = movement.get_path_name()

    _set_prop(movement, "idle_brake_input", 0.15, result["property_changes"])
    _set_prop(movement, "stop_threshold", 5.0, result["property_changes"])
    _set_prop(movement, "wrong_direction_threshold", 30.0, result["property_changes"])

    setups = list(movement.get_editor_property("wheel_setups") or [])
    for idx, setup in enumerate(setups):
        before = str(setup.get_editor_property("wheel_class"))
        if idx in (0, 1):
            setup.set_editor_property("wheel_class", front_wheel_class)
        else:
            setup.set_editor_property("wheel_class", rear_wheel_class)
        after = str(setup.get_editor_property("wheel_class"))
        result["wheel_setup_changes"].append(
            {
                "index": idx,
                "before": before,
                "after": after,
                "bone_name": str(setup.get_editor_property("bone_name")),
            }
        )
    movement.set_editor_property("wheel_setups", setups)

    result["compile"] = _compile_blueprint(blueprint_asset)
    result["saved"] = _save_asset(blueprint_asset)
    return result


def _inspect_event_graph(asset_path: str) -> dict[str, Any]:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        raise RuntimeError("BlueprintAutomationPythonBridge is unavailable.")

    raw = bridge.inspect_blueprint_event_graph(asset_path, True, True)
    success, strings = _normalize_bridge_result(raw, 2)
    graph_json, summary = strings
    if not success and not graph_json:
        raise RuntimeError(f"inspect_blueprint_event_graph failed: {summary}")

    graph = _decode_json(graph_json)
    if graph is None:
        raise RuntimeError(f"inspect_blueprint_event_graph returned no JSON graph payload: {summary}")
    return graph


def _apply_graph_batch(asset_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        raise RuntimeError("BlueprintAutomationPythonBridge is unavailable.")

    batch_json = json.dumps(payload, ensure_ascii=False)
    raw = bridge.apply_graph_batch_json(asset_path, batch_json)
    success, strings = _normalize_bridge_result(raw, 2)
    apply_json, summary = strings
    return {
        "success": bool(success),
        "summary": summary,
        "payload": _decode_json(apply_json),
    }


def _find_node_by_title(graph: dict[str, Any], title: str, class_suffix: str | None = None):
    for node in graph.get("nodes", []) or []:
        if node.get("title") != title:
            continue
        if class_suffix and not str(node.get("class", "")).endswith(class_suffix):
            continue
        return node
    return None


def _find_links(node: dict[str, Any], pin_name: str) -> list[dict[str, Any]]:
    if not node:
        return []
    for pin in node.get("pins", []) or []:
        if pin.get("name") == pin_name:
            return list(pin.get("linked_to", []) or [])
    return []


def _pin_has_links(node: dict[str, Any] | None, pin_name: str) -> bool:
    if not node:
        return False
    return bool(_find_links(node, pin_name))


def _find_node_by_path(graph: dict[str, Any], node_path: str):
    for node in graph.get("nodes", []) or []:
        if node.get("path") == node_path:
            return node
    return None


def _build_respawn_fix_batch(asset_path: str, graph: dict[str, Any]) -> dict[str, Any]:
    reset_event = _find_node_by_title(graph, "ResetVehicle", "K2Node_CustomEvent")
    if reset_event is None:
        raise RuntimeError("ResetVehicle custom event was not found in clone EventGraph.")

    nodes_by_path = {node.get("path"): node for node in graph.get("nodes", []) or []}

    reset_then_links = _find_links(reset_event, "then")
    if not reset_then_links:
        raise RuntimeError("ResetVehicle custom event has no execution links.")

    first_exec_target_path = reset_then_links[0].get("node_path")
    target_gear_node = nodes_by_path.get(first_exec_target_path)
    if target_gear_node is None or target_gear_node.get("title") != "Set Target Gear":
        raise RuntimeError("Could not resolve ResetVehicle Set Target Gear node.")

    target_gear_then_links = _find_links(target_gear_node, "then")
    if not target_gear_then_links:
        raise RuntimeError("ResetVehicle Set Target Gear has no then-link.")

    start_brake_set = nodes_by_path.get(target_gear_then_links[0].get("node_path"))
    if start_brake_set is None or start_brake_set.get("title") != "Set bStartBrakeApplied":
        raise RuntimeError("Could not resolve ResetVehicle Set bStartBrakeApplied node.")

    start_brake_then_links = _find_links(start_brake_set, "then")
    if not start_brake_then_links:
        raise RuntimeError("ResetVehicle Set bStartBrakeApplied has no then-link.")

    reset_brake_node = nodes_by_path.get(start_brake_then_links[0].get("node_path"))
    if reset_brake_node is None or reset_brake_node.get("title") != "Set Brake Input":
        raise RuntimeError("Could not resolve ResetVehicle Set Brake Input node.")

    reset_then_links = _find_links(reset_brake_node, "then")
    for link in reset_then_links:
        existing_target = nodes_by_path.get(link.get("node_path"))
        if existing_target and existing_target.get("title") == "Set Throttle Input":
            angular_node = _find_node_by_title(graph, "Set All Physics Angular Velocity in Degrees", "K2Node_CallFunction")
            if angular_node is not None and not _pin_has_links(angular_node, "NewAngVel"):
                batch = {
                    "nodes": [
                        {
                            "id": "fix_make_zero_angvel",
                            "type": "call_function",
                            "function_path": "/Script/Engine.KismetMathLibrary:MakeVector",
                            "x": -8480,
                            "y": -1488,
                            "pin_defaults": [
                                {"pin": "X", "default_value": "0.0"},
                                {"pin": "Y", "default_value": "0.0"},
                                {"pin": "Z", "default_value": "0.0"},
                            ],
                        }
                    ],
                    "links": [
                        {
                            "from_node": "fix_make_zero_angvel",
                            "from_pin": "ReturnValue",
                            "to_node_path": angular_node.get("path"),
                            "to_pin": "NewAngVel",
                        }
                    ],
                    "execution_chains": [],
                }
                return {
                    "already_present": False,
                    "batch": batch,
                    "reset_brake_node_path": reset_brake_node.get("path"),
                }

            return {
                "already_present": True,
                "batch": {"nodes": [], "links": [], "execution_chains": []},
                "reset_brake_node_path": reset_brake_node.get("path"),
            }

    movement_get_link = None
    for link in _find_links(reset_brake_node, "self"):
        linked_node = _find_node_by_path(graph, link.get("node_path"))
        if linked_node and linked_node.get("title") == "Get VehicleMovementComponent":
            movement_get_link = link
            break
    if movement_get_link is None:
        raise RuntimeError("Could not resolve Get VehicleMovementComponent link for ResetVehicle chain.")

    movement_get_node_path = movement_get_link.get("node_path")
    movement_get_pin_name = movement_get_link.get("pin_name")

    batch = {
        "nodes": [
            {
                "id": "reset_set_throttle_zero",
                "type": "call_function",
                "function_path": "/Script/ChaosVehicles.ChaosVehicleMovementComponent:SetThrottleInput",
                "x": -10960,
                "y": -1280,
                "pin_defaults": [{"pin": "Throttle", "default_value": "0.0"}],
            },
            {
                "id": "reset_set_steering_zero",
                "type": "call_function",
                "function_path": "/Script/ChaosVehicles.ChaosVehicleMovementComponent:SetSteeringInput",
                "x": -10560,
                "y": -1280,
                "pin_defaults": [{"pin": "Steering", "default_value": "0.0"}],
            },
            {
                "id": "reset_set_brake_zero",
                "type": "call_function",
                "function_path": "/Script/ChaosVehicles.ChaosVehicleMovementComponent:SetBrakeInput",
                "x": -10160,
                "y": -1280,
                "pin_defaults": [{"pin": "Brake", "default_value": "0.0"}],
            },
            {
                "id": "reset_set_handbrake_true",
                "type": "call_function",
                "function_path": "/Script/ChaosVehicles.ChaosVehicleMovementComponent:SetHandbrakeInput",
                "x": -9760,
                "y": -1280,
                "pin_defaults": [{"pin": "bNewHandbrake", "default_value": "true"}],
            },
            {
                "id": "reset_get_mesh_component",
                "type": "call_function",
                "function_path": "/Script/Engine.Actor:GetComponentByClass",
                "x": -9360,
                "y": -1280,
                "pin_defaults": [
                    {
                        "pin": "ComponentClass",
                        "default_object": "/Script/Engine.SkeletalMeshComponent",
                    }
                ],
            },
            {
                "id": "reset_cast_mesh_component",
                "type": "dynamic_cast",
                "target_class": "/Script/Engine.SkeletalMeshComponent",
                "x": -8960,
                "y": -1280,
                "pure": False,
            },
            {
                "id": "reset_zero_linear_velocity",
                "type": "call_function",
                "function_path": "/Script/Engine.PrimitiveComponent:SetAllPhysicsLinearVelocity",
                "x": -8560,
                "y": -1280,
            },
            {
                "id": "reset_make_zero_linvel",
                "type": "call_function",
                "function_path": "/Script/Engine.KismetMathLibrary:MakeVector",
                "x": -8740,
                "y": -1472,
                "pin_defaults": [
                    {"pin": "X", "default_value": "0.0"},
                    {"pin": "Y", "default_value": "0.0"},
                    {"pin": "Z", "default_value": "0.0"},
                ],
            },
            {
                "id": "reset_zero_angular_velocity",
                "type": "call_function",
                "function_path": "/Script/Engine.PrimitiveComponent:SetAllPhysicsAngularVelocityInDegrees",
                "x": -8160,
                "y": -1280,
            },
            {
                "id": "reset_make_zero_angvel",
                "type": "call_function",
                "function_path": "/Script/Engine.KismetMathLibrary:MakeVector",
                "x": -8340,
                "y": -1472,
                "pin_defaults": [
                    {"pin": "X", "default_value": "0.0"},
                    {"pin": "Y", "default_value": "0.0"},
                    {"pin": "Z", "default_value": "0.0"},
                ],
            },
            {
                "id": "reset_sleep_mesh",
                "type": "call_function",
                "function_path": "/Script/Engine.PrimitiveComponent:PutRigidBodyToSleep",
                "x": -7760,
                "y": -1280,
            },
        ],
        "links": [
            {
                "from_node_path": reset_brake_node.get("path"),
                "from_pin": "then",
                "to_node": "reset_set_throttle_zero",
                "to_pin": "execute",
            },
            {
                "from_node_path": movement_get_node_path,
                "from_pin": movement_get_pin_name,
                "to_node": "reset_set_throttle_zero",
                "to_pin": "self",
            },
            {
                "from_node": "reset_set_throttle_zero",
                "from_pin": "then",
                "to_node": "reset_set_steering_zero",
                "to_pin": "execute",
            },
            {
                "from_node_path": movement_get_node_path,
                "from_pin": movement_get_pin_name,
                "to_node": "reset_set_steering_zero",
                "to_pin": "self",
            },
            {
                "from_node": "reset_set_steering_zero",
                "from_pin": "then",
                "to_node": "reset_set_brake_zero",
                "to_pin": "execute",
            },
            {
                "from_node_path": movement_get_node_path,
                "from_pin": movement_get_pin_name,
                "to_node": "reset_set_brake_zero",
                "to_pin": "self",
            },
            {
                "from_node": "reset_set_brake_zero",
                "from_pin": "then",
                "to_node": "reset_set_handbrake_true",
                "to_pin": "execute",
            },
            {
                "from_node_path": movement_get_node_path,
                "from_pin": movement_get_pin_name,
                "to_node": "reset_set_handbrake_true",
                "to_pin": "self",
            },
            {
                "from_node": "reset_set_handbrake_true",
                "from_pin": "then",
                "to_node": "reset_cast_mesh_component",
                "to_pin": "execute",
            },
            {
                "from_node": "reset_get_mesh_component",
                "from_pin": "ReturnValue",
                "to_node": "reset_cast_mesh_component",
                "to_pin": "Object",
            },
            {
                "from_node": "reset_cast_mesh_component",
                "from_pin": "then",
                "to_node": "reset_zero_linear_velocity",
                "to_pin": "execute",
            },
            {
                "from_node": "reset_cast_mesh_component",
                "from_pin": "AsSkeletal Mesh Component",
                "to_node": "reset_zero_linear_velocity",
                "to_pin": "self",
            },
            {
                "from_node": "reset_make_zero_linvel",
                "from_pin": "ReturnValue",
                "to_node": "reset_zero_linear_velocity",
                "to_pin": "NewVel",
            },
            {
                "from_node": "reset_zero_linear_velocity",
                "from_pin": "then",
                "to_node": "reset_zero_angular_velocity",
                "to_pin": "execute",
            },
            {
                "from_node": "reset_cast_mesh_component",
                "from_pin": "AsSkeletal Mesh Component",
                "to_node": "reset_zero_angular_velocity",
                "to_pin": "self",
            },
            {
                "from_node": "reset_make_zero_angvel",
                "from_pin": "ReturnValue",
                "to_node": "reset_zero_angular_velocity",
                "to_pin": "NewAngVel",
            },
            {
                "from_node": "reset_zero_angular_velocity",
                "from_pin": "then",
                "to_node": "reset_sleep_mesh",
                "to_pin": "execute",
            },
            {
                "from_node": "reset_cast_mesh_component",
                "from_pin": "AsSkeletal Mesh Component",
                "to_node": "reset_sleep_mesh",
                "to_pin": "self",
            },
        ],
        "execution_chains": [],
    }

    return {
        "already_present": False,
        "batch": batch,
        "reset_brake_node_path": reset_brake_node.get("path"),
    }


def _build_handbrake_release_guard_batch(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes", []) or [])
    nodes_by_path = {node.get("path"): node for node in nodes}

    def _find_release_handbrake_node():
        for node in nodes:
            if node.get("title") != "Set Handbrake Input":
                continue
            execute_links = _find_links(node, "execute")
            is_completed_path = any(
                str(link.get("pin_name")) == "Completed"
                and str((nodes_by_path.get(link.get("node_path")) or {}).get("title", "")).startswith(
                    "EnhancedInputAction IA_Handbrake_Digital"
                )
                for link in execute_links
            )
            if not is_completed_path:
                continue
            b_new_value = ""
            for pin in node.get("pins", []) or []:
                if pin.get("name") == "bNewHandbrake":
                    b_new_value = str(pin.get("default_value", "")).lower()
                    break
            if b_new_value in ("false", "0", "0.0", ""):
                return node
        return None

    release_node = _find_release_handbrake_node()
    if release_node is None:
        raise RuntimeError("Could not resolve IA_Handbrake_Digital Completed -> Set Handbrake Input node.")

    release_bool_links = _find_links(release_node, "bNewHandbrake")
    for link in release_bool_links:
        source_node = nodes_by_path.get(link.get("node_path"))
        if source_node and source_node.get("title") == "Get bStartBrakeApplied":
            return {
                "already_present": True,
                "batch": {"nodes": [], "links": [], "execution_chains": []},
                "release_node_path": release_node.get("path"),
                "guard_source_node_path": source_node.get("path"),
            }

    guard_source_node = None
    for node in nodes:
        if node.get("title") != "Get bStartBrakeApplied":
            continue
        output_links = _find_links(node, "bStartBrakeApplied")
        for link in output_links:
            target_node = nodes_by_path.get(link.get("node_path"))
            if target_node and target_node.get("title") == "NOT Boolean":
                guard_source_node = node
                break
        if guard_source_node is not None:
            break

    if guard_source_node is None:
        for node in nodes:
            if node.get("title") == "Get bStartBrakeApplied":
                guard_source_node = node
                break

    if guard_source_node is None:
        raise RuntimeError("Could not find Get bStartBrakeApplied node for handbrake release guard.")

    batch = {
        "nodes": [],
        "links": [
            {
                "from_node_path": guard_source_node.get("path"),
                "from_pin": "bStartBrakeApplied",
                "to_node_path": release_node.get("path"),
                "to_pin": "bNewHandbrake",
            }
        ],
        "execution_chains": [],
    }

    return {
        "already_present": False,
        "batch": batch,
        "release_node_path": release_node.get("path"),
        "guard_source_node_path": guard_source_node.get("path"),
    }


def _apply_respawn_fix_to_clone(clone_bp_path: str) -> dict[str, Any]:
    result = {
        "asset_path": clone_bp_path,
        "batch_applied": False,
        "already_present": False,
        "handbrake_guard_applied": False,
        "handbrake_guard_already_present": False,
        "apply": {},
        "handbrake_guard_apply": {},
        "compile": {},
        "save": False,
    }

    graph = _inspect_event_graph(clone_bp_path)
    setup = _build_respawn_fix_batch(clone_bp_path, graph)
    result["already_present"] = bool(setup["already_present"])
    result["reset_brake_node_path"] = setup["reset_brake_node_path"]

    if not setup["already_present"]:
        apply_result = _apply_graph_batch(clone_bp_path, setup["batch"])
        result["apply"] = apply_result
        result["batch_applied"] = bool(apply_result.get("success"))
        if not apply_result.get("success"):
            raise RuntimeError(f"Failed to apply respawn fix batch: {apply_result.get('summary')}")
    else:
        result["apply"] = {
            "success": True,
            "summary": "Respawn fix chain already present; no-op.",
            "payload": None,
        }

    graph_after_respawn = _inspect_event_graph(clone_bp_path)
    guard_setup = _build_handbrake_release_guard_batch(graph_after_respawn)
    result["handbrake_guard_already_present"] = bool(guard_setup["already_present"])
    result["handbrake_release_node_path"] = guard_setup["release_node_path"]
    result["handbrake_guard_source_node_path"] = guard_setup["guard_source_node_path"]

    if not guard_setup["already_present"]:
        guard_apply_result = _apply_graph_batch(clone_bp_path, guard_setup["batch"])
        result["handbrake_guard_apply"] = guard_apply_result
        result["handbrake_guard_applied"] = bool(guard_apply_result.get("success"))
        if not guard_apply_result.get("success"):
            raise RuntimeError(f"Failed to apply handbrake guard batch: {guard_apply_result.get('summary')}")
    else:
        result["handbrake_guard_apply"] = {
            "success": True,
            "summary": "Handbrake Completed guard already present; no-op.",
            "payload": None,
        }

    clone_bp = _load_asset(clone_bp_path)
    result["compile"] = _compile_blueprint(clone_bp)
    result["save"] = _save_asset(clone_bp)
    return result


def _switch_level_actor_to_clone(clone_bp_asset) -> dict[str, Any]:
    result = {
        "map_path": MAP_PATH,
        "target_actor_label": TARGET_ACTOR_LABEL,
        "replaced": False,
        "already_clone": False,
        "old_actor_path": "",
        "new_actor_path": "",
        "save_map": False,
    }

    if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        result["error"] = f"Map not found: {MAP_PATH}"
        return result

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    clone_class = _generated_class(clone_bp_asset)
    clone_class_path = clone_class.get_path_name()

    old_actor = None
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == TARGET_ACTOR_LABEL:
            old_actor = actor
            break

    if old_actor is None:
        result["error"] = f"Actor label not found: {TARGET_ACTOR_LABEL}"
        return result

    old_class_path = old_actor.get_class().get_path_name()
    if old_class_path == clone_class_path:
        result["already_clone"] = True
        result["old_actor_path"] = old_actor.get_path_name()
        result["new_actor_path"] = old_actor.get_path_name()
        result["save_map"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
        return result

    old_transform = old_actor.get_actor_transform()
    old_folder_path = ""
    try:
        old_folder_path = str(old_actor.get_folder_path())
    except Exception:
        old_folder_path = ""

    new_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        clone_class,
        old_transform.translation,
        old_transform.rotation.rotator(),
    )
    if new_actor is None:
        result["error"] = "Failed to spawn clone actor from class."
        return result

    new_actor.set_actor_scale3d(old_transform.scale3d)
    new_actor.set_actor_label(TARGET_ACTOR_LABEL, True)
    if old_folder_path:
        try:
            new_actor.set_folder_path(old_folder_path)
        except Exception:
            pass

    result["old_actor_path"] = old_actor.get_path_name()
    result["new_actor_path"] = new_actor.get_path_name()

    unreal.EditorLevelLibrary.destroy_actor(old_actor)
    result["replaced"] = True

    result["save_map"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    return result


def _ensure_input_assets_present() -> dict[str, Any]:
    inputs = [
        "/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz",
        "/Game/CityPark/Kamaz/inputs/IA_GAZ",
        "/Game/CityPark/Kamaz/inputs/IA_TORM",
        "/Game/CityPark/Kamaz/inputs/IA_RUL",
        "/Game/CityPark/Kamaz/inputs/IA_Handbrake_Digital",
        "/Game/CityPark/Kamaz/inputs/IA_Clutch",
        "/Game/CityPark/Kamaz/inputs/IA_Gear1",
        "/Game/CityPark/Kamaz/inputs/IA_Gear2",
        "/Game/CityPark/Kamaz/inputs/IA_Gear3",
        "/Game/CityPark/Kamaz/inputs/IA_Gear4",
        "/Game/CityPark/Kamaz/inputs/IA_Gear5",
        "/Game/CityPark/Kamaz/inputs/IA_GearNeutral",
        "/Game/CityPark/Kamaz/inputs/IA_GearReverse",
        "/Game/CityPark/Kamaz/inputs/IA_PlowLift",
    ]

    report = {"all_present": True, "assets": []}
    for path in inputs:
        exists = bool(unreal.EditorAssetLibrary.does_asset_exist(path))
        report["assets"].append({"path": path, "exists": exists})
        if not exists:
            report["all_present"] = False
    return report


def run(output_dir: str | None = None) -> dict[str, Any]:
    output_dir = output_dir or _saved_output_dir()

    result: dict[str, Any] = {
        "source_assets": {
            "kamaz_bp": SOURCE_KAMAZ_BP,
            "front_wheel_bp": SOURCE_FRONT_WHEEL_BP,
            "rear_wheel_bp": SOURCE_REAR_WHEEL_BP,
        },
        "clone_assets": {
            "kamaz_bp": CLONE_KAMAZ_BP,
            "front_wheel_bp": CLONE_FRONT_WHEEL_BP,
            "rear_wheel_bp": CLONE_REAR_WHEEL_BP,
        },
        "cloned_created": {},
        "front_wheel_tuning": {},
        "rear_wheel_tuning": {},
        "kamaz_clone_tuning": {},
        "respawn_fix": {},
        "map_switch_to_clone": {},
        "input_asset_presence": {},
        "success": False,
    }

    front_clone_asset, front_created = _duplicate_asset_if_missing(SOURCE_FRONT_WHEEL_BP, CLONE_FRONT_WHEEL_BP)
    rear_clone_asset, rear_created = _duplicate_asset_if_missing(SOURCE_REAR_WHEEL_BP, CLONE_REAR_WHEEL_BP)
    kamaz_clone_asset, kamaz_created = _duplicate_asset_if_missing(SOURCE_KAMAZ_BP, CLONE_KAMAZ_BP)

    result["cloned_created"] = {
        CLONE_FRONT_WHEEL_BP: front_created,
        CLONE_REAR_WHEEL_BP: rear_created,
        CLONE_KAMAZ_BP: kamaz_created,
    }

    result["front_wheel_tuning"] = _tune_wheel_blueprint(
        front_clone_asset,
        {
            "friction_force_multiplier": 2.6,
            "cornering_stiffness": 1400.0,
            "side_slip_modifier": 0.75,
            "suspension_damping_ratio": 0.75,
            "max_brake_torque": 1800.0,
        },
    )
    result["rear_wheel_tuning"] = _tune_wheel_blueprint(
        rear_clone_asset,
        {
            "friction_force_multiplier": 2.8,
            "cornering_stiffness": 1300.0,
            "side_slip_modifier": 0.8,
            "suspension_damping_ratio": 0.75,
            "max_brake_torque": 2400.0,
        },
    )

    front_class = _generated_class(front_clone_asset)
    rear_class = _generated_class(rear_clone_asset)

    result["kamaz_clone_tuning"] = _tune_kamaz_clone(kamaz_clone_asset, front_class, rear_class)
    result["respawn_fix"] = _apply_respawn_fix_to_clone(CLONE_KAMAZ_BP)
    result["map_switch_to_clone"] = _switch_level_actor_to_clone(kamaz_clone_asset)
    result["input_asset_presence"] = _ensure_input_assets_present()

    result["success"] = (
        bool(result["front_wheel_tuning"].get("compile", {}).get("success"))
        and bool(result["rear_wheel_tuning"].get("compile", {}).get("success"))
        and bool(result["kamaz_clone_tuning"].get("compile", {}).get("success"))
        and bool(result["respawn_fix"].get("compile", {}).get("success"))
        and bool(result["input_asset_presence"].get("all_present"))
    )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
