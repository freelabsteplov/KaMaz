import json, os
import unreal

def norm(raw, n):
    if isinstance(raw, bool):
        return raw, [""]*n
    success = None
    vals = []
    if isinstance(raw, tuple):
        for i in raw:
            if isinstance(i,bool):
                success = i
            elif isinstance(i,str):
                vals.append(i)
    if success is None:
        raise RuntimeError(f'bad result: {raw!r}')
    while len(vals)<n:
        vals.append("")
    return success, vals[:n]

BP = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase"
raw = unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, False)
ok, (graph_json, summary) = norm(raw, 2)
print('inspect_ok', ok)
print('summary', summary)
if not ok:
    raise SystemExit(1)

obj = json.loads(graph_json)
nodes = obj.get('nodes', [])
none_nodes = [n for n in nodes if 'EnhancedInputAction None' in str(n.get('title',''))]
print('none_nodes', len(none_nodes))

probe = {
    'none_count': len(none_nodes),
    'sample_path': '',
    'load_object_ok': False,
    'find_object_ok': False,
    'node_class': '',
    'prop_candidates': [],
}
if none_nodes:
    p = none_nodes[0].get('path','')
    probe['sample_path'] = p
    node_obj = None
    try:
        node_obj = unreal.load_object(None, p)
    except Exception as e:
        print('load_object_exc', e)
    probe['load_object_ok'] = node_obj is not None

    if node_obj is None and hasattr(unreal, 'find_object'):
        try:
            # signatures vary across versions
            try:
                node_obj = unreal.find_object(None, p)
            except TypeError:
                node_obj = unreal.find_object(name=p)
        except Exception as e:
            print('find_object_exc', e)
    probe['find_object_ok'] = node_obj is not None

    if node_obj is not None:
        probe['node_class'] = node_obj.get_class().get_path_name()
        try:
            probe['prop_candidates'] = [x for x in dir(node_obj) if 'input' in x.lower() or 'action' in x.lower()][:60]
        except Exception:
            pass
        print('node_obj', node_obj)
        print('node_class', probe['node_class'])
        print('props', probe['prop_candidates'])

out_dir = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation')
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, 'tmp_probe_node_access.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(probe, f, indent=2)
print('wrote', out)
