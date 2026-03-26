import json
import os

import unreal


ASSET = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase"
OUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "bp_vehicleadv_graph_api_probe.json")


def obj_path(o):
    if o is None:
        return ""
    try:
        return o.get_path_name()
    except Exception:
        return str(o)


def cls_path(o):
    if o is None:
        return ""
    try:
        return o.get_class().get_path_name()
    except Exception:
        return ""


payload = {
    "asset_path": ASSET,
}

asset = unreal.EditorAssetLibrary.load_asset(ASSET)
payload["asset_loaded"] = bool(asset)
payload["asset_class"] = cls_path(asset)
payload["asset_obj"] = obj_path(asset)

if asset:
    graphs = []
    for prop in ("ubergraph_pages", "function_graphs", "delegate_signature_graphs", "macro_graphs"):
        arr = []
        try:
            arr = list(asset.get_editor_property(prop) or [])
        except Exception as exc:
            payload[f"{prop}_error"] = str(exc)
            arr = []
        payload[f"{prop}_count"] = len(arr)
        for g in arr:
            node_count = 0
            try:
                node_count = len(list(g.get_editor_property("nodes") or []))
            except Exception as exc:
                node_count = -1
                payload[f"{obj_path(g)}_nodes_error"] = str(exc)
            graphs.append(
                {
                    "prop": prop,
                    "graph_name": g.get_name(),
                    "graph_path": obj_path(g),
                    "graph_class": cls_path(g),
                    "node_count": node_count,
                }
            )
    payload["graphs"] = graphs

    enhanced = []
    for g in graphs:
        g_obj = unreal.EditorAssetLibrary.load_asset(g["graph_path"])
        if not g_obj:
            continue
        try:
            nodes = list(g_obj.get_editor_property("nodes") or [])
        except Exception:
            nodes = []
        for n in nodes:
            cp = cls_path(n)
            title = ""
            try:
                title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                try:
                    title = str(n.get_node_title())
                except Exception:
                    title = n.get_name()
            if "K2Node_EnhancedInputAction" in cp or "EnhancedInputAction" in title:
                enhanced.append(
                    {
                        "node_path": obj_path(n),
                        "node_class": cp,
                        "title": title,
                    }
                )
    payload["enhanced_nodes"] = enhanced
    payload["enhanced_count"] = len(enhanced)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
print(json.dumps({"output": OUT, "enhanced_count": payload.get("enhanced_count", 0)}))
