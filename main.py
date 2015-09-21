import sys
import logging

from PySide.QtCore import *
from PySide.QtGui import *

import MainWin
import cpyprot

PROVIDED_TO = "WAYNE EVANS"

lg = logging.getLogger('autoaudit')
ft = logging.Formatter(fmt="[%(filename)10s:%(lineno)4s - %(funcName)15s()] %(message)s")
fh = logging.FileHandler('session.log')
ch = logging.StreamHandler()

lg.setLevel(logging.DEBUG)
fh.setFormatter(ft)
ch.setFormatter(ft)
lg.addHandler(fh)
lg.addHandler(ch)

if __name__ == '__main__':
    lg.debug('Application starting')

    if cpyprot.versionHasExpired():
        lg.debug('This software has expired, and will be destroyed.')
        cpyprot.haraKiri()
        sys.exit(2)

    # cleanlooks is way hot style
    QApplication.setStyle('cleanlooks')

    # DEBUG for use in ipython
    # app = QCoreApplication.instance()
    app = QApplication(sys.argv)

    # change colours if you want
    # pal = app.palette()
    # pal.setColor(QPalette.Base, Qt.black)
    # pal.setColor(QPalette.Text, Qt.white)
    # pal.setColor(QPalette.Highlight, Qt.blue)
    # app.setPalette(pal)

    lg.debug('Starting MainWindow')
    mw = MainWin.MainWin(PROVIDED_TO)
    mw.show()

    res = app.exec_()
    lg.debug('Exiting... Application returned %s', res)
    sys.exit(res)
