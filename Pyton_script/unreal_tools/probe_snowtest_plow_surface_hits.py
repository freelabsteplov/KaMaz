import json
import math
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_snowtest_plow_surface_hits.json",
)


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


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        return _name(actor)


def _safe_get(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            return default
    return getattr(obj, property_name, default)


def _vec_to_dict(vec):
    if vec is None:
        return None
    return {
        "x": float(vec.x),
        "y": float(vec.y),
        "z": float(vec.z),
    }


def _rot_to_dict(rot):
    if rot is None:
        return None
    return {
        "pitch": float(rot.pitch),
        "yaw": float(rot.yaw),
        "roll": float(rot.roll),
    }


def _component_world_location(component):
    if component is None:
        return None
    for method_name in ("get_world_location", "get_component_location"):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                pass
    try:
        transform = component.get_world_transform()
        return transform.translation
    except Exception:
        pass
    owner = component.get_owner() if component else None
    if owner:
        try:
            return owner.get_actor_location()
        except Exception:
            pass
    return None


def _component_world_rotation(component):
    if component is None:
        return None
    for method_name in ("get_world_rotation", "get_component_rotation"):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                pass
    owner = component.get_owner() if component else None
    if owner:
        try:
            return owner.get_actor_rotation()
        except Exception:
            pass
    return None


def _material_entries(component):
    entries = []
    if not component:
        return entries
    try:
        material_count = int(component.get_num_materials())
    except Exception:
        material_count = 0

    for material_index in range(material_count):
        try:
            material = component.get_material(material_index)
        except Exception:
            material = None
        entries.append(
            {
                "slot": int(material_index),
                "material_name": _name(material),
                "material_path": _path(material),
                "material_class": material.get_class().get_name() if material else "",
                "material_parent_path": _path(_safe_get(material, "parent", None)) if material else "",
            }
        )
    return entries


def _find_actor_by_label(label):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_sub.get_all_level_actors() or []):
        if _label(actor) == label:
            return actor
    return None


def _ensure_map_loaded():
    kamaz_actor = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
    trail_actor = _find_actor_by_label(TRAIL_ACTOR_LABEL)
    if kamaz_actor and trail_actor:
        return kamaz_actor, trail_actor

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return _find_actor_by_label(KAMAZ_ACTOR_LABEL), _find_actor_by_label(TRAIL_ACTOR_LABEL)


