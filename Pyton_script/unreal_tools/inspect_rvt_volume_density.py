import json
import os

import unreal


MAP_PATHS = [
    "/Game/CityPark/SnowSystem/SnowTest_Level",
    "/Game/Maps/MoscowEA5",
]
TARGET_RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_rvt_volume_density.json",
)


def _obj_path(obj):
    if not obj:
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


def _round(value):
    return round(float(value), 3)


def _vec_dict(vec):
    if vec is None:
        return None
    return {
        "x": _round(vec.x),
        "y": _round(vec.y),
        "z": _round(vec.z),
    }


def _find_target_volumes(world_actors, target_asset):
    target_path = _obj_path(target_asset)
    rows = []
    for actor in world_actors:
        if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
            continue

        component = actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        if component is None:
            continue

        bound_asset = None
        for prop_name in ("virtual_texture", "VirtualTexture", "RuntimeVirtualTexture"):
            bound_asset = _safe_get(component, prop_name)
            if bound_asset:
                break
        if _obj_path(bound_asset) != target_path:
            continue

        center, extent = actor.get_actor_bounds(False)
        span_x_cm = max(1.0, float(extent.x) * 2.0)
        span_y_cm = max(1.0, float(extent.y) * 2.0)
        span_z_cm = max(1.0, float(extent.z) * 2.0)

        virtual_size = None
        page_table_size = None
        try:
            virtual_size = int(target_asset.get_size())
        except Exception:
            pass
        try:
            page_table_size = int(target_asset.get_page_table_size())
        except Exception:
            pass

        row = {
            "label": actor.get_actor_label(),
            "path": actor.get_path_name(),
            "actor_location": _vec_dict(actor.get_actor_location()),
            "actor_scale": _vec_dict(actor.get_actor_scale3d()),
            "bounds_center": _vec_dict(center),
            "bounds_extent": _vec_dict(extent),
            "world_span_cm": {
                "x": _round(span_x_cm),
                "y": _round(span_y_cm),
                "z": _round(span_z_cm),
            },
            "rvt_virtual_size": virtual_size,
            "rvt_page_table_size": page_table_size,
            "cm_per_texel": {
                "x": _round(span_x_cm / max(1.0, float(virtual_size or 1))),
                "y": _round(span_y_cm / max(1.0, float(virtual_size or 1))),
            },
        }
        rows.append(row)

    return rows


def _find_trail_actor(actors):
    for actor in actors:
        if actor.get_actor_label() == "SnowRuntimeTrailBridgeActor":
            return actor
    return None


def _inspect_map(map_path, target_asset):
    row = {
        "map": map_path,
        "trail_actor": "",
        "trail_component_props": {},
        "target_rvt_volumes": [],
        "all_rvt_volumes": [],
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(map_path)
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = actor_subsystem.get_all_level_actors()

        trail_actor = _find_trail_actor(actors)
        if trail_actor:
            row["trail_actor"] = trail_actor.get_path_name()
            for component in trail_actor.get_components_by_class(unreal.ActorComponent):
                if "SnowRuntimeTrailBridgeComponent" not in component.get_class().get_name():
                    continue
                for prop_name in (
                    "StampSpacingCm",
                    "PersistentPlowLengthCm",
                    "PersistentPlowWidthCm",
                    "RightBermContinuationRatio",
                ):
                    row["trail_component_props"][prop_name] = _safe_get(component, prop_name)
                try:
                    target_rvt = component.get_editor_property("TargetRvt")
                except Exception:
                    target_rvt = None
                row["trail_component_props"]["TargetRvt"] = _obj_path(target_rvt)

        for actor in actors:
            if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
                continue
            component = actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
            if component is None:
                continue
            bound_asset = None
            for prop_name in ("virtual_texture", "VirtualTexture", "RuntimeVirtualTexture"):
                bound_asset = _safe_get(component, prop_name)
                if bound_asset:
                    break
            center, extent = actor.get_actor_bounds(False)
            row["all_rvt_volumes"].append(
                {
                    "label": actor.get_actor_label(),
                    "path": actor.get_path_name(),
                    "bound_asset": _obj_path(bound_asset),
                    "bounds_center": _vec_dict(center),
                    "bounds_extent": _vec_dict(extent),
                }
            )

        row["target_rvt_volumes"] = _find_target_volumes(actors, target_asset)
    except Exception as exc:
        row["error"] = str(exc)

    return row


def main():
    payload = {
        "target_rvt_asset": TARGET_RVT_PATH,
        "maps": [],
        "error": "",
    }

    try:
        target_asset = unreal.EditorAssetLibrary.load_asset(TARGET_RVT_PATH)
        if not target_asset:
            raise RuntimeError(f"Missing RVT asset: {TARGET_RVT_PATH}")

        for map_path in MAP_PATHS:
            payload["maps"].append(_inspect_map(map_path, target_asset))
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
