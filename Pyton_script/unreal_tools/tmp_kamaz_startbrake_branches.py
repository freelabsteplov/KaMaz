import json
import os
import unreal

BP = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
TARGETS = {
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_IfThenElse_15',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_IfThenElse_16',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_19',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_21',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_25',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_26',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_EnhancedInputAction_1',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_EnhancedInputAction_2',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_VariableGet_9',
}
OUT = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_startbrake_branches.json')


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
    return bool(success), strings

raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, True)
ok, strings = norm(raw)
result = {'error': '', 'nodes': []}

try:
    if not ok:
        raise RuntimeError('inspect failed')
    graph = json.loads(strings[0])
    nodes = graph.get('nodes', []) or []
    by_path = {n.get('path'): n for n in nodes if n.get('path')}

    for p in sorted(TARGETS):
        n = by_path.get(p)
        if not n:
            continue
        entry = {
            'path': p,
            'title': n.get('title'),
            'pos': [n.get('pos_x'), n.get('pos_y')],
            'pins': []
        }
        for pin in n.get('pins', []) or []:
            ln = []
            for l in pin.get('linked_to', []) or []:
                np = l.get('node_path')
                ln.append({'path': np, 'title': str(by_path.get(np, {}).get('title', '')), 'pin': l.get('pin_name')})
            if ln or pin.get('default_value'):
                entry['pins'].append({'name': pin.get('name'), 'default': pin.get('default_value'), 'links': ln})
        result['nodes'].append(entry)

except Exception as exc:
    result['error'] = str(exc)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(OUT)
