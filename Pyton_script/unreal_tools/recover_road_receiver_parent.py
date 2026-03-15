import importlib
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra


def main():
    prsra = importlib.reload(prsra)
    result = prsra.reparent_material_instance(
        "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test",
        "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver",
    )
    unreal.log(f"[recover_road_receiver_parent] {result}")


if __name__ == "__main__":
    main()
