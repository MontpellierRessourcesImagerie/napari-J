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
from PyQt5.QtWidgets import QLineEdit, QLabel, QMessageBox
import napari

class Points(QWidget):

    bridge = None

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        getPointsBTN = QPushButton("Get Points")
        getPointsBTN.clicked.connect(self._on_click_get_points)
        self.setLayout(QGridLayout())
        self.layout().addWidget(getPointsBTN, 1, 1)

    def _on_click_get_points(self):
        self.getPoints()
        
    def getPoints(self):
        from .bridge import Bridge
        print("Fetching points from IJ")
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        self.bridge.displayPoints()	 
     	  	
class Image(QWidget):

    bridge = None
    
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        newViewerBTN = QPushButton("New viewer")
        newViewerBTN.clicked.connect(self._on_click_new_viewer)
        btnGetImage = QPushButton("Get Image")
        btnGetImage.clicked.connect(self._on_click_get_image)
        btnScreenshot = QPushButton("Screenshot")
        btnScreenshot.clicked.connect(self._on_click_screenshot)
        self.setLayout(QGridLayout())
        self.layout().addWidget(newViewerBTN, 1, 1)
        self.layout().addWidget(btnGetImage, 2, 1)
        self.layout().addWidget(btnScreenshot, 3, 1)
        
    def _on_click_new_viewer(self):
        self.openNewViewer()
    	
    def _on_click_get_image(self):
    	self.getImage()
    	
    def _on_click_screenshot(self):
    	self.screenshot()
    	
    def openNewViewer(self):
        viewer = napari.Viewer()
        
    def getImage(self):
        from .bridge import Bridge
        print("Fetching the active image from IJ")
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        self.bridge.getActiveImageFromIJ()	 
 
    def screenshot(self):
        from .bridge import Bridge
        print("Sending screenshot to IJ")
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        self.bridge.screenshot()	 
        
class Connection(QWidget):
    
    config = None
    
    def __init__(self, napari_viewer):
        super().__init__()
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
        self.layout().addWidget(fijiPathLabel, 1, 1)
        self.layout().addWidget(self.fijiPathInput, 1, 2)
        self.layout().addWidget(btnBrowseFIJIPath, 1, 3)

        self.layout().addWidget(jvmPathLabel, 2, 1)
        self.layout().addWidget(self.jvmPathInput, 2, 2)
        self.layout().addWidget(btnBrowseJVMPath, 2, 3)

        self.layout().addWidget(self.autostartCB, 3, 2, 3, 1)
        self.layout().addWidget(saveSettingsBTN, 4, 2, 3, 1)
        self.layout().addWidget(makeSettingsDefaultBTN, 5, 2, 3, 1)
        self.layout().addWidget(resetSettingsBTN, 6, 2, 3, 1)
        self.layout().addWidget(startFIJIBTN,7,2,3,1)
        
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
            "-Dij.dir=.",
            "-Dfiji.dir=.",
            "-Dij.executable= "
        )
        for path in Path('./jars').rglob('*.jar'):
            addClassPath(self.path + str(path))
        for path in Path('./plugins').rglob('*.jar'):
            addClassPath(self.path + str(path))
        from net.imagej.launcher import ClassLauncher
        ClassLauncher.main(("-ijjarpath", "jars", "-ijjarpath", "plugins", "net.imagej.Main"))
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
