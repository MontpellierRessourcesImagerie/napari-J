import os
import napari
from qtpy.QtWidgets import QWidget, QPushButton, QGridLayout, QFileDialog, QLineEdit, QLabel
from .config import Config
from magicgui import magic_factory


class Image(QWidget):

    bridge = None
    loadPath = None
    loadInput = None

    savePath = None
    saveInput = None

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        config = Config()
        btnNewViewer = QPushButton("New viewer")
        btnNewViewer.clicked.connect(self._on_click_new_viewer)
        btnGetImage = QPushButton("Get Image")
        btnGetImage.clicked.connect(self._on_click_get_image)
        btnGetLabels = QPushButton("Get Labels")
        btnGetLabels.clicked.connect(self._on_click_get_labels)
        if config.isLimeSegInstalled():
            btnGetSurfaces = QPushButton("Get Surfaces")
            btnGetSurfaces.clicked.connect(self._on_click_get_surfaces)
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
        self.layout().addWidget(btnGetSurfaces  , 4, 1, 1, -1)
        self.layout().addWidget(btnScreenshot   , 5, 1, 1, -1)

        self.layout().addWidget(loadLabel       , 6, 1, 1, 2)
        self.layout().addWidget(self.loadInput  , 7, 1)
        self.layout().addWidget(btnBrowseload   , 7, 2)
        self.layout().addWidget(btnLoad         , 8, 1, 1, 2)

        self.layout().addWidget(saveLabel       , 9, 1, 1, 2)
        self.layout().addWidget(self.saveInput  , 10, 1)
        self.layout().addWidget(btnBrowseSave   , 10, 2)
        self.layout().addWidget(btnSave         , 11, 1, 1, 2)


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

    def _on_click_get_surfaces(self):
        self.getSurfaces()

    def _on_click_screenshot(self):
        self.screenshot()

    def _on_click_load(self):
        self.loadFromFolders()

    def _on_click_save(self):
        self.saveLayers()
    	
    def openNewViewer(self):
        viewer = napari.Viewer()

    def getBridge(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        return self.bridge
       
    def getImage(self):
        print("Fetching the active image from IJ")
        self.getBridge().getActiveImageFromIJ()	 
 
    def getLabels(self):
        print("Fetching the active labels image from IJ")
        self.getBridge().getLabelsFromIJ()	 

    def getSurfaces(self):
        print("Fetching the surfaces from IJ")
        self.getBridge().getSurfacesFromIJ()

    def screenshot(self):
        print("Sending screenshot to IJ")
        self.getBridge().screenshot()	 

    def loadFromFolders(self):
        print("Loading Files from folder")
        self.getBridge().loadAllLayers(self.loadPath)

    def saveLayers(self):
        print("Saving each layer")
        self.getBridge().saveAllLayers(self.savePath)
