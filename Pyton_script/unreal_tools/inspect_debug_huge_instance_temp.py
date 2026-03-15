import json, os, unreal
asset = unreal.EditorAssetLibrary.load_asset('/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_DebugHuge')
lib = unreal.MaterialEditingLibrary
names = ['BrushLengthCm','BrushWidthCm','BrushHeightCm','BrushStrength']
out = {}
for name in names:
    try:
        out[name] = lib.get_material_instance_scalar_parameter_value(asset, name)
    except Exception as exc:
        out[name] = str(exc)
path = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'inspect_debug_huge_instance.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path,'w',encoding='utf-8') as f:
    json.dump(out,f,indent=2)
print(out)
