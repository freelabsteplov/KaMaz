import json
import os

import unreal


OUTPUT_BASENAME = "vehicle_regression_check"

VEHICLE_TEMPLATE_BLUEPRINTS = [
    "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase",
    "/Game/VehicleTemplate/Blueprints/SportsCar/BP_VehicleAdvSportsCar",
]

KAMAZ_BP_ASSET_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
KAMAZ_GAMEMODE_ASSET_PATH = "/Game/BPs/BP_KamazGameMode"
KAMAZ_MAPPING_CONTEXT_ASSET_PATH = "/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz"
KAMAZ_MAPPING_CONTEXT_OBJECT_PATH = (
    "/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz.IMC_MOZA_Kamaz"
)
KAMAZ_EXPECTED_GAME_STATE_CLASS_PATH = "/Script/Engine.GameStateBase"
KAMAZ_MAPPING_CONTEXT_NODE_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP:EventGraph.K2Node_CallFunction_29"
)
KAMAZ_MAPPING_CONTEXT_NODE_TITLE = "Add Mapping Context"
KAMAZ_MAPPING_CONTEXT_PIN_NAME = "MappingContext"

KAMAZ_ACTIVE_INPUT_ASSETS = [
    "/Game/CityPark/Kamaz/inputs/IA_GAZ",
    "/Game/CityPark/Kamaz/inputs/IA_TORM",
    "/Game/CityPark/Kamaz/inputs/IA_RUL",
    "/Game/CityPark/Kamaz/inputs/IA_Handbrake_Digital",
]


