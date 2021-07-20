from jpype import *
import jpype.imports
from jpype.types import *
import numpy as np
import napari
import pandas as pd
from ij.measure import ResultsTable
from ij import IJ, ImagePlus, WindowManager
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

    def screenshot(self):
        screenshot = self.viewer.screenshot(canvas_only=True)
        pixels = JInt[:](list(screenshot[:, :, 0:3].flatten()))
        image = java.awt.image.BufferedImage(screenshot.shape[1], screenshot.shape[0], java.awt.image.BufferedImage.TYPE_3BYTE_BGR)
        image.getRaster().setPixels(0,0,screenshot.shape[1], screenshot.shape[0], pixels)
        title = self.viewer.layers[0].name
        if 'C1-' in title:
            title = title.split('C1-')[1]
        ip = ImagePlus("screenshot of " + title, image)
        ip.show()
       
    def displayPoints(self):
        results = ResultsTable.getResultsTable()
        cal = IJ.getImage().getCalibration()
        headings = list(results.getColumnHeadings().split("\t"))[1:]
        data = {}
        for i in range(0, len(headings)):
            data[headings[i]] = results.getColumn(i)
        results = pd.DataFrame(data=data)
        coords = [[z, y, x] for [x,y,z] in np.delete(results.values,[3], axis=1)]
        zFactor = cal.getZ(1) / cal.getX(1)
        qualities = results['V'].values / 255
        properties = {'confidence' : qualities}
        points_layer = self.viewer.add_points(coords,  properties=properties, 
                                                  face_color='confidence',
                                                  face_colormap='viridis',
                                                  size=3, scale=[zFactor, 1, 1])
                                                  
    def pointsToIJ(self, points):
        sel = [(coords, v) for coords,v in zip(points.data, points.properties['confidence']) if v>0]
        rw = WindowManager.getWindow("Results")
        rw.close(False)
        counter = 0;
        rt = ResultsTable(JObject(JInt(len(sel))));       
        for row in sel:
            rt.setValue("X", counter, row[0][2])
            rt.setValue("Y", counter, row[0][1])
            rt.setValue("Z", counter, row[0][0])
            rt.setValue("V", counter, row[1]*255)
            counter = counter + 1
        rt.show("Results")
