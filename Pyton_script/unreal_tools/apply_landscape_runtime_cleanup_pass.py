import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
LANDSCAPE_LABEL = "Landscape"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
KAMAZ_LABEL = "Kamaz_SnowTest"
LANDSCAPE_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape"
SNOW_DIFFUSE_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Diffuse"
SNOW_NORMAL_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Normal"
SNOW_ROUGHNESS_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Roughness"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_landscape_runtime_cleanup_pass.json",
)
DEFAULT_STAMP_SPACING_CM = 15.0


def find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def find_scene_plow_component(kamaz_actor):
    fallback = None
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        if not isinstance(component, unreal.SceneComponent):
            continue

        name = component.get_name()
        if "BP_PlowBrush_Component" in name:
            return component
        if ("PlowBrush" in name or "BP_PlowBrush" in name) and fallback is None:
            fallback = component
    return fallback


def save_output(payload: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return OUTPUT_PATH


def main():
    result = {
        "map_path": MAP_PATH,
        "landscape_actor_path": "",
        "trail_component_path": "",
        "plow_component_path": "",
        "assigned_landscape_material": "",
        "updated_landscape_scalar_values": {},
        "updated_landscape_texture_values": {},
        "trail_component_values": {},
        "saved_material": False,
        "saved_level": False,
        "saved_dirty_packages": False,
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

        landscape = find_actor_by_label(LANDSCAPE_LABEL)
        trail_actor = find_actor_by_label(TRAIL_ACTOR_LABEL)
        kamaz = find_actor_by_label(KAMAZ_LABEL)
        if not landscape:
            raise RuntimeError("Landscape actor not found")
        if not trail_actor:
            raise RuntimeError("SnowRuntimeTrailBridgeActor not found")
        if not kamaz:
            raise RuntimeError("Kamaz_SnowTest not found")

        result["landscape_actor_path"] = landscape.get_path_name()

        landscape_material = unreal.EditorAssetLibrary.load_asset(LANDSCAPE_MATERIAL_PATH)
        if not landscape_material:
            raise RuntimeError(f"Landscape material instance not found: {LANDSCAPE_MATERIAL_PATH}")

        diffuse = unreal.EditorAssetLibrary.load_asset(SNOW_DIFFUSE_PATH)
        normal = unreal.EditorAssetLibrary.load_asset(SNOW_NORMAL_PATH)
        roughness = unreal.EditorAssetLibrary.load_asset(SNOW_ROUGHNESS_PATH)
        if not diffuse or not normal or not roughness:
            raise RuntimeError("CAA_SnowV2 P1 texture set could not be loaded")

        scalar_updates = {
            "SnowTexUVScale": 8.0,
            "HeightContrast": 1.0,
            "HeightBias": 0.0,
            "HeightAmplitude": -100.0,
            "EdgeRaiseAmplitude": 12.0,
            "EdgeSharpness": 1.0,
            "RoadEdgeBlendEnabled": 0.0,
            "RoadEdgeHeightFade": 0.0,
        }
        for name, value in scalar_updates.items():
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(landscape_material, name, value)
            result["updated_landscape_scalar_values"][name] = float(
                unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(landscape_material, name)
            )

        texture_updates = {
            "Snow_Diffuse": diffuse,
            "Snow_Normal": normal,
            "Snow_Roughness": roughness,
        }
        for name, texture in texture_updates.items():
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(landscape_material, name, texture)
            resolved = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(landscape_material, name)
            result["updated_landscape_texture_values"][name] = resolved.get_path_name() if resolved else ""

        unreal.MaterialEditingLibrary.update_material_instance(landscape_material)
        result["saved_material"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(landscape_material))

        landscape.modify()
        landscape.set_editor_property("landscape_material", landscape_material)
        post_edit_change = getattr(landscape, "post_edit_change", None)
        if callable(post_edit_change):
            post_edit_change()
        mark_package_dirty = getattr(landscape, "mark_package_dirty", None)
        if callable(mark_package_dirty):
            mark_package_dirty()
        result["assigned_landscape_material"] = landscape_material.get_path_name()

        component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
        trail_component = trail_actor.get_component_by_class(component_class) if component_class else None
        if not trail_component:
            raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")

        result["trail_component_path"] = trail_component.get_path_name()

        plow_component = find_scene_plow_component(kamaz)
        if not plow_component:
            raise RuntimeError("BP_PlowBrush scene component not found on Kamaz_SnowTest")
        result["plow_component_path"] = plow_component.get_path_name()

        trail_values = {
            "bEnableRuntimeTrail": True,
            "bMarkPersistentSnowState": True,
            "PersistentSurfaceFamily": unreal.SnowReceiverSurfaceFamily.LANDSCAPE,
            "StampSpacingCm": DEFAULT_STAMP_SPACING_CM,
            "PersistentPlowLengthCm": 120.0,
            "PersistentPlowWidthCm": 320.0,
            "bUseSourceHeightGate": True,
            "SourceActiveMaxRelativeZ": -0.5,
            "RuntimeHeightAmplitudeWhenActive": -100.0,
            "RuntimeHeightAmplitudeWhenInactive": 0.0,
            "bEnableRvtVisualStamp": True,
            "SourceComponentOverride": plow_component,
        }

        trail_actor.modify()
        trail_component.modify()
        for name, value in trail_values.items():
            trail_component.set_editor_property(name, value)
        trail_post_edit_change = getattr(trail_component, "post_edit_change", None)
        if callable(trail_post_edit_change):
            trail_post_edit_change()
        actor_post_edit_change = getattr(trail_actor, "post_edit_change", None)
        if callable(actor_post_edit_change):
            actor_post_edit_change()
        mark_package_dirty = getattr(trail_actor, "mark_package_dirty", None)
        if callable(mark_package_dirty):
            mark_package_dirty()

        for name in (
            "bEnableRuntimeTrail",
            "bMarkPersistentSnowState",
            "PersistentSurfaceFamily",
            "StampSpacingCm",
            "PersistentPlowLengthCm",
            "PersistentPlowWidthCm",
            "bUseSourceHeightGate",
            "SourceActiveMaxRelativeZ",
            "RuntimeHeightAmplitudeWhenActive",
            "RuntimeHeightAmplitudeWhenInactive",
            "bEnableRvtVisualStamp",
            "SourceComponentOverride",
        ):
            value = trail_component.get_editor_property(name)
            if hasattr(value, "get_path_name"):
                result["trail_component_values"][name] = value.get_path_name()
            else:
                result["trail_component_values"][name] = str(value)

        settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
        if settings:
            settings.set_editor_property("bEnablePersistentSnowStateV1", True)
            save_config = getattr(settings, "save_config", None)
            if callable(save_config):
                save_config()

        result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
        result["saved_dirty_packages"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    except Exception as exc:
        result["error"] = str(exc)

    result["output_path"] = save_output(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
