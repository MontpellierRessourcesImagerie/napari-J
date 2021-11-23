from jpype import *
# Enable Java imports
import jpype.imports
# Pull in types
from jpype.types import *
import os
from pathlib import Path
import jupyter_client
import sys
from PyQt5 import QtCore
    
def startFIJI(aPath):
    os.chdir(aPath)
    startJVM(
        aPath + "/java/linux-amd64/jdk1.8.0_172/jre/lib/amd64/server/libjvm.so",
        "-ea",
        "-Dpython.cachedir.skip=false",
        "-Dplugins.dir=.",
        "-Xmx19639m",
        "-Djava.class.path=./jars/imagej-launcher-5.0.3.jar",
        "-Dimagej.dir=.",
        "-Dij.dir=.",
        "-Dfiji.dir=.",
        "-Dij.executable= "
    )
    for path in Path('./jars').rglob('*.jar'):
        addClassPath(aPath + str(path))
    for path in Path('./plugins').rglob('*.jar'):
        addClassPath(aPath + str(path))
    from net.imagej.launcher import ClassLauncher
    ClassLauncher.main(("-ijjarpath", "jars", "-ijjarpath", "plugins", "net.imagej.Main"))
    from ij import IJ, ImageJ
    IJ.setProperty('jupter_connection_file', jupyter_client.find_connection_file())
    IJ.setProperty('python_executable', sys.executable)
    
def startImageJ():
    path = '/media/baecker/DONNEES1/programs/fiji-linux64/Fiji.app/'
    startFIJI(path)
    
def startFIJIInThread():
    QtCore.QTimer.singleShot(0, startImageJ)
