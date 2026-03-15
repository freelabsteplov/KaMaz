import os
import sys


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from material_tools import create_rvt_writer_pair


create_rvt_writer_pair()
