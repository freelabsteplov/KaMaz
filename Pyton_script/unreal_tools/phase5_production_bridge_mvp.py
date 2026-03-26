import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
HEIGHT_M_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
HEIGHT_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP"

WRITER_LABEL = "VT_MVP_DebugWriter"
SPHERE_PROOF_LABEL = "SnowHeightTestSurface_MVP"
FLAT_PROOF_LABEL = "SnowHeightTestSurface_FlatDense_MVP"
BRIDGE_LABEL = "SnowHeightBridgeSurface_MVP"
SNOWTESTGROUND_LABEL = "SnowTestGround"

BRIDGE_MESH_PATH = "/Engine/EditorMeshes/PlanarReflectionPlane.PlanarReflectionPlane"
BRIDGE_SCALE = unreal.Vector(1.0, 1.0, 1.0)
BRIDGE_Z_OFFSET_FROM_FLAT = -120.0
TARGET_SLOT = 0


ASSET_LIB = unreal.EditorAssetLibrary


def _obj_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_get(obj, prop, default=None):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return default


def _safe_set(obj, prop, value) -> bool:
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _vec3_tuple(vec):
    if vec is None:
        return (0.0, 0.0, 0.0)
    return (
        round(float(vec.x), 3),
        round(float(vec.y), 3),
        round(float(vec.z), 3),
    )


def _slot_material_path(component, slot=0) -> str:
    if component is None:
        return ""
    try:
        if component.get_num_materials() <= slot:
            return ""
        return _obj_path(component.get_material(slot))
    except Exception:
        return ""


def _load_asset(path: str):
    return ASSET_LIB.load_asset(path)


def _find_actor_by_label(label: str):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _first_smc(actor):
    if actor is None:
        return None
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def _bounds(actor):
    return actor.get_actor_bounds(False)


def _inside_volume(actor, volume) -> bool:
    if actor is None or volume is None:
        return False
    a_loc, a_ext = _bounds(actor)
    v_loc, v_ext = _bounds(volume)
    return (
        (a_loc.x - a_ext.x) >= (v_loc.x - v_ext.x)
        and (a_loc.x + a_ext.x) <= (v_loc.x + v_ext.x)
        and (a_loc.y - a_ext.y) >= (v_loc.y - v_ext.y)
        and (a_loc.y + a_ext.y) <= (v_loc.y + v_ext.y)
        and (a_loc.z - a_ext.z) >= (v_loc.z - v_ext.z)
        and (a_loc.z + a_ext.z) <= (v_loc.z + v_ext.z)
    )


def _xy_overlap(a, b) -> bool:
    if a is None or b is None:
        return False
    a_loc, a_ext = _bounds(a)
    b_loc, b_ext = _bounds(b)
    return (
        abs(a_loc.x - b_loc.x) <= (a_ext.x + b_ext.x)
        and abs(a_loc.y - b_loc.y) <= (a_ext.y + b_ext.y)
    )


def _find_rvt_volume_for_asset(rvt_asset):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
            continue
        comp = actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        if comp is None:
            continue
        vt = _safe_get(comp, "virtual_texture")
        if _obj_path(vt) == _obj_path(rvt_asset):
            return actor
    return None


def _mesh_profile(mesh) -> dict:
    sm_sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    verts = -1
    extents = [0.0, 0.0, 0.0]
    flat_ratio = 999.0
    if mesh is not None:
        try:
            verts = int(sm_sub.get_number_verts(mesh, 0))
        except Exception:
            verts = -1
        try:
            b = mesh.get_bounds()
            extents = [float(b.box_extent.x), float(b.box_extent.y), float(b.box_extent.z)]
            flat_ratio = extents[2] / max(1.0, max(extents[0], extents[1]))
        except Exception:
            pass
    return {
        "mesh_path": _obj_path(mesh),
        "verts_lod0": verts,
        "extents": extents,
        "flat_ratio": flat_ratio,
    }


