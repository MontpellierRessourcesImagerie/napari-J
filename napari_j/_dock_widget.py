"""
This module is an example of a barebones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QFileDialog, QCheckBox
from magicgui import magic_factory
from jpype import *
# Enable Java imports
import jpype.imports
# Pull in types
from jpype.types import *
import os
from pathlib import Path
import yaml
import jupyter_client
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QLineEdit, QLabel

class Connection(QWidget):
    
    bridge = None
    
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
        
        resetSettingsBTN = QPushButton("Reset Settings")
        resetSettingsBTN.clicked.connect(self._on_reset_settings_click)
        
        btn = QPushButton("Start FIJI")
        btn.clicked.connect(self._on_click)

        btnGetImage = QPushButton("Get Image")
        btnGetImage.clicked.connect(self._on_click_get_image)
        
        self.setLayout(QGridLayout())
        self.layout().addWidget(fijiPathLabel, 1, 1)
        self.layout().addWidget(self.fijiPathInput, 1, 2)
        self.layout().addWidget(btnBrowseFIJIPath, 1, 3)

        self.layout().addWidget(jvmPathLabel, 2, 1)
        self.layout().addWidget(self.jvmPathInput, 2, 2)
        self.layout().addWidget(btnBrowseJVMPath, 2, 3)

        self.layout().addWidget(self.autostartCB, 3, 2, 3, 1)
        self.layout().addWidget(saveSettingsBTN, 4, 2, 3, 1)
        self.layout().addWidget(resetSettingsBTN, 5, 2, 3, 1)
        self.layout().addWidget(btn,6,2,3,1)
        self.layout().addWidget(btnGetImage,7,2,3,1)
          
    def readConfig(self):
        with open('./naparij.yml', 'r') as file:
            params = yaml.load(file, Loader=yaml.FullLoader)
        connectionParams = params['connection']
        self.jvmPath = connectionParams['jvm_path']
        self.fijiPath = connectionParams['fiji_path']
        self.autostartFIJI = connectionParams['autostart_fiji']
    	
    def _on_click_browse_fiji_path(self):
        folder = QFileDialog.getExistingDirectory() 
        if folder:
            self.fijiPath = folder + os.sep
            self.fijiPathInput.setText(self.fijiPath)
            
    def _on_save_settings_click(self):
    	pass
    
    def _on_reset_settings_click(self):
    	pass
    	
    def _on_click_browse_jvm_path(self):
        jvmFile = QFileDialog.getOpenFileName(None, 'Single File', '', '*.so *.dll')
        if jvmFile:
            self.jvmPath = folder + os.sep
            self.jvmPathInput.setText(self.jvmPath)
            
    def _on_click(self):
        print("STARTING FIJI...")
        self.startFIJI(self.fijiPath)

    def _on_click_get_image(self):
        from .bridge import Bridge
        print("Fetching the active image from IJ")
        if not self.bridge:
        	self.bridge = Bridge(self.viewer)
        self.bridge.getActiveImageFromIJ()    
        
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

@magic_factory
def example_magic_widget(img_layer: "napari.layers.Image"):
    print(f"you have selected {img_layer}")


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [Connection, example_magic_widget]
