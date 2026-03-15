import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


import inspect_material_graph as material_graph_tools


if __name__ == "__main__":
    print(
        material_graph_tools.inspect_material_graph(
            "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush"
        )
    )
