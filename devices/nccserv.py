import xml.etree.ElementTree as et
import json
import logging

from PySide.QtCore import QProcess

import jsnmp
import util
import sys

SYSINFO_CMD = "systeminfo /S %s /U %s /P %s"

description = "nCC Server"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new nCC server at %s', ipa)
        self.info = {
            'productname'  : None,
            'unitname'     : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'uptime'       : None
        }

        self.licenses = Licenses()
        self.interfaces = Interfaces()

        self.oids = {
            'productname'  : '1.3.6.1.4.1.1773.3.1.1.1.0',
            'unitname'     : '1.3.6.1.2.1.1.5.0',
            'ipaddress'    : '',
            'swversion'    : '1.3.6.1.4.1.1773.3.1.1.10.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0'
        }

        # ncc server doesn't have a config?
        self.config  = ''

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.licenses.clear()
        self.interfaces.clear()

        # fill the info dict, by any means neccessary
        for k, v in self.info.iteritems():
            if k in self.oids:
                # use snmp to get parameter
                p = jsnmp.jsnmp()
                p.snmpRequest(self.info['ipaddress'], self.oids[k])
                if p.payload:
                    p.decode()
                    if p.decodeList[-1] is not None:
                        self.info[k] = p.decodeList[-1]
            else:
                # no idea, just leave as it is
                self.info[k] = v

        # overide the name, since nCC calls itself "SNMP Agent" like a douche
        self.info['productname'] = 'nCompass Server'

        # run the special method to get systeminfo, and add it to info
        self.info.update(self._getSystemInfo())

        self._getLicenses()
        self._getInterfaces()

    def _getLicenses(self):
        # get ids first
        # keep get-nexting until we get to the next oid
        rootOID = self.licenses.oids['idx']
        nextOID = rootOID
        idxs = []
        while True:
            p = jsnmp.jsnmp()
            p.snmpRequest(self.info['ipaddress'], nextOID, getNext=True)
            if p.payload:
                p.decode()
                if not rootOID in p.decodeList[-2]:
                    break
                idxs.append(p.decodeList[-1])
                nextOID = p.decodeList[-2]
            else:
                break

        # then get the names and status for those idxs
        # and make an object for each of them
        for idx in idxs:
            tkey = None
            tval = None
            p = jsnmp.jsnmp()
            nameoid = '.'.join([self.licenses.oids['name'], str(idx)])
            p.snmpRequest(self.info['ipaddress'], nameoid)
            if p.payload:
                p.decode()
                tkey = p.decodeList[-1]

            p = jsnmp.jsnmp()
            statusoid = '.'.join([self.licenses.oids['status'], str(idx)])
            p.snmpRequest(self.info['ipaddress'], statusoid)
            if p.payload:
                p.decode()
                tval = (p.decodeList[-1] == 2)

            if tkey is not None and tval is not None:
                self.licenses[tkey] = tval

    def _getInterfaces(self):
        # get ip addresses first
        # keep get-nexting until we get to the next oid
        rootOID = self.interfaces.oids['entidx']
        nextOID = rootOID
        idxs = []
        while True:
            p = jsnmp.jsnmp()
            p.snmpRequest(self.info['ipaddress'], nextOID, getNext=True)
            if p.payload:
                p.decode()
                if not rootOID in p.decodeList[-2]:
                    break
                idxs.append(p.decodeList[-1])
                nextOID = p.decodeList[-2]
            else:
                break


        # then get the parameters for those idxs
        # and make an object for each of them
        for idx in idxs:
            if idx.startswith('127'):
                # loopback, don't care
                continue
            ti = {}

            p = jsnmp.jsnmp()
            ipaddressoid = '.'.join([self.interfaces.oids['ipaddress'], str(idx)])
            p.snmpRequest(self.info['ipaddress'], ipaddressoid)
            if p.payload:
                p.decode()
                ti['ipaddress'] = p.decodeList[-1]

            # for the next parameters, we are querying a different table
            # need to use 'ifidx' instead to index into that table
            p = jsnmp.jsnmp()
            ifidxoid = '.'.join([self.interfaces.oids['ifidx'], str(idx)])
            p.snmpRequest(self.info['ipaddress'], ifidxoid)
            if p.payload:
                p.decode()
                ti['ifidx'] = p.decodeList[-1]

            p = jsnmp.jsnmp()
            nameoid = '.'.join([self.interfaces.oids['name'], str(ti['ifidx'])])
            p.snmpRequest(self.info['ipaddress'], nameoid)
            if p.payload:
                p.decode()
                # the names are null-term strings, so trim that
                ti['name'] = p.decodeList[-1][:-1]

            p = jsnmp.jsnmp()
            macaddressoid = '.'.join([self.interfaces.oids['macaddress'], str(ti['ifidx'])])
            p.snmpRequest(self.info['ipaddress'], macaddressoid)
            if p.payload:
                p.decode()
                # need to pretty print the bytes as a mac address:
                ti['macaddress'] = ':'.join(['%02x' % ord(b) for b in p.decodeList[-1]])

            p = jsnmp.jsnmp()
            statusoid = '.'.join([self.interfaces.oids['status'], str(ti['ifidx'])])
            p.snmpRequest(self.info['ipaddress'], statusoid)
            if p.payload:
                p.decode()
                ti['status'] = (p.decodeList[-1] == 1)

            # finally, add it to the dict!
            self.interfaces[ti['ifidx']] = ti

    def _getSystemInfo(self):
        "special method to extract server info, WINDOWS ONLY"
        if not sys.platform.lower().startswith('win'):
            # don't bother if any platform other than windows
            return {}

        qp = QProcess()
        qp.start(SYSINFO_CMD % (self.info['ipaddress'], 'Administrator', 'Ericss0n'))
        # this takes ages, give it a chance
        qp.waitForFinished(60000)

        if qp.exitCode() != 0:
            # looks like that was the wrong password...
            # its probably an older system, try the other pass
            qp = QProcess()
            qp.start(SYSINFO_CMD % (self.info['ipaddress'], 'Administrator', 'admin'))
            qp.waitForFinished(60000)

        if qp.exitCode() != 0:
            # still no luck, log it and give update
            return {}

        # otherwise, process the result!
        temp = {}
        for line in unicode(qp.readAllStandardOutput()).splitlines():
            if 'Hotfix' in line:
                # don't bother with the rest
                break
            try:
                k, v = line.split(':', 1)
            except ValueError:
                # malformed k/v pair, skip
                continue

            k = k.strip()
            v = v.strip()
            if k and v:
                temp[k] = v

        print "exit code:",
        # if qp.exitCode() != 0:

        return temp

    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'licenses':    self.licenses,
            'interfaces':  self.interfaces
        }

        return json.dumps(tobj)

class Licenses(dict):
    oids = {
        'idx'    : '1.3.6.1.4.1.1773.1.1.13.1.1',
        'name'   : '1.3.6.1.4.1.1773.1.1.13.1.2',
        'status' : '1.3.6.1.4.1.1773.1.1.13.1.3'
    }

class Interfaces(dict):
    oids = {
        'entidx'     : '1.3.6.1.2.1.4.20.1.1',
        'name'       : '1.3.6.1.2.1.2.2.1.2',
        'ipaddress'  : '1.3.6.1.2.1.4.20.1.1',
        'macaddress' : '1.3.6.1.2.1.2.2.1.6',
        'status'     : '1.3.6.1.2.1.2.2.1.8',
        'ifidx'      : '1.3.6.1.2.1.4.20.1.2'
    }


if __name__ == '__main__':
    d = Device('192.168.118.11')
    print d.dumpToJson()
