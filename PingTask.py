import sys
import logging
import telnetlib
import time

from PySide.QtCore import *

import jsnmp
import devices.util as util

# this works, but not with pyinstaller
# from devices import *
# so do this instead
from devices import brocade, cisco, dev, elemental, en8000, en8100, eq8000, iplex, leitch, m6100, mx5000, mx5210, mx8400, nccserv, rx1200, rx8000, rx9500, sm6600, spr1000, svp1000, svp2000, tt6120, unk

lg = logging.getLogger('autoaudit')

if sys.platform.lower().startswith('win'):
    #WINDOWS
    PING_CMD = "ping -n 1 -w 1000 %s"
elif sys.platform.lower().startswith('linux'):
    #LiNUX
    PING_CMD = "ping -c 1 -w 1 %s"
elif sys.platform.lower().startswith('darwin'):
    #OSX
    PING_CMD = "ping -c 1 -W 1000 %s"
else:
    lg.info("This operating system '%s' is probably not supported", sys.platform)
    PING_CMD = "ping -c 1 -w 1 %s"


class PingTask(QObject, QRunnable):
    """
        QRunnable which contacts a single host using the
        system's ping command. If it gets a response,
        it will try to identify the host using the available
        Device drivers.
        str ipa: IP address of the host to be contacted
        str pdir: QDir showing where to put result directory
    """
    # signals need to be class vars, not instance vars
    complete = Signal(int)
    def __init__(self, ipa, pdir, ignoreUnk=True, parent=None):
        lg.debug("created a new PingTask for %s", ipa)
        self.ipa = ipa
        self.pdir = pdir
        self.ignoreUnk = ignoreUnk
        self.mainwin = parent

        # QRunnable does not inherit from QObject
        # need the slot capability from QObject
        # so inherit them both
        QObject.__init__(self)
        QRunnable.__init__(self)

    def run(self):
        try:
            if self.pingHost():
                # something there!
                found = self.decision()
                # if we are ignoring unk and it is unk, skip saving
                if (self.ignoreUnk and (found is unk)):
                    lg.debug("discarding device at %s since it is unknown", self.ipa)
                elif not (found in self.mainwin.palette.widget().getSelectedDevices()):
                    lg.debug("discarding %s at %s since is it deselected", found.description, self.ipa)
                else:
                    u = found.Device(self.ipa)
                    self.saveData(u)
                self.complete.emit(1)
            else:
                self.complete.emit(0)
        except Exception as e:
            lg.debug(e)
            self.complete.emit(0)


    def pingHost(self):
        """
            Run the system ping command in a separate QProcess,
            and block until it is complete.
        """
        qp = QProcess()
        qp.start(PING_CMD % self.ipa)
        qp.waitForFinished()
        return bool(qp.exitCode() == 0)

    def decision(self):
        """
            decide what kind of unit this is
            out: device module describing what is there
        """

        # first try SNMP to check cfgProductName
        # this works for Tandberg/Ericsson DEVICES only
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, '1.3.6.1.4.1.1773.1.1.1.7.0', getNext=False)
        if p.payload:
            p.decode()
            pname = p.decodeList[-1]
            if pname is None:
                pass
            elif 'RX95' in pname:
                return rx9500
            elif 'RX8' in pname:
                return rx8000
            elif 'RX12' in pname:
                return rx1200
            elif 'TT12' in pname:
                return rx1200
            elif 'ViPENC' in pname:
                return en8100
            elif 'CENC' in pname:
                return en8100
            elif 'EMSP' in pname or 'SPR' in pname:
                return spr1000
            elif 'EN80' in pname:
                return en8000
            elif 'E57' in pname:
                return en8000
            elif 'MX84' in pname:
                return mx8400
            elif 'SM66' in pname:
                return sm6600
            elif 'EQ80' in pname:
                return eq8000
            elif '6120' in pname:
                return tt6120
            elif '5210' in pname:
                return mx5210
            elif 'IPLEX' in pname:
                return iplex
            else:
                # todo: more device definitions needed
                return unk

        # maybe this is a SERVICE (eg nCC server)
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, '1.3.6.1.4.1.1773.3.1.1.1.0', getNext=False)
        if p.payload:
            p.decode()
            pname = p.decodeList[-1]
            if pname is None:
                pass
            elif 'nCompass' in pname:
                return nccserv

        # praps it is an old school NDS product?
        # try mx5000
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, '1.3.6.1.4.1.1855.2.21.1.1.2.0', getNext=False)
        if p.payload:
            p.decode()
            pname = p.decodeList[-1]
            if pname is None:
                pass
            else:
                return mx5000

        # it could be a cisco product
        ciscoOid = '1.3.6.1.4.1.9'
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, ciscoOid, getNext=True)
        if p.payload:
            p.decode()
            if ciscoOid in p.decodeList[0]:
                return cisco

        # or perhaps a brocade?
        brocadeOid = '1.3.6.1.4.1.1991'
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, brocadeOid, getNext=True)
        if p.payload:
            p.decode()
            if brocadeOid in p.decodeList[0]:
                return brocade

        # I have a feeling it is a newtec modulator
        newtecOid = '1.3.6.1.4.1.5835.5.2.100.1.1.4.0'
        p = jsnmp.jsnmp()
        p.snmpRequest(self.ipa, newtecOid)
        if p.payload:
            p.decode()
            if 'M6100' in p.decodeList[-1]:
                return m6100

        # lets try a few guesses using HTTP
        # to save time, make one request for the front page
        # and just read the data from there
        page = util.makeHttpRequest(self.ipa, '/')
        # is it an elemental/svp4000?
        if page and 'lemental' in page:
            return elemental

        # check if it is a dev
        if page and 'DEV Systemtechnik' in page:
            return dev

        # insert other searches within the root page here

        # svp2000 does things its own way...
        page = util.makeHttpRequest(self.ipa, '/objects')
        if page and 'SVP' in page:
            return svp2000

        # and SVP1000 uses port 8080
        page = util.makeHttpRequest(self.ipa, '/admin/login.php', port=8080)
        if page and 'goob' in page:
            return svp1000

        # now we are scraping the barrel, try telnet
        try:
            tel = telnetlib.Telnet(self.ipa, timeout=2)
        except Exception:
            pass
        else:
            header = tel.read_until('\r\n', 2)
            tel.close()

            # TODO find out why the socket gets reused
            # just wait a bit for now
            time.sleep(0.1)
            lg.debug("got telnet header: %s", header)
            if "LEITCH" in header.upper():
                return leitch

        # no idea, just mark it UNK
        return unk

    def saveData(self, data):
        mdir = QDir(self.pdir)
        mdir.mkdir(self.ipa)
        mdir.cd(self.ipa)
        conff = QFile(mdir.filePath("%s_conf.xml" % self.ipa))
        dataf = QFile(mdir.filePath("%s_data.json" % self.ipa))

        # first, write the config
        if conff.open(QIODevice.WriteOnly):
            if data.config:
                conff.write(data.config)
                conff.close()
        else:
            lg.error("Cannot create the file %s", conff.fileName())

        # now write the info file
        if dataf.open(QIODevice.WriteOnly):
            dataf.write(data.dumpToJson())
            dataf.close()
        else:
            lg.error("Cannot create the file %s", dataf.fileName())


if __name__ == '__main__':
    p = PingTask('192.168.103.25', QDir('.'))
    p.run()