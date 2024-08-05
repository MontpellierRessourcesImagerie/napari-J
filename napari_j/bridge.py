import yaml
import pandas as pd
from os import listdir
from os.path import isfile, join
from jpype import *
import jpype.imports
from jpype.types import *
import numpy as np
from ij.measure import ResultsTable
from ij import IJ, ImagePlus, WindowManager
from ij.plugin import HyperStackConverter
from napari.utils.colormaps import * 
from napari.utils.colormaps.colormap_utils import * 
from vispy.color import Colormap, get_colormap
from .config import Config


class Bridge:
    """
        The Bridge allows napari to communicate with ImageJ.
    """
    colors = ['magenta', 'cyan', 'yellow', 'red', 'green', 'blue', 'orange', 'brown', 'white']

    def __init__(self, viewer):
        """
        The constructor creates a new Bridge-object. 

        Parameters
        ----------
        viewer : napari.viewer.Viewer
            The napari-viewer instance that will communicate with ImageJ.

        Returns
        -------
        None.
        """
        self.viewer = viewer

    def getActiveImageFromIJ(self):
        """
        Removes all layers from the viewer. Gets the active image from ImageJ
        and add it's channels as image-layers to the viewer.
        
        Returns
        -------
        None.
        """
        for c in range(0, len(self.viewer.layers)):
            self.viewer.layers.pop(0)
        title, dims, voxelSize, unit, pixels = self.getPixelsFromImageJ()
        if dims[3]==1:
            voxelSize = (voxelSize[1], voxelSize[2])
        for c in range(0, dims[2]):
            data = pixels.reshape(
                    dims[4], dims[3], dims[2], dims[1], dims[0])[:, :, c, :, :]
            while data.shape[0] == 1:
                data = np.squeeze(data, axis=0)    
            self.viewer.add_image(
                data, 
                name = "C" + str(c + 1) + "-" + str(title),
                colormap = self.colors[c],
                blending = 'additive',
                scale = voxelSize)
        self.viewer.scale_bar.unit = unit
        self.viewer.dims.ndisplay = 3

    def getLabelsFromIJ(self):
        """
        Adds the active image in ImageJ as a new labels-layer to the viewer.

        Returns
        -------
        None.
        """
        title, dims, voxelSize, unit, pixels = self.getPixelsFromImageJ()
        if dims[3] == 1:
            voxelSize = (voxelSize[1], voxelSize[2])
        data = pixels.reshape(
            dims[4], dims[3], dims[2], dims[1], dims[0])[:, :, 0, :, :].astype(int)
        while data.shape[0] == 1:
            data = np.squeeze(data, axis=0)
        self.viewer.add_labels(data, name=str(title), scale=voxelSize)
        self.viewer.scale_bar.unit = unit

    def getSurfacesFromIJ(self):
        from eu.kiaru.limeseg import LimeSeg
        from eu.kiaru.limeseg.struct import Cell
        vertices = np.array([])
        norms = np.array([])
        for c in LimeSeg.allCells:
            LimeSeg.currentCell = c
            for dot in c.dots:
                vector = np.array([dot.pos.z, dot.pos.y, dot.pos.x])
                np.append(vertices, vector)
                normVector = np.array([dot.Norm.z, dot.Norm.y, dot.Norm.x])
                np.append(norms, normVector)
        print(vertices)
        print(norms)

    def getPixelsFromImageJ(self):
        """
        Get the title, dimensions, zFactor and pixel data from the active 
        image in ImageJ. The pixel data is returned as a linear list. Use
        
        pixels.reshape(dims[4], dims[3], dims[2], dims[1], dims[0])
        
        to get an image with the right order of dimensions for python.

        Returns
        -------
        title : java.lang.String
            The title of the image.
        dims : list
            A list [x,y,c,z,t] of the size in each dimension of the image.
        voxelSize : list
            A list of the voxel sizes in the order z, y, x.
        unit : string
            The unit string, for example nm, micrometer or cm.
        pixels : numpy.ndarray
            The pixel data of the active image in ImageJ as a linear list.
        """
        image = IJ.getImage()
        title, dims, voxelSize, unit, size = self.getMetadataFromImage(image)
        isHyperStack = image.isHyperStack()
        HyperStackConverter.toStack(image)
        stackDims = list(image.getDimensions())
        dim = stackDims[3]
        if stackDims[2] == 1 and stackDims[3] == 1 and stackDims[4] > 1:
            dim = dims[4]
        if size <= 2147483647: #(2^31)-1
                pixels = np.array(image.getStack().getVoxels(0, 0, 0, stackDims[0], stackDims[1], dim, []))
        else:
                ia = image.getStack().getImageArray()
                ia = list(filter(None, ia))
                pixels = np.array(ia)
        if isHyperStack:
            self.toHyperstack(image, dims)
        bitDepth = image.getBitDepth();
        if bitDepth == 8:
            pixels = pixels.astype(np.uint8)
        if bitDepth == 16:
            pixels = pixels.astype(np.uint16)
            
        return title, dims, voxelSize, unit, pixels
    
    def getMetadataFromImage(self, image):
        """
        Get the metadata from the ImageJ image.

        Parameters
        ----------
        image : ij.ImagePlus
            The image from which the metadata is extracted.

        Returns
        -------
        title : java.lang.String
            The short-title of the image.
        dims : list
            A list [x,y,c,z,t] of the size in each dimension of the image. 
        voxelSize : list
            A list of the voxel sizes in the order z, y, x.
        unit : string
            The unit string, for example nm, micrometer or cm.
        size : int
            The size of one channel of the image
        """
        dims = list(image.getDimensions())
        size = dims[0] * dims[1] * dims[3] * dims[4]
        cal = image.getCalibration()
        voxelSize = [cal.getZ(1), cal.getY(1), cal.getX(1)]
        unit = str(cal.getUnit())
        title = image.getShortTitle()
        return title, dims, voxelSize, unit, size
    
    def toHyperstack(self, image, dims):
        """
        Convert image to a hyperstack with the dimensions dims. The number of
        voxels must be equal to the product of the elements of dims. 

        Parameters
        ----------
        image : ij.ImagePlus
            The image that will be converted to a hyperstack.
        dims : list
            A list [x,y,c,z,t] of the size in each dimension of the image. 

        Returns
        -------
        hyperstack : ij.ImagePlus
            The hyperstack into which the input image has been converted.
        """
        hyperstack = HyperStackConverter.toHyperStack(image, dims[2], dims[3], dims[4], "Composite");
        if hyperstack.getID() == image.getID():
            image.hide()
            image.show()
        else:
            image.close()
            hyperstack.show()
        return hyperstack
            
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

    def displayPoints(self,tableTitle="Results", inColormap='inferno'):
        results = ResultsTable.getResultsTable(tableTitle)
        cal = IJ.getImage().getCalibration()
        headings = list(results.getColumnHeadings().split("\t"))[0:]
        confidenceHeaders = ["V", "Confidence"]
        confidenceHeaderID = len(confidenceHeaders)
        confidenceID = len(headings)
        data = {}
        for i in range(0, len(headings)):
            if(headings[i] in confidenceHeaders):
                confidenceHeaderID = min(confidenceHeaders.index(headings[i]), confidenceHeaderID)
                confidenceID = min(confidenceID,i)
            data[headings[i]] = results.getColumn(i)
        resultsDF = pd.DataFrame(data=data)

        coords = [[z, y, x] for [x, y, z] in resultsDF.iloc[:,0:3].to_numpy()]
        zFactor = cal.getZ(1) / cal.getX(1)

        qualities = resultsDF[confidenceHeaders[confidenceHeaderID]].to_numpy(copy=True)
        print("qualities type: "+str(type(qualities)))
        print(qualities)

        properties = {'confidence' : qualities}
        points_layer = self.viewer.add_points(coords,
                                                properties=properties,
                                                name=tableTitle,
                                                face_color='confidence',
                                                face_colormap=inColormap,
                                                face_contrast_limits=(0.0, 1.0),
                                                size=3,
                                                scale=[zFactor, 1, 1])


    def getPairs(self, tableTitle="Results"):
        results = ResultsTable.getResultsTable(tableTitle)
        cal = IJ.getImage().getCalibration()
        headings = list(results.getColumnHeadings().split("\t"))[1:]
        data = {}
        for i in range(0, len(headings)):
            data[headings[i]] = results.getColumn(i)
        results = pd.DataFrame(data=data)
        zFactor = cal.getZ(1) / cal.getX(1)
        
        coordsA = [[z, y, x] for [x, y, z] in zip(data[headings[0]],data[headings[1]],data[headings[2]])]
        coordsB = [[z, y, x] for [x, y, z] in zip(data[headings[3]],data[headings[4]],data[headings[5]])]
        
        lines = []
        for i in range(len(coordsA)):
            lines.append([coordsA[i], coordsB[i]])
        self.viewer.add_shapes(lines, name=tableTitle, shape_type='line', scale=[zFactor, 1, 1])

    def pointsToIJ(self, points):
        tableTitle = self.viewer.layers.selection.active.name
        print(tableTitle)
        sel = [(coords, v) for coords, v in zip(points.data, points.properties['confidence']) if v > 0]
        resultsWindow = WindowManager.getWindow(tableTitle)
        if resultsWindow:
            resultsWindow.close(False)
        counter = 0;
        rt = ResultsTable(JObject(JInt(len(sel))));
        for row in sel:
            rt.setValue("X", counter, row[0][2])
            rt.setValue("Y", counter, row[0][1])
            rt.setValue("Z", counter, row[0][0])
            rt.setValue("V", counter, row[1])
            counter = counter + 1
        rt.show(tableTitle)

    def saveAllLayers(self, directoryName):
        savePath = directoryName
        layerList = self.viewer.layers

        layersArray = []
        for i in range(len(layerList)):
            currentLayer = layerList[i]
            name = currentLayer.name
            type_ = str(type(currentLayer))
            print(type_)
            if(type_.find('image')>-1):
                scale = currentLayer.scale
                type_ = 'image'
                filename = name + ".tif"
                colormap = currentLayer.colormap.name
            elif(type_.find('points')>-1):
                type_ = 'points'
                filename = name + ".csv"
                colormap = currentLayer.face_colormap.name
            elif(type_.find('shapes')>-1):
                type_ = 'shapes'
                filename = name + ".csv"
                colormap = currentLayer.face_colormap.name
            else:
                print(name + " : This Layer Type may be unsupported !!")
                filename = name + ".layer"
                colormap = ""
            layersArray.append({'name':name, 'filename':filename, 'type':type_, 'colormap':colormap})
            
        layersPart = {'layers':layersArray}
        
        print(scale[1])
        print(type(scale[1]))
        zFactor = float(scale[1])

        calibrationPart = {'calibration':{'x':1, 'y':1, 'z':zFactor}}
        #configDict = [{calibrationPart},{layersPart}]
        #configDict = calibrationPart+layersPart
        with open(join(savePath, "config.yml"), 'w+') as file:
            yaml.dump(calibrationPart, file, sort_keys=False)
            yaml.dump(layersPart, file, sort_keys=False)

        layerList.save(savePath)

    def loadAllLayers(self, directoryName):
        colorID = 0

        currentDirectory = str(directoryName).replace("\\", "/").replace("//", "/")
        configFile = ""

        for f in listdir(currentDirectory):
            if isfile(join(currentDirectory, f)) and f.endswith(".yml"):
                configFile = join(currentDirectory, f)

        with open(configFile, 'r') as file:
            configs = yaml.load(file, Loader=yaml.FullLoader)
            #Calibration:
            x = configs['calibration']['x']
            z = configs['calibration']['z']
            zFactor = z / x
            for parameter in configs['layers']:
                name = parameter['name']
                filename = parameter['filename']
                type = parameter['type']
                colormap =parameter['colormap']
                if(type == 'image'):
                    self.viewer.open(join(currentDirectory, filename), layer_type=type, name=name, colormap=colormap, scale=[zFactor, 1, 1], blending='additive')
                elif(type == 'points'):
                    pointsCsv = pd.read_csv(join(currentDirectory, filename))
                    qualities = pointsCsv['confidence'].values
                    properties = {'confidence' : qualities}
                    self.viewer.open(join(currentDirectory, filename), layer_type=type, name=name, face_colormap=colormap, scale=[zFactor, 1, 1], size=3, properties=properties, face_color='confidence', face_contrast_limits=(0.0, 1.0))
                elif(type == 'shapes'):
                    self.viewer.open(join(currentDirectory, filename), layer_type=type, name=name, face_colormap=colormap, scale=[zFactor, 1, 1])
                else:
                    print(filename + " : This Layer Type may be unsupported !!")
                    self.viewer.open(join(currentDirectory, filename), layer_type=type, name=name, scale=[zFactor, 1, 1])
                    
