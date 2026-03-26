import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_current_snowtest_receivers.json",
)

ROAD_LABEL_PREFIX = "SnowSplineRoad_"
TRAIL_LABEL = "SnowRuntimeTrailBridgeActor"


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _name(obj):
    if not obj:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _class_name(obj):
    try:
        return obj.get_class().get_name()
    except Exception:
        return ""


def _scalar_value(material_interface, param_name):
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material_interface, param_name))
    except Exception:
        return None


def _scalar_names(material):
    try:
        return [str(x) for x in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)]
    except Exception:
        return []


def _parent_chain(material_interface):
    chain = []
    current = material_interface
    while current:
        chain.append(
            {
                "name": _name(current),
                "path": _path(current),
                "class": _class_name(current),
                "scalar_params": _scalar_names(current),
            }
        )
        if isinstance(current, unreal.MaterialInstance):
            current = current.parent
        else:
            break
    return chain


def _inspect_road_actor(actor):
    row = {
        "label": actor.get_actor_label(),
        "path": actor.get_path_name(),
        "snow_road_material": "",
        "component_materials": [],
    }

    try:
        assigned = actor.get_editor_property("snow_road_material")
        row["snow_road_material"] = _path(assigned)
    except Exception:
        pass

    components = actor.get_components_by_class(unreal.SplineMeshComponent)
    for comp in components:
        comp_row = {
            "component": comp.get_name(),
            "materials": [],
        }
        for idx in range(comp.get_num_materials()):
            material = comp.get_material(idx)
            comp_row["materials"].append(
                {
                    "slot": idx,
                    "path": _path(material),
                    "chain": _parent_chain(material) if material else [],
                    "instance_scalars": {
                        "HeightAmplitude": _scalar_value(material, "HeightAmplitude") if material else None,
                        "EdgeRaiseAmplitude": _scalar_value(material, "EdgeRaiseAmplitude") if material else None,
                        "RoadEdgeBlendWidth": _scalar_value(material, "RoadEdgeBlendWidth") if material else None,
                        "RoadEdgeHeightFade": _scalar_value(material, "RoadEdgeHeightFade") if material else None,
                        "RightBermRaise": _scalar_value(material, "RightBermRaise") if material else None,
                        "RepeatAccumulationDepth": _scalar_value(material, "RepeatAccumulationDepth") if material else None,
                        "WheelTrackMaskAmplify": _scalar_value(material, "WheelTrackMaskAmplify") if material else None,
                        "WheelTrackContrast": _scalar_value(material, "WheelTrackContrast") if material else None,
                        "WheelTrackStrength": _scalar_value(material, "WheelTrackStrength") if material else None,
                        "WheelTrackAsphaltRoughness": _scalar_value(material, "WheelTrackAsphaltRoughness") if material else None,
                        "WheelTrackSnowRoughness": _scalar_value(material, "WheelTrackSnowRoughness") if material else None,
                    },
                }
            )
        row["component_materials"].append(comp_row)

    return row


def _inspect_trail_actor(actor):
    row = {
        "label": actor.get_actor_label(),
        "path": actor.get_path_name(),
        "components": [],
    }

    for comp in actor.get_components_by_class(unreal.ActorComponent):
        comp_name = comp.get_name()
        comp_class = _class_name(comp)
        if "SnowRuntimeTrailBridgeComponent" not in comp_class:
            continue

        comp_row = {
            "component": comp_name,
            "class": comp_class,
            "stamp_material": "",
            "stamp_material_scalar_names": [],
            "stamp_material_chain": [],
            "props": {},
        }

        props = [
            "StampSpacingCm",
            "PersistentPlowLengthCm",
            "PersistentPlowWidthCm",
            "RightBermContinuationRatio",
            "bEnableRepeatClearingAccumulation",
            "bEnableRuntimeReceiverHeightControl",
            "bUseSourceHeightGate",
            "RepeatAccumulationMaxPasses",
            "FirstPassClearStrength",
            "RepeatPassClearStrengthStep",
            "MaxAccumulatedClearStrength",
            "SourceActiveMaxRelativeZ",
            "MinStampEngagementToWrite",
            "PlowLiftHeightForNoEffect",
            "RuntimeHeightAmplitudeWhenActive",
            "RuntimeHeightAmplitudeWhenInactive",
            "SourceComponentOverride",
        ]
        for prop in props:
            try:
                value = comp.get_editor_property(prop)
            except Exception:
                value = None
            if prop == "SourceComponentOverride":
                value = _path(value) if value else ""
            comp_row["props"][prop] = value

        try:
            stamp_material = comp.get_editor_property("StampMaterial")
        except Exception:
            stamp_material = None

        comp_row["stamp_material"] = _path(stamp_material)
        if stamp_material:
            comp_row["stamp_material_scalar_names"] = _scalar_names(stamp_material)
            comp_row["stamp_material_chain"] = _parent_chain(stamp_material)

        row["components"].append(comp_row)

    return row


def main():
    result = {
        "map": MAP_PATH,
        "roads": [],
        "trail": {},
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = actor_subsystem.get_all_level_actors()

        for actor in actors:
            label = actor.get_actor_label()
            if label.startswith(ROAD_LABEL_PREFIX):
                result["roads"].append(_inspect_road_actor(actor))
            elif label == TRAIL_LABEL:
                result["trail"] = _inspect_trail_actor(actor)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
