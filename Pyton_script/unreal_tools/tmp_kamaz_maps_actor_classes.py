import json, os
import unreal

MAPS = ['/Game/CityPark/SnowSystem/SnowTest_Level', '/Game/Maps/MoscowEA5']

res = {'maps': []}
for m in MAPS:
    item = {'map': m, 'loaded': False, 'actors': []}
    if not unreal.EditorAssetLibrary.does_asset_exist(m):
        item['error'] = 'map missing'
        res['maps'].append(item)
        continue
    unreal.EditorLoadingAndSavingUtils.load_map(m)
    item['loaded'] = True
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        name = a.get_actor_label()
        path = a.get_path_name()
        cls = a.get_class().get_path_name()
        if 'Kamaz' in name or 'Kamaz' in path or 'Kamaz' in cls:
            entry = {'label': name, 'path': path, 'class': cls}
            try:
                entry['bStartBrakeApplied'] = bool(a.get_editor_property('bStartBrakeApplied'))
            except Exception:
                entry['bStartBrakeApplied'] = 'N/A'
            item['actors'].append(entry)
    res['maps'].append(item)

p = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_maps_actor_classes.json')
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=2)
print(p)
