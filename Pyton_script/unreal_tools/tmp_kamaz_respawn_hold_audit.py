import json
import os
import unreal

BP_PATH = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
OUT_PATH = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_respawn_hold_audit.json')


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


def links_for(node, pin_name):
    for p in node.get('pins', []) or []:
        if p.get('name') == pin_name:
            return list(p.get('linked_to', []) or [])
    return []


result = {
    'bp_path': BP_PATH,
    'summary': '',
    'beginplay_chain_titles': [],
    'input_nodes': {},
    'set_handbrake_nodes': [],
    'set_brake_nodes': [],
    'set_throttle_nodes': [],
    'set_start_brake_var_nodes': [],
    'error': '',
}

try:
    raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP_PATH, True, True)
    success, strings = norm_bridge(raw, 2)
    graph_json, summary = strings
    result['summary'] = summary
    graph = decode_json(graph_json)
    if not success or graph is None:
        raise RuntimeError(f'inspect failed: success={success}, summary={summary}')

    nodes = graph.get('nodes', []) or []
    by_path = {n.get('path'): n for n in nodes if n.get('path')}

    begin = None
    for n in nodes:
        if str(n.get('title', '')) == 'Event BeginPlay':
            begin = n
            break

    chain_titles = []
    if begin:
        visited = set()
        cur = begin
        for _ in range(24):
            cur_path = cur.get('path')
            if not cur_path or cur_path in visited:
                break
            visited.add(cur_path)
            chain_titles.append(str(cur.get('title', '')))
            then_links = links_for(cur, 'then')
            if not then_links:
                break
            nxt_path = then_links[0].get('node_path')
            cur = by_path.get(nxt_path)
            if not cur:
                break
    result['beginplay_chain_titles'] = chain_titles

    input_titles = [
        'EnhancedInputAction IA_Handbrake_Digital',
        'EnhancedInputAction IA_GAZ',
        'EnhancedInputAction IA_TORM',
        'EnhancedInputAction IA_RUL',
        'EnhancedInputAction IA_RESET',
        'EnhancedInputAction IA_Reset',
        'EnhancedInputAction IA_Space',
    ]

    for title in input_titles:
        matches = [n for n in nodes if str(n.get('title', '')) == title]
        items = []
        for n in matches:
            item = {
                'path': n.get('path'),
                'outputs': {},
            }
            for pin in ('Triggered', 'Started', 'Ongoing', 'Canceled', 'Completed'):
                outs = links_for(n, pin)
                if outs:
                    item['outputs'][pin] = [
                        {
                            'node_path': o.get('node_path'),
                            'pin_name': o.get('pin_name'),
                            'node_title': str(by_path.get(o.get('node_path'), {}).get('title', '')),
                        }
                        for o in outs
                    ]
            items.append(item)
        if items:
            result['input_nodes'][title] = items

    for n in nodes:
        title = str(n.get('title', ''))
        if title == 'Set Handbrake Input':
            result['set_handbrake_nodes'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'default_bNewHandbrake': next((p.get('default_value') for p in n.get('pins', []) or [] if p.get('name') == 'bNewHandbrake'), ''),
                'exec_from': [
                    {
                        'node_path': o.get('node_path'),
                        'pin_name': o.get('pin_name'),
                        'node_title': str(by_path.get(o.get('node_path'), {}).get('title', '')),
                    }
                    for o in links_for(n, 'execute')
                ],
                'then_to': [
                    {
                        'node_path': o.get('node_path'),
                        'pin_name': o.get('pin_name'),
                        'node_title': str(by_path.get(o.get('node_path'), {}).get('title', '')),
                    }
                    for o in links_for(n, 'then')
                ],
            })
        elif title == 'Set Brake Input':
            result['set_brake_nodes'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'default_brake': next((p.get('default_value') for p in n.get('pins', []) or [] if p.get('name') == 'Brake'), ''),
                'exec_from_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'execute')],
                'then_to_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'then')],
            })
        elif title == 'Set Throttle Input':
            result['set_throttle_nodes'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'default_throttle': next((p.get('default_value') for p in n.get('pins', []) or [] if p.get('name') == 'Throttle'), ''),
                'exec_from_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'execute')],
                'then_to_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'then')],
            })
        elif title == 'Set bStartBrakeApplied':
            result['set_start_brake_var_nodes'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'default_value': next((p.get('default_value') for p in n.get('pins', []) or [] if p.get('name') == 'bStartBrakeApplied'), ''),
                'exec_from_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'execute')],
                'then_to_titles': [str(by_path.get(o.get('node_path'), {}).get('title', '')) for o in links_for(n, 'then')],
            })

except Exception as exc:
    result['error'] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(OUT_PATH)
