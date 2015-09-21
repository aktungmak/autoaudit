import logging
import time
import sys
import webbrowser

from PySide.QtCore import *
from PySide.QtGui import *

import DevicePalette
import DeviceTreeModel
import generated.guiMain
import ProductTreeModel
import ReportWin
import ScanTask
import devices.util as util

lg = logging.getLogger('autoaudit')

class MainWin(QMainWindow):
    """
        This is the main application view. It manages the
        task of pre-filtering and scanning for devices,
        as well as viewing results in a tree view.
        The other views (such as reporting) are all launched
        from here.
    """
    def __init__(self, providedTo, parent=None):
        super(MainWin, self).__init__(parent)
        lg.debug('MainWin __init__ called')
        self.ui = generated.guiMain.Ui_MainWindow()
        self.ui.setupUi(self)

        # this mutex protects the current count for the progress bar
        self.pbMutex = QMutex()

        # configure action groups
        self.modelActionGroup = QActionGroup(self)
        self.ui.actionIPAddress.setActionGroup(self.modelActionGroup)
        self.ui.actionUnitType.setActionGroup(self.modelActionGroup)

        # this is the currently selected model.
        # use this when creating a new model, and
        # change it when the model should be different
        self.modelClass = ProductTreeModel.ProductTreeModel
        self.resetModel()
        self.ui.actionUnitType.setChecked(True)
        self.ui.treeView.setUniformRowHeights(True)
        self.ui.treeView.setHeaderHidden(True)
        self.ui.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.treeView.setSelectionBehavior(QAbstractItemView.SelectItems)
        # when the user opens a branch, make sure they can see its name
        self.ui.treeView.expanded.connect(
            lambda x: self.ui.treeView.resizeColumnToContents(x.column())
        )

        # configure and attach the palette view
        self.palette = QDockWidget('Device Palette', self)
        self.palette.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        dp = DevicePalette.DevicePalette()
        self.palette.setWidget(dp)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.palette)

        # hook up buttons and menu actions
        self.ui.pbStart.clicked.connect(self.doScan)
        self.ui.pbTargetDir.clicked.connect(self.doSetTargetDir)
        self.ui.actionIPAddress.triggered.connect(self.onActionIPAddress)
        self.ui.actionUnitType.triggered.connect(self.onActionUnitType)
        self.ui.actionCreateReport.triggered.connect(self.onActionCreateReport)
        self.ui.actionShowPalette.triggered.connect(self.onActionShowPalette)
        self.ui.treeView.customContextMenuRequested.connect(self.onTreeViewRightClick)

        # put on the supplied to info, for tracking
        ptl = QLabel(providedTo)
        ptl.setFrameStyle(QFrame.Panel|QFrame.Sunken)
        self.ui.statusbar.addPermanentWidget(ptl)

        #Debug#####
        self.ui.leStart.setText('192.168.103.10')
        self.ui.leFinish.setText('192.168.103.30')
        ###########

        self.ui.leTargetDir.setText(QDir.currentPath())
        self.ui.leTargetDir.editingFinished.connect(self.resetModel)


        # Flag to indicate a scan is already in progress
        self.scanTask = None

        # var for report window to ensure only one is ever open
        self.reportWin = None

        lg.debug('MainWin __init__ complete')

    def doScan(self):
        "start a scan if idle, or stop the current scan"
        strt = self.ui.leStart.text()
        fini = self.ui.leFinish.text()

        if self.scanTask is None:
            lg.debug('starting a new scan')
            # there is no scan currently running, so begin one
            self.postMessage("Scanning...")

            rdirstr = QDir(self.ui.leTargetDir.text()).filePath(time.strftime("%Y-%m-%d_%H-%M-%S"))
            rdir = QDir(rdirstr)
            if not rdir.exists():
                lg.debug('creating a new directory for the result: %s' % rdir.absolutePath())
                rdir.mkdir(rdir.absolutePath())
            # TODO figure out how to stop result dirs nesting
            self.ui.leTargetDir.setText(rdirstr)
            self.ui.leTargetDir.editingFinished.emit()

            self.scanTask = ScanTask.ScanTask(strt, fini, rdir,
                self.ui.cbIgnoreUnk.isChecked(), self.ui.cbLocalhost.isChecked(), parent=self)
            self.scanTask.stepComplete.connect(self.incrementProgress)
            self.scanTask.finished.connect(self.onScanComplete)

            self.ui.treeView.setEnabled(False)
            self.ui.pbStart.setText('Stop')

            self.ui.progressBar.reset()
            self.ui.progressBar.setMinimum(1)
            self.ui.progressBar.setMaximum(self.scanTask.steps)
            self.scanTask.start()

        else:
            lg.debug('stopping the scan')
            # there is a scan running, the user wants to cancel
            self.ui.pbStart.setEnabled(False)
            self.scanTask.stopScan()
            self.postMessage("Stopping scan, waiting for last units to respond...")

            self.scanTask.finished.disconnect(self.onScanComplete)
            self.scanTask.finished.connect(self.onScanCancelled)

    def doSetTargetDir(self):
        "allow the user to choose a new directory for the results"
        lg.info('user requested target dir change, opening dialog...')
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.Option(QFileDialog.ShowDirsOnly)

        if dialog.exec_():
            fname = dialog.selectedFiles()[0]
            lg.info('new file selected: %s' % fname)
            self.ui.leTargetDir.setText(fname)
            self.ui.leTargetDir.editingFinished.emit()
            self.ui.treeView.resizeColumnToContents(0)

    def incrementProgress(self):
        self.pbMutex.lock()
        val = self.ui.progressBar.value()
        lg.debug('progress bar step %d / %d', val+1, self.ui.progressBar.maximum())
        self.ui.progressBar.setValue(val+1)
        self.pbMutex.unlock()
        self.ui.treeView.resizeColumnToContents(0)

    def onScanComplete(self):
        lg.info('scan complete, took %.2f seconds', self.scanTask.timetaken)

        self.postMessage("Scan complete, found %s units in %s"
            % (self.deviceModel.howManyHosts(),
               util.secondsToMinSec(self.scanTask.timetaken))
        )
        self.ui.treeView.setEnabled(True)
        self.ui.pbStart.setText('Go!')
        self.scanTask = None
        self.resetModel()

    def onScanCancelled(self):
        lg.info('scan cancelled by user, took %.2f seconds', self.scanTask.timetaken)

        self.postMessage("Scan cancelled, found %s units in %s"
            % (self.deviceModel.howManyHosts(),
               util.secondsToMinSec(self.scanTask.timetaken))
        )
        self.ui.treeView.setEnabled(True)
        self.ui.pbStart.setText('Go!')
        self.ui.pbStart.setEnabled(True)
        self.scanTask = None
        self.ui.treeView.resizeColumnToContents(0)

    def onActionIPAddress(self):
        if self.ui.actionIPAddress.isChecked():
            # not checked, so change mode
            lg.debug('changing model to DeviceTreeModel...')
            self.modelClass = DeviceTreeModel.DeviceTreeModel
            self.resetModel()
            self.ui.actionIPAddress.setChecked(True)

    def onActionUnitType(self):
        if self.ui.actionUnitType.isChecked():
            # not checked, so change mode
            lg.debug('changing model to ProductTreeModel...')
            self.modelClass = ProductTreeModel.ProductTreeModel
            self.resetModel()
            self.ui.actionUnitType.setChecked(True)

    def onActionShowPalette(self):
        self.palette.show()
        self.palette.setFloating(False)

    def resetModel(self):
        lg.debug('resetting the model!')
        self.deviceModel = self.modelClass(QDir(self.ui.leTargetDir.text()))
        self.ui.treeView.setModel(self.deviceModel)
        self.ui.treeView.resizeColumnToContents(0)

    def onActionCreateReport(self):
        lg.debug('user requested report window')
        if self.reportWin is None:
            self.reportWin = ReportWin.ReportWin(self)
        self.reportWin.show()

    def postMessage(self, mesg):
        "convenience function to write on the statusbar"
        self.ui.statusbar.clearMessage()
        self.ui.statusbar.showMessage(mesg)

    def onTreeViewRightClick(self, position):
        "handle right clicks on the treeview"
        lg.debug("user right-clicked on the model!")
        indexes = self.ui.treeView.selectedIndexes()
        level = 0
        if len(indexes) == 1:
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1

        menu = QMenu()
        if level >= 0:
            menu.addAction("Copy Text", lambda: self.rcCopyText(indexes))
        if level == self.deviceModel.entityDepth:
            menu.addAction("Save Device Config")
            menu.addAction("Save Device info (JSON)")
            menu.addAction("Browse unit", lambda: self.rcBrowseUnit(indexes[0].data()))
            if sys.platform.lower().startswith('win'):
                menu.addAction("Telnet to unit", lambda: self.rcTelnetUnit(indexes[0].data()))
                menu.addAction("RDP to unit", lambda: self.rcRdpUnit(indexes[0].data()))

        menu.exec_(self.ui.treeView.viewport().mapToGlobal(position))


    def rcRdpUnit(self, ipa):
        lg.info("opening Remote Desktop to %s", ipa)
        cmdstr = "C:\\Windows\\System32\\mstsc.exe /v:%s" % ipa
        QProcess.startDetached(cmdstr)

    def rcTelnetUnit(self, ipa):
        # TODO actually start a telnet session
        lg.info("opening telnet session to %s", ipa)
        cmdstr = "C:\\Windows\\System32\\cmd.exe"
        QProcess.startDetached(cmdstr)

    def rcBrowseUnit(self, ipa):
        lg.info('opening browser to http://%s/', ipa)
        webbrowser.open(ipa)

    def rcCopyText(self, indexes):
        """
            copy text at indexes to clipboard,
            after a right click
            list<QModelIndex> indexes: the clicked indexes
        """
        # the user might not have selected the items contiguously
        data = [(i.row(), i.column(), i.data()) for i in indexes]
        data.sort()

        # keep track of the row we are on, to insert appropriate newlines
        prevrow = data[0][0]
        text = u''

        for tup in data:
            # if end of row (second column) add a newline
            if tup[0] != prevrow:
                text = "".join([text, '\n', unicode(tup[2]), '\t'])
                prevrow = tup[0]
            # otherwise put a tab in there
            else:
                text = "".join([text, unicode(tup[2]), '\t'])

        clip = QApplication.clipboard()
        clip.setText(text)

