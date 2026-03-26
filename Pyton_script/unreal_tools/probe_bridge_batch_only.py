import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_bridge_batch_only.json",
)


def main():
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    result = {
        "bridge_exists": bridge is not None,
        "has_batch": False,
        "result_repr": "",
        "result_type": "",
        "error": "",
    }

    if bridge is not None:
        result["has_batch"] = hasattr(bridge, "set_blueprint_properties_batch_json")
        if result["has_batch"]:
            try:
                raw = bridge.set_blueprint_properties_batch_json(
                    "/Game/CityPark/SnowSystem/BP_PlowBrush_Component",
                    "",
                    json.dumps(
                        {
                            "operations": [
                                {
                                    "property_name": "BrushMaterial",
                                    "value_as_string": "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.M_Snow_PlowBrush",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    False,
                )
                result["result_repr"] = repr(raw)
                result["result_type"] = str(type(raw))
            except Exception as exc:
                result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
