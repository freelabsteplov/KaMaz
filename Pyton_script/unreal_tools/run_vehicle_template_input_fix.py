import importlib
import os
import sys


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import fix_vehicle_template_input_nodes as fix_vehicle_template_input_nodes_module


def run():
    module = importlib.reload(fix_vehicle_template_input_nodes_module)
    return module.fix_vehicle_template_input_nodes()


if __name__ == "__main__":
    print(run())
