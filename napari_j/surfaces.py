from skimage import exposure, io, measure
import numpy as np

class SurfaceTool:

    def __init__(self, viewer):
        self.viewer = viewer

    def createSurface(self, minValue, maxValue):
        layer = self.viewer.layers.selection.active
        scale = layer.scale
        spacing = (scale[1], scale[2], scale[0])
        rawData = layer.data
        data = np.squeeze(rawData)
        volume = np.logical_and(data >= minValue, data <= maxValue).transpose(1, 2, 0)
        verts, faces, _, values = measure.marching_cubes_lewiner(volume, level=0, spacing=spacing)
        self.viewer.add_surface((verts[:, [2, 0, 1]], faces, np.linspace(0, 1, len(verts))), name='surface of ' + layer.name)
        
        
        
