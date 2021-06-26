from jpype import *
import jpype.imports
from jpype.types import *
import numpy as np
import napari
import pandas as pd
from ij.measure import ResultsTable
from ij import IJ, ImagePlus
from ij.plugin import HyperStackConverter

class Bridge:

    def __init__(self, viewer):
        self.viewer = viewer
        
    def getActiveImageFromIJ(self):
        for c in range(0, len(self.viewer.layers)):
            self.viewer.layers.pop(0)
        image = IJ.getImage()
        cal = image.getCalibration()
        zFactor = cal.getZ(1) / cal.getX(1)
        title = image.getShortTitle()
        shift = 128
        bitDepth = image.getBitDepth()
        if bitDepth==16:
            shift = 32768
        dims = list(image.getDimensions())
        isHyperStack = image.isHyperStack()
        HyperStackConverter.toStack(image)
        stackDims = list(image.getDimensions())
        dim = stackDims[3]
        if stackDims[2] == 1 and stackDims[3] == 1 and stackDims[4] > 1:
            dim = dims[4]
        pixels = np.array(image.getStack().getVoxels(0, 0, 0, stackDims[0], stackDims[1], dim, [])) + shift
        if isHyperStack:
            image2 = HyperStackConverter.toHyperStack(image, dims[2], dims[3], dims[4], "Composite");
            image.close()
            image2.show()
        colors = ['magenta', "cyan", "yellow", "red", "green", "blue"]
        for c in range(0, dims[2]):
            self.viewer.add_image(pixels.reshape(dims[4], dims[3], dims[2], dims[1], dims[0])[:, :, c, :, :],
                             name="C" + str(c + 1) + "-" + str(title),
                             colormap=colors[c],
                             blending='additive',
                             scale=[zFactor, 1, 1])
        self.viewer.dims.ndisplay = 3
        
        
