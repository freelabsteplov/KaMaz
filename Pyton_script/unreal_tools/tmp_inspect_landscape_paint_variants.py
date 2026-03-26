import json, os, unreal
ASSETS=[
 '/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_LandscapePaint',
 '/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_LandscapePaint'
]
out={'items':[]}
mel=unreal.MaterialEditingLibrary
for asset_path in ASSETS:
    item={'asset':asset_path,'class':'','parent_chain':[],'scalar_names':[],'vector_names':[],'texture_names':[],'error':''}
    try:
        a=unreal.EditorAssetLibrary.load_asset(asset_path)
        if not a: raise RuntimeError('load failed')
        item['class']=a.get_class().get_path_name()
        cur=a
        seen=set()
        while cur:
            p=cur.get_path_name()
            if p in seen: break
            seen.add(p)
            item['parent_chain'].append({'name':cur.get_name(),'path':p,'class':cur.get_class().get_path_name()})
            nxt=None
            for prop in ('parent','Parent','ParentEditorOnly'):
                try:
                    nxt=cur.get_editor_property(prop)
                    if nxt: break
                except Exception:
                    pass
            cur=nxt
        try: item['scalar_names']=[str(x) for x in (mel.get_scalar_parameter_names(a) or [])]
        except Exception: pass
        try: item['vector_names']=[str(x) for x in (mel.get_vector_parameter_names(a) or [])]
        except Exception: pass
        try: item['texture_names']=[str(x) for x in (mel.get_texture_parameter_names(a) or [])]
        except Exception: pass
    except Exception as exc:
        item['error']=str(exc)
    out['items'].append(item)
path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','inspect_landscape_paint_variants.json')
os.makedirs(os.path.dirname(path),exist_ok=True)
with open(path,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(path)
