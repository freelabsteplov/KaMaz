import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


import blueprint_graph_dump_tools as graph_tools


if __name__ == "__main__":
    print(graph_tools.export_plowbrush_drawplowclearance())
