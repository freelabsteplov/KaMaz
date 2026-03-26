import unreal


CANDIDATES = [
    "/Engine/BasicShapes/Plane.Plane",
    "/Engine/BasicShapes/Cube.Cube",
    "/Engine/BasicShapes/Sphere.Sphere",
    "/Engine/BasicShapes/Cylinder.Cylinder",
    "/Engine/BasicShapes/Cone.Cone",
    "/Engine/EditorMeshes/EditorPlane.EditorPlane",
    "/Engine/EditorMeshes/EditorCube.EditorCube",
    "/Engine/EditorMeshes/EditorSphere.EditorSphere",
    "/Engine/EditorMeshes/EditorCylinder.EditorCylinder",
    "/Engine/EditorMeshes/EditorCone.EditorCone",
    "/Engine/EditorMeshes/MatineeCam_SM.MatineeCam_SM",
]


def main():
    sm_subsys = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for path in CANDIDATES:
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if mesh is None:
            print(f"path={path} exists=NO")
            continue
        try:
            verts = int(sm_subsys.get_number_verts(mesh, 0))
        except Exception:
            verts = -1
        try:
            b = mesh.get_bounds()
            ex = float(b.box_extent.x)
            ey = float(b.box_extent.y)
            ez = float(b.box_extent.z)
            flat_ratio = ez / max(1.0, max(ex, ey))
        except Exception:
            ex = ey = ez = flat_ratio = -1.0
        print(
            f"path={path} exists=YES verts={verts} ext=({ex:.1f},{ey:.1f},{ez:.1f}) flat_ratio={flat_ratio:.4f}"
        )


if __name__ == "__main__":
    main()
