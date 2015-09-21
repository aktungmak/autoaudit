import xml.etree.ElementTree as et
import json
import logging

import jsnmp
import util

description = "RX9500 bulk descrambler"

# TODO: convert this to XPO3 properly
lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new rx9500 at %s', ipa)
        self.info = {
            'productname'  : 'ViPENC',
            'unitname'     : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'sntpserver'   : None,
            'uptime'       : None,
            'serialnumber' : None
        }

        self.licenses = Licenses()
        self.optioncards = Cards()
        self.interfaces = Interfaces()


        self.oids = {
            'ipaddress'    : '1.3.6.1.4.1.1773.1.1.1.1.0',
            'productname'  : '1.3.6.1.4.1.1773.1.1.1.7.0',
            'swversion'    : '1.3.6.1.4.1.1773.1.1.1.16.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0'
        }

        self.endpoints = {
            'sntpserver'   : '/api/system/sntp',
            'serialnumber' : '/api/hardware/chassis'
        }

        self.jpaths = {
            'sntpserver'   : ['collection', 'data', 'ipAddress', 'value'],
            'serialnumber' : ['collection', 'data', 'serialNumber', 'value']
        }

        self.config  = ''
        self.configp = None

        self.configuri = '/api/profiles/active/config'
        self.licenseuri = '/api/license/licenses.xml'

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.licenses.clear()
        self.optioncards.clear()

        # first grab the config and parse it
        self.config = util.makeHttpRequest(self.info['ipaddress'], self.configuri)
        try:
            self.configp = et.fromstring(self.config)
        except et.ParseError as e:
            lg.error("couldn't understand config from %s: %s", self.info['ipaddress'], e)

        # fill the info dict, by any means neccessary
        for k, v in self.info.iteritems():
            if k in self.oids:
                # use snmp to get parameter
                p = jsnmp.jsnmp()
                p.snmpRequest(self.info['ipaddress'], self.oids[k])
                if p.payload:
                    p.decode()
                    self.info[k] = p.decodeList[-1] if p.decodeList[-1] else v
            # use the clunky api to get the values
            elif k in self.endpoints and k in self.jpaths:
                resp = util.makeHttpRequest(self.info['ipaddress'], self.endpoints[k])
                jdat = json.loads(resp)
                self.info[k] = util.getp(self.jpaths[k], jdat)
            else:
                # no idea, just leave as it is
                self.info[k] = v

        self._getLicenses()
        self._getOptionCards()
        self._getInterfaces()

    def _getLicenses(self):
        # rx9500 does not present licenses via SNMP
        # so, get them via XML!
        data = util.makeHttpRequest(self.info['ipaddress'], self.licenseuri)
        try:
            datap = et.fromstring(data)
        except et.ParseError as e:
            lg.error("couldn't parse licenses from %s: %s", self.info['ipaddress'], e)
            return
        licenselist = datap.findall('.//activeLicenses/licenseKey')
        try:
            for license in licenselist:
                desc = license.find('licenseDescription').text
                amnt = int(license.find('instances').text)

                self.licenses[desc] = amnt
        except Exception as e:
            lg.exception(e)
            lg.error("malformed XPO3 license file received from %s", self.info['ipaddress'])


    def _getOptionCards(self):
        # get all the slotnums first, in the same way as licenses
        # they are not contiguous!
        rootOID = self.optioncards.oids['slotnum']
        nextOID = rootOID
        snums = []
        while True:
            p = jsnmp.jsnmp()
            p.snmpRequest(self.info['ipaddress'], nextOID, getNext=True)
            if p.payload:
                p.decode()
                if not rootOID in p.decodeList[-2]:
                    break
                snums.append(p.decodeList[-1])
                nextOID = p.decodeList[-2]
            else:
                break

        for snum in snums:
            tc = {}
            # this device uses oids and xpaths, so concat the two key lists
            for k in self.optioncards.oids.keys() + self.optioncards.xpaths.keys():
                if k in self.optioncards.oids:
                    p = jsnmp.jsnmp()
                    # notice that we add 1 to snum, the instaces are 1-indexed
                    toid = '.'.join([self.optioncards.oids[k], str(snum+1), str(0)])
                    p.snmpRequest(self.info['ipaddress'], toid)
                    if p.payload:
                        p.decode()
                        tc[k] = p.decodeList[-1]
                elif k in self.optioncards.xpaths and self.configp is not None:
                    # use xpath to get parameter, if we have vaild config
                    # there is an irritating corner case for the chipid
                    if k == 'chipid' and snum == 0:
                        temp = self.configp.find('.//host//chipId')
                    else:
                        temp = self.configp.find(self.optioncards.xpaths[k] % snum)
                    if temp is not None and 'value' in temp.attrib:
                        tc[k] = temp.attrib['value'].strip()


            self.optioncards["%02d - %s" % (tc['slotnum'], tc['type'])] = tc

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

    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'licenses':    self.licenses,
            'optioncards': self.optioncards
        }

        return json.dumps(tobj)

class Cards(dict):
    oids = {
        'slotnum'      : '1.3.6.1.4.1.1773.1.1.3.1.1',
        'swversion'    : '1.3.6.1.4.1.1773.1.1.3.1.4',
        'hwversion'    : '1.3.6.1.4.1.1773.1.1.3.1.5',
        'fwversion'    : '1.3.6.1.4.1.1773.1.1.3.1.7',
        'serialnumber' : '1.3.6.1.4.1.1773.1.1.3.1.8',
        'type'         : '1.3.6.1.4.1.1773.1.1.3.1.9'
    }

    xpaths = {
        'chipid'     : './/slot[%s]//chipId'
    }

class Licenses(dict):
    oids = {}

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
    # d = Device('192.168.103.29')
    d = Device('192.168.32.91')
    print d.dumpToJson()
