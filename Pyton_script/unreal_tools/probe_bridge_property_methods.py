import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_bridge_property_methods.json",
)


def main():
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    result = {
        "bridge_exists": bridge is not None,
        "matching_names": [],
        "has_set_blueprint_property_value": False,
        "has_set_blueprint_properties_batch_json": False,
        "single_result_repr": "",
        "single_result_type": "",
        "batch_result_repr": "",
        "batch_result_type": "",
        "single_error": "",
        "batch_error": "",
    }

    if bridge is not None:
        result["matching_names"] = sorted([name for name in dir(bridge) if "property" in name.lower() and "blueprint" in name.lower()])
        result["has_set_blueprint_property_value"] = hasattr(bridge, "set_blueprint_property_value")
        result["has_set_blueprint_properties_batch_json"] = hasattr(bridge, "set_blueprint_properties_batch_json")

        if result["has_set_blueprint_property_value"]:
            try:
                raw = bridge.set_blueprint_property_value(
                    "/Game/CityPark/SnowSystem/BP_PlowBrush_Component",
                    "",
                    "BrushMaterial",
                    "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.M_Snow_PlowBrush",
                    False,
                )
                result["single_result_repr"] = repr(raw)
                result["single_result_type"] = str(type(raw))
            except Exception as exc:
                result["single_error"] = str(exc)

        if result["has_set_blueprint_properties_batch_json"]:
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
                result["batch_result_repr"] = repr(raw)
                result["batch_result_type"] = str(type(raw))
            except Exception as exc:
                result["batch_error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
