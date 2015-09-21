# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'reportcol.ui'
#
# Created: Fri Sep 18 09:45:35 2015
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_wReportCol(object):
    def setupUi(self, wReportCol):
        wReportCol.setObjectName("wReportCol")
        wReportCol.resize(405, 41)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(wReportCol.sizePolicy().hasHeightForWidth())
        wReportCol.setSizePolicy(sizePolicy)
        wReportCol.setMaximumSize(QtCore.QSize(16777215, 41))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(wReportCol)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pbAddField = QtGui.QPushButton(wReportCol)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pbAddField.sizePolicy().hasHeightForWidth())
        self.pbAddField.setSizePolicy(sizePolicy)
        self.pbAddField.setMaximumSize(QtCore.QSize(20, 16777215))
        self.pbAddField.setObjectName("pbAddField")
        self.horizontalLayout_2.addWidget(self.pbAddField)
        self.pbRemoveField = QtGui.QPushButton(wReportCol)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pbRemoveField.sizePolicy().hasHeightForWidth())
        self.pbRemoveField.setSizePolicy(sizePolicy)
        self.pbRemoveField.setMaximumSize(QtCore.QSize(20, 16777215))
        self.pbRemoveField.setObjectName("pbRemoveField")
        self.horizontalLayout_2.addWidget(self.pbRemoveField)
        self.hlCBoxes = QtGui.QHBoxLayout()
        self.hlCBoxes.setObjectName("hlCBoxes")
        self.horizontalLayout_2.addLayout(self.hlCBoxes)

        self.retranslateUi(wReportCol)
        QtCore.QMetaObject.connectSlotsByName(wReportCol)

    def retranslateUi(self, wReportCol):
        wReportCol.setWindowTitle(QtGui.QApplication.translate("wReportCol", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.pbAddField.setText(QtGui.QApplication.translate("wReportCol", "+", None, QtGui.QApplication.UnicodeUTF8))
        self.pbRemoveField.setText(QtGui.QApplication.translate("wReportCol", "-", None, QtGui.QApplication.UnicodeUTF8))

