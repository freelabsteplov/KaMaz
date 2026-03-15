import json
import os

import unreal


DEFAULT_SOURCE_INSTANCE_PATH = "/Game/SnappyRoads/Materials/Old/M_SR_RoadSection001_Inst"
DEFAULT_TARGET_PACKAGE = "/Game/CityPark/SnowSystem/Receivers"
DEFAULT_TEST_ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
OUTPUT_BASENAME = "road_snow_receiver_prep"


def _log(message: str) -> None:
    unreal.log(f"[prepare_road_snow_receiver_assets] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _ensure_directory(path: str) -> None:
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def _get_parent(material):
    for property_name in ("parent", "Parent", "ParentEditorOnly"):
        try:
            parent = material.get_editor_property(property_name)
            if parent is not None:
                return parent
        except Exception:
            continue
    return None


def _duplicate_asset(source_asset_path: str, target_asset_path: str):
    if unreal.EditorAssetLibrary.does_asset_exist(target_asset_path):
        asset = unreal.EditorAssetLibrary.load_asset(target_asset_path)
        if asset is None:
            raise RuntimeError(f"Target asset exists but could not be loaded: {target_asset_path}")
        return asset, False

    if not unreal.EditorAssetLibrary.duplicate_asset(source_asset_path, target_asset_path):
        raise RuntimeError(f"Failed to duplicate {source_asset_path} -> {target_asset_path}")

    asset = unreal.EditorAssetLibrary.load_asset(target_asset_path)
    if asset is None:
        raise RuntimeError(f"Duplicated asset could not be loaded: {target_asset_path}")
    return asset, True


def _set_instance_parent(instance_asset, parent_asset) -> None:
    instance_asset.set_editor_property("parent", parent_asset)


def _selected_or_all_level_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = list(actor_subsystem.get_selected_level_actors() or [])
    if selected_actors:
        return selected_actors
    return list(actor_subsystem.get_all_level_actors() or [])


def _all_level_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def _get_texture_parameter_values(material):
    values = []
    library = getattr(unreal, "MaterialEditingLibrary", None)
    if library is None:
        return values

    get_names = getattr(library, "get_texture_parameter_names", None)
    get_value = getattr(library, "get_material_instance_texture_parameter_value", None)
    if get_names is None or get_value is None:
        return values

    try:
        parameter_names = get_names(material) or []
    except Exception:
        parameter_names = []

    for parameter_name in parameter_names:
        try:
            texture = get_value(material, parameter_name)
        except Exception:
            texture = None
        values.append(
            {
                "parameter_name": str(parameter_name),
                "texture_name": _object_name(texture),
                "texture_path": _object_path(texture),
            }
        )

    return values


def _refresh_component_render_state(component) -> list[str]:
    actions = []
    for method_name in ("modify", "mark_render_state_dirty", "reregister_component", "post_edit_change"):
        method = getattr(component, method_name, None)
        if not callable(method):
            continue
        try:
            method()
            actions.append(method_name)
        except Exception:
            continue
    return actions


def prepare_road_snow_receiver_assets(
    source_instance_path: str = DEFAULT_SOURCE_INSTANCE_PATH,
    target_package: str = DEFAULT_TARGET_PACKAGE,
    output_dir: str | None = None,
) -> dict:
    output_dir = output_dir or _saved_output_dir()
    _ensure_directory(target_package)

    source_instance = _load_asset(source_instance_path)
    source_parent = _get_parent(source_instance)
    if source_parent is None:
        raise RuntimeError(f"Material instance has no parent material: {source_instance_path}")

    source_parent_path = _object_path(source_parent)
    source_instance_name = _object_name(source_instance)
    source_parent_name = _object_name(source_parent)

    duplicated_parent_name = f"{source_parent_name}_SnowReceiver"
    duplicated_instance_name = f"{source_instance_name}_SnowReceiver_Test"

    duplicated_parent_path = f"{target_package}/{duplicated_parent_name}"
    duplicated_instance_path = f"{target_package}/{duplicated_instance_name}"

    duplicated_parent, created_parent = _duplicate_asset(source_parent_path, duplicated_parent_path)
    duplicated_instance, created_instance = _duplicate_asset(source_instance_path, duplicated_instance_path)

    _set_instance_parent(duplicated_instance, duplicated_parent)
    unreal.EditorAssetLibrary.save_loaded_asset(duplicated_parent, False)
    unreal.EditorAssetLibrary.save_loaded_asset(duplicated_instance, False)

    result = {
        "source_instance_path": source_instance_path,
        "source_parent_path": source_parent_path,
        "duplicated_parent_path": _object_path(duplicated_parent),
        "duplicated_instance_path": _object_path(duplicated_instance),
        "created_parent": bool(created_parent),
        "created_instance": bool(created_instance),
        "duplicated_instance_parent_after": _object_path(_get_parent(duplicated_instance)),
        "source_texture_parameters": _get_texture_parameter_values(source_instance),
        "summary": (
            f"Prepared isolated receiver assets: parent={_object_path(duplicated_parent)} "
            f"instance={_object_path(duplicated_instance)}"
        ),
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def apply_material_to_selected_slot0(material_asset_path: str) -> dict:
    material_asset = _load_asset(material_asset_path)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = list(actor_subsystem.get_selected_level_actors() or [])

    applied = []
    for actor in selected_actors:
        try:
            components = actor.get_components_by_class(unreal.MeshComponent)
        except Exception:
            components = []

        for component in components or []:
            try:
                component.set_material(0, material_asset)
                refresh_actions = _refresh_component_render_state(component)
                applied.append(
                    {
                        "actor_name": _object_name(actor),
                        "actor_path": _object_path(actor),
                        "component_name": _object_name(component),
                        "component_path": _object_path(component),
                        "refresh_actions": refresh_actions,
                    }
                )
            except Exception:
                continue

    result = {
        "material_asset_path": material_asset_path,
        "num_selected_actors": len(selected_actors),
        "num_components_updated": len(applied),
        "updated_components": applied,
    }

    output_path = os.path.join(_saved_output_dir(), "road_snow_receiver_apply_result.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def apply_material_to_actor_slot0(actor_path: str, material_asset_path: str) -> dict:
    material_asset = _load_asset(material_asset_path)
    matched = []

    for actor in _all_level_actors():
        if _object_path(actor) != actor_path:
            continue

        try:
            components = actor.get_components_by_class(unreal.MeshComponent)
        except Exception:
            components = []

        for component in components or []:
            try:
                component.set_material(0, material_asset)
                refresh_actions = _refresh_component_render_state(component)
                matched.append(
                    {
                        "actor_name": _object_name(actor),
                        "actor_path": _object_path(actor),
                        "component_name": _object_name(component),
                        "component_path": _object_path(component),
                        "refresh_actions": refresh_actions,
                    }
                )
            except Exception:
                continue

    result = {
        "actor_path": actor_path,
        "material_asset_path": material_asset_path,
        "num_components_updated": len(matched),
        "updated_components": matched,
    }

    output_path = os.path.join(_saved_output_dir(), "road_snow_receiver_apply_result.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def restore_original_material_on_test_actor(
    actor_path: str = DEFAULT_TEST_ROAD_ACTOR_PATH,
    material_asset_path: str = DEFAULT_SOURCE_INSTANCE_PATH,
) -> dict:
    return apply_material_to_actor_slot0(actor_path, material_asset_path)


def reparent_material_instance(
    instance_asset_path: str,
    parent_material_path: str,
    allow_non_receiver_parent: bool = False,
) -> dict:
    if not allow_non_receiver_parent and not parent_material_path.startswith(f"{DEFAULT_TARGET_PACKAGE}/"):
        raise RuntimeError(
            "Refusing to reparent to a non-receiver material. "
            "Use a material under /Game/CityPark/SnowSystem/Receivers or pass allow_non_receiver_parent=True."
        )

    instance_asset = _load_asset(instance_asset_path)
    parent_asset = _load_asset(parent_material_path)

    before_parent = _get_parent(instance_asset)
    _set_instance_parent(instance_asset, parent_asset)
    unreal.EditorAssetLibrary.save_loaded_asset(instance_asset, False)
    after_parent = _get_parent(instance_asset)

    result = {
        "instance_asset_path": instance_asset_path,
        "parent_material_path": parent_material_path,
        "before_parent_path": _object_path(before_parent),
        "after_parent_path": _object_path(after_parent),
        "saved": True,
    }

    output_path = os.path.join(_saved_output_dir(), "road_snow_receiver_reparent_result.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(prepare_road_snow_receiver_assets())
