from ijpb.fiji.IPythonProxy import IPythonProxy

p = IPythonProxy()
p.run("import napari")
p.run("from napari_j.bridge import Bridge")
p.run("viewer = napari.Viewer()")
p.run("bridge = Bridge(viewer)")
p.run("bridge.getActiveImageFromIJ()")
p.disconnect()
