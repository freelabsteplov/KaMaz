import json, os
import unreal

BP='/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'


def norm(raw):
    success=None; strings=[]
    if isinstance(raw,tuple):
        for i in raw:
            if isinstance(i,bool): success=i
            elif isinstance(i,str): strings.append(i)
    elif isinstance(raw,bool): success=raw
    elif isinstance(raw,str): strings.append(raw)
    if success is None: success = True if strings else False
    while len(strings)<2: strings.append('')
    return success, strings[0], strings[1]

ok, j, summary = norm(unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP, True, True))
if not ok or not j:
    raise RuntimeError('inspect failed')

graph = json.loads(j)
by_path = {n.get('path'): n for n in graph.get('nodes',[]) or []}


def links(node, pin):
    for p in node.get('pins',[]) or []:
        if p.get('name') == pin:
            return list(p.get('linked_to',[]) or [])
    return []

begin = None
for n in graph.get('nodes',[]) or []:
    if str(n.get('title','')) == 'Event BeginPlay':
        begin = n
        break
if not begin:
    raise RuntimeError('beginplay not found')

# BFS over execution links (then/execute/then pin names)
visited = set()
queue = [(begin.get('path'), 'then', 0)]
trace = []
max_depth = 12
while queue:
    node_path, from_pin, depth = queue.pop(0)
    if depth > max_depth:
        continue
    node = by_path.get(node_path)
    if not node:
        continue
    key = (node_path, depth)
    if key in visited:
        continue
    visited.add(key)

    node_entry = {
        'depth': depth,
        'path': node_path,
        'title': node.get('title'),
        'class': node.get('class'),
        'defaults': {str(p.get('name')): str(p.get('default_value')) for p in (node.get('pins',[]) or []) if p.get('default_value') not in ('', None)},
        'exec_out': []
    }
    for exec_pin in ('then','execute','Completed','Triggered','Started','Canceled','Ongoing','Triggered 1'):
        for l in links(node, exec_pin):
            target_path = l.get('node_path')
            target = by_path.get(target_path)
            node_entry['exec_out'].append({
                'from_pin': exec_pin,
                'to_pin': l.get('pin_name'),
                'to_path': target_path,
                'to_title': str((target or {}).get('title','')),
            })
            if target_path:
                queue.append((target_path, l.get('pin_name'), depth + 1))
    trace.append(node_entry)

out={'bp':BP,'summary':summary,'trace':trace}
p=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','tmp_kamaz_beginplay_exec_trace.json')
os.makedirs(os.path.dirname(p),exist_ok=True)
with open(p,'w',encoding='utf-8') as f: json.dump(out,f,indent=2)
print(p)
