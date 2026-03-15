import json, os, unreal
names = sorted([n for n in dir(unreal.MaterialEditingLibrary) if 'scalar' in n.lower() or 'parameter' in n.lower()])
path = os.path.join(r'C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation', 'material_editing_library_methods.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path,'w',encoding='utf-8') as f:
    json.dump(names,f,indent=2)
print(names)
