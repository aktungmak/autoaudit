import os
import types
import logging

from PySide.QtCore import *
from PySide.QtGui import *

import devices

import generated.guiPalette

lg = logging.getLogger('autoaudit')

class DevicePalette(QWidget):
    """
        a palette which shows all supported devices and allows
        them to be selected. Usually this will be shown inside
        a QDockWidget. Its primary use is on the MainWin to
        show what units the tool knows about and to pre-filter
        the search.
    """
    def __init__(self, parent=None):
        super(DevicePalette, self).__init__()
        self.parent = parent
        self.drivers = {}
        self.ui = generated.guiPalette.Ui_wPalette()
        self.ui.setupUi(self)

        self.ui.pbSelAll.clicked.connect(self.doSelectAll)
        self.ui.pbSelNone.clicked.connect(self.doSelectNone)

        self.deviceMap = {}

        # DEBUG
        # self.loadCruft()
        self.loadDrivers()

    def loadCruft(self):
        "test func to provide some sample data"
        for item in ['toaster', 'parasol', 'racecar', 'marigold']:
            qlwi = QListWidgetItem(item)
            qlwi.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled|Qt.ItemIsSelectable)
            qlwi.setCheckState(Qt.Checked)
            self.ui.lwDrivers.addItem(qlwi)


    def loadDrivers(self):
        "load all drivers in the devices module"
        self.deviceMap = dict([(mod.description, mod)
                            for mod
                            in devices.__dict__.values()
                            if isinstance(mod, types.ModuleType)
                            and hasattr(mod, 'Device')])

        for key in sorted(self.deviceMap):
            qlwi = QListWidgetItem(key)
            qlwi.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled|Qt.ItemIsSelectable)
            qlwi.setCheckState(Qt.Checked)
            self.ui.lwDrivers.addItem(qlwi)

        # TODO resize widget to fit
        # self.ui.lwDrivers.setMinimumWidth(self.ui.lwDrivers.sizeHintForColumn(0))
        # self.ui.lwDrivers.resize(self.ui.lwDrivers.contentsHeight())


    def getSelectedDevices(self):
        "return list of all checked drivers"
        rl = []
        for i in range(0, self.ui.lwDrivers.count()):
            item = self.ui.lwDrivers.item(i)
            if item.checkState():
                dev = self.deviceMap.get(item.text(), None)
                if dev is not None:
                    rl.append(dev)
        return rl


    def doSelectAll(self):
        "modify selection to check all"
        for i in range(self.ui.lwDrivers.count()):
            self.ui.lwDrivers.item(i).setCheckState(Qt.Checked)

    def doSelectNone(self):
        "modify selection to check none"
        for i in range(self.ui.lwDrivers.count()):
            self.ui.lwDrivers.item(i).setCheckState(Qt.Unchecked)

if __name__ == '__main__':
    dp = DevicePalette()
    print dp.loadDrivers()