def _assign_mi(actor, mi) -> str:
    comp = _first_smc(actor)
    if comp is None:
        raise RuntimeError("Bridge target has no StaticMeshComponent")
    if comp.get_num_materials() <= TARGET_SLOT:
        raise RuntimeError("Bridge target has no slot 0")
    comp.set_material(TARGET_SLOT, mi)
    comp.modify()
    return _obj_path(comp.get_material(TARGET_SLOT))


def _ensure_bridge_actor(writer_actor, flat_actor):
    actor = _find_actor_by_label(BRIDGE_LABEL)
    created = False
    if actor is None:
        loc = writer_actor.get_actor_location()
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(float(loc.x), float(loc.y), float(loc.z)),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        created = True

    actor.set_actor_label(BRIDGE_LABEL)
    comp = _first_smc(actor)
    if comp is None:
        raise RuntimeError("Could not access bridge static mesh component")

    mesh = _load_asset(BRIDGE_MESH_PATH)
    if mesh is None:
        raise RuntimeError(f"Missing mesh: {BRIDGE_MESH_PATH}")

    _safe_set(comp, "static_mesh", mesh)
    actor.set_actor_scale3d(BRIDGE_SCALE)
    actor.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)

    writer_loc = writer_actor.get_actor_location()
    flat_loc = flat_actor.get_actor_location() if flat_actor else writer_loc
    target_loc = unreal.Vector(
        float(writer_loc.x),
        float(writer_loc.y),
        float(flat_loc.z + BRIDGE_Z_OFFSET_FROM_FLAT),
    )
    actor.set_actor_location(target_loc, False, False)
    return actor, created


def _tighten_rvt_volume(volume_actor, anchors: list):
    if volume_actor is None:
        return {"changed": False, "reason": "missing_volume"}
    if not anchors:
        return {"changed": False, "reason": "missing_anchors"}

    old_actor_loc = volume_actor.get_actor_location()
    old_center, old_ext = _bounds(volume_actor)
    old_scale = volume_actor.get_actor_scale3d()

    min_x = 1e30
    min_y = 1e30
    min_z = 1e30
    max_x = -1e30
    max_y = -1e30
    max_z = -1e30

    for actor in anchors:
        loc, ext = _bounds(actor)
        min_x = min(min_x, loc.x - ext.x)
        min_y = min(min_y, loc.y - ext.y)
        min_z = min(min_z, loc.z - ext.z)
        max_x = max(max_x, loc.x + ext.x)
        max_y = max(max_y, loc.y + ext.y)
        max_z = max(max_z, loc.z + ext.z)

    margin_xy = 120.0
    margin_z = 220.0
    min_x -= margin_xy
    max_x += margin_xy
    min_y -= margin_xy
    max_y += margin_xy
    min_z -= margin_z
    max_z += margin_z

    desired_center = unreal.Vector(
        float((min_x + max_x) * 0.5),
        float((min_y + max_y) * 0.5),
        float((min_z + max_z) * 0.5),
    )
    desired_ext = unreal.Vector(
        float(max(300.0, (max_x - min_x) * 0.5)),
        float(max(300.0, (max_y - min_y) * 0.5)),
        float(max(220.0, (max_z - min_z) * 0.5)),
    )

    # RuntimeVirtualTextureVolume transform convention:
    # bounds_center ~= actor_location + bounds_extents, and bounds_extents ~= actor_scale * 0.5
    new_scale = unreal.Vector(
        float(desired_ext.x * 2.0),
        float(desired_ext.y * 2.0),
        float(desired_ext.z * 2.0),
    )
    new_actor_loc = unreal.Vector(
        float(desired_center.x - desired_ext.x),
        float(desired_center.y - desired_ext.y),
        float(desired_center.z - desired_ext.z),
    )

    volume_actor.set_actor_location(new_actor_loc, False, False)
    volume_actor.set_actor_scale3d(new_scale)

    new_center, new_ext = _bounds(volume_actor)
    return {
        "changed": True,
        "old_actor_location": str(old_actor_loc),
        "old_center": str(old_center),
        "old_extents": str(old_ext),
        "old_scale": str(old_scale),
        "new_actor_location": str(volume_actor.get_actor_location()),
        "new_center": str(new_center),
        "new_extents": str(new_ext),
        "new_scale": str(new_scale),
    }


