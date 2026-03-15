import json
import os

import unreal


OUTPUT_BASENAME = "vehicle_regression_check"

KEY_BLUEPRINTS = [
    "/Game/CityPark/Kamaz/model/KamazBP",
    "/Game/BPs/BP_KamazPlayerController",
    "/Game/BPs/BP_KamazGameMode",
]

KEY_INPUT_ASSETS = [
    "/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz",
    "/Game/CityPark/Kamaz/inputs/IA_Throttle",
    "/Game/CityPark/Kamaz/inputs/IA_Brake",
    "/Game/CityPark/Kamaz/inputs/IA_Steering",
    "/Game/CityPark/Kamaz/inputs/IA_Handbrake_Digital",
    "/Game/CityPark/Kamaz/inputs/IA_GAZ",
    "/Game/CityPark/Kamaz/inputs/IA_TORM",
    "/Game/CityPark/Kamaz/inputs/IA_RUL",
    "/Game/CityPark/Kamaz/inputs/IA_PlowLift",
    "/Game/CityPark/Kamaz/inputs/IA_Gear1",
    "/Game/CityPark/Kamaz/inputs/IA_Gear2",
    "/Game/CityPark/Kamaz/inputs/IA_Gear3",
    "/Game/CityPark/Kamaz/inputs/IA_Gear4",
    "/Game/CityPark/Kamaz/inputs/IA_Gear5",
    "/Game/CityPark/Kamaz/inputs/IA_GearNeutral",
    "/Game/CityPark/Kamaz/inputs/IA_GearReverse",
]

OPTIONAL_UI_ASSETS = [
    "/Game/CityPark/Kamaz/UI/WBP_KamazCluster",
    "/Game/CityPark/Kamaz/UI/BP_KamazTelemetry",
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


def _decode_compile_report(report_json: str):
    if not report_json:
        return None

    try:
        return json.loads(report_json)
    except Exception as exc:
        return {"decode_error": str(exc), "raw_prefix": report_json[:500]}


def _compile_with_bridge(asset_path: str) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return {
            "asset_path": asset_path,
            "success": False,
            "summary": "BlueprintAutomationPythonBridge is not available in this editor session.",
            "report": None,
        }

    try:
        raw_result = bridge.compile_blueprint(asset_path)
    except Exception as exc:
        return {
            "asset_path": asset_path,
            "success": False,
            "summary": f"compile_blueprint raised: {exc}",
            "report": None,
        }

    success = False
    strings = []

    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
    elif isinstance(raw_result, bool):
        success = raw_result

    while len(strings) < 2:
        strings.append("")

    report_json, summary = strings[:2]

    return {
        "asset_path": asset_path,
        "success": success,
        "summary": summary,
        "report": _decode_compile_report(report_json),
    }


def run_vehicle_regression_check(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    result = {
        "project_saved_dir": unreal.Paths.project_saved_dir(),
        "blueprints": [],
        "inputs": [],
        "ui_assets": [],
        "overall_ok": True,
    }

    for asset_path in KEY_BLUEPRINTS:
        asset_info = _asset_result(asset_path)
        compile_info = _compile_with_bridge(asset_path)
        combined = {
            **asset_info,
            "compile_success": compile_info["success"],
            "compile_summary": compile_info["summary"],
            "compile_report": compile_info["report"],
        }
        result["blueprints"].append(combined)

        if not combined["exists"] or not combined["compile_success"]:
            result["overall_ok"] = False

    for asset_path in KEY_INPUT_ASSETS:
        asset_info = _asset_result(asset_path)
        result["inputs"].append(asset_info)
        if not asset_info["exists"]:
            result["overall_ok"] = False

    for asset_path in OPTIONAL_UI_ASSETS:
        result["ui_assets"].append(_asset_result(asset_path))

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
    for entry in result["blueprints"]:
        log_fn = _log if entry["compile_success"] and entry["exists"] else _warn
        log_fn(
            f"blueprint {entry['asset_path']}: exists={entry['exists']} "
            f"compile_success={entry['compile_success']} summary={entry['compile_summary']}"
        )

    for entry in result["inputs"]:
        log_fn = _log if entry["exists"] else _warn
        log_fn(f"input {entry['asset_path']}: exists={entry['exists']}")

    _log(f"summary_path={payload['output_path']}")
    return payload


if __name__ == "__main__":
    _log("Loaded vehicle_regression_tools.py")
