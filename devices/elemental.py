import xml.etree.ElementTree as et
import json
import logging

import util

description = "Elemental/SVP4000 encoder"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new Elemental at %s', ipa)
        self.info = {
            'productname'  : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'unitname'     : None,
        }

        self.interfaces = Interfaces()


        self.oids = {}

        self.xpaths = {
            'productname'  : './product',
            'swversion'    : './version',
            'unitname'     : './hostname',

        }

        self.config = ''
        self.configp = None

        self.configuri = '/api/live_events.xml'
        self.infouri = '/api/settings/version.xml'
        self.neturi = '/api/settings/network.xml'

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.interfaces.clear()
        self._getInterfaces()

        # the live event config is different from the info data
        self.config = util.makeHttpRequest(self.info['ipaddress'], self.configuri)

        # first grab the config and parse it
        verstr = util.makeHttpRequest(self.info['ipaddress'], self.infouri)
        try:
            verstrp = et.fromstring(verstr)
        except et.ParseError as e:
            lg.error("couldn't understand config from %s: %s", self.info['ipaddress'], e)
        else:
            for k in self.xpaths:
                r = verstrp.find(self.xpaths[k])
                if r is not None:
                    self.info[k] = r.text
            # Need to discriminate between Elemental/Ericsson
            if 'er' in self.info.get('swversion', ''):
                self.info['productname'] = 'SVP4000'
            else:
                self.info['productname'] = 'Elemental Live'



    def _getInterfaces(self):
        netstr = util.makeHttpRequest(self.info['ipaddress'], self.neturi)
        try:
            netstrp = et.fromstring(netstr)
        except et.ParseError as e:
            lg.error("couldn't understand network config from %s: %s", self.info['ipaddress'], e)
            return
        ifaces = netstrp.findall('.//eth_config')
        for i, iface in enumerate(ifaces):
            tmp = {}
            for k, v in self.interfaces.xpaths.iteritems():
                res = iface.find(v)
                if res is not None:
                    tmp[k] = res.text

            self.interfaces[tmp.get('name', i)] = tmp



    def dumpToJson(self):
        tobj = {
            'info' :       self.info,
            'interfaces':  self.interfaces
        }

        return json.dumps(tobj)

class Interfaces(dict):
    xpaths = {
        'ifidx'      : './/id',
        'name'       : './/eth_dev',
        'ipaddress'  : './/ipv4_addr',
        'management' : './/management'
    }

if __name__ == '__main__':
    # d = Device('137.58.68.243')
    d = Device('192.168.102.14')
    print d.config
    print d.dumpToJson()
