import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"


def _safe_get_verts(sm_subsys, mesh):
    try:
        return int(sm_subsys.get_number_verts(mesh, 0))
    except Exception:
        return -1


def main():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sm_subsys = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)

    rows = []
    for actor in actor_subsystem.get_all_level_actors():
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp is None:
            continue
        mesh = comp.get_editor_property("static_mesh")
        if mesh is None:
            continue
        verts = _safe_get_verts(sm_subsys, mesh)
        _, ext = actor.get_actor_bounds(False)
        ex, ey, ez = float(ext.x), float(ext.y), float(ext.z)
        flat_ratio = ez / max(1.0, max(ex, ey))
        rows.append(
            (
                flat_ratio,
                -verts,
                actor.get_actor_label(),
                actor.get_path_name(),
                mesh.get_path_name(),
                verts,
                ex,
                ey,
                ez,
            )
        )

    rows.sort()
    print(f"mesh_actor_count={len(rows)}")
    for row in rows[:120]:
        flat_ratio, neg_verts, label, actor_path, mesh_path, verts, ex, ey, ez = row
        print(
            f"label={label} verts={verts} ext=({ex:.1f},{ey:.1f},{ez:.1f}) flat_ratio={flat_ratio:.4f} mesh={mesh_path} actor={actor_path}"
        )


if __name__ == "__main__":
    main()
