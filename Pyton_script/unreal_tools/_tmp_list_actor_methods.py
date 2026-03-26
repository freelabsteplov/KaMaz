import json
import unreal

MAP = "/Game/CityPark/SnowSystem/SnowTest_Level"

unreal.EditorLoadingAndSavingUtils.load_map(MAP)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
target = None
for actor in actors:
    if actor.get_actor_label() == "Kamaz_SnowTest":
        target = actor
        break

if not target:
    raise RuntimeError("Kamaz actor not found")

    methods = sorted(dir(target))
payload = {
    "actor_label": target.get_actor_label(),
    "path": target.get_path_name(),
    "methods": methods,
}

path = unreal.Paths.project_saved_dir() + "/BlueprintAutomation/_tmp_actor_methods.json"
unreal.log(f"[tmp] wrote {path}")
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
