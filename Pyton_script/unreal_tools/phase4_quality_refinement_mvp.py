import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
HEIGHT_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP"

WRITER_LABEL = "VT_MVP_DebugWriter"
OLD_HEIGHT_LABEL = "SnowHeightTestSurface_MVP"
NEW_HEIGHT_LABEL = "SnowHeightTestSurface_FlatDense_MVP"
SNOW_GROUND_LABEL = "SnowTestGround"

FLAT_DENSE_MESH_PATH = "/Engine/EditorMeshes/PlanarReflectionPlane.PlanarReflectionPlane"
NEW_HEIGHT_SCALE = unreal.Vector(0.35, 0.35, 1.0)

TARGET_SLOT = 0


ASSET_LIB = unreal.EditorAssetLibrary


def _obj_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_set(obj, prop, value) -> bool:
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _load_asset(path: str):
    return ASSET_LIB.load_asset(path)


def _find_actor_by_label(label: str):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _first_static_mesh_component(actor):
    if actor is None:
        return None
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def _find_rvt_volume_for_asset(rvt_asset):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_sub.get_all_level_actors():
        if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
            continue
        comp = actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        if comp is None:
            continue
        vt = comp.get_editor_property("virtual_texture")
        if _obj_path(vt) == _obj_path(rvt_asset):
            return actor
    return None


def _actor_bounds(actor) -> tuple[unreal.Vector, unreal.Vector]:
    loc, ext = actor.get_actor_bounds(False)
    return loc, ext


def _inside_volume(actor, volume) -> bool:
    if actor is None or volume is None:
        return False
    a_loc, a_ext = _actor_bounds(actor)
    v_loc, v_ext = _actor_bounds(volume)
    min_x = a_loc.x - a_ext.x
    max_x = a_loc.x + a_ext.x
    min_y = a_loc.y - a_ext.y
    max_y = a_loc.y + a_ext.y
    min_z = a_loc.z - a_ext.z
    max_z = a_loc.z + a_ext.z
    return (
        min_x >= (v_loc.x - v_ext.x)
        and max_x <= (v_loc.x + v_ext.x)
        and min_y >= (v_loc.y - v_ext.y)
        and max_y <= (v_loc.y + v_ext.y)
        and min_z >= (v_loc.z - v_ext.z)
        and max_z <= (v_loc.z + v_ext.z)
    )


def _mesh_profile(mesh) -> dict:
    sm_sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    verts = -1
    flat_ratio = 9999.0
    ext = [0.0, 0.0, 0.0]
    if mesh is not None:
        try:
            verts = int(sm_sub.get_number_verts(mesh, 0))
        except Exception:
            verts = -1
        try:
            b = mesh.get_bounds()
            ext = [float(b.box_extent.x), float(b.box_extent.y), float(b.box_extent.z)]
            flat_ratio = ext[2] / max(1.0, max(ext[0], ext[1]))
        except Exception:
            pass
    return {
        "mesh_path": _obj_path(mesh),
        "verts_lod0": verts,
        "extents": ext,
        "flat_ratio": flat_ratio,
    }


def _assign_mi(actor, mi):
    comp = _first_static_mesh_component(actor)
    if comp is None:
        raise RuntimeError("Target has no StaticMeshComponent")
    if comp.get_num_materials() <= TARGET_SLOT:
        raise RuntimeError("Target has no slot 0")
    comp.set_material(TARGET_SLOT, mi)
    comp.modify()
    return _obj_path(comp.get_material(TARGET_SLOT))


def _spawn_or_get_new_height_actor(writer_actor, old_actor):
    actor = _find_actor_by_label(NEW_HEIGHT_LABEL)
    created = False
    if actor is None:
        base_loc = unreal.Vector(0.0, 0.0, 0.0)
        if writer_actor is not None:
            base_loc = writer_actor.get_actor_location()
        elif old_actor is not None:
            base_loc = old_actor.get_actor_location()
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            base_loc,
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        created = True

    actor.set_actor_label(NEW_HEIGHT_LABEL)
    comp = _first_static_mesh_component(actor)
    if comp is None:
        raise RuntimeError("Could not get component for new height actor")

    mesh = _load_asset(FLAT_DENSE_MESH_PATH)
    if mesh is None:
        raise RuntimeError(f"Missing dense flat mesh: {FLAT_DENSE_MESH_PATH}")

    _safe_set(comp, "static_mesh", mesh)
    actor.set_actor_scale3d(NEW_HEIGHT_SCALE)
    actor.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)

    # Keep it aligned with writer XY for readable overlap; keep old target Z if available.
    loc = actor.get_actor_location()
    if writer_actor is not None:
        writer_loc = writer_actor.get_actor_location()
        loc = unreal.Vector(float(writer_loc.x), float(writer_loc.y), float(loc.z))
    if old_actor is not None:
        old_loc = old_actor.get_actor_location()
        loc = unreal.Vector(float(loc.x), float(loc.y), float(old_loc.z))
    actor.set_actor_location(loc, False, False)

    return actor, created


