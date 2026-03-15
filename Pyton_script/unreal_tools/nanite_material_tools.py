import unreal


DEFAULT_ROOT = "/Game/Datasmith/TrafficLights_KIT/Geometries"


def _resolve_material(material_interface):
    current = material_interface
    visited = set()
    last_material = None
    last_blend_mode = None

    while current and hasattr(current, "get_editor_property"):
        path = current.get_path_name()
        if path in visited:
            break
        visited.add(path)

        try:
            blend_mode = current.get_editor_property("blend_mode")
            last_material = current
            last_blend_mode = blend_mode
        except Exception:
            blend_mode = None

        if type(current).__name__ == "Material":
            return current, blend_mode

        try:
            current = current.get_editor_property("parent")
        except Exception:
            current = None

    return last_material, last_blend_mode


def scan_invalid_nanite_meshes(root=DEFAULT_ROOT):
    invalid_meshes = []
    asset_paths = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)

    for asset_path in asset_paths:
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not mesh or type(mesh).__name__ != "StaticMesh":
            continue

        try:
            nanite = mesh.get_editor_property("nanite_settings")
            if not nanite.get_editor_property("enabled"):
                continue
        except Exception:
            continue

        bad_slots = []
        for idx, slot in enumerate(mesh.get_editor_property("static_materials")):
            material = slot.get_editor_property("material_interface")
            resolved_material, blend_mode = _resolve_material(material)
            if blend_mode not in (unreal.BlendMode.BLEND_OPAQUE, unreal.BlendMode.BLEND_MASKED):
                bad_slots.append(
                    {
                        "slot": idx,
                        "material": material.get_path_name() if material else None,
                        "resolved_material": resolved_material.get_path_name() if resolved_material else None,
                        "blend_mode": str(blend_mode),
                    }
                )

        if bad_slots:
            invalid_meshes.append(
                {
                    "mesh": asset_path,
                    "bad_slots": bad_slots,
                }
            )

    return invalid_meshes


def disable_nanite_for_invalid_meshes(root=DEFAULT_ROOT):
    updated = []

    for entry in scan_invalid_nanite_meshes(root):
        mesh = unreal.EditorAssetLibrary.load_asset(entry["mesh"])
        if not mesh:
            continue

        nanite = mesh.get_editor_property("nanite_settings")
        if not nanite.get_editor_property("enabled"):
            continue

        mesh.modify()
        nanite.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", nanite)

        saved = unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
        updated.append(
            {
                "mesh": entry["mesh"],
                "saved": saved,
                "bad_slots": entry["bad_slots"],
            }
        )

    return updated


def print_invalid_nanite_meshes(root=DEFAULT_ROOT):
    invalid_meshes = scan_invalid_nanite_meshes(root)
    print(f"Invalid Nanite meshes under {root}: {len(invalid_meshes)}")
    for entry in invalid_meshes:
        print(entry["mesh"])
        for slot in entry["bad_slots"]:
            print(
                f"  slot={slot['slot']} material={slot['material']} "
                f"resolved={slot['resolved_material']} blend={slot['blend_mode']}"
            )
    return invalid_meshes


def fix_traffic_lights_kit_nanite():
    updated = disable_nanite_for_invalid_meshes(DEFAULT_ROOT)
    print(f"Updated meshes: {len(updated)}")
    for entry in updated:
        print(f"{entry['mesh']} saved={entry['saved']}")
    return updated
