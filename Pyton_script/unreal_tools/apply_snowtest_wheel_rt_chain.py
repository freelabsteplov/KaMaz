import json
import os
import runpy

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_snowtest_wheel_rt_chain.json",
)


def _run_script(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    runpy.run_path(path, run_name="__main__")


def main():
    result = {
        "mode": "apply_snowtest_wheel_rt_chain",
        "steps": [
            "persist_snowtest_wheel_rt_bounds_to_mpc_asset.py",
            "rebuild_m_snow_wheel_brush.py",
            "ensure_snowtest_wheel_trace_component.py",
            "apply_snowtest_wheel_rt_overlay_inplace.py",
        ],
        "error": "",
    }

    try:
        _run_script("persist_snowtest_wheel_rt_bounds_to_mpc_asset.py")
        _run_script("rebuild_m_snow_wheel_brush.py")
        _run_script("ensure_snowtest_wheel_trace_component.py")
        _run_script("apply_snowtest_wheel_rt_overlay_inplace.py")
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
