import copy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget, QPushButton, QGridLayout, QSlider, QLineEdit
from magicgui import magic_factory


class Points(QWidget):
    bridge = None
    ax = None

    sliderMin = None
    sliderMax = None
    thresholdMin = 0
    thresholdMax = 0
    lowBound = {}
    highBound = {}
    confidence = None
    points = {}
    selectedPoints = None
    colormapID = 0

    
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.fieldTableName = QLineEdit(self)
        self.fieldTableName.setText("Results")

        btnGetPoints = QPushButton("Get Points")
        btnGetPoints.clicked.connect(self._on_click_get_points)
        
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        
        self.sliderMin = QSlider(Qt.Horizontal, self)
        self.sliderMin.valueChanged[int].connect(self.changeValueMin)
        self.sliderMin.setMinimum(0)   
        self.sliderMin.setMaximum(100)
        self.sliderMin.setValue(0)

        self.sliderMax = QSlider(Qt.Horizontal, self)
        self.sliderMax.valueChanged[int].connect(self.changeValueMax)
        self.sliderMax.setMinimum(0)   
        self.sliderMax.setMaximum(100)
        self.sliderMax.setValue(100)
        
        changeColormapButton = QPushButton("Change Colormap")
        changeColormapButton.clicked.connect(self._on_click_changeColormap)
        btnPointsToIJ = QPushButton("Points to IJ")
        btnPointsToIJ.clicked.connect(self._on_click_pointsToIJ)
        btnGetLines = QPushButton("Get Lines")
        btnGetLines.clicked.connect(self._on_click_getLines)
        
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.fieldTableName , 1, 1, 1,  2)
        self.layout().addWidget(btnGetPoints        , 1, 3, 1, -1)
        self.layout().addWidget(self.canvas         , 2, 1, 1, -1)
        self.layout().addWidget(self.sliderMin      , 3, 1, 1, -1)
        self.layout().addWidget(self.sliderMax      , 4, 1, 1, -1)
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
            self.thresholdMin = self.lowBound[anID]
            self.thresholdMax = self.highBound[anID]
        else:
            points = self.getSelectedLayer()
            if not points:
                return
            self.confidence = copy.deepcopy(points.properties['confidence'])
            self.points[anID] = points, self.confidence
            self.lowBound[anID] = min(self.confidence)
            self.highBound[anID] = max(self.confidence)

            self.selectedPoints = self.points[anID][0]

        self.thresholdMin = self.lowBound[anID]
        self.thresholdMax = self.highBound[anID]

        self.sliderMin.setValue(self.thresholdMin*100)
        self.sliderMax.setValue(self.thresholdMax*100)
        self.sliderMin.setSliderPosition(self.thresholdMin*100)
        self.sliderMax.setSliderPosition(self.thresholdMax*100)
        self.drawHistogram()
        
    def _on_remove_layer(self, event):
        anID = id(self.viewer.layers.selection.active)
        if anID in self.points:
            self.points.pop(anID)
            self.lowBound.pop(anID)
            self.highBound.pop(anID)

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
        self.selectedPoints, self.confidence = self.getPoints(self.fieldTableName.text())
        #self.selectedPoints, self.confidence = self.getPoints()
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
        anID = id(self.viewer.layers.selection.active)
        self.lowBound[anID] = self.thresholdMin
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
        anID = id(self.viewer.layers.selection.active)
        self.highBound[anID] = self.thresholdMax
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
            
    def getBridge(self):
        from .bridge import Bridge
        if not self.bridge:
            self.bridge = Bridge(self.viewer)
        return self.bridge
    
    def getPoints(self,tableTitle="Results"):
        print("Fetching points from IJ")
        self.getBridge().displayPoints(tableTitle)
        points = self.getSelectedLayer()
        if not points:
            return
        self.confidence = copy.deepcopy(points.properties['confidence'])
        return points, self.confidence

    def changeColormap(self):
        colormaps = ['viridis','cividis','inferno']
        points = self.getSelectedLayer()
        if not points:
            return
        points.face_colormap=self.bridge.cropColormap(colormaps[self.colormapID])
        self.colormapID=(self.colormapID+1)%len(colormaps)
        points.refresh_colors() 

    def pointsToIJ(self):
        if not self.selectedPoints:
            return
        print("Sending points to IJ")
        self.getBridge().pointsToIJ(self.selectedPoints)

    def getSelectedLayer(self):
        points = self.viewer.layers.selection.active
        print(type(points))
        print(str(type(points)))
        if str(type(points))=="<class 'napari.layers.points.points.Points'>":
            return points
        return None
