import unreal, json, os
MAP='/Game/CityPark/SnowSystem/SnowTest_Level'
unreal.EditorLoadingAndSavingUtils.load_map(MAP)
actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows=[]
for a in actor_sub.get_all_level_actors():
    label=a.get_actor_label()
    path=a.get_path_name()
    cls=a.get_class().get_name()
    l=label.lower()
    if any(k in l for k in ['kamaz','plow','snowheight','vt_mvp','writer','bridge','snowtestground','snowtest']):
        rows.append({'label':label,'path':path,'class':cls})
rows=sorted(rows,key=lambda r:r['label'])
out={'map':MAP,'count':len(rows),'actors':rows}
out_path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','_tmp_phase6_actor_scan.json')
os.makedirs(os.path.dirname(out_path),exist_ok=True)
with open(out_path,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(out)