def _mat_has_wpo(mat) -> bool:
    if mat is None:
        return False
    try:
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(
            mat, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
        )
        return node is not None
    except Exception:
        return False


def _output_path():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "phase5_production_bridge_mvp.json")


def main():
    payload = {
        "map_path": MAP_PATH,
        "facts": {},
        "final_bridge_target": {},
        "rvt_placement_action": {},
        "assigned_target": {},
        "bridge_verdict": {
            "production_bridge_target_ready": False,
            "real_height_visible_on_bridge": False,
        },
        "exact_blocker": "",
    }

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    rvt = _load_asset(RVT_PATH)
    mat = _load_asset(HEIGHT_M_PATH)
    mi = _load_asset(HEIGHT_MI_PATH)
    if rvt is None:
        raise RuntimeError(f"Missing RVT: {RVT_PATH}")
    if mi is None:
        raise RuntimeError(f"Missing MI: {HEIGHT_MI_PATH}")

    writer = _find_actor_by_label(WRITER_LABEL)
    sphere = _find_actor_by_label(SPHERE_PROOF_LABEL)
    flat = _find_actor_by_label(FLAT_PROOF_LABEL)
    snow_ground = _find_actor_by_label(SNOWTESTGROUND_LABEL)
    if writer is None:
        raise RuntimeError("Missing VT_MVP_DebugWriter")
    if sphere is None:
        raise RuntimeError("Missing SnowHeightTestSurface_MVP")
    if flat is None:
        raise RuntimeError("Missing SnowHeightTestSurface_FlatDense_MVP")
    if snow_ground is None:
        raise RuntimeError("Missing SnowTestGround")

    # Snapshot fallback state for safety check.
    sphere_comp = _first_smc(sphere)
    flat_comp = _first_smc(flat)
    writer_comp = _first_smc(writer)
    sphere_mesh_before = _obj_path(_safe_get(sphere_comp, "static_mesh"))
    sphere_mat_before = _slot_material_path(sphere_comp, 0)
    flat_mesh_before = _obj_path(_safe_get(flat_comp, "static_mesh"))
    flat_mat_before = _slot_material_path(flat_comp, 0)
    writer_loc_before = _vec3_tuple(writer.get_actor_location())
    writer_mesh_before = _obj_path(_safe_get(writer_comp, "static_mesh"))

    bridge, bridge_created = _ensure_bridge_actor(writer, flat)
    bridge_comp = _first_smc(bridge)
    bridge_mesh = _safe_get(bridge_comp, "static_mesh") if bridge_comp else None
    bridge_mesh_profile = _mesh_profile(bridge_mesh)

    assigned_path = _assign_mi(bridge, mi)

    volume = _find_rvt_volume_for_asset(rvt)
    tighten = _tighten_rvt_volume(volume, [writer, flat, bridge])

    inside_writer = _inside_volume(writer, volume)
    inside_flat = _inside_volume(flat, volume)
    inside_bridge = _inside_volume(bridge, volume)
    writer_covers_bridge = _xy_overlap(writer, bridge)

    # Confirm fallback unchanged.
    sphere_comp_after = _first_smc(sphere)
    flat_comp_after = _first_smc(flat)
    writer_comp_after = _first_smc(writer)
    sphere_mesh_after = _obj_path(_safe_get(sphere_comp_after, "static_mesh"))
    sphere_mat_after = _slot_material_path(sphere_comp_after, 0)
    flat_mesh_after = _obj_path(_safe_get(flat_comp_after, "static_mesh"))
    flat_mat_after = _slot_material_path(flat_comp_after, 0)
    writer_loc_after = _vec3_tuple(writer.get_actor_location())
    writer_mesh_after = _obj_path(_safe_get(writer_comp_after, "static_mesh"))

    fallback_unchanged = bool(
        sphere_mesh_before == sphere_mesh_after
        and sphere_mat_before == sphere_mat_after
        and flat_mesh_before == flat_mesh_after
        and flat_mat_before == flat_mat_after
        and writer_loc_before == writer_loc_after
        and writer_mesh_before == writer_mesh_after
    )

    snow_comp = _first_smc(snow_ground)
    snow_slot0 = _obj_path(snow_comp.get_material(0)) if snow_comp and snow_comp.get_num_materials() > 0 else ""

    flat_area = max(1.0, float(flat.get_actor_bounds(False)[1].x) * 2.0 * float(flat.get_actor_bounds(False)[1].y) * 2.0)
    bridge_area = max(1.0, float(bridge.get_actor_bounds(False)[1].x) * 2.0 * float(bridge.get_actor_bounds(False)[1].y) * 2.0)
    area_ratio = bridge_area / flat_area

    bridge_flat_dense = bool(
        bridge_mesh_profile["mesh_path"] == BRIDGE_MESH_PATH
        and bridge_mesh_profile["verts_lod0"] >= 1000
        and bridge_mesh_profile["flat_ratio"] <= 0.01
    )
    assigned_ok = assigned_path == _obj_path(mi)
    has_wpo = _mat_has_wpo(mat)

    real_height_visible = bool(
        bridge_flat_dense
        and inside_bridge
        and inside_writer
        and writer_covers_bridge
        and assigned_ok
        and has_wpo
    )
    production_bridge_ready = bool(
        real_height_visible
        and area_ratio >= 3.0
        and fallback_unchanged
        and inside_flat
    )

    payload["facts"] = {
        "preserved_isolated_proof": fallback_unchanged,
        "bridge_actor_created": bridge_created,
        "writer_repositioned": False,
        "snowtestground_slot0_material": snow_slot0,
        "calibrated": {
            "bridge_scale": str(bridge.get_actor_scale3d()),
            "bridge_location": str(bridge.get_actor_location()),
            "rvt_volume_bounds_tightened": bool(tighten.get("changed", False)),
        },
    }
    payload["final_bridge_target"] = {
        "actor_path": _obj_path(bridge),
        "mesh": bridge_mesh_profile["mesh_path"],
        "scale": str(bridge.get_actor_scale3d()),
        "why_more_production_like": "Flat dense plane with significantly larger working area than tiny proof plane (area ratio {:.2f}x).".format(area_ratio),
    }
    payload["rvt_placement_action"] = {
        "bounds_changed": bool(tighten.get("changed", False)),
        "bounds_details": tighten,
        "writer_position_changed": False,
        "writer_inside_volume": inside_writer,
        "flat_proof_inside_volume": inside_flat,
        "bridge_inside_volume": inside_bridge,
        "writer_covers_bridge_xy": writer_covers_bridge,
        "final_rvt_asset": RVT_PATH,
    }
    payload["assigned_target"] = {
        "actor": _obj_path(bridge),
        "slot": TARGET_SLOT,
        "mi": assigned_path,
    }
    payload["bridge_verdict"]["production_bridge_target_ready"] = production_bridge_ready
    payload["bridge_verdict"]["real_height_visible_on_bridge"] = real_height_visible

    if not production_bridge_ready or not real_height_visible:
        payload["exact_blocker"] = (
            "Bridge gate failed (flat-dense mesh, assignment, WPO path, RVT coverage, or fallback-preservation check)."
        )

    unreal.EditorLoadingAndSavingUtils.save_current_level()

    out = _output_path()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(payload)


if __name__ == "__main__":
    main()
