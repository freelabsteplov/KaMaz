import json
import os
import unreal

BP_PATH = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
MATERIAL_PATH = '/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP'
OUT_PATH = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'fix_kamaz_startbrake_release_path_and_nanite.json')

# Known node paths in current BP graph
NODE_IA_HANDBRAKE = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_EnhancedInputAction_13'
NODE_SET_HANDBRAKE_TRUE = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_13'
NODE_SET_THROTTLEVALUE = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_19'
NODE_SET_BRAKEVALUE = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_21'
NODE_SET_BRAKE_INPUT_MAIN = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_1'
NODE_SET_STEERING_RESET = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_56'
NODE_SET_BRAKE_RESET_ZERO = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_85'
NODE_SET_HANDBRAKE_RESET_TRUE = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_96'


def norm_bridge(raw, expected=2):
    success = None
    strings = []
    if isinstance(raw, tuple):
        for item in raw:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
    elif isinstance(raw, bool):
        success = raw
    elif isinstance(raw, str):
        strings.append(raw)
    if success is None:
        success = True if strings else False
    while len(strings) < expected:
        strings.append('')
    return bool(success), strings[:expected]


def decode_json(payload):
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def apply_graph_batch(bp_path, batch):
    raw = unreal.BlueprintAutomationPythonBridge.apply_graph_batch_json(bp_path, json.dumps(batch, ensure_ascii=False))
    success, strings = norm_bridge(raw, 2)
    payload_json, summary = strings
    return {
        'success': bool(success),
        'summary': summary,
        'payload': decode_json(payload_json),
    }


def compile_bp(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.compile_blueprint(bp_path)
    success, strings = norm_bridge(raw, 2)
    report_json, summary = strings
    report = decode_json(report_json)
    ok = bool(success)
    if isinstance(report, dict) and int(report.get('num_errors', 0) or 0) > 0:
        ok = False
    return ok, summary, report


def save_bp(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.save_blueprint(bp_path)
    success, strings = norm_bridge(raw, 1)
    return bool(success), strings[0]


result = {
    'bp_path': BP_PATH,
    'material_path': MATERIAL_PATH,
    'graph_patch': {},
    'bp_compile': {},
    'bp_save': {},
    'material_fix': {
        'found': False,
        'property_set': False,
        'saved': False,
        'errors': [],
    },
    'error': '',
}

try:
    # 1) Patch BP graph with a narrow, deterministic fix:
    # - release start-brake only via explicit IA_Handbrake_Digital trigger
    # - bypass axis auto-release branch path
    # - keep reset chain brake held before handbrake/sleep (skip node that forces Brake=0)
    batch = {
        'nodes': [
            {
                'id': 'set_start_brake_false_on_handbrake_trigger',
                'type': 'variable_set',
                'variable': 'bStartBrakeApplied',
                'x': -11296,
                'y': -8464,
                'pin_defaults': [
                    {'pin': 'bStartBrakeApplied', 'default_value': 'false'}
                ],
            }
        ],
        'links': [
            {
                'from_node_path': NODE_IA_HANDBRAKE,
                'from_pin': 'Triggered',
                'to_node': 'set_start_brake_false_on_handbrake_trigger',
                'to_pin': 'execute',
            },
            {
                'from_node': 'set_start_brake_false_on_handbrake_trigger',
                'from_pin': 'then',
                'to_node_path': NODE_SET_HANDBRAKE_TRUE,
                'to_pin': 'execute',
            },
            {
                'from_node_path': NODE_SET_THROTTLEVALUE,
                'from_pin': 'then',
                'to_node_path': NODE_SET_BRAKE_INPUT_MAIN,
                'to_pin': 'execute',
            },
            {
                'from_node_path': NODE_SET_BRAKEVALUE,
                'from_pin': 'then',
                'to_node_path': NODE_SET_BRAKE_INPUT_MAIN,
                'to_pin': 'execute',
            },
            {
                'from_node_path': NODE_SET_STEERING_RESET,
                'from_pin': 'then',
                'to_node_path': NODE_SET_HANDBRAKE_RESET_TRUE,
                'to_pin': 'execute',
            }
        ],
        'execution_chains': [],
    }

    apply_res = apply_graph_batch(BP_PATH, batch)
    result['graph_patch'] = apply_res
    if not apply_res.get('success'):
        raise RuntimeError(f"Graph patch failed: {apply_res.get('summary')}")

    compile_ok, compile_summary, compile_report = compile_bp(BP_PATH)
    result['bp_compile'] = {
        'success': compile_ok,
        'summary': compile_summary,
        'report': compile_report,
    }
    if not compile_ok:
        raise RuntimeError(f'Blueprint compile failed: {compile_summary}')

    save_ok, save_summary = save_bp(BP_PATH)
    result['bp_save'] = {
        'success': save_ok,
        'summary': save_summary,
    }
    if not save_ok:
        raise RuntimeError(f'Blueprint save failed: {save_summary}')

    # 2) Re-apply Nanite usage flag on receiver material and save
    mat = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
    result['material_fix']['found'] = bool(mat)
    if not mat:
        raise RuntimeError(f'Material not found: {MATERIAL_PATH}')

    for prop in ('used_with_nanite', 'b_used_with_nanite', 'bUsedWithNanite'):
        try:
            mat.set_editor_property(prop, True)
            result['material_fix']['property_set'] = True
            break
        except Exception:
            continue

    if not result['material_fix']['property_set']:
        result['material_fix']['errors'].append('Failed to set any Nanite usage property name on material.')

    try:
        unreal.MaterialEditingLibrary.recompile_material(mat)
    except Exception as exc:
        result['material_fix']['errors'].append(f'recompile_failed:{exc}')

    try:
        result['material_fix']['saved'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mat, False))
    except Exception as exc:
        result['material_fix']['errors'].append(f'save_failed:{exc}')

except Exception as exc:
    result['error'] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(OUT_PATH)
