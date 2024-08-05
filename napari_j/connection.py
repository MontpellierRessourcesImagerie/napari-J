import sys
import os
import shutil
import copy
from pathlib import Path
import yaml
import jupyter_client
from qtpy import QtCore
from qtpy.QtWidgets import QWidget, QPushButton, QGridLayout, QFileDialog, QCheckBox, QLineEdit, QLabel, QMessageBox
from magicgui import magic_factory
from .config import Config

from jpype import *
# Enable Java imports
import jpype.imports
# Pull in types
from jpype.types import *


class Connection(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()
        self.config = Config()
        self.originalDir = None
        self.path = None
        self.viewer = napari_viewer

        fijiPathLabel = QLabel(self)
        fijiPathLabel.setText("FIJI path: ")
        self.fijiPathInput = QLineEdit(self)
        self.fijiPathInput.setText(self.config.fijiPath)
        btnBrowseFIJIPath = QPushButton("Browse...")
        btnBrowseFIJIPath.clicked.connect(self._on_click_browse_fiji_path)

        jvmPathLabel = QLabel(self)
        jvmPathLabel.setText("jvm: ")
        self.jvmPathInput = QLineEdit(self)
        self.jvmPathInput.setText(self.config.jvmPath)
        btnBrowseJVMPath = QPushButton("Browse...")
        btnBrowseJVMPath.clicked.connect(self._on_click_browse_jvm_path)

        self.autostartCB = QCheckBox("automatically start FIJI")
        self.autostartCB.setChecked(self.config.autostartFIJI)

        saveSettingsBTN = QPushButton("Save Settings")
        saveSettingsBTN.clicked.connect(self._on_save_settings_click)

        makeSettingsDefaultBTN = QPushButton("Make Default")
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
        
        if self.config.autostartFIJI:
            self.startFIJI(self.config.fijiPath)

    def _on_click_browse_fiji_path(self):
        folder = QFileDialog.getExistingDirectory()
        if folder:
            self.setFIJIPath(folder + os.sep)
            self.fijiPathInput.setText(self.config.fijiPath)

    def _on_make_settings_default(self):
        self.makeSettingsDefault()

    def makeSettingsDefault(self):
        try:
            self.config.makeSettingsDefault()
            self.showMessage("make settings default...", "The settings have been defined as default.")
        except Exception:
            self.showMessage("make settings default...", "Failed to make the settings default.")

    def resetSettings(self):
        try:
            self.config.resetSettings()
            self.showMessage("reset settings...", "The settings have been reset.")
        except Exception:
            self.showMessage("reset settings...", "Failed to reset the settings.")

    def setFIJIPath(self, aPath):
        self.config.setFIJIPath(aPath)
        self.fijiPathInput.setText(aPath)

    def setJVMPath(self, aPath):
        self.config.setJVMPath(aPath)
        self.jvmPathInput.setText(aPath)

    def setAutostartFIJI(self, aBool):
        self.config.setAutostartFIJI(aBool)
        self.autostartCB.setChecked(aBool)

    def _on_save_settings_click(self):
        self.saveSettings()

    def saveSettings(self):
        fijiPath = self.fijiPathInput.text()
        self.setFIJIPath(fijiPath)
        jvmPath = self.jvmPathInput.text()
        self.setJVMPath(jvmPath)
        autostart = self.autostartCB.isChecked()
        self.setAutostartFIJI(autostart)
        self.config.save()
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
            self.setJVMPath(jvmFile[0])

    def _on_click_start_FIJI(self):
        print("STARTING FIJI...")
        self.startFIJI(self.config.fijiPath)

    def start(self):
        print("Starting jvm...")
        startJVM(
            self.config.jvmPath,
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

    def startFIJI(self, aPath):
        self.originalDir = os.getcwd()
        os.chdir(aPath)
        self.path = aPath
        QtCore.QTimer.singleShot(200, self.start)