def _find_trail_component(trail_actor):
    if not trail_actor:
        return None
    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    if component_class:
        component = trail_actor.get_component_by_class(component_class)
        if component:
            return component
    for component in list(trail_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if "SnowRuntimeTrailBridgeComponent" in component.get_class().get_name():
                return component
        except Exception:
            continue
    return None


def _find_plow_component(kamaz_actor):
    preferred = None
    fallback = None
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if not isinstance(component, unreal.SceneComponent):
                continue
        except Exception:
            continue
        component_name = _name(component)
        class_name = component.get_class().get_name()
        if "BP_PlowBrush_Component" in component_name or "BP_PlowBrush_Component" in class_name:
            preferred = component
            break
        if ("PlowBrush" in component_name or "BP_PlowBrush" in component_name) and fallback is None:
            fallback = component
    return preferred or fallback


def _serialize_hit(hit):
    if hit is None:
        return {
            "blocking_hit": False,
            "distance": 0.0,
            "impact_point": None,
            "location": None,
            "normal": None,
            "actor_label": "",
            "actor_name": "",
            "actor_path": "",
            "actor_class": "",
            "component_name": "",
            "component_path": "",
            "component_class": "",
            "materials": [],
        }
    actor = hit.get_actor()
    component = hit.get_component()
    return {
        "blocking_hit": bool(hit.is_valid_blocking_hit()),
        "distance": float(hit.distance),
        "impact_point": _vec_to_dict(hit.impact_point),
        "location": _vec_to_dict(hit.location),
        "normal": _vec_to_dict(hit.impact_normal),
        "actor_label": _label(actor),
        "actor_name": _name(actor),
        "actor_path": _path(actor),
        "actor_class": actor.get_class().get_name() if actor else "",
        "component_name": _name(component),
        "component_path": _path(component),
        "component_class": component.get_class().get_name() if component else "",
        "materials": _material_entries(component),
    }


def _component_world_bounds(component):
    get_bounds = getattr(component, "get_bounds", None)
    if callable(get_bounds):
        try:
            bounds = get_bounds()
            return bounds.origin, bounds.box_extent
        except Exception:
            pass
    try:
        origin, extent = component.get_local_bounds()
        return origin, extent
    except Exception:
        pass
    owner = component.get_owner() if component else None
    if owner:
        try:
            return owner.get_actor_bounds(True)
        except Exception:
            pass
    return None, None


def _collect_nearby_meshes(source_location, plow_length_cm, plow_width_cm):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    entries = []
    for actor in list(actor_sub.get_all_level_actors() or []):
        components = list(actor.get_components_by_class(unreal.MeshComponent) or [])
        for component in components:
            origin, extent = _component_world_bounds(component)
            if origin is None or extent is None:
                continue
            component_location = _component_world_location(component)
            if component_location is None:
                component_location = origin
            entries.append(
                {
                    "actor_label": _label(actor),
                    "actor_name": _name(actor),
                    "actor_path": _path(actor),
                    "actor_class": actor.get_class().get_name() if actor else "",
                    "component_name": _name(component),
                    "component_path": _path(component),
                    "component_class": component.get_class().get_name() if component else "",
                    "component_location": _vec_to_dict(component_location),
                    "bounds_origin": _vec_to_dict(origin),
                    "bounds_extent": _vec_to_dict(extent),
                    "distance_xy_to_plow": math.sqrt(
                        ((float(component_location.x) - float(source_location.x)) ** 2)
                        + ((float(component_location.y) - float(source_location.y)) ** 2)
                    ),
                    "delta_z_to_plow": float(component_location.z) - float(source_location.z),
                    "materials": _material_entries(component),
                }
            )
    entries.sort(
        key=lambda item: (
            float(item["distance_xy_to_plow"]),
            abs(float(item["delta_z_to_plow"])),
            item["actor_label"],
            item["component_name"],
        )
    )
    return entries[:80]


def main():
    payload = {
        "map": MAP_PATH,
        "trail_component_path": "",
        "plow_source_path": "",
        "plow_source_location": None,
        "plow_source_rotation": None,
        "persistent_plow_length_cm": None,
        "persistent_plow_width_cm": None,
        "trace_hits": [],
        "nearby_mesh_components": [],
        "error": "",
    }

    try:
        kamaz_actor, trail_actor = _ensure_map_loaded()
        if not kamaz_actor or not trail_actor:
            raise RuntimeError("Missing Kamaz_SnowTest or SnowRuntimeTrailBridgeActor")

        trail_component = _find_trail_component(trail_actor)
        if not trail_component:
            raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")
        payload["trail_component_path"] = _path(trail_component)

        plow_source = _find_plow_component(kamaz_actor)
        if not plow_source:
            raise RuntimeError("BP_PlowBrush_Component not found")
        payload["plow_source_path"] = _path(plow_source)

        plow_location = _component_world_location(plow_source)
        if plow_location is None:
            raise RuntimeError("Could not resolve plow source world location")
        owner = plow_source.get_owner()
        plow_rotation = _component_world_rotation(plow_source)
        owner_yaw = float(owner.get_actor_rotation().yaw) if owner else float(plow_rotation.yaw if plow_rotation else 0.0)
        flat_rotator = unreal.Rotator(0.0, owner_yaw, 0.0)
        forward = unreal.MathLibrary.get_forward_vector(flat_rotator)
        right = unreal.MathLibrary.get_right_vector(flat_rotator)

        plow_length_cm = float(_safe_get(trail_component, "PersistentPlowLengthCm", 120.0))
        plow_width_cm = float(_safe_get(trail_component, "PersistentPlowWidthCm", 340.0))

        payload["plow_source_location"] = _vec_to_dict(plow_location)
        payload["plow_source_rotation"] = _rot_to_dict(flat_rotator)
        payload["persistent_plow_length_cm"] = plow_length_cm
        payload["persistent_plow_width_cm"] = plow_width_cm

        world = unreal.EditorLevelLibrary.get_editor_world()
        if not world:
            raise RuntimeError("Editor world is unavailable")

        forward_offset = forward * (plow_length_cm * 0.15)
        lateral_offsets = (-0.45, -0.20, 0.0, 0.20, 0.45)
        for offset_ratio in lateral_offsets:
            lateral_offset = right * (plow_width_cm * 0.5 * offset_ratio)
            trace_point = plow_location + forward_offset + lateral_offset
            trace_start = trace_point + unreal.Vector(0.0, 0.0, 250.0)
            trace_end = trace_point - unreal.Vector(0.0, 0.0, 1200.0)
            hit = unreal.SystemLibrary.line_trace_single(
                world,
                trace_start,
                trace_end,
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                False,
                [kamaz_actor],
                unreal.DrawDebugTrace.NONE,
                False,
                unreal.LinearColor(1.0, 0.0, 0.0, 1.0),
                unreal.LinearColor(0.0, 1.0, 0.0, 1.0),
                0.0,
            )
            if isinstance(hit, tuple):
                hit_result = hit[1] if len(hit) > 1 else None
            else:
                hit_result = hit
            payload["trace_hits"].append(
                {
                    "offset_ratio": float(offset_ratio),
                    "trace_start": _vec_to_dict(trace_start),
                    "trace_end": _vec_to_dict(trace_end),
                    "hit": _serialize_hit(hit_result),
                }
            )

        payload["nearby_mesh_components"] = _collect_nearby_meshes(plow_location, plow_length_cm, plow_width_cm)
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
