import unreal, json, os
NODE_PATH = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.BP_VehicleAdvPawnBase:EventGraph.K2Node_EnhancedInputAction_0"
obj = unreal.load_object(None, NODE_PATH)
methods = []
if obj:
    for name in dir(obj):
        if any(k in name.lower() for k in ['destroy', 'remove', 'break', 'reconstruct', 'pin', 'node', 'input']):
            methods.append(name)
out = {'has_obj': obj is not None, 'methods': methods[:300]}
path = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_probe_enhanced_node_methods.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(path)
