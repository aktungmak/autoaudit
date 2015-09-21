import xml.etree.ElementTree as et
import json
import logging
import re

import jsnmp
import util

description = "TT6120 TS Processor"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new tt6120 at %s', ipa)
        self.info = {
            'productname'  : None,
            'unitname'     : None,
            'ipaddress'    : ipa,
            'uptime'       : None
        }

        self.optioncards = Cards()

        self.oids = {
            'productname'  : '1.3.6.1.4.1.1773.1.1.1.7.0',
            'unitname'     : '',
            'ipaddress'    : '1.3.6.1.4.1.1773.1.1.1.1.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0'
        }

        # no configs on TT6120
        self.config  = ''

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.optioncards.clear()

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
            else:
                # no idea, just leave as it is
                self.info[k] = v

        #grab the unit name
        page = util.makeHttpRequest(self.info['ipaddress'], '/update_page')
        r = re.findall('top.product_name = "(.+?)";', page)
        if r: self.info['unitname'] = r[0]


        self._getOptionCards()

    def _getOptionCards(self):
        # get all the slotnums first
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

if __name__ == '__main__':
    d = Device('192.168.102.34')
    print d.dumpToJson()