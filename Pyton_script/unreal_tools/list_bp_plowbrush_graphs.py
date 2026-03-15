import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


import blueprint_graph_dump_tools as graph_tools


OUTPUT_PATH = os.path.join(
    "C:\\Users\\post\\Documents\\Unreal Projects\\Kamaz_Cleaner\\Saved\\BlueprintAutomation",
    "bp_plowbrush_graphs.json",
)


if __name__ == "__main__":
    payload = graph_tools.list_graphs("/Game/CityPark/SnowSystem/BP_PlowBrush_Component")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(OUTPUT_PATH)
