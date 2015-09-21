import json
import logging
import telnetlib

import jsnmp
import util

description = "iPLEX encoders"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new iPLEX at %s', ipa)
        self.info = {
            'productname'  : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'uptime'       : None,
            'unitname'     : None,
            'serialnumber' : None
        }

        self.interfaces = Interfaces()

        self.oids = {
            'productname'  : '1.3.6.1.4.1.9.5.1.2.16.0',
            'swversion'    : '1.3.6.1.2.1.1.1.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0',
            'unitname'     : '1.3.6.1.2.1.1.5.0',
            'serialnumber' : '1.3.6.1.4.1.9.5.1.2.19.0'
        }

        self.xpaths = {}

        self.user = 'root'
        self.passwd = 'skystream'

        self.config = ''
        self.configp = None

        self.configuri = ''

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.interfaces.clear()

        # fill the info dict
        for k, v in self.info.iteritems():
            if k in self.oids:
                # use snmp to get parameter
                p = jsnmp.jsnmp()
                p.snmpRequest(self.info['ipaddress'], self.oids[k])
                if p.payload:
                    p.decode()
                    self.info[k] = p.decodeList[-1] if p.decodeList[-1] else v
            else:
                # no idea, just leave as it is
                self.info[k] = v

        self.getConfig()
        self._getInterfaces()

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

    def getConfig(self):
        tel = telnetlib.Telnet(self.info['ipaddress'])
        tel.read_until('login: ')
        tel.write(self.user + '\x0d\x0a')

        tel.read_until('Password: ')
        tel.write(self.passwd + '\x0d\x0a')

        tel.read_until(']')
        tel.write('show running-config\x0d\x0a')

        tel.read_until('?')
        tel.write('Y\x0d\x0a')

        self.config = tel.read_until('[')

        tel.close()

    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'interfaces':  self.interfaces
        }

        return json.dumps(tobj)

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
    d = Device('192.168.102.36')
    print d.config
    print d.dumpToJson()
