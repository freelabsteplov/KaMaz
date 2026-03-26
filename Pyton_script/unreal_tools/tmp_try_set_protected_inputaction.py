import unreal, json, os
bp = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase"
node_path = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.BP_VehicleAdvPawnBase:EventGraph.K2Node_EnhancedInputAction_0"
ia = unreal.EditorAssetLibrary.load_asset('/Game/VehicleTemplate/Input/Actions/IA_Throttle')
node = unreal.load_object(None, node_path)
out = {'node_ok': node is not None, 'ia_ok': ia is not None}
if node and ia:
    try:
        node.set_editor_property('InputAction', ia)
        out['set_editor_property'] = 'ok'
    except Exception as e:
        out['set_editor_property'] = str(e)
    try:
        node.set_editor_properties({'InputAction': ia})
        out['set_editor_properties'] = 'ok'
    except Exception as e:
        out['set_editor_properties'] = str(e)
    try:
        node.call_method('ReconstructNode')
        out['call_reconstruct'] = 'ok'
    except Exception as e:
        out['call_reconstruct'] = str(e)

# compile report
raw = unreal.BlueprintAutomationPythonBridge.compile_blueprint(bp)
out['compile_raw_type'] = str(type(raw))
out['compile_raw'] = str(raw)[:1200]
# save
raw_save = unreal.BlueprintAutomationPythonBridge.save_blueprint(bp)
out['save_raw'] = str(raw_save)

path = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_try_set_protected_inputaction.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(path)
