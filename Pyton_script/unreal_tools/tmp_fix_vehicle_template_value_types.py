import json, os
import unreal

bp = '/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase'
actions = [
    '/Game/VehicleTemplate/Input/Actions/IA_Throttle',
    '/Game/VehicleTemplate/Input/Actions/IA_Brake',
    '/Game/VehicleTemplate/Input/Actions/IA_Steering',
]

result = {'actions': [], 'compile': {}, 'save_bp': ''}
for path in actions:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    item = {'path': path, 'loaded': asset is not None}
    if asset is not None:
        before = str(asset.get_editor_property('value_type'))
        asset.set_editor_property('value_type', unreal.InputActionValueType.BOOLEAN)
        after = str(asset.get_editor_property('value_type'))
        saved = unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        item.update({'before': before, 'after': after, 'saved': bool(saved)})
    result['actions'].append(item)

raw_compile = unreal.BlueprintAutomationPythonBridge.compile_blueprint(bp)
if isinstance(raw_compile, tuple):
    strings = [x for x in raw_compile if isinstance(x, str)]
    report_json = strings[0] if len(strings) > 0 else ''
    summary = strings[1] if len(strings) > 1 else ''
else:
    report_json = ''
    summary = str(raw_compile)

result['compile']['summary'] = summary
result['compile']['report_json'] = report_json
try:
    result['compile']['report'] = json.loads(report_json) if report_json else {}
except Exception as exc:
    result['compile']['report_parse_error'] = str(exc)

raw_save = unreal.BlueprintAutomationPythonBridge.save_blueprint(bp)
result['save_bp'] = str(raw_save)

out = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_fix_vehicle_template_value_types.json')
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(out)
