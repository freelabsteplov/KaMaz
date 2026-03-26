import json, os
import unreal

BP = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'


def norm(raw):
    success = None
    strings = []
    if isinstance(raw, tuple):
        for i in raw:
            if isinstance(i, bool):
                success = i
            elif isinstance(i, str):
                strings.append(i)
    elif isinstance(raw, bool):
        success = raw
    elif isinstance(raw, str):
        strings.append(raw)
    if success is None:
        success = True if strings else False
    while len(strings) < 2:
        strings.append('')
    return success, strings[0], strings[1]

success, graph_json, summary = norm(unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, True))
if not success or not graph_json:
    raise RuntimeError(f'inspect failed success={success} summary={summary}')

graph = json.loads(graph_json)
by_path = {n.get('path'): n for n in graph.get('nodes',[]) or []}


def links(node, pin):
    for p in node.get('pins',[]) or []:
        if p.get('name') == pin:
            return list(p.get('linked_to',[]) or [])
    return []

begin = None
for n in graph.get('nodes',[]) or []:
    t = str(n.get('title',''))
    if t == 'Event BeginPlay' or 'BeginPlay' in t:
        begin = n
        break

interesting = []
for n in graph.get('nodes',[]) or []:
    t = str(n.get('title',''))
    if t in ('Set bStartBrakeApplied','Set Handbrake Input','Set Target Gear','Set Brake Input','Set Throttle Input','Set Steering Input','Get VehicleMovementComponent') or 'EnhancedInputAction IA_Handbrake_Digital' in t:
        interesting.append({
            'title': t,
            'path': n.get('path'),
            'pos_x': n.get('pos_x'),
            'pos_y': n.get('pos_y'),
            'defaults': {str(p.get('name')): str(p.get('default_value')) for p in (n.get('pins',[]) or []) if p.get('default_value') not in ('',None)},
            'then_to': [
                {
                    'path': l.get('node_path'),
                    'title': str((by_path.get(l.get('node_path')) or {}).get('title','')),
                    'pin_name': l.get('pin_name')
                }
                for l in links(n,'then')
            ],
            'exec_from': [
                {
                    'path': l.get('node_path'),
                    'title': str((by_path.get(l.get('node_path')) or {}).get('title','')),
                    'pin_name': l.get('pin_name')
                }
                for l in links(n,'execute')
            ],
        })

out = {
    'bp': BP,
    'summary': summary,
    'beginplay': {
        'path': begin.get('path') if begin else '',
        'title': begin.get('title') if begin else '',
        'then_to': [
            {
                'path': l.get('node_path'),
                'title': str((by_path.get(l.get('node_path')) or {}).get('title','')),
                'pin_name': l.get('pin_name')
            }
            for l in (links(begin,'then') if begin else [])
        ],
    },
    'interesting': interesting,
}

p = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_beginplay_chain_audit.json')
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(p)