def _tighten_rvt_volume(volume_actor, anchors: list):
    if volume_actor is None:
        return {"changed": False, "reason": "missing_volume"}
    if not anchors:
        return {"changed": False, "reason": "missing_anchors"}

    old_actor_loc = volume_actor.get_actor_location()
    old_loc, old_ext = _actor_bounds(volume_actor)
    old_scale = volume_actor.get_actor_scale3d()

    min_x = 1e30
    min_y = 1e30
    min_z = 1e30
    max_x = -1e30
    max_y = -1e30
    max_z = -1e30

    for actor in anchors:
        loc, ext = _actor_bounds(actor)
        min_x = min(min_x, loc.x - ext.x)
        min_y = min(min_y, loc.y - ext.y)
        min_z = min(min_z, loc.z - ext.z)
        max_x = max(max_x, loc.x + ext.x)
        max_y = max(max_y, loc.y + ext.y)
        max_z = max(max_z, loc.z + ext.z)

    margin_xy = 220.0
    margin_z = 300.0

    min_x -= margin_xy
    max_x += margin_xy
    min_y -= margin_xy
    max_y += margin_xy
    min_z -= margin_z
    max_z += margin_z

    desired_loc = unreal.Vector(
        float((min_x + max_x) * 0.5),
        float((min_y + max_y) * 0.5),
        float((min_z + max_z) * 0.5),
    )
    desired_ext = unreal.Vector(
        float(max(300.0, (max_x - min_x) * 0.5)),
        float(max(300.0, (max_y - min_y) * 0.5)),
        float(max(300.0, (max_z - min_z) * 0.5)),
    )

    # RuntimeVirtualTextureVolume behaves as:
    # bounds_center ~= actor_location + bounds_extents
    # bounds_extents ~= actor_scale * 0.5
    new_scale = unreal.Vector(
        float(desired_ext.x * 2.0),
        float(desired_ext.y * 2.0),
        float(desired_ext.z * 2.0),
    )
    new_actor_loc = unreal.Vector(
        float(desired_loc.x - desired_ext.x),
        float(desired_loc.y - desired_ext.y),
        float(desired_loc.z - desired_ext.z),
    )

    volume_actor.set_actor_location(new_actor_loc, False, False)
    volume_actor.set_actor_scale3d(new_scale)

    new_loc, new_ext = _actor_bounds(volume_actor)
    return {
        "changed": True,
        "old_actor_location": str(old_actor_loc),
        "old_location": str(old_loc),
        "old_extents": str(old_ext),
        "old_scale": str(old_scale),
        "new_actor_location": str(volume_actor.get_actor_location()),
        "new_location": str(new_loc),
        "new_extents": str(new_ext),
        "new_scale": str(new_scale),
        "xy_extent_reduction_factor": (
            (old_ext.x * old_ext.y) / max(1.0, new_ext.x * new_ext.y)
        ),
    }


def _output_path() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "phase4_quality_refinement_mvp.json")


