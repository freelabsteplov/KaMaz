import json, os, unreal
ASSET='/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape_SoftSeam'
out={'asset':ASSET,'exists':False,'scalar_values':{},'error':''}
try:
    a=unreal.EditorAssetLibrary.load_asset(ASSET)
    out['exists']=bool(a)
    if a:
        mel=unreal.MaterialEditingLibrary
        for name in ['SnowTexUVScale','HeightAmplitude','EdgeRaiseAmplitude','HeightContrast','EdgeSharpness']:
            out['scalar_values'][name]=float(mel.get_material_instance_scalar_parameter_value(a,name))
except Exception as exc:
    out['error']=str(exc)
path=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','inspect_snowtest_landscape_soft_seam_values.json')
os.makedirs(os.path.dirname(path),exist_ok=True)
with open(path,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(path)
