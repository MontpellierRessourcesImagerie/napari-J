from ijpb.fiji.IPythonProxy import IPythonProxy

p = IPythonProxy()
p.run("import napari")
p.run("viewer = napari.Viewer()")
p.disconnect()
