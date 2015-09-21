import json
import logging

from PySide.QtCore import *
from PySide.QtGui import *
import jsonpath_rw as jpath

import generated.guiReportBuilder
import generated.guiReportColumn
import devices.util as util

lg = logging.getLogger('autoaudit')

# TODO make it so the user doesn't have to click "get available fields" with template

class ReportWin(QDialog):
    "QDialog to configure and produce a report from result dir"
    def __init__(self, parent=None):
        super(ReportWin, self).__init__()
        lg.debug('ReportWin __init__ called')
        self.parent = parent
        self.ui = generated.guiReportBuilder.Ui_Dialog()
        self.ui.setupUi(self)

        # create a list to contain the path lists
        self.availableFields = []

        # this holds all the device information from the folder to save reloading
        self.devicedicts = []

        # this keeps track of all the fields for easy access
        self.columns = []

        self.ui.pbSourceDir.clicked.connect(self.doSetSourceDir)
        self.ui.pbGetKeys.clicked.connect(self.getAvailableFields)
        self.ui.buttonBox.accepted.connect(self.runReport)
        self.ui.pbOutFile.clicked.connect(self.doSetTargetFile)
        self.ui.pbSaveTemplate.clicked.connect(self.saveReportTemplate)
        self.ui.pbLoadTemplate.clicked.connect(self.loadReportTemplate)

        lg.debug('ReportWin __init__ complete')

    def doSetSourceDir(self):
        lg.info('user requested source dir change, opening dialog...')
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.Option(QFileDialog.ShowDirsOnly)

        if dialog.exec_():
            fname = dialog.selectedFiles()[0]
            lg.info('new source dir selected for report: %s' % fname)
            self.ui.leSourceDir.setText(fname)
            self.ui.leSourceDir.editingFinished.emit()

    def doSetTargetFile(self):
        lg.info('user requested target file change, opening dialog...')
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setDefaultSuffix('csv')
        dialog.setNameFilter("CSV files (*.csv)")

        if dialog.exec_():
            fname = dialog.selectedFiles()[0]
            lg.info('new target file selected for report: %s' % fname)
            self.ui.leOutFile.setText(fname)
            self.ui.leOutFile.editingFinished.emit()

    def getAvailableFields(self):
        lg.debug("extracting available fields")
        # res must be a tuple so we can convert it to a set
        res = []
        self.devicedicts = []

        # first, grab all the pieces of json data from the files
        rdir = QDir(self.ui.leSourceDir.text())
        dirs = rdir.entryInfoList(filters=QDir.Dirs|QDir.NoDotAndDotDot)
        for d in dirs:
            fname = d.absoluteDir().filePath('{0}/{0}_data.json'.format(d.fileName()))
            lg.debug("trying to open file %s", fname)
            try:
                with open(fname, 'r') as f:
                    self.devicedicts.append(json.loads(f.read()))
            except (IOError, ValueError) as e:
                # skip it, since this is probably not a device directory...
                lg.error(e)
                lg.error("couldn't process dir: %s, skipping", fname)
                continue
        # for each json string
        for devicedict in self.devicedicts:
            # recurse through the keys of the device
            # check out util.yieldPath for how this is done
            for path in util.yieldPath(devicedict):
                # unsplit
                res.append(path)

        # now remove duplicates from res
        # it might be more efficient to use a tuple and convert to a set
        res = set(res)

        lg.debug("found %d available fields, updating field model", len(res))
        # copy the found fields into the instance variable
        self.availableFields = res
        self.addColumn()
        lg.debug("finished updating field model")

    def addColumn(self):
        lg.debug("creating a new column")
        col = QWidget(self)
        col.ui = generated.guiReportColumn.Ui_wReportCol()
        col.ui.setupUi(col)

        self.addComboBox(col.ui.hlCBoxes, 0, self.availableFields, col)

        col.ui.pbAddField.clicked.connect(self.addColumn)
        col.ui.pbRemoveField.clicked.connect(
            lambda: self.removeColumn(col)
        )
        self.columns.append(col)
        self.ui.saContents.layout().addWidget(col)
        lg.debug("added the column to the layout")

    def addComboBox(self, layout, index, searchspace, parent=None):
        lg.debug("might add a new combobox")

        lg.debug("index: %s", index)
        lg.debug("searchspace len: %s", len(searchspace))
        lg.debug("searchspace: %s", searchspace)

        # if it is not the last in the row, clean up the rest
        if index != layout.count():
            # remove all subsequent boxes and start again
            lg.debug("resetting the path from index %d", index)
            el = layout.takeAt(index)
            while el:
                el.widget().deleteLater()
                el = layout.takeAt(index)

        # now, add the next cb if the selection is not terminal
        if len(searchspace) > 1:
            # construct cb and add to layout
            cb = QComboBox(parent)
            layout.addWidget(cb)

            # first add the wildcard option, with all options after it
            tails = [path[1:] for path in searchspace if len(path) > 1]
            cb.addItem('*', userData=tails)

            # heads will be what populates the actual list
            heads = set([item[0] for item in searchspace])
            for head in sorted(heads):
                # tails are the possible continuations for that head
                # gets stored in the user data role
                tails = [path[1:] for path in filter(lambda x: x[0] == head, searchspace) if len(path) > 1]
                cb.addItem(head, userData=tails)

            # set the index to -1, forcing the user to make an initial selection
            cb.setCurrentIndex(-1)
            # link up the signal to produce more cb's
            cb.currentIndexChanged.connect(
                lambda: self.addComboBox(layout, index + 1, cb.itemData(cb.currentIndex(), Qt.UserRole), parent)
            )
            lg.debug("added the combobox to the column")
        else:
            lg.debug("terminal selection")

    def removeColumn(self, col):
        lg.debug("removing a column")
        lg.debug(self.columns)
        lg.debug(col)
        lg.debug(col in self.columns)
        self.columns.remove(col)
        self.ui.saContents.layout().removeWidget(col)
        col.deleteLater()

    def getAllPaths(self):
        "iterate throught the columns and return a list of clean string paths"
        ret = []
        for col in self.columns:
            temp = []
            for i in range(col.ui.hlCBoxes.count()):
                val = col.ui.hlCBoxes.itemAt(i).widget().currentText()
                temp.append(val)
            ret.append(temp)

        ret2 = []
        for field in ret:
            # some fields have spaces, and this trips up jpath
            # first, clean out qutoes from each field
            field = map(lambda tok: tok.replace('"', ''), field)
            # and then wrap each token in quotes
            field = map(lambda tok: '"%s"' % tok, field)
            ret2.append(field)

        return ret2

    def expandFields(self):
        lg.debug('expanding fields...')
        # check what the user selected
        fields = self.getAllPaths()
        lg.debug(fields)
        # if there are no wildcard * then we have nothing to do
        if not any(map(lambda x: '*' in x, sum(fields, []))):
            return fields

        # precompile the queries outside the loop
        queries = ['.'.join(['$']+field) for field in fields]
        queries = [jpath.parse(jp) for jp in queries]

        xfields = []
        # otherwise, check all the devices and expand out all the paths
        for device in self.devicedicts:
            for qry in queries:
                res = [r.full_path.tolist() for r in qry.find(device)]
                xfields.extend(res)

        # deduplication, because lists aren't hashable
        xfields = [list(x) for x in set(tuple(y) for y in xfields)]

        return xfields

    def runReport(self):
        lg.debug("generating report...")

        # get a list of path lists
        # TODO add a GUI control for expand
        expand = True
        if expand:
            fields = self.expandFields()
        else:
            fields = self.getAllPaths()
        lg.debug(fields)

        fname = self.ui.leOutFile.text()
        # used to show the result later on
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Result")

        # generate all the jpath queries here
        # by convrting from list of lists to jsonpath string
        # a lot of fields have spaces, so wrap with quotes
        queries = ['.'.join(['$']+
                        map(lambda x: '"%s"'%x, field))
                        for field in fields]
        queries = [jpath.parse(jp) for jp in sorted(queries)]

        try:
            with open(fname, 'w') as f:
                lg.info("writing report to %s", fname)
                # create and write the title first
                titles = ['|'.join(segs) for segs in fields]
                f.write(u','.join(titles)+u'\n')

                # for every device
                for device in self.devicedicts:
                    # extract each of the fields
                    row = []
                    for qry in queries:
                        value = [d.value for d in qry.find(device)]

                        # flatten list, convert to unicode and clean out commas
                        value = u'  '.join(map(lambda v: unicode(v).replace(',', ''), value))
                        row.append(value)
                    # write out the row
                    f.write(u','.join(row)+u'\n')
        except Exception as e:
            lg.error("couldn't save report: %s", e)
            msgBox.setText("Error saving report: %s" % e)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.exec_()
            raise e
            return
        else:
            lg.info("successfully saved report to %s", fname)
            msgBox.setText("Saved report to %s" % fname)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.exec_()

        # close the dialog with success, but don't delete it
        self.accept()

    def saveReportTemplate(self):
        lg.debug("Saving the current report template")

        lg.info('opening file select dialog...')
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setDefaultSuffix('tmpl')
        dialog.setNameFilter("Template files (*.tmpl)")

        if dialog.exec_():
            fname = dialog.selectedFiles()[0]
            lg.info('will save report template in: %s' % fname)

        with open(fname, 'wb') as f:
            for col in self.columns:
                for i in range(col.ui.hlCBoxes.count()):
                    val = col.ui.hlCBoxes.itemAt(i).widget().currentText()
                    f.write(val)
                    # this is a unicode info seperator one, btw
                    f.write(u'\u001F')
                f.write(u'\u001E')

    def loadReportTemplate(self):
        lg.debug("Loading a report template")

        lg.info('opening file select dialog...')
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setDefaultSuffix('tmpl')
        dialog.setNameFilter("Template files (*.tmpl)")

        if dialog.exec_():
            fname = dialog.selectedFiles()[0]
            lg.info('loading report template from: %s' % fname)

        with open(fname, 'rb') as f:
            data = f.read()
            # deserialise, and drop any empty strings
            columns = [[seg for seg in path.split(u'\u001F') if seg] for path in data.split(u'\u001E') if path]
            lg.debug(columns)
            for column in columns:
                lg.debug("creating a new column")
                col = QWidget(self)
                col.ui = generated.guiReportColumn.Ui_wReportCol()
                col.ui.setupUi(col)

                col.ui.pbAddField.clicked.connect(self.addColumn)
                col.ui.pbRemoveField.clicked.connect(
                    lambda x=col: self.removeColumn(x)
                )
                self.columns.append(col)
                self.ui.saContents.layout().addWidget(col)
                lg.debug("added the column to the layout")

                for seg in column:
                    # make a combobox
                    cb = QComboBox(col)
                    # add it to col.layout
                    col.ui.hlCBoxes.addWidget(cb)
                    # populate it with the text in seg
                    cb.addItem(seg)

if __name__ == '__main__':
    import sys

    ch = logging.StreamHandler()
    ft = logging.Formatter(fmt="[%(filename)10s:%(lineno)4s - %(funcName)15s()] %(message)s")

    lg.setLevel(logging.DEBUG)
    ch.setFormatter(ft)
    lg.addHandler(ch)

    app = QApplication(sys.argv)
    r = ReportWin()
    r.ui.leSourceDir.setText('C:/Users/greenj/Dropbox/autoaudit/phase4/dist/2015-07-03_14-31-11')
    r.ui.leOutFile.setText('C:/Users/greenj/Dropbox/autoaudit/phase4/dist/out.csv')
    r.getAvailableFields()
    r.show()


    sys.exit(app.exec_())