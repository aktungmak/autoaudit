import xml.etree.ElementTree as et
import json
import logging

import jsnmp
import util

description = "RX1290/TT12xx receivers"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new rx1200 at %s', ipa)
        self.info = {
            'productname'  : None,
            'unitname'     : None,
            'servicename'  : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'dallasid'     : None,
            'uptime'       : None
        }

        self.licenses = Licenses()
        self.optioncards = Cards()

        self.oids = {
            'productname'  : '1.3.6.1.4.1.1773.1.1.1.7.0',
            'ipaddress'    : '1.3.6.1.4.1.1773.1.1.1.1.0',
            'swversion'    : '1.3.6.1.4.1.1773.1.1.1.16.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0'
        }

        self.xpaths = {
            'unitname'     : './/Str[@N="Name"]',
            'servicename'  : './/Str[@N="m_serviceIdStat"]',
            'dallasid'     : './/*[@N="m_caDir5UniqueId"]'
        }

        self.config  = ''
        self.configp = None

        self.configuri = '/tcf?cgi=dcp&method=get'

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.licenses.clear()
        self.optioncards.clear()

        # first grab the config and parse it
        self.config = util.makeHttpRequest(self.info['ipaddress'], self.configuri, auth={"Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="})
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
            elif k in self.xpaths and self.configp is not None:
                # use xpath to get parameter, if we have vaild config
                temp = self.configp.find(self.xpaths[k])
                if temp is not None:
                    self.info[k] = temp.attrib['V'].strip()
                    # just need to format the dallas properly
                    if k is 'dallasid':
                        self.info[k] = int(self.info[k].replace(' ', ''))
                        self.info[k] = hex(self.info[k]).strip('0xL').zfill(12)
            else:
                # no idea, just leave as it is
                self.info[k] = v

        self._getLicenses()
        self._getOptionCards()

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

            # only care about licenses that have at least 1 enabled, apparently
            if tkey is not None and tval:
                self.licenses[tkey] = tval

    def _getOptionCards(self):
        # get all the slotnums first, in the same way as licenses
        # they are not contiguous, donc pas si simple!
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
            for k in self.optioncards.oids.keys():
                p = jsnmp.jsnmp()
                toid = '.'.join([self.optioncards.oids[k], str(snum)])
                p.snmpRequest(self.info['ipaddress'], toid)
                if p.payload:
                    p.decode()
                    tc[k] = p.decodeList[-1]

            self.optioncards["%02d - %s" % (tc['slotnum'], tc['type'])] = tc

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

class Licenses(dict):
    oids = {
        'idx'    : '1.3.6.1.4.1.1773.1.1.13.1.1',
        'name'   : '1.3.6.1.4.1.1773.1.1.13.1.2',
        'status' : '1.3.6.1.4.1.1773.1.1.13.1.3'
    }

if __name__ == '__main__':
    d = Device('192.168.32.205')
    print d.dumpToJson()
