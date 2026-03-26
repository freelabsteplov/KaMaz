import json, os, unreal
ASSET='/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape'
out={'asset':ASSET,'class':'','parent_chain':[],'scalar_names':[],'vector_names':[],'texture_names':[],'scalar_values':{},'vector_values':{},'texture_values':{},'error':''}
try:
    a=unreal.EditorAssetLibrary.load_asset(ASSET)
    if not a:
        raise RuntimeError('asset load failed')
    out['class']=a.get_class().get_path_name()
    cur=a
    seen=set()
    while cur:
        p=cur.get_path_name()
        if p in seen:
            break
        seen.add(p)
        out['parent_chain'].append({'name':cur.get_name(),'path':p,'class':cur.get_class().get_path_name()})
        nxt=None
        for prop in ('parent','Parent','ParentEditorOnly'):
            try:
                nxt=cur.get_editor_property(prop)
                if nxt:
                    break
            except Exception:
                pass
        cur=nxt
    mel=unreal.MaterialEditingLibrary
    for name in mel.get_scalar_parameter_names(a) or []:
        key=str(name)
        out['scalar_names'].append(key)
        try:
            out['scalar_values'][key]=mel.get_material_instance_scalar_parameter_value(a,name)
        except Exception as exc:
            out['scalar_values'][key]=f'ERR: {exc}'
    for name in mel.get_vector_parameter_names(a) or []:
        key=str(name)
        out['vector_names'].append(key)
        try:
            v=mel.get_material_instance_vector_parameter_value(a,name)
            out['vector_values'][key]=str(v)
        except Exception as exc:
            out['vector_values'][key]=f'ERR: {exc}'
    for name in mel.get_texture_parameter_names(a) or []:
        key=str(name)
        out['texture_names'].append(key)
        try:
            t=mel.get_material_instance_texture_parameter_value(a,name)
            out['texture_values'][key]=t.get_path_name() if t else ''
        except Exception as exc:
            out['texture_values'][key]=f'ERR: {exc}'
except Exception as exc:
    out['error']=str(exc)
path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','inspect_snowtest_landscape_mi_params.json')
os.makedirs(os.path.dirname(path),exist_ok=True)
with open(path,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(path)
