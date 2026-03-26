import json, os
import unreal

assets = [
 '/Game/CityPark/Kamaz/inputs/IA_GAZ',
 '/Game/CityPark/Kamaz/inputs/IA_TORM',
 '/Game/CityPark/Kamaz/inputs/IA_RUL',
 '/Game/CityPark/Kamaz/inputs/IA_Handbrake_Digital',
 '/Game/CityPark/Kamaz/inputs/IMC_MOZA_Kamaz',
]

out=[]
for p in assets:
    a=unreal.EditorAssetLibrary.load_asset(p)
    item={'path':p,'exists':bool(a),'class':a.get_class().get_name() if a else ''}
    if not a:
        out.append(item); continue
    if a.get_class().get_name()=='InputAction':
        for prop in ['value_type','consume_input','trigger_when_paused','triggers','modifiers']:
            try:
                v=a.get_editor_property(prop)
                if prop in ('triggers','modifiers'):
                    item[prop]=[x.get_class().get_name() for x in list(v or [])]
                else:
                    item[prop]=str(v)
            except Exception as exc:
                item[prop]=f'ERR:{exc}'
    if a.get_class().get_name()=='InputMappingContext':
        maps=[]
        try:
            mappings=list(a.get_editor_property('mappings') or [])
            for m in mappings:
                rec={}
                try: rec['action']=m.get_editor_property('action').get_path_name()
                except Exception: rec['action']=''
                try: rec['key']=str(m.get_editor_property('key'))
                except Exception: rec['key']=''
                try: rec['modifiers']=[x.get_class().get_name() for x in list(m.get_editor_property('modifiers') or [])]
                except Exception: rec['modifiers']=[]
                try: rec['triggers']=[x.get_class().get_name() for x in list(m.get_editor_property('triggers') or [])]
                except Exception: rec['triggers']=[]
                maps.append(rec)
        except Exception as exc:
            item['mappings_error']=str(exc)
            maps=[]
        item['mappings']=maps
    out.append(item)

res={'assets':out}
p=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','tmp_kamaz_input_assets_audit.json')
os.makedirs(os.path.dirname(p),exist_ok=True)
with open(p,'w',encoding='utf-8') as f: json.dump(res,f,indent=2)
print(p)
