import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_snow_road_materials.json",
)


def get_parent_chain(material_interface):
    chain = []
    current = material_interface
    while current:
        chain.append(
            {
                "name": current.get_name(),
                "path": current.get_path_name(),
                "class": current.get_class().get_path_name(),
            }
        )
        if isinstance(current, unreal.MaterialInstance):
            current = current.parent
        else:
            break
    return chain


def inspect_material_interface(material_interface):
    data = {
        "name": material_interface.get_name(),
        "path": material_interface.get_path_name(),
        "class": material_interface.get_class().get_path_name(),
        "parent_chain": get_parent_chain(material_interface),
        "scalar_values": {},
        "vector_values": {},
        "texture_values": {},
    }

    if isinstance(material_interface, unreal.MaterialInstanceConstant):
        for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material_interface):
            data["scalar_values"][str(name)] = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                material_interface, name
            )
        for name in unreal.MaterialEditingLibrary.get_vector_parameter_names(material_interface):
            data["vector_values"][str(name)] = str(
                unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material_interface, name)
            )
        for name in unreal.MaterialEditingLibrary.get_texture_parameter_names(material_interface):
            texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
                material_interface, name
            )
            data["texture_values"][str(name)] = texture.get_path_name() if texture else None
    elif isinstance(material_interface, unreal.MaterialInstanceDynamic):
        parent = material_interface.parent
        data["dynamic_parent"] = parent.get_path_name() if parent else None

    return data


result = {
    "map": MAP_PATH,
    "roads": [],
    "error": "",
}

try:
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)

    for actor in actors:
        if not actor.get_class().get_name().startswith("SnowSplineRoadActor"):
            continue

        road_info = {
            "label": actor.get_actor_label(),
            "path": actor.get_path_name(),
            "components": [],
        }

        for component in actor.get_components_by_class(unreal.SplineMeshComponent):
            materials = []
            for index in range(component.get_num_materials()):
                material = component.get_material(index)
                if material:
                    materials.append(inspect_material_interface(material))

            road_info["components"].append(
                {
                    "component": component.get_name(),
                    "materials": materials,
                }
            )

        result["roads"].append(road_info)
except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
    json.dump(result, output_file, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))
