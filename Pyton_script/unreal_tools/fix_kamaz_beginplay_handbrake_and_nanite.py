import json
import os
import unreal

BP_PATH = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
MAP_PATH = '/Game/CityPark/SnowSystem/SnowTest_Level'
MATERIAL_PATH = '/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP'
OUT_PATH = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'fix_kamaz_beginplay_handbrake_and_nanite.json')


# --- helpers ---
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


def inspect_event_graph(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(bp_path, True, True)
    success, strings = norm_bridge(raw, 2)
    graph_json, summary = strings
    if not success and not graph_json:
        raise RuntimeError(f'inspect failed: {summary}')
    graph = decode_json(graph_json)
    if graph is None:
        raise RuntimeError(f'failed to decode graph json: {summary}')
    return graph


def apply_graph_batch(bp_path, batch):
    raw = unreal.BlueprintAutomationPythonBridge.apply_graph_batch_json(bp_path, json.dumps(batch, ensure_ascii=False))
    success, strings = norm_bridge(raw, 2)
    apply_json, summary = strings
    return {
        'success': bool(success),
        'summary': summary,
        'payload': decode_json(apply_json),
    }


def compile_bp(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.compile_blueprint(bp_path)
    success, strings = norm_bridge(raw, 2)
    report_json, summary = strings
    report = decode_json(report_json)
    compile_ok = bool(success)
    if isinstance(report, dict):
        if int(report.get('num_errors', 0) or 0) > 0:
            compile_ok = False
    return compile_ok, summary, report


def save_bp(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.save_blueprint(bp_path)
    success, strings = norm_bridge(raw, 1)
    return bool(success), strings[0]


def find_links(node, pin_name):
    for p in node.get('pins', []) or []:
        if p.get('name') == pin_name:
            return list(p.get('linked_to', []) or [])
    return []


result = {
    'bp_path': BP_PATH,
    'material_path': MATERIAL_PATH,
    'beginplay_fix': {
        'applied': False,
        'already_present': False,
        'details': '',
        'apply': {},
    },
    'bp_compile': {},
    'bp_save': {},
    'material_fix': {
        'found': False,
        'usage_set': False,
        'property_set': False,
        'recompiled': False,
        'saved': False,
        'errors': [],
    },
    'level_saved': False,
    'error': '',
}

try:
    # --- patch BeginPlay handbrake ---
    graph = inspect_event_graph(BP_PATH)
    nodes_by_path = {n.get('path'): n for n in graph.get('nodes', []) or []}

    begin = None
    for n in graph.get('nodes', []) or []:
        if str(n.get('title', '')) == 'Event BeginPlay':
            begin = n
            break
    if begin is None:
        raise RuntimeError('Event BeginPlay not found')

    begin_then = find_links(begin, 'then')
    if not begin_then:
        raise RuntimeError('BeginPlay then link missing')

    n_gear = nodes_by_path.get(begin_then[0].get('node_path'))
    if not n_gear or str(n_gear.get('title')) != 'Set Target Gear':
        raise RuntimeError('Unexpected BeginPlay first node (expected Set Target Gear)')

    n_map = nodes_by_path.get((find_links(n_gear, 'then') or [{}])[0].get('node_path'))
    n_throttle = nodes_by_path.get((find_links(n_map, 'then') or [{}])[0].get('node_path')) if n_map else None
    n_print = nodes_by_path.get((find_links(n_throttle, 'then') or [{}])[0].get('node_path')) if n_throttle else None
    n_brake = nodes_by_path.get((find_links(n_print, 'then') or [{}])[0].get('node_path')) if n_print else None
    n_start = nodes_by_path.get((find_links(n_brake, 'then') or [{}])[0].get('node_path')) if n_brake else None

    if not (n_map and n_throttle and n_print and n_brake and n_start):
        raise RuntimeError('Failed to resolve BeginPlay startup chain nodes')

    if str(n_brake.get('title')) != 'Set Brake Input' or str(n_start.get('title')) != 'Set bStartBrakeApplied':
        raise RuntimeError('BeginPlay chain shape mismatch around brake/start brake nodes')

    next_after_start_link = (find_links(n_start, 'then') or [{}])[0]
    next_after_start_path = next_after_start_link.get('node_path')
    next_after_start_node = nodes_by_path.get(next_after_start_path)

    # Already patched if immediate next node is Set Handbrake Input(true)
    already = False
    if next_after_start_node and str(next_after_start_node.get('title')) == 'Set Handbrake Input':
        for p in next_after_start_node.get('pins', []) or []:
            if p.get('name') == 'bNewHandbrake':
                already = str(p.get('default_value', '')).lower() in ('true', '1', '1.0')
                break

    result['beginplay_fix']['already_present'] = already

    if not already:
        # Source for self pin: whatever currently feeds BeginPlay Set Brake Input self pin.
        self_links = find_links(n_brake, 'self')
        if not self_links:
            raise RuntimeError('BeginPlay Set Brake Input has no self link to movement component')
        movement_get_path = self_links[0].get('node_path')
        movement_get_pin = self_links[0].get('pin_name') or 'ReturnValue'

        start_pos_x = int(n_start.get('pos_x') or 0)
        start_pos_y = int(n_start.get('pos_y') or 0)

        batch = {
            'nodes': [
                {
                    'id': 'beginplay_set_handbrake_true',
                    'type': 'call_function',
                    'function_path': '/Script/ChaosVehicles.ChaosVehicleMovementComponent:SetHandbrakeInput',
                    'x': start_pos_x + 384,
                    'y': start_pos_y,
                    'pin_defaults': [
                        {'pin': 'bNewHandbrake', 'default_value': 'true'}
                    ],
                }
            ],
            'links': [
                {
                    'from_node_path': n_start.get('path'),
                    'from_pin': 'then',
                    'to_node': 'beginplay_set_handbrake_true',
                    'to_pin': 'execute',
                },
                {
                    'from_node_path': movement_get_path,
                    'from_pin': movement_get_pin,
                    'to_node': 'beginplay_set_handbrake_true',
                    'to_pin': 'self',
                },
                {
                    'from_node': 'beginplay_set_handbrake_true',
                    'from_pin': 'then',
                    'to_node_path': next_after_start_path,
                    'to_pin': 'execute',
                },
            ],
            'execution_chains': [],
        }

        apply_res = apply_graph_batch(BP_PATH, batch)
        result['beginplay_fix']['apply'] = apply_res
        if not apply_res.get('success'):
            raise RuntimeError(f"BeginPlay handbrake patch failed: {apply_res.get('summary')}")
        result['beginplay_fix']['applied'] = True
        result['beginplay_fix']['details'] = 'Inserted SetHandbrakeInput(true) after BeginPlay Set bStartBrakeApplied.'
    else:
        result['beginplay_fix']['details'] = 'BeginPlay already includes SetHandbrakeInput(true) after start brake set.'

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

    # --- fix material nanite usage flag ---
    mat = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
    result['material_fix']['found'] = bool(mat)
    if not mat:
        raise RuntimeError(f'Material not found: {MATERIAL_PATH}')

    usage_enum = None
    mu = getattr(unreal, 'MaterialUsage', None)
    if mu:
        for name in dir(mu):
            if name.lower() == 'matusage_nanite':
                usage_enum = getattr(mu, name)
                break
        if usage_enum is None:
            for name in dir(mu):
                if 'nanite' in name.lower():
                    usage_enum = getattr(mu, name)
                    break

    if usage_enum is not None:
        try:
            usage_result = unreal.MaterialEditingLibrary.set_material_usage(mat, usage_enum)
            if isinstance(usage_result, tuple):
                result['material_fix']['usage_set'] = bool(usage_result[0])
            else:
                result['material_fix']['usage_set'] = bool(usage_result)
        except Exception as exc:
            result['material_fix']['errors'].append(f'set_material_usage_failed:{exc}')

    for prop in ('used_with_nanite', 'b_used_with_nanite', 'bUsedWithNanite'):
        try:
            mat.set_editor_property(prop, True)
            result['material_fix']['property_set'] = True
            break
        except Exception:
            continue

    try:
        unreal.MaterialEditingLibrary.recompile_material(mat)
        result['material_fix']['recompiled'] = True
    except Exception as exc:
        result['material_fix']['errors'].append(f'recompile_failed:{exc}')

    try:
        result['material_fix']['saved'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mat, False))
    except Exception as exc:
        result['material_fix']['errors'].append(f'save_failed:{exc}')

    # persist current level state too (actor instance remains in clone)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    result['level_saved'] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())

except Exception as exc:
    result['error'] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(OUT_PATH)
