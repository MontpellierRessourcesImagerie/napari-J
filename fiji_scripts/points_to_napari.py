from ijpb.fiji.IPythonProxy import IPythonProxy

p = IPythonProxy()
p.run("from napari_j.bridge import Bridge")
p.run("bridge = Bridge(viewer)")
p.run("bridge.displayPoints()")
p.disconnect()
