import json
import logging

import jsnmp
import util

description = "Unknown device"

lg = logging.getLogger('autoaudit')

class Device(object):
    """
        An unknown Device that still conforms to the
        interface, but everything is unpopulated.
        str ipa: the IP sddress this was found at
    """
    def __init__(self, ipa):
        lg.debug('creating new unknown device at %s', ipa)
        self.info = {
            'productname'  : 'UNKNOWN',
            'unitname'     : 'UNKNOWN',
            'ipaddress'    : ipa,
        }

        self.licenses = Licenses()
        self.optioncards = Cards()
        self.oids = {
            'productname'  : '1.3.6.1.2.1.1.1',
            'unitname'     : '1.3.6.1.2.1.1.5',
        }
        self.xpaths = {}

        self.config  = ''
        self.configp = None
        self.configuri = ''

        # now populate all the fields
        self.populate()

    def populate(self):
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

    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'licenses':    self.licenses,
            'optioncards': self.optioncards
        }
        return json.dumps(tobj)

class Cards(dict):
    oids = {}

class Licenses(dict):
    oids = {}


if __name__ == '__main__':
    d = Device('192.168.35.101')
    print d.dumpToJson()
