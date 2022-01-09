""" The NapariJ-plugin connects napari and ImageJ (both ways). Napari
(and python) accesses ImageJ via jpype. ImageJ can access napari and
python via the jupyter-client.

The plugin has the following features:
- start FIJI
- get the active image (hyperstack) from FIJI with each channel being a layer in napari
- send a snapshot from napari to FIJI
- use FIJI to detect spots, display and filter spots in napari, send the filtered spots back to FIJI
"""

from napari_plugin_engine import napari_hook_implementation
from .connection import Connection
from .image import Image
from .points import Points


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [Connection, Image, Points]
