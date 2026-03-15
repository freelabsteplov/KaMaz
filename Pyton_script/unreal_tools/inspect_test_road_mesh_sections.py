import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
OUTPUT_BASENAME = "inspect_test_road_mesh_sections"


def _log(message: str) -> None:
    unreal.log(f"[inspect_test_road_mesh_sections] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _find_actor(actor_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _component_materials(component):
    materials = []
    try:
        num_materials = int(component.get_num_materials())
    except Exception:
        num_materials = 0
    for slot_index in range(num_materials):
        try:
            material = component.get_material(slot_index)
        except Exception:
            material = None
        materials.append(
            {
                "slot_index": int(slot_index),
                "material_path": _object_path(material),
            }
        )
    return materials


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor = _find_actor(TEST_ACTOR_PATH)
    if actor is None:
        raise RuntimeError(f"Could not find actor: {TEST_ACTOR_PATH}")

    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component is None:
        raise RuntimeError(f"Actor has no StaticMeshComponent: {TEST_ACTOR_PATH}")

    static_mesh = _safe_property(component, "static_mesh")
    if static_mesh is None:
        raise RuntimeError(f"StaticMeshComponent has no StaticMesh: {_object_path(component)}")

    static_materials = []
    for index, entry in enumerate(list(_safe_property(static_mesh, "static_materials", []) or [])):
        static_materials.append(
            {
                "slot_index": int(index),
                "material_path": _object_path(_safe_property(entry, "material_interface")),
                "material_slot_name": str(_safe_property(entry, "material_slot_name")),
                "imported_material_slot_name": str(_safe_property(entry, "imported_material_slot_name")),
            }
        )

    sm_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    lod_count = 0
    try:
        lod_count = int(sm_subsystem.get_lod_count(static_mesh))
    except Exception:
        try:
            lod_count = int(static_mesh.get_num_lods())
        except Exception:
            lod_count = 0

    lod_sections = []
    for lod_index in range(lod_count):
        try:
            section_count = int(static_mesh.get_num_sections(lod_index))
        except Exception:
            section_count = 0

        sections = []
        for section_index in range(section_count):
            material_slot_index = None
            try:
                material_slot_index = int(sm_subsystem.get_lod_material_slot(static_mesh, lod_index, section_index))
            except Exception:
                material_slot_index = None
            section_entry = {
                "section_index": int(section_index),
                "material_slot_index": material_slot_index,
            }
            if material_slot_index is not None and 0 <= material_slot_index < len(static_materials):
                section_entry["material_slot_path"] = static_materials[material_slot_index]["material_path"]
                section_entry["material_slot_name"] = static_materials[material_slot_index]["material_slot_name"]
            sections.append(section_entry)

        lod_sections.append(
            {
                "lod_index": int(lod_index),
                "section_count": int(section_count),
                "sections": sections,
            }
        )

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_path": TEST_ACTOR_PATH,
        "component_path": _object_path(component),
        "static_mesh_path": _object_path(static_mesh),
        "component_materials": _component_materials(component),
        "static_materials": static_materials,
        "lod_count": int(lod_count),
        "lod_sections": lod_sections,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
