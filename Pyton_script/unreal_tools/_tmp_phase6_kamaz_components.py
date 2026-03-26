import unreal, json, os
MAP='/Game/CityPark/SnowSystem/SnowTest_Level'
LABEL='Kamaz_SnowTest'
unreal.EditorLoadingAndSavingUtils.load_map(MAP)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actor=None
for a in sub.get_all_level_actors():
    if a.get_actor_label()==LABEL:
        actor=a
        break
out={'map':MAP,'actor_label':LABEL,'found':actor is not None,'components':[]}
if actor:
    for c in actor.get_components_by_class(unreal.ActorComponent):
        try:
            cls=c.get_class().get_name()
            path=c.get_path_name()
            name=c.get_name()
            info={'name':name,'class':cls,'path':path}
            if isinstance(c,unreal.SceneComponent):
                info['world_location']=str(c.get_world_location())
                info['world_rotation']=str(c.get_world_rotation())
            out['components'].append(info)
        except Exception as e:
            out['components'].append({'error':str(e)})
out['components']=sorted(out['components'],key=lambda x:x.get('name',''))
out_path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','_tmp_phase6_kamaz_components.json')
os.makedirs(os.path.dirname(out_path),exist_ok=True)
with open(out_path,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(out)
