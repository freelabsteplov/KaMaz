import json
import os
import unreal

BP = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
OUT = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_startbrake_var_usage.json')


def norm(raw):
    success = None
    strings = []
    if isinstance(raw, tuple):
        for x in raw:
            if isinstance(x, bool):
                success = x
            elif isinstance(x, str):
                strings.append(x)
    elif isinstance(raw, bool):
        success = raw
    elif isinstance(raw, str):
        strings.append(raw)
    if success is None:
        success = True if strings else False
    while len(strings) < 2:
        strings.append('')
    return bool(success), strings[0], strings[1]

raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, True)
ok, gj, summary = norm(raw)
result = {'bp': BP, 'summary': summary, 'sets': [], 'gets': [], 'error': ''}

try:
    if not ok:
        raise RuntimeError('inspect failed')
    graph = json.loads(gj)
    nodes = graph.get('nodes', []) or []
    by_path = {n.get('path'): n for n in nodes if n.get('path')}

    def links(node, pin):
        for p in node.get('pins', []) or []:
            if p.get('name') == pin:
                return list(p.get('linked_to', []) or [])
        return []

    for n in nodes:
        title = str(n.get('title', ''))
        if title == 'Set bStartBrakeApplied':
            dv = ''
            for p in n.get('pins', []) or []:
                if p.get('name') == 'bStartBrakeApplied':
                    dv = p.get('default_value', '')
                    break
            result['sets'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'default_value': dv,
                'exec_from': [
                    {'title': str(by_path.get(l.get('node_path'), {}).get('title', '')), 'path': l.get('node_path'), 'pin': l.get('pin_name')}
                    for l in links(n, 'execute')
                ],
                'then_to': [
                    {'title': str(by_path.get(l.get('node_path'), {}).get('title', '')), 'path': l.get('node_path'), 'pin': l.get('pin_name')}
                    for l in links(n, 'then')
                ],
            })
        elif title == 'Get bStartBrakeApplied':
            result['gets'].append({
                'path': n.get('path'),
                'pos_x': n.get('pos_x'),
                'pos_y': n.get('pos_y'),
                'linked_to': [
                    {'title': str(by_path.get(l.get('node_path'), {}).get('title', '')), 'path': l.get('node_path'), 'pin': l.get('pin_name')}
                    for l in links(n, 'bStartBrakeApplied')
                ],
            })

except Exception as exc:
    result['error'] = str(exc)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(OUT)
