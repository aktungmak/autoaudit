import json

from PySide.QtCore import *

class DeviceTreeModel(QAbstractItemModel):
    """
        Model representing a results directory containing
        a directory for each Device found. Within this it 
        expects to find a JSON file containing info about
        the device. 
        It will then construct a dict of this data, and 
        the model provides an interface for accessing this.
        QDir rdir: A QDir pointing to the Device results
    """
    # at what depth in the tree do individual devices appear?
    # used for the context menu 
    entityDepth = 0
    def __init__(self, rdir, parent=None):
        super(DeviceTreeModel, self).__init__(parent)
        self.rdir = rdir

        self.devices = {}
        self.dirWatcher = QFileSystemWatcher()
        self.dirWatcher.addPath(self.rdir.absolutePath())
        self.dirWatcher.directoryChanged.connect(self.repopulate)

        self.rootItem = DeviceModel(('tree', 'root'), None)
        self.repopulate()

    def __del__(self):
        del self.rdir
        del self.devices
        del self.dirWatcher
        del self.rootItem

    def repopulate(self):
        """
            repopulate self.devices in response to a 
            change in self.rdir. Called automatically by
            self.dirWatcher.
        """
        self.devices = {}
        dirs = self.rdir.entryInfoList(filters=QDir.Dirs|QDir.NoDotAndDotDot)
        for d in dirs:
            fname = d.absoluteDir().filePath('{0}/{0}_data.json'.format(d.fileName()))
            try:
                with open(fname, 'r') as f:
                    td = json.loads(f.read())
            except (IOError, ValueError) as e:
                # skip it, since this is probably not a device directory...
                continue
            self.devices[d.fileName()] = td

        self.beginInsertRows(QModelIndex(), self.rowCount(), 0)
        self.setupModelData()
        self.endInsertRows()

    def setupModelData(self):
        self.rootItem = DeviceModel(('tree', 'root'), None)
        self.parentItem = {0: self.rootItem}
        items = self.devices.items()
        items.sort(key=lambda x: x[0].split('.'))
        for item in items:
            newparent = DeviceModel(item, self.rootItem)
            self.rootItem.appendChild(newparent)

    def howManyHosts(self):
        """
            how many hosts are there in the current 
            results dir? this isn't always the same 
            as the row count!
            out: count of dirs in the resuls dir
        """
        return len(self.rdir.entryList(filters=QDir.Dirs|QDir.NoDotAndDotDot))

    def columnCount(self, parent=None):
        if parent and parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return 2

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return item.data(index.column())
        if role == Qt.UserRole:
            if item:
                return item.data(index.column())

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        # here!
        if not childItem:
            return QModelIndex()

        parentItem = childItem.parent()

        if parentItem == self.rootItem or parentItem is None:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            p_Item = self.rootItem
        else:
            p_Item = parent.internalPointer()
        return p_Item.childCount()

class DeviceModel(object):
    def __init__(self, initObj, parentItem):
        self.parentItem = parentItem
        self.childItems = []

        key, value = initObj
        self.key = key
        self.value = value
        if isinstance(value, dict):
            self.itemData = key
            items = value.items()
            items.sort(key=lambda x: x[0].split('.'))
            for item in items:
                self.appendChild(DeviceModel(item, self))
        elif isinstance(value, list):
            self.itemData = key
            for item in value:
                self.appendChild(DeviceModel((None, item), self))
        else:
            self.itemData = u': '.join([unicode(key), unicode(value)])

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 2

    def data(self, column):
        if column == 0:
            return self.key
        elif column == 1 and type(self.value) is not dict and type(self.value) is not list:
            return self.value
        else:
            return ''

    def parent(self):
        if hasattr(self, 'parentItem'):
            return self.parentItem
        else:
            return QModelIndex()

    def absRow(self):
        parent = self
        rowcnt = 0
        while parent.parentItem is not None:
            rowcnt += parent.parentItem.childItems.index(self)
            parent = parent.parentItem  

        return rowcnt
        
    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0