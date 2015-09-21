import json
import logging

import util

description = "DEV RF Switch"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new DEV at %s', ipa)
        self.info = {
            'productname'  : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
        }

        self.infouri = '/showdata.htm'

        # now populate all the fields
        self.populate()

    def populate(self):
        # this device does not provide much info...
        page = util.makeHttpRequest(self.info['ipaddress'], self.infouri)
        a = page.replace('<p>', '')
        a = a.replace('</p>', '')
        a = a.split('<br>')
        for l in a:
            if 'Model' in l:
                f = l.split(':')
                if len(f) > 1:
                    self.info['productname'] = f[1].strip()
            elif 'Firmware' in l:
                f = l.split(':')
                if len(f) > 1:
                    self.info['swversion'] = f[1].strip()

    def dumpToJson(self):
        tobj = {
            'info' : self.info,
        }

        return json.dumps(tobj)



if __name__ == '__main__':
    d = Device('192.168.116.29')
    print d.dumpToJson()
