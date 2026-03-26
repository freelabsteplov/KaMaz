import json
import os
import unreal

BP_PATH = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
TARGET_PATHS = {
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_55',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_56',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_85',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_96',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_DynamicCast_2',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_99',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_100',
    '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_101',
}
OUT_PATH = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_reset_chain_detail.json')


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

out = {'bp': BP_PATH, 'nodes': [], 'error': ''}

try:
    raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP_PATH, True, True)
    success, strings = norm_bridge(raw, 2)
    graph = decode_json(strings[0])
    if not success or graph is None:
        raise RuntimeError('inspect failed')

    by_path = {n.get('path'): n for n in graph.get('nodes', []) or [] if n.get('path')}

    for p in sorted(TARGET_PATHS):
        n = by_path.get(p)
        if not n:
            continue
        pins = []
        for pin in n.get('pins', []) or []:
            links = []
            for l in pin.get('linked_to', []) or []:
                np = l.get('node_path')
                links.append({
                    'node_path': np,
                    'node_title': str(by_path.get(np, {}).get('title', '')),
                    'pin_name': l.get('pin_name'),
                })
            pins.append({
                'name': pin.get('name'),
                'direction': pin.get('direction'),
                'default_value': pin.get('default_value'),
                'links': links,
            })
        out['nodes'].append({
            'path': p,
            'title': n.get('title'),
            'pos_x': n.get('pos_x'),
            'pos_y': n.get('pos_y'),
            'pins': pins,
        })

except Exception as exc:
    out['error'] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(OUT_PATH)