def _log(message: str) -> None:
    unreal.log(f"[vehicle_regression_tools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[vehicle_regression_tools] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(asset_path)
    except Exception:
        return None


def _asset_result(asset_path: str) -> dict:
    asset = _load_asset(asset_path)
    return {
        "asset_path": asset_path,
        "exists": asset is not None,
        "object_path": asset.get_path_name() if asset else "",
        "class_name": asset.get_class().get_name() if asset else "",
    }


def _decode_json(payload: str):
    if not payload:
        return None

    try:
        return json.loads(payload)
    except Exception as exc:
        return {"decode_error": str(exc), "raw_prefix": payload[:500]}


def _normalize_bridge_result(raw_result, expected_string_count: int) -> dict:
    bools = []
    strings = []

    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                bools.append(item)
            elif isinstance(item, str):
                strings.append(item)
    elif isinstance(raw_result, bool):
        bools.append(raw_result)
    elif isinstance(raw_result, str):
        strings.append(raw_result)

    while len(strings) < expected_string_count:
        strings.append("")

    return {
        "raw_success": bools[-1] if bools else None,
        "strings": strings[:expected_string_count],
    }


def _compile_report_success(report) -> bool | None:
    if not isinstance(report, dict):
        return None

    status = str(report.get("status", "")).lower()
    try:
        num_errors = int(report.get("num_errors", 0) or 0)
    except Exception:
        return None

    if num_errors > 0:
        return False
    if status in ("success", "up_to_date", "up_to_date_with_warnings"):
        return True
    if status == "error":
        return False
    return None


def _compile_with_bridge(asset_path: str) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return {
            "asset_path": asset_path,
            "success": False,
            "raw_success": None,
            "summary": "BlueprintAutomationPythonBridge is not available in this editor session.",
            "report": None,
        }

    try:
        raw_result = bridge.compile_blueprint(asset_path)
    except Exception as exc:
        return {
            "asset_path": asset_path,
            "success": False,
            "raw_success": None,
            "summary": f"compile_blueprint raised: {exc}",
            "report": None,
        }

    normalized = _normalize_bridge_result(raw_result, 2)
    report_json, summary = normalized["strings"]
    report = _decode_json(report_json)
    success = _compile_report_success(report)
    if success is None:
        success = bool(normalized["raw_success"])

    return {
        "asset_path": asset_path,
        "success": success,
        "raw_success": normalized["raw_success"],
        "summary": summary,
        "report": report,
    }


def _inspect_event_graph_with_bridge(asset_path: str) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return {
            "asset_path": asset_path,
            "success": False,
            "raw_success": None,
            "summary": "BlueprintAutomationPythonBridge is not available in this editor session.",
            "graph": None,
        }

    try:
        raw_result = bridge.inspect_blueprint_event_graph(asset_path, True, False)
    except Exception as exc:
        return {
            "asset_path": asset_path,
            "success": False,
            "raw_success": None,
            "summary": f"inspect_blueprint_event_graph raised: {exc}",
            "graph": None,
        }

    normalized = _normalize_bridge_result(raw_result, 2)
    graph_json, summary = normalized["strings"]
    graph = _decode_json(graph_json)
    success = bool(graph) if normalized["raw_success"] is None else bool(normalized["raw_success"])

    return {
        "asset_path": asset_path,
        "success": success,
        "raw_success": normalized["raw_success"],
        "summary": summary,
        "graph": graph,
    }


def _find_graph_node(graph: dict, node_path: str, node_title: str):
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return None, ""

    for node in nodes:
        if isinstance(node, dict) and node.get("path") == node_path:
            return node, "path"

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("title") != node_title:
            continue
        pins = node.get("pins")
        if isinstance(pins, list):
            for pin in pins:
                if isinstance(pin, dict) and pin.get("name") == KAMAZ_MAPPING_CONTEXT_PIN_NAME:
                    return node, "title_fallback"

    return None, ""


def _find_pin(node: dict, pin_name: str):
    pins = node.get("pins") if isinstance(node, dict) else None
    if not isinstance(pins, list):
        return None

    for pin in pins:
        if isinstance(pin, dict) and pin.get("name") == pin_name:
            return pin
    return None


def run_vehicle_template_compile_check() -> dict:
    entries = []
    overall_ok = True

    for asset_path in VEHICLE_TEMPLATE_BLUEPRINTS:
        asset_info = _asset_result(asset_path)
        compile_info = _compile_with_bridge(asset_path)
        entry = {
            **asset_info,
            "compile_success": compile_info["success"],
            "compile_raw_success": compile_info["raw_success"],
            "compile_summary": compile_info["summary"],
            "compile_report": compile_info["report"],
        }
        entries.append(entry)
        if not entry["exists"] or not entry["compile_success"]:
            overall_ok = False

    return {
        "compile_checks": entries,
        "overall_ok": overall_ok,
    }


def run_kamaz_mapping_context_check() -> dict:
    blueprint_info = _asset_result(KAMAZ_BP_ASSET_PATH)
    mapping_context_info = _asset_result(KAMAZ_MAPPING_CONTEXT_ASSET_PATH)
    graph_info = _inspect_event_graph_with_bridge(KAMAZ_BP_ASSET_PATH)

    node = None
    node_match_mode = ""
    pin = None
    if isinstance(graph_info["graph"], dict):
        node, node_match_mode = _find_graph_node(
            graph_info["graph"],
            KAMAZ_MAPPING_CONTEXT_NODE_PATH,
            KAMAZ_MAPPING_CONTEXT_NODE_TITLE,
        )
        pin = _find_pin(node, KAMAZ_MAPPING_CONTEXT_PIN_NAME) if node else None

    actual_default_object = ""
    if isinstance(pin, dict):
        actual_default_object = str(pin.get("default_object", "") or "")

    overall_ok = (
        blueprint_info["exists"]
        and mapping_context_info["exists"]
        and graph_info["success"]
        and node is not None
        and pin is not None
        and actual_default_object == KAMAZ_MAPPING_CONTEXT_OBJECT_PATH
    )

    return {
        "blueprint": blueprint_info,
        "mapping_context_asset": mapping_context_info,
        "graph_success": graph_info["success"],
        "graph_raw_success": graph_info["raw_success"],
        "graph_summary": graph_info["summary"],
        "node_found": node is not None,
        "node_match_mode": node_match_mode,
        "node_path": node.get("path", "") if isinstance(node, dict) else "",
        "node_title": node.get("title", "") if isinstance(node, dict) else "",
        "pin_found": pin is not None,
        "pin_name": KAMAZ_MAPPING_CONTEXT_PIN_NAME,
        "expected_default_object": KAMAZ_MAPPING_CONTEXT_OBJECT_PATH,
        "actual_default_object": actual_default_object,
        "overall_ok": overall_ok,
    }


def run_kamaz_input_asset_check() -> dict:
    entries = [_asset_result(KAMAZ_MAPPING_CONTEXT_ASSET_PATH)]
    entries.extend(_asset_result(asset_path) for asset_path in KAMAZ_ACTIVE_INPUT_ASSETS)
    overall_ok = all(entry["exists"] for entry in entries)
    return {
        "input_assets": entries,
        "overall_ok": overall_ok,
    }


def run_kamaz_gamemode_check() -> dict:
    asset = _load_asset(KAMAZ_GAMEMODE_ASSET_PATH)
    generated_class = None
    cdo = None

    try:
        generated_class = unreal.EditorAssetLibrary.load_blueprint_class(KAMAZ_GAMEMODE_ASSET_PATH)
    except Exception:
        generated_class = None

    try:
        cdo = unreal.get_default_object(generated_class) if generated_class else None
    except Exception:
        cdo = None

    actual_game_state_class = ""
    if cdo:
        try:
            value = cdo.get_editor_property("game_state_class")
            if value is not None:
                actual_game_state_class = value.get_path_name()
        except Exception:
            value = None
            try:
                value = cdo.get_editor_property("game_state_class")
            except Exception:
                value = None
            if value is not None:
                try:
                    actual_game_state_class = value.get_path_name()
                except Exception:
                    actual_game_state_class = str(value)

    overall_ok = bool(asset) and actual_game_state_class == KAMAZ_EXPECTED_GAME_STATE_CLASS_PATH
    return {
        "asset_path": KAMAZ_GAMEMODE_ASSET_PATH,
        "exists": asset is not None,
        "generated_class": generated_class.get_path_name() if generated_class else "",
        "cdo": cdo.get_path_name() if cdo else "",
        "expected_game_state_class": KAMAZ_EXPECTED_GAME_STATE_CLASS_PATH,
        "actual_game_state_class": actual_game_state_class,
        "overall_ok": overall_ok,
    }


def run_vehicle_regression_check(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    result = {
        "project_saved_dir": unreal.Paths.project_saved_dir(),
        "vehicle_template": run_vehicle_template_compile_check(),
        "kamaz": {
            "gamemode": run_kamaz_gamemode_check(),
            "mapping_context": run_kamaz_mapping_context_check(),
            "input_assets": run_kamaz_input_asset_check(),
        },
    }

    result["kamaz"]["overall_ok"] = (
        result["kamaz"]["gamemode"]["overall_ok"]
        and
        result["kamaz"]["mapping_context"]["overall_ok"]
        and result["kamaz"]["input_assets"]["overall_ok"]
    )
    result["overall_ok"] = result["vehicle_template"]["overall_ok"] and result["kamaz"]["overall_ok"]

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {
        "overall_ok": result["overall_ok"],
        "output_path": output_path,
        "result": result,
    }


def print_vehicle_regression_summary(output_dir: str = None):
    payload = run_vehicle_regression_check(output_dir)
    result = payload["result"]

    _log(f"overall_ok={payload['overall_ok']}")

    for entry in result["vehicle_template"]["compile_checks"]:
        log_fn = _log if entry["exists"] and entry["compile_success"] else _warn
        log_fn(
            f"vehicle_template {entry['asset_path']}: exists={entry['exists']} "
            f"compile_success={entry['compile_success']} summary={entry['compile_summary']}"
        )

    gamemode = result["kamaz"]["gamemode"]
    gamemode_log = _log if gamemode["overall_ok"] else _warn
    gamemode_log(
        "kamaz gamemode: "
        f"actual_game_state_class={gamemode['actual_game_state_class']} "
        f"expected_game_state_class={gamemode['expected_game_state_class']}"
    )

    mapping_context = result["kamaz"]["mapping_context"]
    mapping_log = _log if mapping_context["overall_ok"] else _warn
    mapping_log(
        "kamaz mapping_context: "
        f"node_found={mapping_context['node_found']} "
        f"pin_found={mapping_context['pin_found']} "
        f"actual_default_object={mapping_context['actual_default_object']}"
    )

    for entry in result["kamaz"]["input_assets"]["input_assets"]:
        log_fn = _log if entry["exists"] else _warn
        log_fn(f"kamaz input {entry['asset_path']}: exists={entry['exists']}")

    _log(f"summary_path={payload['output_path']}")
    return payload


if __name__ == "__main__":
    print_vehicle_regression_summary()
