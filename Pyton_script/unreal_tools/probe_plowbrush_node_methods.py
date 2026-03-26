import json
import os

import unreal


TARGETS = {
    "event_draw_call": "/Game/CityPark/SnowSystem/BP_PlowBrush_Component.BP_PlowBrush_Component:EventGraph.K2Node_CallFunction_3",
    "event_followup_set": "/Game/CityPark/SnowSystem/BP_PlowBrush_Component.BP_PlowBrush_Component:EventGraph.K2Node_VariableSet_3",
}

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_plowbrush_node_methods.json",
)


def _path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _name(obj):
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _probe_pin(pin):
    links = []
    try:
        linked = list(getattr(pin, "linked_to", []) or [])
    except Exception:
        linked = []
    for item in linked:
        links.append(
            {
                "pin_name": _name(item),
                "pin_path": _path(item),
                "owner_node": _path(getattr(item, "owning_node", None)),
            }
        )

    methods = []
    for name in dir(pin):
        lowered = name.lower()
        if any(token in lowered for token in ("break", "link", "connect", "pin")):
            methods.append(name)

    return {
        "pin_name": _name(pin),
        "pin_path": _path(pin),
        "direction": str(getattr(pin, "direction", "")),
        "linked_to": links,
        "interesting_methods": methods[:200],
    }


def _probe_node(label, object_path):
    node = unreal.load_object(None, object_path)
    result = {
        "label": label,
        "node_found": node is not None,
        "node_path": _path(node),
        "node_class": _path(node.get_class()) if node else "",
        "interesting_methods": [],
        "pins": [],
    }
    if node is None:
        return result

    for name in dir(node):
        lowered = name.lower()
        if any(token in lowered for token in ("break", "destroy", "remove", "reconstruct", "link", "pin", "node")):
            result["interesting_methods"].append(name)

    try:
        pins = list(node.get_editor_property("pins") or [])
    except Exception:
        pins = []
    for pin in pins:
        result["pins"].append(_probe_pin(pin))
    return result


def main():
    payload = {"targets": []}
    for label, object_path in TARGETS.items():
        payload["targets"].append(_probe_node(label, object_path))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
