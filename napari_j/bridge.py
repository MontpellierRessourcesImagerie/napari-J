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


class Bridge:
    '''
        The Bridge allows napari to communicate with ImageJ.
    '''
    colors = ['magenta', 'cyan', 'yellow', 'red', 'green', 'blue', 'orange', 'brown', 'white']

    def __init__(self, viewer):
        '''
        The constructor creates a new Bridge-object. 

        Parameters
        ----------
        viewer : napari.viewer.Viewer
            The napari-viewer instance that will communicate with ImageJ.

        Returns
        -------
        None.
        '''
        self.viewer = viewer

    def getActiveImageFromIJ(self):
        '''
        Removes all layers from the viewer. Gets the active image from ImageJ
        and add it's channels as image-layers to the viewer.
        
        Returns
        -------
        None.
        '''
        for c in range(0, len(self.viewer.layers)):
            self.viewer.layers.pop(0)
        title, dims, zFactor, pixels = self.getPixelsFromImageJ()
        for c in range(0, dims[2]):
            self.viewer.add_image(pixels.reshape(
                dims[4], dims[3], dims[2], dims[1], dims[0])[:, :, c, :, :],
                name="C" + str(c + 1) + "-" + str(title),
                colormap=self.colors[c],
                blending='additive',
                scale=[zFactor, 1, 1])
        self.viewer.dims.ndisplay = 3

    def getLabelsFromIJ(self):
        '''
        Adds the active image in ImageJ as a new labels-layer to the viewer.

        Returns
        -------
        None.
        '''
        title, dims, zFactor, pixels = self.getPixelsFromImageJ()
        self.viewer.add_labels(pixels.reshape(
            dims[4], dims[3], dims[2], dims[1], dims[0])[:, :, 0, :, :].astype(int), 
            name=str(title), 
            scale=[zFactor, 1, 1])
    	
    def getPixelsFromImageJ(self):
        '''
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
        zFactor : float
            The ratio of the voxel size in the z-dimension and x-dimension.
        pixels : numpy.ndarray
            The pixel data of the active image in ImageJ as a linear list.
        '''
        image = IJ.getImage()
        title, dims, zFactor, size = self.getMetadataFromImage(image)
        isHyperStack = image.isHyperStack()
        HyperStackConverter.toStack(image)
        stackDims = list(image.getDimensions())
        dim = stackDims[3]
        if stackDims[2] == 1 and stackDims[3] == 1 and stackDims[4] > 1:
            dim = dims[4]
        if size<=2147483647:
                pixels = np.array(image.getStack().getVoxels(0, 0, 0, stackDims[0], stackDims[1], dim, []))
        else:
                ia = image.getStack().getImageArray()
                ia = list(filter(None, ia))
                pixels = np.array(ia)
        if isHyperStack:
            self.toHyperstack(image, dims)
        return title, dims, zFactor, pixels
    
    def getMetadataFromImage(self, image):
        dims = list(image.getDimensions())
        size = dims[0]*dims[1]*dims[3]*dims[4]
        cal = image.getCalibration()
        zFactor = cal.getZ(1) / cal.getX(1)
        title = image.getShortTitle()
        return title, dims, zFactor, size
    
    def toHyperstack(self, image, dims):
        image2 = HyperStackConverter.toHyperStack(image, dims[2], dims[3], dims[4], "Composite");
        if image2.getID() == image.getID():
            image.hide()
            image.show()
        else:
            image.close()
            image2.show()
            
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

    def displayPoints(self,tableTitle="Results",inColormap='inferno'):
        results = ResultsTable.getResultsTable(tableTitle)
        cal = IJ.getImage().getCalibration()
        headings = list(results.getColumnHeadings().split("\t"))[1:]
        confidenceHeaders = ["V","Confidence","Z"]
        confidenceHeaderID = len(confidenceHeaders)
        data = {}
        for i in range(0, len(headings)):
            if(headings[i] in confidenceHeaders):
                confidenceHeaderID = min(confidenceHeaders.index(headings[i]),confidenceHeaderID)
            data[headings[i]] = results.getColumn(i)
        results = pd.DataFrame(data=data)

        coords = [[z, y, x] for [x,y,z] in results.iloc[:,0:3].to_numpy()]
        zFactor = cal.getZ(1) / cal.getX(1)


        qualities = results[confidenceHeaders[confidenceHeaderID]].values / 255
        properties = {'confidence' : qualities}
        colormap = self.cropColormap(inColormap)
        points_layer = self.viewer.add_points(coords, properties=properties,name=tableTitle,
                                                  face_color='confidence',
                                                  face_colormap=colormap,
                                                  face_contrast_limits=(0.0,1.0),
                                                  size=3, scale=[zFactor, 1, 1])


    def getPairs(self,tableTitle="Results"):
        results = ResultsTable.getResultsTable(tableTitle)
        cal = IJ.getImage().getCalibration()
        headings = list(results.getColumnHeadings().split("\t"))[1:]
        data = {}
        for i in range(0, len(headings)):
            data[headings[i]] = results.getColumn(i)
        results = pd.DataFrame(data=data)
        zFactor = cal.getZ(1) / cal.getX(1)
        
        coordsA = [[z, y, x] for [x,y,z] in np.delete(results.values,[3,4,5,6], axis=1)]
        # 
        # qualities = results['Dist'].values / 255
        # properties = {'confidence' : qualities}
        # colormap = self.cropColormap('inferno')
        # points_layer = self.viewer.add_points(coordsA,  properties=properties,
        #                                           face_color='confidence',
        #                                           face_colormap=colormap,
        #                                           face_contrast_limits=(0.0,1.0),
        #                                           size=3, scale=[zFactor, 1, 1])

        coordsB = [[z, y, x] for [x,y,z] in np.delete(results.values,[0,1,2,6], axis=1)]
        #
        # qualities = results['Dist'].values / 255
        # properties = {'confidence' : qualities}
        # colormap = self.cropColormap('viridis')
        # points_layer = self.viewer.add_points(coordsB,  properties=properties,
        #                                           face_color='confidence',
        #                                           face_colormap=colormap,
        #                                           face_contrast_limits=(0.0,1.0),
        #                                           size=3, scale=[zFactor, 1, 1])
        lines = []
        for i in range(len(coordsA)):
            lines.append([coordsA[i],coordsB[i]])
        self.viewer.add_shapes(lines,name=tableTitle, shape_type='line', scale=[zFactor, 1, 1])

    def cropColormap(self,colorMapName):
        #Get colorMap values
        cm = get_colormap(colorMapName)
        for i in range(256):
            cm.colors.rgba[i]=cm.colors.rgba[int(i/2)+128]
            if i==0:
                cm.colors.rgba[0]=[0.0,0.0,0.0,1.0]
        return convert_vispy_colormap(cm, name=colorMapName)

    def pointsToIJ(self, points):
        sel = [(coords, v) for coords,v in zip(points.data, points.properties['confidence']) if v>0]
        rw = WindowManager.getWindow("Results")
        if rw:
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

    def saveAllLayers(self,directoryName):
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
            else:
                if(type_.find('points')>-1):
                    type_ = 'points'
                else:
                    type_ = 'shapes'
                filename = name + ".csv"
                colormap = currentLayer.face_colormap.name

            layersArray.append({'name':name,'filename':filename,'type':type_,'colormap':colormap})
            
        layersPart = {'layers':layersArray}
        
        print(scale[1])
        print(type(scale[1]))
        zFactor = float(scale[1])

        calibrationPart = {'calibration':{'x':1,'y':1,'z':zFactor}}
        #configDict = [{calibrationPart},{layersPart}]
        #configDict = calibrationPart+layersPart
        with open(join(savePath, "config.yml"), 'w+') as file:
            yaml.dump(calibrationPart, file, sort_keys=False)
            yaml.dump(layersPart, file, sort_keys=False)

        layerList.save(savePath)

    def loadAllLayers(self,directoryName):
        colorID = 0

        currentDirectory = str(directoryName).replace("\\", "/").replace("//", "/")
        configFile = ""

        for f in listdir(currentDirectory):
            if isfile(join(currentDirectory, f)) and f.endswith(".yml"):
                configFile = join(currentDirectory, f)

        with open(configFile, 'r') as file:
            configs = yaml.load(file, Loader=yaml.FullLoader)
            #Calibration:
            x=configs['calibration']['x']
            z=configs['calibration']['z']
            zFactor = z / x
            for parameter in configs['layers']:
                name = parameter['name']
                filename = parameter['filename']
                type = parameter['type']
                colormap =parameter['colormap']
                if(type == 'image'):
                    self.viewer.open(join(currentDirectory, filename),layer_type=type,name=name,colormap=colormap,scale=[zFactor, 1, 1],blending='additive')
                if(type == 'points'):
                    pointsCsv = pd.read_csv(join(currentDirectory, filename))
                    qualities = pointsCsv['confidence'].values
                    properties = {'confidence' : qualities}
                    croppedColormap = self.cropColormap(colormap)
                    self.viewer.open(join(currentDirectory, filename),layer_type=type,name=name,face_colormap=croppedColormap,scale=[zFactor, 1, 1],size=3,properties=properties,face_color='confidence',face_contrast_limits=(0.0,1.0))
                if(type == 'shapes'):
                    self.viewer.open(join(currentDirectory, filename),layer_type=type,name=name,face_colormap=colormap,scale=[zFactor, 1, 1])

