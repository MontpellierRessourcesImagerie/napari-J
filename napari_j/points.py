import copy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget, QPushButton, QGridLayout, QSlider, QLineEdit, QDoubleSpinBox
from magicgui import magic_factory


_MAXIMUM_HISTOGRAM = 65536

class Points(QWidget):
    bridge = None
    ax = None

    sliderMin = None
    sliderMax = None

    histogramMin = 0
    histogramMax = 1

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
        
        #Histogram Min/Max Text
        self.histogramMinBox = QDoubleSpinBox(self)
        self.histogramMinBox.setValue(self.histogramMin)
        self.histogramMinBox.setMinimum(0)   
        self.histogramMinBox.setMaximum(_MAXIMUM_HISTOGRAM)
        self.histogramMinBox.valueChanged[float].connect(self.changeHistogramMin)

        btnResetRange = QPushButton("Reset Histogram Range")
        btnResetRange.clicked.connect(self._on_click_resetRange)

        self.histogramMaxBox = QDoubleSpinBox(self)
        self.histogramMaxBox.setValue(self.histogramMax)
        self.histogramMaxBox.setMinimum(0)   
        self.histogramMaxBox.setMaximum(_MAXIMUM_HISTOGRAM)
        self.histogramMaxBox.valueChanged[float].connect(self.changeHistogramMax)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        
        self.sliderMin = QSlider(Qt.Horizontal, self)
        self.sliderMin.valueChanged[int].connect(self.changeSliderMin)
        self.sliderMin.setMinimum(0)   
        self.sliderMin.setMaximum(_MAXIMUM_HISTOGRAM)
        self.sliderMin.setValue(0)

        self.sliderMax = QSlider(Qt.Horizontal, self)
        self.sliderMax.valueChanged[int].connect(self.changeSliderMax)
        self.sliderMax.setMinimum(0)   
        self.sliderMax.setMaximum(_MAXIMUM_HISTOGRAM)
        self.sliderMax.setValue(_MAXIMUM_HISTOGRAM)
        
        changeColormapButton = QPushButton("Change Colormap")
        changeColormapButton.clicked.connect(self._on_click_changeColormap)
        btnPointsToIJ = QPushButton("Points to IJ")
        btnPointsToIJ.clicked.connect(self._on_click_pointsToIJ)
        btnGetLines = QPushButton("Get Lines")
        btnGetLines.clicked.connect(self._on_click_getLines)
        
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.fieldTableName , 1, 1, 1,  2)
        self.layout().addWidget(btnGetPoints        , 1, 3, 1, -1)
        self.layout().addWidget(self.histogramMinBox, 2, 1, 1,  1)
        self.layout().addWidget(btnResetRange       , 2, 2, 1,  1)
        self.layout().addWidget(self.histogramMaxBox, 2, 3, 1,  1)
        self.layout().addWidget(self.canvas         , 3, 1, 1, -1)
        self.layout().addWidget(self.sliderMin      , 4, 1, 1, -1)
        self.layout().addWidget(self.sliderMax      , 5, 1, 1, -1)
        self.layout().addWidget(changeColormapButton, 6, 1, 1, -1)
        self.layout().addWidget(btnPointsToIJ       , 7, 1, 1, -1)
        self.layout().addWidget(btnGetLines         , 8, 1, 1, -1)
        
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
        self.resetHistogramRange()
        sliderMin = self.getValueInSlider(self.thresholdMin, self.histogramMin, self.histogramMax)
        sliderMax = self.getValueInSlider(self.thresholdMax, self.histogramMin, self.histogramMax)

        self.setSliderMin(sliderMin)
        self.setSliderMax(sliderMax)
        
        self.drawHistogram()

    def setSliderMin(self, value):
        self.sliderMin.setValue(value)
        self.sliderMin.setSliderPosition(value)

    def setSliderMax(self, value):
        self.sliderMax.setValue(value)
        self.sliderMax.setSliderPosition(value)

    def getValueInSlider(self, floatValue, histoMin, histoMax):
        valueOut = int(_MAXIMUM_HISTOGRAM * (floatValue - histoMin) / (histoMax - histoMin))
        return valueOut;

    def getValueFromSlider(self, intValue, histoMin, histoMax):
        valueOut = histoMin + (float(intValue) / float(_MAXIMUM_HISTOGRAM)) * (histoMax - histoMin)
        return valueOut;

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
        
        range = (self.histogramMin, self.histogramMax)

        # plot data
        self.ax.hist(self.confidence, bins='fd', range=range)
        self.ax.axvline(self.thresholdMin, color='k', linestyle='dashed', linewidth=1)
        self.ax.axvline(self.thresholdMax, color='k', linestyle='dashed', linewidth=1)
   
        # refresh canvas
        self.canvas.draw()

    def _on_click_get_points(self):
        #print(str(self.fieldTableName.text()))
        self.selectedPoints, self.confidence = self.getPoints(self.fieldTableName.text())
        self.points[id(self.selectedPoints)] = self.selectedPoints, self.confidence
        self.drawHistogram()

    def _on_click_resetRange(self):
        self.resetHistogramRange()


    def _on_click_pointsToIJ(self):
        self.pointsToIJ()

    def _on_click_changeColormap(self):
        self.changeColormap()

    def _on_click_getLines(self):
        self.getBridge()
        print("Fetching pairs from IJ")
        self.bridge.getPairs(self.fieldTableName.text())


    def changeSliderMin(self, value):
        self.thresholdMin = self.getValueFromSlider(value, self.histogramMin, self.histogramMax)
        anID = id(self.viewer.layers.selection.active)
        self.lowBound[anID] = self.thresholdMin
        if not self.ax:
            return
        points = self.selectedPoints
        if not points:
            return
        self.drawHistogram()
        self.setOutsidePointsBlack(points)
        points.refresh_colors() 

    def changeSliderMax(self, value):
        self.thresholdMax = self.getValueFromSlider(value, self.histogramMin, self.histogramMax)
        anID = id(self.viewer.layers.selection.active)
        self.highBound[anID] = self.thresholdMax
        if not self.ax:
            return
        points = self.selectedPoints
        if not points:
            return
        self.drawHistogram()
        self.setOutsidePointsBlack(points)
        points.refresh_colors()

    def resetHistogramRange(self):
        tMin = self.thresholdMin
        tMax = self.thresholdMax
        self.thresholdMin = 0
        self.thresholdMax = _MAXIMUM_HISTOGRAM+1
        self.histogramMin = min(self.confidence)
        self.histogramMax = max(self.confidence)
        self.thresholdMin = tMin
        self.thresholdMax = tMax
        self.changeHistogramMin(self.histogramMin)
        self.changeHistogramMax(self.histogramMax)


    def changeHistogramMin(self,value):
        self.histogramMin = value
        self.histogramMinBox.setValue(self.histogramMin)
        sliderMin = self.getValueInSlider(self.thresholdMin, self.histogramMin, self.histogramMax)
        sliderMax = self.getValueInSlider(self.thresholdMax, self.histogramMin, self.histogramMax)

        self.setSliderMin(sliderMin)
        self.setSliderMax(sliderMax)
        self.drawHistogram()

    def changeHistogramMax(self,value):
        self.histogramMax = value
        self.histogramMaxBox.setValue(self.histogramMax)
        sliderMin = self.getValueInSlider(self.thresholdMin, self.histogramMin, self.histogramMax)
        sliderMax = self.getValueInSlider(self.thresholdMax, self.histogramMin, self.histogramMax)

        self.setSliderMin(sliderMin)
        self.setSliderMax(sliderMax)
        self.drawHistogram()
        
    def setOutsidePointsBlack(self,points):
        p = points.properties['confidence']
        #print(str(p))
        print("Bounds = ["+str(self.thresholdMin)+"; "+str(self.thresholdMax)+"]")
        for i in range(0, len(p)):
            if self.confidence[i]>self.thresholdMax or self.confidence[i]<self.thresholdMin:
                p[i] = 0
            else:
                p[i] = self.confidence[i]

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
        points.face_colormap=colormaps[self.colormapID]
        self.colormapID=(self.colormapID+1)%len(colormaps)
        points.refresh_colors() 

    def pointsToIJ(self):
        if not self.selectedPoints:
            return
        print("Sending points to IJ")
        self.getBridge().pointsToIJ(self.selectedPoints)

    def getSelectedLayer(self):
        points = self.viewer.layers.selection.active
        #print("Type of the active Layer Proxy :" + str(type(points)))
        if str(type(points)) != "<class 'napari.utils._proxies.PublicOnlyProxy'>":
            return None

        #print("Type of the active Layer :" + str(type(points.__wrapped__)))
        if str(type(points.__wrapped__)) != "<class 'napari.layers.points.points.Points'>":
            return None
        
        return points