def main():
    payload = {
        "map_path": MAP_PATH,
        "preserved_assets": [
            "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP",
            "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP",
            "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP",
            OLD_HEIGHT_LABEL,
            WRITER_LABEL,
        ],
        "changes": {},
        "final_quality_target": {},
        "rvt_quality_action": {},
        "assignment": {},
        "quality_verdict": {
            "clean_flat_dense_height_target": False,
            "height_quality_improved": False,
        },
        "exact_blocker": "",
    }

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    rvt = _load_asset(RVT_PATH)
    if rvt is None:
        raise RuntimeError(f"Missing RVT asset: {RVT_PATH}")
    mi = _load_asset(HEIGHT_MI_PATH)
    if mi is None:
        raise RuntimeError(f"Missing height MI: {HEIGHT_MI_PATH}")

    writer_actor = _find_actor_by_label(WRITER_LABEL)
    old_actor = _find_actor_by_label(OLD_HEIGHT_LABEL)
    snow_ground = _find_actor_by_label(SNOW_GROUND_LABEL)
    if writer_actor is None:
        raise RuntimeError("Missing VT_MVP_DebugWriter")
    if old_actor is None:
        raise RuntimeError("Missing SnowHeightTestSurface_MVP")
    if snow_ground is None:
        raise RuntimeError("Missing SnowTestGround")

    old_comp = _first_static_mesh_component(old_actor)
    old_mesh_before = _obj_path(old_comp.get_editor_property("static_mesh")) if old_comp else ""
    old_mat_before = _obj_path(old_comp.get_material(0)) if old_comp else ""

    new_actor, new_created = _spawn_or_get_new_height_actor(writer_actor, old_actor)
    new_comp = _first_static_mesh_component(new_actor)
    new_mesh = new_comp.get_editor_property("static_mesh") if new_comp else None
    new_mesh_profile = _mesh_profile(new_mesh)

    assigned_path = _assign_mi(new_actor, mi)

    volume_actor = _find_rvt_volume_for_asset(rvt)
    anchors = [writer_actor, new_actor]
    tighten = _tighten_rvt_volume(volume_actor, anchors)

    inside_writer = _inside_volume(writer_actor, volume_actor)
    inside_new = _inside_volume(new_actor, volume_actor)
    inside_old = _inside_volume(old_actor, volume_actor)

    # Verify fallback remained untouched.
    old_comp_after = _first_static_mesh_component(old_actor)
    old_mesh_after = _obj_path(old_comp_after.get_editor_property("static_mesh")) if old_comp_after else ""
    old_mat_after = _obj_path(old_comp_after.get_material(0)) if old_comp_after else ""
    fallback_untouched = (old_mesh_before == old_mesh_after and old_mat_before == old_mat_after)

    # Keep the old SnowTestGround receiver mapping unchanged by this step.
    snow_comp = _first_static_mesh_component(snow_ground)
    snow_ground_mat = _obj_path(snow_comp.get_material(0)) if snow_comp and snow_comp.get_num_materials() > 0 else ""

    clean_flat_dense = (
        new_mesh_profile["mesh_path"] == FLAT_DENSE_MESH_PATH
        and new_mesh_profile["verts_lod0"] >= 1000
        and new_mesh_profile["flat_ratio"] <= 0.01
    )
    improved_proxy = bool(
        clean_flat_dense
        and tighten.get("changed", False)
        and inside_writer
        and inside_new
        and tighten.get("xy_extent_reduction_factor", 1.0) >= 1.2
    )

    payload["changes"] = {
        "new_actor_created": new_created,
        "fallback_untouched": fallback_untouched,
        "snowtestground_slot0_material": snow_ground_mat,
    }
    payload["final_quality_target"] = {
        "actor_path": _obj_path(new_actor),
        "actor_label": new_actor.get_actor_label(),
        "mesh_path": new_mesh_profile["mesh_path"],
        "mesh_verts_lod0": new_mesh_profile["verts_lod0"],
        "mesh_flat_ratio": new_mesh_profile["flat_ratio"],
        "location": str(new_actor.get_actor_location()),
        "scale": str(new_actor.get_actor_scale3d()),
        "better_than_old_reason": "True flat plane topology with denser local grid than flattened sphere and cleaner normal orientation.",
    }
    payload["rvt_quality_action"] = {
        "rvt_volume_changed": bool(tighten.get("changed", False)),
        "volume_tighten": tighten,
        "writer_inside_volume": inside_writer,
        "new_target_inside_volume": inside_new,
        "old_target_inside_volume": inside_old,
        "new_rvt_asset_created": False,
        "final_rvt_asset_used": RVT_PATH,
    }
    payload["assignment"] = {
        "actor": _obj_path(new_actor),
        "slot": TARGET_SLOT,
        "material_instance_assigned": assigned_path,
    }
    payload["quality_verdict"]["clean_flat_dense_height_target"] = bool(clean_flat_dense)
    payload["quality_verdict"]["height_quality_improved"] = bool(improved_proxy)

    if not payload["quality_verdict"]["height_quality_improved"]:
        payload["exact_blocker"] = (
            "Quality gate not met: either flat-dense target, tight RVT bounds, or in-volume overlap check failed."
        )

    # Save changed level state.
    unreal.EditorLoadingAndSavingUtils.save_current_level()

    out_path = _output_path()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(payload)


if __name__ == "__main__":
    main()
