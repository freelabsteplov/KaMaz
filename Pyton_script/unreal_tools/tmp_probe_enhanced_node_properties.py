import unreal, json, os
NODE_PATH = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.BP_VehicleAdvPawnBase:EventGraph.K2Node_EnhancedInputAction_0"
out = {}
obj = None
try:
    obj = unreal.load_object(None, NODE_PATH)
except Exception as e:
    out['load_object_exc'] = str(e)
out['obj_loaded'] = obj is not None
if obj is None and hasattr(unreal, 'find_object'):
    try:
        obj = unreal.find_object(None, NODE_PATH)
    except Exception as e:
        out['find_object_exc'] = str(e)
out['obj_found'] = obj is not None
if obj is not None:
    out['class_path'] = obj.get_class().get_path_name()
    out['name'] = obj.get_name()
    out['all_input_props'] = [p for p in dir(obj) if 'input' in p.lower() or 'action' in p.lower()][:120]
    for pn in ('input_action','InputAction','enhanced_input_action'):
        try:
            val = obj.get_editor_property(pn)
            out[f'prop_{pn}'] = str(val)
        except Exception as e:
            out[f'prop_{pn}_err'] = str(e)

    pins_info = []
    try:
        pins = obj.get_editor_property('pins')
    except Exception:
        pins = []
    for pin in pins:
        entry = {
            'pin_name': str(getattr(pin, 'pin_name', '')),
            'default_object': str(getattr(pin, 'default_object', None)),
            'default_value': str(getattr(pin, 'default_value', '')),
            'direction': str(getattr(pin, 'direction', '')),
        }
        pins_info.append(entry)
    out['pins'] = pins_info

save_dir = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation')
os.makedirs(save_dir, exist_ok=True)
path = os.path.join(save_dir, 'tmp_probe_enhanced_node_properties.json')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(path)
