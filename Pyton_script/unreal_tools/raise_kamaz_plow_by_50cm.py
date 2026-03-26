import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
KAMAZ_BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
KAMAZ_BLUEPRINT_PLOW_SUBOBJECT_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP_C:BP_PlowBrush_Component_GEN_VARIABLE"
)
KAMAZ_BLUEPRINT_VISIBLE_PLOW_SUBOBJECT_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP_C:PlowBrush_GEN_VARIABLE"
)
Z_OFFSET_CM = 50.0
OUTPUT_BASENAME = "raise_kamaz_plow_by_50cm"


def _log(message: str) -> None:
    unreal.log(f"[raise_kamaz_plow_by_50cm] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _vec_to_list(value):
    if value is None:
        return []
    return [float(value.x), float(value.y), float(value.z)]


def _raise_component_relative_z(component, z_offset_cm: float) -> dict:
    before = component.get_editor_property("relative_location")
    target = unreal.Vector(float(before.x), float(before.y), float(before.z) + float(z_offset_cm))
    component.modify()
    component.set_editor_property("relative_location", target)
    post_edit = getattr(component, "post_edit_change", None)
    if callable(post_edit):
        post_edit()
    after = component.get_editor_property("relative_location")
    return {
        "component_path": _object_path(component),
        "before": _vec_to_list(before),
        "after": _vec_to_list(after),
        "delta_z": float(after.z) - float(before.z),
    }


def _find_kamaz_actors():
    actors = []
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        actor_name = actor.get_name()
        class_path = _object_path(actor.get_class())
        if "KamazBP" in actor_name or "KamazBP" in class_path or "Kamaz" in actor_name:
            actors.append(actor)
    return actors


def _find_named_scene_component(actor, token: str):
    for component in actor.get_components_by_class(unreal.SceneComponent):
        if token in component.get_name():
            return component
    return None


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "kamaz_blueprint_path": KAMAZ_BLUEPRINT_PATH,
        "z_offset_cm": Z_OFFSET_CM,
        "blueprint_changes": [],
        "map_actor_changes": [],
        "saved_blueprint": False,
        "saved_level": False,
        "error": "",
        "notes": [
            "Raises both the visible plow and the BP_PlowBrush writer source by the same offset.",
            "This keeps the writer and visible blade aligned instead of moving only the mesh.",
        ],
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

        kamaz_blueprint = unreal.EditorAssetLibrary.load_asset(KAMAZ_BLUEPRINT_PATH)
        if not kamaz_blueprint:
            raise RuntimeError(f"Could not load blueprint: {KAMAZ_BLUEPRINT_PATH}")

        blueprint_components = [
            unreal.load_object(None, KAMAZ_BLUEPRINT_PLOW_SUBOBJECT_PATH),
            unreal.load_object(None, KAMAZ_BLUEPRINT_VISIBLE_PLOW_SUBOBJECT_PATH),
        ]
        for component in blueprint_components:
            if component is None:
                continue
            result["blueprint_changes"].append(_raise_component_relative_z(component, Z_OFFSET_CM))

        if result["blueprint_changes"]:
            mark_dirty = getattr(kamaz_blueprint, "mark_package_dirty", None)
            if callable(mark_dirty):
                mark_dirty()
            result["saved_blueprint"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(kamaz_blueprint, False))

        for actor in _find_kamaz_actors():
            actor_entry = {
                "actor_path": _object_path(actor),
                "component_changes": [],
            }
            for token in ("BP_PlowBrush_Component", "PlowBrush"):
                component = _find_named_scene_component(actor, token)
                if component is None:
                    continue
                actor.modify()
                actor_entry["component_changes"].append(_raise_component_relative_z(component, Z_OFFSET_CM))
            if actor_entry["component_changes"]:
                post_edit = getattr(actor, "post_edit_change", None)
                if callable(post_edit):
                    post_edit()
                mark_dirty = getattr(actor, "mark_package_dirty", None)
                if callable(mark_dirty):
                    mark_dirty()
                result["map_actor_changes"].append(actor_entry)

        if result["map_actor_changes"]:
            result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary(output_dir: str | None = None):
    result = run(output_dir)
    summary = (
        f"raised blueprint={len(result.get('blueprint_changes', []))} "
        f"map_actors={len(result.get('map_actor_changes', []))} "
        f"saved_blueprint={result.get('saved_blueprint', False)} "
        f"saved_level={result.get('saved_level', False)}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return {
        "success": result.get("success", False),
        "summary": summary,
        "output_path": result.get("output_path", ""),
    }


if __name__ == "__main__":
    print(print_summary())
