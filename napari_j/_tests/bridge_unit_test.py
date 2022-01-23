#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 23 22:19:32 2022

@author: baecker
"""

import sys
sys.path.append('./napari_j/_tests/surrogate')
from surrogate import surrogate
from unittest.mock import patch
from unittest.mock import Mock, MagicMock
import napari

def getImage():
    imageMock = MagicMock()
    imageMock.getDimensions.return_value = [2, 3, 1, 1, 1]
    stackMock = MagicMock()
    stackMock.getVoxels.return_value = [255, 0 ,128, 0, 64, 32]
    imageMock.getStack.return_value = stackMock
    return imageMock

IJMock = Mock()
IJMock.getImage = getImage
HyperStackConverterMock = Mock()

@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)
def test_constructor(Viewer):
    from ..bridge import Bridge
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    assert(bridge.viewer==viewer)

@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)
def test_getActiveImageFromIJ(Viewer):
    from ..bridge import Bridge 
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    bridge.getActiveImageFromIJ()
    assert(bridge.viewer.dims.ndisplay==3)
    
