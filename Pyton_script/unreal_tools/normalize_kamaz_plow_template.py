import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from normalize_plow_writer_defaults import run_kamaz_template


if __name__ == "__main__":
    print(json.dumps(run_kamaz_template(), indent=2, ensure_ascii=False))
