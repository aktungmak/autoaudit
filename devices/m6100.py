import xml.etree.ElementTree as et
import json
import logging

import jsnmp
import util

description = "Newtec M6100 Modulator"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new m6100 at %s', ipa)
        self.info = {
            'chipid'       : None,
            'ipaddress'    : ipa,
            'productname'  : None,
            'serialnumber' : None,
            'sntpserver'   : None,
            'swversion'    : None,
            'unitname'     : None,
            'uptime'       : None
        }

        self.licenses = Licenses()

        self.oids = {
            'chipid'       : '1.3.6.1.4.1.5835.5.2.100.1.1.3.0',
            'ipaddress'    : '1.3.6.1.4.1.5835.5.2.400.1.1.1.2',
            'productname'  : '1.3.6.1.4.1.5835.5.2.100.1.1.4.0',
            'serialnumber' : '1.3.6.1.4.1.5835.5.2.100.1.1.2.0',
            'sntpserver'   : '1.3.6.1.4.1.5835.5.2.100.1.8.3.2.1.2.1',
            'swversion'    : '1.3.6.1.4.1.5835.5.2.100.1.1.9.0',
            'unitname'     : '1.3.6.1.4.1.5835.5.2.100.1.1.1.0',
            'uptime'       : '1.3.6.1.2.1.1.3.0'
        }

        self.config  = ''

        self.loginuri = '/cgi-bin/pogui/auth/autologin'
        self.configuri = '/cgi-bin/pogui/diagnostics/download'

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.licenses.clear()

        # to get the config, must "log in" and get a token
        ldat = util.makeHttpRequest(self.info['ipaddress'], self.loginuri, method='POST')
        ldat = json.loads(ldat)
        token = ldat.get('login', {}).get('token', '')

        # now use it to request the config
        self.config = util.makeHttpRequest(self.info['ipaddress'], self.configuri, auth={"Cookie": "token="+token})

        for k, v in self.info.iteritems():
            if k in self.oids:
                p = jsnmp.jsnmp()
                p.snmpRequest(self.info['ipaddress'], self.oids[k])
                if p.payload:
                    p.decode()
                    self.info[k] = p.decodeList[-1] if p.decodeList[-1] else v
            else:
                # no idea, just leave as it is
                self.info[k] = v

        self._getLicenses()

    def _getLicenses(self):
        rootOID = self.licenses.oids['name']
        nextOID = rootOID
        idxs = []
        while True:
            p = jsnmp.jsnmp()
            p.snmpRequest(self.info['ipaddress'], nextOID, getNext=True)
            if p.payload:
                p.decode()
                if not rootOID in p.decodeList[-2]:
                    break
                self.licenses[p.decodeList[-1]] = True
                nextOID = p.decodeList[-2]
            else:
                break

    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'licenses':    self.licenses,
        }
        return json.dumps(tobj)

class Licenses(dict):
    oids = {
        'name'   : '1.3.6.1.4.1.5835.5.2.100.1.1.10.1.2',
    }

if __name__ == '__main__':
    d = Device('192.168.103.25')
    print d.config
    print d.dumpToJson()
