import json, os
import unreal

BP = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
TAGS = ['ResetVehicle','Set Target Gear','Set Brake Input','Set Throttle Input','Set Steering Input','Set Handbrake Input','Set bStartBrakeApplied','EnhancedInputAction IA_Handbrake_Digital','EnhancedInputAction IA_GAZ','EnhancedInputAction IA_TORM','EnhancedInputAction IA_RUL']

raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, False)
success = False
strings = []
if isinstance(raw, tuple):
    for it in raw:
        if isinstance(it, bool):
            success = it
        elif isinstance(it, str):
            strings.append(it)
elif isinstance(raw, bool):
    success = raw

if not success:
    raise RuntimeError(f'inspect failed: {raw}')

graph_json = strings[0] if strings else ''
summary = strings[1] if len(strings) > 1 else ''
graph = json.loads(graph_json)

hits = []
for n in graph.get('nodes', []) or []:
    title = str(n.get('title',''))
    if not any(t in title for t in TAGS):
        continue
    pin_defaults = {}
    for p in n.get('pins', []) or []:
        dv = p.get('default_value', '')
        if dv not in ('', None):
            pin_defaults[str(p.get('name',''))] = str(dv)
    hits.append({
        'title': title,
        'path': n.get('path'),
        'class': n.get('class'),
        'pos_x': n.get('pos_x'),
        'pos_y': n.get('pos_y'),
        'pin_defaults': pin_defaults,
    })

out = {'bp': BP, 'summary': summary, 'hit_count': len(hits), 'hits': hits}

p = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_kamaz_handbrake_graph_nodes.json')
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(p)
