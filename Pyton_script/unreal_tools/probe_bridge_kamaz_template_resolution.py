import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_bridge_kamaz_template_resolution.json",
)

BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
PROPERTY_NAME = "BrushMaterial"
PROPERTY_VALUE = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.M_Snow_PlowBrush"
COMPONENT_NAMES = [
    "BP_PlowBrush_Component",
    "BP_PlowBrush_Component_GEN_VARIABLE",
    "PlowBrush",
    "PlowBrush_GEN_VARIABLE",
]


def _decode(raw):
    return {
        "repr": repr(raw),
        "type": str(type(raw)),
    }


def _run_batch(bridge, component_name: str):
    raw = bridge.set_blueprint_properties_batch_json(
        BLUEPRINT_PATH,
        component_name,
        json.dumps(
            {
                "operations": [
                    {
                        "property_name": PROPERTY_NAME,
                        "value_as_string": PROPERTY_VALUE,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        True,
    )
    return _decode(raw)


def _run_single(bridge, component_name: str):
    raw = bridge.set_blueprint_property_value(
        BLUEPRINT_PATH,
        component_name,
        PROPERTY_NAME,
        PROPERTY_VALUE,
        True,
    )
    return _decode(raw)


def main():
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    result = {
        "bridge_exists": bridge is not None,
        "component_names": COMPONENT_NAMES,
        "results": [],
        "error": "",
    }

    try:
        if bridge is None:
            raise RuntimeError("BlueprintAutomationPythonBridge is unavailable")

        for component_name in COMPONENT_NAMES:
            entry = {
                "component_name": component_name,
                "batch": {},
                "single": {},
                "batch_error": "",
                "single_error": "",
            }
            try:
                entry["batch"] = _run_batch(bridge, component_name)
            except Exception as exc:
                entry["batch_error"] = str(exc)

            try:
                entry["single"] = _run_single(bridge, component_name)
            except Exception as exc:
                entry["single_error"] = str(exc)

            result["results"].append(entry)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
