import json, os, unreal
MAP='/Game/CityPark/SnowSystem/SnowTest_Level'
out={'map':MAP,'landscapes':[],'roads':[],'error':''}
try:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        cls=a.get_class().get_path_name()
        label=a.get_actor_label()
        path=a.get_path_name()
        if 'Landscape' in cls:
            mats=[]
            try:
                m=a.get_editor_property('landscape_material')
                mats.append(m.get_path_name() if m else '')
            except Exception:
                pass
            out['landscapes'].append({'label':label,'path':path,'class':cls,'materials':sorted(set([x for x in mats if x]))})
        if 'SnowSplineRoadActor' in cls or 'StaticMeshActor' in cls and 'SnowHeight' in label:
            comps=[]
            try:
                for c in a.get_components_by_class(unreal.MeshComponent):
                    mats=[]
                    try:
                        mats=[m.get_path_name() for m in (c.get_materials() or []) if m]
                    except Exception:
                        pass
                    comps.append({'component':c.get_name(),'class':c.get_class().get_path_name(),'materials':mats})
            except Exception:
                pass
            out['roads'].append({'label':label,'path':path,'class':cls,'components':comps})
except Exception as exc:
    out['error']=str(exc)
output=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','snowtest_landscape_road_material_audit.json')
os.makedirs(os.path.dirname(output),exist_ok=True)
with open(output,'w',encoding='utf-8') as f:
    json.dump(out,f,indent=2,ensure_ascii=False)
print(output)
