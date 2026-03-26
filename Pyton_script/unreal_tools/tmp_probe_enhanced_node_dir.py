import unreal, json, os
obj = unreal.load_object(None, "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.BP_VehicleAdvPawnBase:EventGraph.K2Node_EnhancedInputAction_0")
out = {'has_obj': obj is not None, 'dir': dir(obj) if obj else []}
path = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_probe_enhanced_node_dir.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(path)
