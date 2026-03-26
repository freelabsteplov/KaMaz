import unreal, json, os
assets = [
'/Game/VehicleTemplate/Input/Actions/IA_Throttle',
'/Game/VehicleTemplate/Input/Actions/IA_Brake',
'/Game/VehicleTemplate/Input/Actions/IA_Steering',
'/Game/VehicleTemplate/Input/Actions/IA_Handbrake',
'/Game/VehicleTemplate/Input/Actions/IA_Reset',
'/Game/VehicleTemplate/Input/Actions/IA_LookAround',
'/Game/VehicleTemplate/Input/Actions/IA_ToggleCamera',
'/Game/VehicleTemplate/Input/Actions/IA_Headlights',
]
out=[]
for p in assets:
    a = unreal.EditorAssetLibrary.load_asset(p)
    item={'path':p,'loaded':a is not None,'class':a.get_class().get_path_name() if a else ''}
    if a:
        for prop in ['value_type','ValueType','consume_input','trigger_events_that_consume_legacy_keys']:
            try:
                v = a.get_editor_property(prop)
                item[prop]=str(v)
            except Exception:
                pass
        item['dir_sample']=[n for n in dir(a) if 'value' in n.lower() or 'type' in n.lower()][:20]
    out.append(item)
path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','tmp_input_action_types.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path,'w',encoding='utf-8') as f:
    json.dump(out,f,indent=2)
print(path)
