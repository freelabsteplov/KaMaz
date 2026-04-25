import json
import os

import unreal


BLUEPRINT_PATH = "/Game/BPs/BP_KamazPlayerController"
CLUSTER_WIDGET_CLASS_DEFAULT = (
    "/Game/CityPark/Kamaz/UI/WBP_KamazCluster.WBP_KamazCluster_C"
)
VEHICLE_MAPPING_CONTEXT_DEFAULT = (
    "/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz.IMC_MOZA_Kamaz"
)
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_kamaz_player_controller_runtime.json",
)


def _decode_bridge_result(raw):
    payload = {
        "success": None,
        "json": "",
        "summary": "",
        "raw_repr": repr(raw),
        "result": {},
    }

    if isinstance(raw, tuple):
        for item in raw:
            if isinstance(item, bool):
                payload["success"] = item
            elif isinstance(item, str):
                if not payload["json"]:
                    payload["json"] = item
                elif not payload["summary"]:
                    payload["summary"] = item
    elif isinstance(raw, bool):
        payload["success"] = raw
    elif isinstance(raw, str):
        payload["summary"] = raw

    if payload["json"]:
        try:
            payload["result"] = json.loads(payload["json"])
        except Exception:
            payload["result"] = {"raw": payload["json"]}

    return payload


def _bridge():
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        raise RuntimeError("BlueprintAutomationPythonBridge is unavailable")
    return bridge


def _compile_report(asset_path: str) -> dict:
    return _decode_bridge_result(_bridge().compile_blueprint(asset_path))


def _set_property(asset_path: str, property_name: str, value_as_string: str) -> dict:
    return _decode_bridge_result(
        _bridge().set_blueprint_property_value(
            asset_path,
            "",
            property_name,
            value_as_string,
            False,
        )
    )


def _inspect_event_graph(asset_path: str) -> dict:
    return _decode_bridge_result(_bridge().inspect_blueprint_event_graph(asset_path, True, True))


def _graph_check(graph_json: str) -> dict:
    result = {
        "begin_play_connected": False,
        "has_add_mapping_context": False,
        "has_create_widget": False,
        "has_add_to_viewport": False,
        "create_widget_class_default": "",
    }

    try:
        graph = json.loads(graph_json) if graph_json else {}
    except Exception:
        return result

    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    title_to_node = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = str(node.get("title", "") or "")
        title_to_node.setdefault(title, []).append(node)

    add_mapping_context = (title_to_node.get("Add Mapping Context") or [None])[0]
    create_widget = (title_to_node.get("Create Widget") or [None])[0]
    add_to_viewport = (title_to_node.get("Add to Viewport") or [None])[0]
    event_begin_play = (title_to_node.get("Event BeginPlay") or [None])[0]

    result["has_add_mapping_context"] = add_mapping_context is not None
    result["has_create_widget"] = create_widget is not None
    result["has_add_to_viewport"] = add_to_viewport is not None

    if isinstance(event_begin_play, dict):
        for pin in event_begin_play.get("pins", []):
            if not isinstance(pin, dict) or pin.get("name") != "then":
                continue
            linked_to = pin.get("linked_to", [])
            for link in linked_to:
                if isinstance(link, dict) and link.get("node_name") == "K2Node_CallFunction_2":
                    result["begin_play_connected"] = True
                    break

    if isinstance(create_widget, dict):
        for pin in create_widget.get("pins", []):
            if not isinstance(pin, dict) or pin.get("name") != "Class":
                continue
            result["create_widget_class_default"] = str(pin.get("default_object", "") or "")
            break

    return result


def _property_exists_on_cdo(asset_path: str, property_name: str) -> bool:
    try:
        blueprint = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not blueprint:
            return False
        generated_class = unreal.BlueprintEditorLibrary.generated_class(blueprint)
        if not generated_class:
            return False
        cdo = unreal.get_default_object(generated_class)
        if not cdo:
            return False
        cdo.get_editor_property(property_name)
        return True
    except Exception:
        return False


def main():
    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "cluster_widget_class_default": CLUSTER_WIDGET_CLASS_DEFAULT,
        "vehicle_mapping_context_default": VEHICLE_MAPPING_CONTEXT_DEFAULT,
        "compile_before": {},
        "removed_unused_variables": None,
        "cluster_widget_class_property_exists_before": False,
        "cluster_widget_class_property_exists_after_remove_unused": False,
        "cluster_widget_class_added": False,
        "set_cluster_widget_class": {},
        "set_vehicle_mapping_context": {},
        "compile_after": {},
        "graph_check": {},
        "saved": False,
        "error": "",
    }

    try:
        blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
        if not blueprint:
            raise RuntimeError(f"Failed to load blueprint asset: {BLUEPRINT_PATH}")

        result["compile_before"] = _compile_report(BLUEPRINT_PATH)
        result["cluster_widget_class_property_exists_before"] = _property_exists_on_cdo(
            BLUEPRINT_PATH,
            "ClusterWidgetClass",
        )

        remove_unused = getattr(unreal.BlueprintEditorLibrary, "remove_unused_variables", None)
        if not callable(remove_unused):
            raise RuntimeError("BlueprintEditorLibrary.remove_unused_variables is unavailable")

        result["removed_unused_variables"] = int(remove_unused(blueprint))
        result["cluster_widget_class_property_exists_after_remove_unused"] = _property_exists_on_cdo(
            BLUEPRINT_PATH,
            "ClusterWidgetClass",
        )

        if not result["cluster_widget_class_property_exists_after_remove_unused"]:
            cluster_widget_type = unreal.BlueprintEditorLibrary.get_class_reference_type(
                unreal.UserWidget.static_class()
            )
            add_ok = unreal.BlueprintEditorLibrary.add_member_variable(
                blueprint,
                "ClusterWidgetClass",
                cluster_widget_type,
            )
            result["cluster_widget_class_added"] = bool(add_ok)

        result["set_cluster_widget_class"] = _set_property(
            BLUEPRINT_PATH,
            "ClusterWidgetClass",
            CLUSTER_WIDGET_CLASS_DEFAULT,
        )
        result["set_vehicle_mapping_context"] = _set_property(
            BLUEPRINT_PATH,
            "VehicleMappingContext",
            VEHICLE_MAPPING_CONTEXT_DEFAULT,
        )
        result["compile_after"] = _compile_report(BLUEPRINT_PATH)

        graph_info = _inspect_event_graph(BLUEPRINT_PATH)
        result["graph_check"] = _graph_check(graph_info.get("json", ""))
        result["graph_check"]["inspect_summary"] = graph_info.get("summary", "")

        result["saved"] = bool(
            result["set_cluster_widget_class"].get("result", {}).get("saved", False)
            or result["set_vehicle_mapping_context"].get("result", {}).get("saved", False)
        )

    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
