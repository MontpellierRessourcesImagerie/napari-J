#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 23 22:19:32 2022

@author: baecker
"""

import sys
sys.path.append('./napari_j/_tests/surrogate')
if __name__ == '__main__':
    from surrogate.surrogate import surrogate
else:
    from surrogate import surrogate
from unittest.mock import patch
from unittest.mock import Mock, MagicMock
import napari
import numpy as np

def getImage():
    imageMock = MagicMock()
    imageMock.getDimensions.return_value = [3, 2, 1, 1, 1]
    imageMock.getShortTitle.return_value = 'blobs'
    stackMock = MagicMock()
    stackMock.getVoxels.return_value = [255.0, 0.0 ,128.0, 0.0, 64.0, 32.0]
    imageMock.getStack.return_value = stackMock
    calibrationMock = MagicMock()
    calibrationMock.getZ.return_value = 2.5
    calibrationMock.getX.return_value = 1
    imageMock.getCalibration.return_value = calibrationMock
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
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
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
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
        from ..bridge import Bridge 
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    bridge.getActiveImageFromIJ()
    
    # Display should be set to 3D
    assert(viewer.dims.ndisplay==3)

    # The voxel data should be rearranged in the form expected by napari 
    actual = viewer.add_image.call_args[0]
    expected = np.array([[[[255.0, 0.0, 128.0], [0.0, 64.0, 32.0]]]])
    comparison = actual == expected
    assert(comparison.all())

    # The name should be C<channel-nr.>-<short title of the ij-image>
    assert(viewer.add_image.call_args[1]['name']=='C1-blobs')
    
    # The lut should be the first (or n-th) color defined in Bridge
    assert(viewer.add_image.call_args[1]['colormap']==bridge.colors[0])
    
    # The default blending should be additive
    assert(viewer.add_image.call_args[1]['blending']=='additive')
    
    # The z-scale should have been calculated as the ratio of the z-step and
    # the x-pixel size.
    assert(viewer.add_image.call_args[1]['scale'][0]==2.5)
    assert(viewer.add_image.call_args[1]['scale'][1]==1)    
    assert(viewer.add_image.call_args[1]['scale'][2]==1)
    
    # All layers are removed from napari before an image is fetched from ij.
    viewer.layers.__len__.return_value = 1
    bridge.getActiveImageFromIJ()
    bridge.viewer.layers.pop.assert_called_once()

@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)    
def test_getLabelsFromIJ(Viewer):
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
        from ..bridge import Bridge 
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    bridge.getLabelsFromIJ()

    # The image data should be of type int, independent from the image type in ij.
    actual = viewer.add_labels.call_args[0]
    expected = np.array([[[[255, 0, 128], [0, 64, 32]]]])
    comparison = actual == expected
    assert(comparison.all())
    assert(isinstance(actual[0][0][0][0][0], np.int_))
    
    # The name should be short title of the ij-image
    assert(viewer.add_labels.call_args[1]['name']=='blobs')
    
    # The z-scale should have been calculated as the ratio of the z-step and
    # the x-pixel size.
    assert(viewer.add_labels.call_args[1]['scale'][0]==2.5)
    assert(viewer.add_labels.call_args[1]['scale'][1]==1)    
    assert(viewer.add_labels.call_args[1]['scale'][2]==1)

@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)    
def test_getPixelsFromImageJ(Viewer):
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
        from ..bridge import Bridge
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    title, dims, zFactor, pixels = bridge.getPixelsFromImageJ()

    # The title should be the short-title of the image in ImageJ
    assert(title=='blobs')

    # The test image has a width of 3 pixels, a height of 2 pixels, one channel,
    # one z-slice and one time-frame.
    expected = [3, 2, 1, 1, 1]
    comparison = np.array(dims) == np.array(expected)
    assert(comparison.all())

    # The z-scale should have been calculated as the ratio of the z-step and
    # the x-pixel size.
    assert(zFactor==2.5)     
    
    # The pixel data is returned as a linear list with the order of dimensions
    # given by dim, i.e. xyczt.
    expected = np.array([255.0, 0.0, 128.0, 0.0, 64.0, 32.0])
    comparison = pixels == expected
    assert(comparison.all())

@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)    
def test_getMetadataFromImage(Viewer):
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
        from ..bridge import Bridge
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    image = getImage()
    title, dims, zFactor, size = bridge.getMetadataFromImage(image)

    # The title should be the short-title of the image in ImageJ
    assert(title=='blobs')

    # The test image has a width of 3 pixels, a height of 2 pixels, one channel,
    # one z-slice and one time-frame.
    expected = [3, 2, 1, 1, 1]
    comparison = np.array(dims) == np.array(expected)
    assert(comparison.all())

    # The z-scale should have been calculated as the ratio of the z-step and
    # the x-pixel size.
    assert(zFactor==2.5)

    # The size of one channel of the image is the product of the sizes of the
    # remaining dimensions (without c)
    assert(size==dims[0]*dims[1]*dims[3]*dims[4])
    assert(size==6)
    
@patch('napari.Viewer')
@surrogate('ij.measure.ResultsTable')
@surrogate('ij.IJ')
@patch('ij.IJ', IJMock)
@surrogate('ij.ImagePlus')
@surrogate('ij.WindowManager')
@surrogate('ij.plugin.HyperStackConverter')
@patch('ij.plugin.HyperStackConverter', HyperStackConverterMock)
def test_toHyperstack(Viewer):
    if __name__ == '__main__':
        from bridge import Bridge 
    else:    
        from ..bridge import Bridge
    viewer = napari.Viewer()
    bridge = Bridge(viewer)
    image = getImage()
    title, dims, zFactor, size = bridge.getMetadataFromImage(image)
    bridge.toHyperstack(image, dims)
    
    # If the converted image has a different id from the input image, the
    # input image is closed and the new image is shown.
    image.close.assert_called_once()
    
if __name__ == '__main__':
    test_constructor()
    test_getActiveImageFromIJ()
    test_getLabelsFromIJ()
    test_getPixelsFromImageJ()
    test_getMetadataFromImage()
    test_toHyperstack()

