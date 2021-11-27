"""
The NapariJ-plugin connects napari and ImageJ (both ways). Napari (and python) accesses ImageJ
via jpype. ImageJ can access napari and python via the jupyter-client.

The plugin has the following features:
- start FIJI
- get the active image (hyperstack) from FIJI with each channel being a layer in napari
- send a snapshot from napari to FIJI
- use FIJI to detect spots, display and filter spots in napari, send the filtered spots back to FIJI
"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QFileDialog, QCheckBox
from magicgui import magic_factory
from jpype import *
# Enable Java imports
import jpype.imports
# Pull in types
from jpype.types import *
import os, shutil
from pathlib import Path
import yaml
import jupyter_client
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QLineEdit, QLabel, QMessageBox, QSlider
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import napari, copy
import numpy as np

class Points(QWidget):

    bridge = None
    ax = None
    thresholdMin = 0
    thresholdMax = 0
    confidence = None
    points = {}
    selectedPoints = None
    colormapID = 0

    
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        btnGetPoints = QPushButton("Get Points")
        btnGetPoints.clicked.connect(self._on_click_get_points)
        
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        
        sliderMin = QSlider(Qt.Horizontal, self)
        sliderMin.valueChanged[int].connect(self.changeValueMin)
        sliderMin.setMinimum(0)   
        sliderMin.setMaximum(100)
        sliderMin.setValue(0)

        sliderMax = QSlider(Qt.Horizontal, self)
        sliderMax.valueChanged[int].connect(self.changeValueMax)
        sliderMax.setMinimum(0)   
        sliderMax.setMaximum(100)
        sliderMax.setValue(100)
        changeColormapButton = QPushButton("Change Colormap")
        changeColormapButton.clicked.connect(self._on_click_changeColormap)
        btnPointsToIJ = QPushButton("Points to IJ")
        btnPointsToIJ.clicked.connect(self._on_click_pointsToIJ)
        btnGetLines = QPushButton("Get Lines")
        btnGetLines.clicked.connect(self._on_click_getLines)
        
        self.setLayout(QGridLayout())
        self.layout().addWidget(btnGetPoints        , 1, 1, 1, -1)
        self.layout().addWidget(self.canvas         , 2, 1, 1, -1)
        self.layout().addWidget(sliderMin           , 3, 1, 1, -1)
        self.layout().addWidget(sliderMax           , 4, 1, 1, -1)
        self.layout().addWidget(changeColormapButton, 5, 1, 1, -1)
        self.layout().addWidget(btnPointsToIJ       , 6, 1, 1, -1)
        self.layout().addWidget(btnGetLines         , 7, 1, 1, -1)
        
        self.viewer.layers.selection.events.active.connect(self._on_layer_changed)
        self.viewer.layers.events.removed.connect(self._on_remove_layer)

    def _on_layer_changed(self, event):
        anID = id(self.viewer.layers.selection.active)
        if anID in self.points:
            self.confidence = self.points[anID][1]
            self.selectedPoints = self.points[anID][0]
        else:
            points = self.getSelectedLayer()
            if not points:
                return
            self.confidence = copy.deepcopy(points.properties['confidence'])
            self.points[anID] = points, self.confidence
            self.selectedPoints = self.points[anID][0]

        self.drawHistogram()
        
    def _on_remove_layer(self, event):
        anID = id(self.viewer.layers.selection.active)
        if anID in self.points:
            self.points.pop(anID)
            self.confidence = None
            self.selectedPoints = None

    def drawHistogram(self):
        print("Drawing Histogram...")
        if self.confidence is None:
            return
        self.figure.clear()

        # create an axis
        self.ax = self.figure.add_subplot(111)
        
        range = (0,1)

        # plot data
        self.ax.hist(self.confidence, bins='fd', range=range)
        self.ax.axvline(self.thresholdMin, color='k', linestyle='dashed', linewidth=1)
        self.ax.axvline(self.thresholdMax, color='k', linestyle='dashed', linewidth=1)
   
        # refresh canvas
        self.canvas.draw()

    def _on_click_get_points(self):
        self.selectedPoints, self.confidence = self.getPoints()
        self.points[id(self.selectedPoints)] = self.selectedPoints, self.confidence
        self.drawHistogram()

    def _on_click_pointsToIJ(self):
        self.pointsToIJ()

    def _on_click_changeColormap(self):
        self.changeColormap()

    def _on_click_getLines(self):
        self.checkBridge()
        print("Fetching pairs from IJ")
        self.bridge.getPairs()

    
    def changeValueMin(self, value):
        self.thresholdMin = value / 100.0
        if not self.ax:
            return
        points = self.selectedPoints
        if not points:
            return
        self.drawHistogram()
        
        p = points.properties['confidence']
        for i in range(0, len(p)):
            if self.confidence[i]<self.thresholdMin:
                p[i] = 0
            else:
                p[i] = self.confidence[i]
        points.refresh_colors() 

    def changeValueMax(self, value):
        self.thresholdMax = value / 100.0
        if not self.ax:
            return
        points = self.selectedPoints
        if not points:
            return
        self.drawHistogram()
        
        p = points.properties['confidence']
        for i in range(0, len(p)):
            if self.confidence[i]>self.thresholdMax:
                p[i] = 0
            else:
                p[i] = self.confidence[i]
        points.refresh_colors() 
            
    def getPoints(self):
        self.checkBridge()
        print("Fetching points from IJ")
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        self.bridge.displayPoints()
        points = self.getSelectedLayer()
        if not points:
            return
        self.confidence = copy.deepcopy(points.properties['confidence'])
        return points, self.confidence

    def changeColormap(self):
        self.checkBridge()
        colormaps = ['viridis','cividis','inferno']
        points = self.getSelectedLayer()
        if not points:
            return
        points.face_colormap=self.bridge.cropColormap(colormaps[self.colormapID])
        self.colormapID=(self.colormapID+1)%len(colormaps)
        points.refresh_colors() 

    def pointsToIJ(self):
        self.checkBridge()
        if not self.selectedPoints:
            return
        print("Sending points to IJ")
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        self.bridge.pointsToIJ(self.selectedPoints)

    def checkBridge(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)

    def getSelectedLayer(self):
        points = self.viewer.layers.selection.active
        print(type(points))
        print(str(type(points)))
        if str(type(points))=="<class 'napari.layers.points.points.Points'>":
            print("I'm on it")
            return points
        return None

class Image(QWidget):

    bridge = None
    loadPath = None
    loadInput = None

    savePath = None
    saveInput = None

    
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        btnNewViewer = QPushButton("New viewer")
        btnNewViewer.clicked.connect(self._on_click_new_viewer)
        btnGetImage = QPushButton("Get Image")
        btnGetImage.clicked.connect(self._on_click_get_image)
        btnGetLabels = QPushButton("Get Labels")
        btnGetLabels.clicked.connect(self._on_click_get_labels)
        btnScreenshot = QPushButton("Screenshot")
        btnScreenshot.clicked.connect(self._on_click_screenshot)

        loadLabel = QLabel(self)
        loadLabel.setText("Loading Files from a Folder :")
        self.loadInput = QLineEdit(self)
        self.loadInput.setText(self.loadPath)
        btnBrowseload = QPushButton("Browse...")
        btnBrowseload.clicked.connect(self._on_click_browse_load)
        btnLoad = QPushButton("Load")
        btnLoad.clicked.connect(self._on_click_load)

        saveLabel = QLabel(self)
        saveLabel.setText("Save Layers to a Folder :")
        self.saveInput = QLineEdit(self)
        self.saveInput.setText(self.savePath)
        btnBrowseSave = QPushButton("Browse...")
        btnBrowseSave.clicked.connect(self._on_click_browse_save)
        btnSave = QPushButton("Save")
        btnSave.clicked.connect(self._on_click_save)

        self.setLayout(QGridLayout())
        self.layout().addWidget(btnNewViewer    , 1, 1, 1, -1)
        self.layout().addWidget(btnGetImage     , 2, 1, 1, -1)
        self.layout().addWidget(btnGetLabels    , 3, 1, 1, -1)
        self.layout().addWidget(btnScreenshot   , 4, 1, 1, -1)

        self.layout().addWidget(loadLabel       , 5, 1, 1, 2)
        self.layout().addWidget(self.loadInput  , 6, 1)
        self.layout().addWidget(btnBrowseload   , 6, 2)
        self.layout().addWidget(btnLoad         , 7, 1, 1, 2)

        self.layout().addWidget(saveLabel       , 8, 1, 1, 2)
        self.layout().addWidget(self.saveInput  , 9, 1)
        self.layout().addWidget(btnBrowseSave   , 9, 2)
        self.layout().addWidget(btnSave         , 10, 1, 1, 2)


    def _on_click_browse_load(self):
        folder = QFileDialog.getExistingDirectory() 
        if folder:
            self.loadPath = folder + os.sep
            self.loadInput.setText(self.loadPath) 
    
    def _on_click_browse_save(self):
        folder = QFileDialog.getExistingDirectory() 
        if folder:
            self.savePath = folder + os.sep
            self.saveInput.setText(self.savePath)
        
    def _on_click_new_viewer(self):
        self.openNewViewer()
    	
    def _on_click_get_image(self):
    	self.getImage()

    def _on_click_get_labels(self):
        self.getLabels()
        
    def _on_click_screenshot(self):
    	self.screenshot()

    def _on_click_load(self):
        self.loadFromFolders()

    def _on_click_save(self):
        self.saveLayers()
    	
    def openNewViewer(self):
        viewer = napari.Viewer()

    def getImage(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        print("Fetching the active image from IJ")
        self.bridge.getActiveImageFromIJ()	 
 
    def getLabels(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        print("Fetching the active labels image from IJ")
        self.bridge.getLabelsFromIJ()	 
    
    def screenshot(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        print("Sending screenshot to IJ")
        self.bridge.screenshot()	 

    def loadFromFolders(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        print("Loading Files from folder")
        self.bridge.loadAllLayers(self.loadPath)

    def saveLayers(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        print("Saving each layer")
        self.bridge.saveAllLayers(self.savePath)     

        
class Connection(QWidget):
    
    config = None
    home = None
    def __init__(self, napari_viewer):
        super().__init__()
        self.home = os.getcwd()
        self.readConfig()
        self.viewer = napari_viewer

        fijiPathLabel = QLabel(self)
        fijiPathLabel.setText("FIJI path: ")
        self.fijiPathInput = QLineEdit(self)
        self.fijiPathInput.setText(self.fijiPath)
        btnBrowseFIJIPath = QPushButton("Browse...")
        btnBrowseFIJIPath.clicked.connect(self._on_click_browse_fiji_path)

        jvmPathLabel = QLabel(self)
        jvmPathLabel.setText("jvm: ")
        self.jvmPathInput = QLineEdit(self)
        self.jvmPathInput.setText(self.jvmPath)
        btnBrowseJVMPath = QPushButton("Browse...")
        btnBrowseJVMPath.clicked.connect(self._on_click_browse_jvm_path)

        self.autostartCB = QCheckBox("automatically start FIJI")
        self.autostartCB.setChecked(self.autostartFIJI)

        saveSettingsBTN = QPushButton("Save Settings")
        saveSettingsBTN.clicked.connect(self._on_save_settings_click)

        makeSettingsDefaultBTN =  QPushButton("Make Default")
        makeSettingsDefaultBTN.clicked.connect(self._on_make_settings_default)

        resetSettingsBTN = QPushButton("Reset Settings")
        resetSettingsBTN.clicked.connect(self._on_reset_settings_click)

        startFIJIBTN = QPushButton("Start FIJI")
        startFIJIBTN.clicked.connect(self._on_click_start_FIJI)

        self.setLayout(QGridLayout())
        self.layout().addWidget(fijiPathLabel       , 1, 1)
        self.layout().addWidget(self.fijiPathInput  , 1, 2)
        self.layout().addWidget(btnBrowseFIJIPath   , 1, 3)

        self.layout().addWidget(jvmPathLabel        , 2, 1)
        self.layout().addWidget(self.jvmPathInput   , 2, 2)
        self.layout().addWidget(btnBrowseJVMPath    , 2, 3)

        self.layout().addWidget(self.autostartCB        , 3, 1, 3, -1)
        self.layout().addWidget(saveSettingsBTN         , 4, 1, 3, -1)
        self.layout().addWidget(makeSettingsDefaultBTN  , 5, 1, 3, -1)
        self.layout().addWidget(resetSettingsBTN        , 6, 1, 3, -1)
        self.layout().addWidget(startFIJIBTN            , 7, 1, 3, -1)
        
        if self.autostartFIJI:
            self.startFIJI(self.fijiPath)

    def readConfig(self):
        with open('./naparij.yml', 'r') as file:
            params = yaml.load(file, Loader=yaml.FullLoader)
        self.config = params
        connectionParams = params['connection']
        self.jvmPath = connectionParams['jvm_path']
        self.fijiPath = connectionParams['fiji_path']
        self.autostartFIJI = connectionParams['autostart_fiji']

    def _on_click_browse_fiji_path(self):
        folder = QFileDialog.getExistingDirectory()
        if folder:
            self.fijiPath = folder + os.sep
            self.fijiPathInput.setText(self.fijiPath)

    def _on_make_settings_default(self):
    	self.makeSettingsDefault()

    def makeSettingsDefault(self):
        try:
            shutil.copy("./naparij.yml", "./naparij_default.yml")
            self.showMessage("make settings default...", "The settings have been defined as default.")
        except:
            self.showMessage("make settings default...", "Failed to make the settings default.")

    def resetSettings(self):
        try:
            shutil.copy("./naparij_default.yml", "./naparij.yml")
            self.showMessage("reset settings...", "The settings have been reset.")
        except:
            self.showMessage("reset settings...", "Failed to reset the settings.")

    def setFIJIPath(self, aPath):
    	self.fijiPath = aPath
    	self.fijiPathInput.setText(aPath)
    	self.config['connection']['fiji_path'] = aPath

    def setJVMPath(self, aPath):
    	self.jvmPath = aPath
    	self.jvmPathInput.setText(aPath)
    	self.config['connection']['jvm_path'] = aPath

    def activateAutostartFIJI(self):
        self.autostartFIJI = True
        self.autostartCB.setChecked(True)
        self.config['connection']['autostart_fiji'] = True

    def deactivateAutostartFIJI(self):
        self.autostartFIJI = False
        self.autostartCB.setChecked(False)
        self.config['connection']['autostart_fiji'] = False

    def _on_save_settings_click(self):
        self.saveSettings()

    def saveSettings(self):
        fijiPath = self.fijiPathInput.text()
        self.setFIJIPath(fijiPath)
        jvmPath = self.jvmPathInput.text()
        self.setJVMPath(jvmPath)
        autostart = self.autostartCB.isChecked()
        if autostart:
            self.activateAutostartFIJI()
        else:
            self.deactivateAutostartFIJI()
        with open('./naparij.yml', 'w') as file:
            yaml.dump(self.config, file)
        self.showMessage("Settings saved...", "The settings have been saved.")

    def showMessage(self, title, message):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(message)
        msgBox.setWindowTitle(title)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()

    def _on_reset_settings_click(self):
    	self.resetSettings()

    def _on_click_browse_jvm_path(self):
        jvmFile = QFileDialog.getOpenFileName(None, 'Single File', '', '*.so *.dll')
        if jvmFile:
            self.jvmPath = jvmFile[0]
            self.jvmPathInput.setText(self.jvmPath)

    def _on_click_start_FIJI(self):
        print("STARTING FIJI...")
        self.startFIJI(self.fijiPath)

    def start(self):
        startJVM(
            self.jvmPath,
            "-ea",
            "-Dpython.cachedir.skip=false",
            "-Dplugins.dir=.",
            "-Dimagej.dir=.",
            "-Dfiji.dir=.",
            "-Dij.executable= ",
            "-Dij.dir="+os.getcwd()
        )
        paths = {}
        for path in Path('./jars').rglob('*.jar'):
            jar = str(path).split('/')[-1]
            if not jar in paths:
                addClassPath(self.path + str(path))
                paths[jar]=jar
        for path in Path('./plugins').rglob('*.jar'):
            jar = str(path).split('/')[-1]
            if not jar in paths:
                addClassPath(self.path + str(path))
                paths[jar]=jar
        from net.imagej.launcher import ClassLauncher
        ClassLauncher.main(("-ijjarpath", "jars", "-ijjarpath", "plugins", "-ijjarpath", "retro", "net.imagej.Main"))
        from ij import IJ, ImageJ
        IJ.setProperty('jupter_connection_file', jupyter_client.find_connection_file())
        IJ.setProperty('python_executable', sys.executable)

    def startFIJI(self, aPath):
        os.chdir(aPath)
        self.path = aPath
        QtCore.QTimer.singleShot(200, self.start)

@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [Connection, Image, Points]
