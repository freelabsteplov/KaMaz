import unreal


TOKENS = ("plane", "ground", "road", "floor", "test", "snow")
MIN_VERTS = 500


def _matches(path: str) -> bool:
    p = path.lower()
    return any(t in p for t in TOKENS)


def _safe_bounds(mesh):
    try:
        bounds = mesh.get_bounds()
        return bounds.box_extent
    except Exception:
        return None


def main():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(
        class_names=["StaticMesh"],
        package_paths=["/Game"],
        recursive_paths=True,
        recursive_classes=True,
    )
    data = reg.get_assets(flt)

    sm_subsys = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    rows = []
    for entry in data:
        obj_path = str(entry.object_path)
        if not _matches(obj_path):
            continue
        mesh = unreal.EditorAssetLibrary.load_asset(obj_path)
        if mesh is None:
            continue
        try:
            verts = int(sm_subsys.get_number_verts(mesh, 0))
        except Exception:
            continue
        if verts < MIN_VERTS:
            continue

        ext = _safe_bounds(mesh)
        ex = float(ext.x) if ext else 0.0
        ey = float(ext.y) if ext else 0.0
        ez = float(ext.z) if ext else 0.0
        flat_ratio = (ez / max(1.0, max(ex, ey))) if max(ex, ey) > 0 else 999.0
        rows.append((flat_ratio, -verts, obj_path, verts, ex, ey, ez))

    rows.sort()
    print(f"candidate_count={len(rows)}")
    for flat_ratio, neg_verts, path, verts, ex, ey, ez in rows[:40]:
        print(
            f"path={path} verts={verts} extent=({ex:.1f},{ey:.1f},{ez:.1f}) flat_ratio={flat_ratio:.4f}"
        )


if __name__ == "__main__":
    main()
