import os
import shutil
import yaml
from pathlib import Path


class Config:
    """
        Manage the settings of napari-j.
    """

    def __init__(self):
        self.config = None
        self.home = os.getcwd()
        self.dir = Path.home().joinpath(".napari-j")
        self.jvmPath = None
        self.fijiPath = None
        self.autostartFIJI = None
        self.create()
        self.read()

    def create(self):
        """
            If it doesn't already exist, create a config file with the name 'napari.yml'.
        """
        if not self.dir.exists():
            self.dir.mkdir()
        configFile = self.dir.joinpath("naparij.yml")
        if not configFile.exists():
            self.config = {'connection': {'fiji_path': str(Path.home()), 'jvm_path': str(Path.home()), 'autostart_fiji': False}}
            with configFile.open(mode='w') as file:
                yaml.dump(self.config, file)

    def read(self):
        with self.dir.joinpath('naparij.yml').open() as file:
            params = yaml.load(file, Loader=yaml.FullLoader)
        self.config = params
        connectionParams = params['connection']
        self.jvmPath = connectionParams['jvm_path']
        self.fijiPath = connectionParams['fiji_path']
        self.autostartFIJI = connectionParams['autostart_fiji']

    def save(self):
        with self.dir.joinpath("naparij.yml").open(mode='w') as file:
            yaml.dump(self.config, file)

    def setFIJIPath(self, aPath):
        self.fijiPath = aPath
        self.config['connection']['fiji_path'] = aPath

    def setJVMPath(self, aPath):
        self.jvmPath = aPath
        self.config['connection']['jvm_path'] = aPath

    def setAutostartFIJI(self, aBool):
        self.autostartFIJI = aBool
        self.config['connection']['autostart_fiji'] = aBool

    def makeSettingsDefault(self):
        shutil.copy(str(self.dir.joinpath("naparij.yml")),
                    str(self.dir.joinpath("naparij_default.yml")))

    def resetSettings(self):
        shutil.copy(str(self.dir.joinpath("naparij_default.yml")),
                    str(self.dir.joinpath("naparij.yml")))

    def isLimeSegInstalled(self):
        path = os.path.join(self.fijiPath, "jars/")
        files = os.listdir(path)
        for aFile in files:
            if aFile.startswith('limeseg'):
                return True
        return False
