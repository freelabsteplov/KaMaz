import json, os
import unreal

MAP = '/Game/CityPark/SnowSystem/SnowTest_Level'
ACTOR_LABEL = 'Kamaz_SnowTest'
CLONE_BP = '/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit'
ORIG_BP = '/Game/CityPark/Kamaz/model/KamazBP'

out = {
    'map': MAP,
    'actor_label': ACTOR_LABEL,
    'actor_found': False,
    'actor_path': '',
    'actor_class_path': '',
    'is_clone_actor': False,
    'actor_bStartBrakeApplied': 'NOT_AVAILABLE',
    'clone_class_path': '',
    'orig_class_path': '',
    'clone_cdo_bStartBrakeApplied': 'NOT_AVAILABLE',
    'orig_cdo_bStartBrakeApplied': 'NOT_AVAILABLE',
    'clone_idle_brake_input': 'NOT_AVAILABLE',
    'orig_idle_brake_input': 'NOT_AVAILABLE',
}


def _get_class_path(bp_path):
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        return None, None
    gen = getattr(bp, 'generated_class', None)
    if callable(gen):
        gen = gen()
    if gen is None:
        return bp, None
    return bp, gen


def _get_movement(cdo):
    for c in list(cdo.get_components_by_class(unreal.ActorComponent) or []):
        cp = c.get_class().get_path_name()
        if 'ChaosWheeledVehicleMovementComponent' in cp or 'ChaosVehicleMovementComponent' in cp:
            return c
    return None


unreal.EditorLoadingAndSavingUtils.load_map(MAP)

bp_clone, cls_clone = _get_class_path(CLONE_BP)
bp_orig, cls_orig = _get_class_path(ORIG_BP)
out['clone_class_path'] = cls_clone.get_path_name() if cls_clone else ''
out['orig_class_path'] = cls_orig.get_path_name() if cls_orig else ''

actor = None
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if a.get_actor_label() == ACTOR_LABEL:
        actor = a
        break

if actor:
    out['actor_found'] = True
    out['actor_path'] = actor.get_path_name()
    out['actor_class_path'] = actor.get_class().get_path_name()
    out['is_clone_actor'] = bool(cls_clone and actor.get_class() == cls_clone)
    try:
        out['actor_bStartBrakeApplied'] = bool(actor.get_editor_property('bStartBrakeApplied'))
    except Exception as exc:
        out['actor_bStartBrakeApplied'] = f'ERR: {exc}'

if cls_clone:
    cdo = unreal.get_default_object(cls_clone)
    try:
        out['clone_cdo_bStartBrakeApplied'] = bool(cdo.get_editor_property('bStartBrakeApplied'))
    except Exception as exc:
        out['clone_cdo_bStartBrakeApplied'] = f'ERR: {exc}'
    mv = _get_movement(cdo)
    if mv:
        try:
            out['clone_idle_brake_input'] = float(mv.get_editor_property('idle_brake_input'))
        except Exception as exc:
            out['clone_idle_brake_input'] = f'ERR: {exc}'

if cls_orig:
    cdo = unreal.get_default_object(cls_orig)
    try:
        out['orig_cdo_bStartBrakeApplied'] = bool(cdo.get_editor_property('bStartBrakeApplied'))
    except Exception as exc:
        out['orig_cdo_bStartBrakeApplied'] = f'ERR: {exc}'
    mv = _get_movement(cdo)
    if mv:
        try:
            out['orig_idle_brake_input'] = float(mv.get_editor_property('idle_brake_input'))
        except Exception as exc:
            out['orig_idle_brake_input'] = f'ERR: {exc}'

p = os.path.join(unreal.Paths.project_saved_dir(), 'BlueprintAutomation', 'tmp_inspect_kamaz_respawn_state.json')
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(p)
