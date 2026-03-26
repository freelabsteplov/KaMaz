import json, os, unreal
BP='/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
OUT=os.path.join(unreal.Paths.project_saved_dir(),'BlueprintAutomation','tmp_kamaz_brake_nodes_detail.json')
TARGETS={
'/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_1',
'/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_16',
'/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_42',
'/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit.KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_15'}

def norm(raw):
 s=None; arr=[]
 if isinstance(raw,tuple):
  for x in raw:
   if isinstance(x,bool): s=x
   elif isinstance(x,str): arr.append(x)
 elif isinstance(raw,bool): s=raw
 elif isinstance(raw,str): arr.append(raw)
 if s is None: s=True if arr else False
 while len(arr)<2: arr.append('')
 return bool(s),arr
ok,arr=norm(unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph(BP,True,True))
res={'error':'','nodes':[]}
try:
 if not ok: raise RuntimeError('inspect failed')
 g=json.loads(arr[0]); by={n.get('path'):n for n in g.get('nodes',[]) if n.get('path')}
 for p in sorted(TARGETS):
  n=by.get(p)
  if not n: continue
  e={'path':p,'title':n.get('title'),'pins':[]}
  for pin in n.get('pins',[]) or []:
   links=[{'path':l.get('node_path'),'title':str(by.get(l.get('node_path'),{}).get('title','')),'pin':l.get('pin_name')} for l in pin.get('linked_to',[]) or []]
   if links or pin.get('default_value'):
    e['pins'].append({'name':pin.get('name'),'default':pin.get('default_value'),'links':links})
  res['nodes'].append(e)
except Exception as ex:
 res['error']=str(ex)
os.makedirs(os.path.dirname(OUT),exist_ok=True)
open(OUT,'w',encoding='utf-8').write(json.dumps(res,indent=2))
print(OUT)
