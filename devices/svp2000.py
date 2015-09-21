import json
import logging

import util

description = "SVP2000 ABR encoder/decoder"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new svp2000 at %s', ipa)
        self.info = {
            'productname'  : None,
            'unitname'     : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'hwversion'    : None,
            'sntpserver'   : None,
            'serialnumber' : None,
            'licensekey'   : None,
            'uptime'       : None
        }

        self.licenses = Licenses()
        self.interfaces = Interfaces()

        self.endpoints = {
            'productname'  : '/objects/device/System/ModelName',
            'unitname'     : '/objects/device/System/DeviceName',
            'swversion'    : '/objects/device/Firmware/SoftwareVersion',
            'hwversion'    : '/objects/device/Firmware/HardwareVersion',
            'sntpserver'   : '/objects/device/DateTime/NtpServerList',
            'serialnumber' : '/objects/device/System/Uid',
            'licensekey'   : '/objects/device/System/LicenseKey',
            'uptime'       : '/objects/device/System/UpTime'
        }

        self.config  = ''

        self.configuri = ''

        # now populate all the fields
        self.populate()

    def populate(self):
        # clear the previous values
        self.licenses.clear()
        self.interfaces.clear()

        # first grab the config and save it
        # TODO needs more work
        self.config = util.makeHttpRequest(self.info['ipaddress'], self.configuri)

        # fill the info dict, by any means neccessary
        for k, v in self.info.iteritems():
            if k in self.endpoints:
                val = util.makeHttpRequest(self.info['ipaddress'], self.endpoints[k])
                # clean up the response
                val = json.loads(val)

                self.info[k] = val



        self._getLicenses()
        self._getInterfaces()

    def _getLicenses(self):
        data = util.makeHttpRequest(self.info['ipaddress'], self.licenses.endpoint)
        ld = json.loads(data)
        for k, v in ld.iteritems():
            self.licenses[k] = v

    def _getInterfaces(self):
        data = util.makeHttpRequest(self.info['ipaddress'], self.interfaces.endpoint)
        li = json.loads(data)
        for i, ifce in enumerate(li):
            tmp = {}
            tmp['name'] = ifce.get('Adapter', '')
            tmp['ipaddress'] = ifce.get('CurrentIpAddress', '')
            tmp['status'] = ifce.get('OperationalStatus', '') == 1
            self.interfaces[ifce.get('Adapter', i)] = tmp


    def dumpToJson(self):
        tobj = {
            'info'       : self.info,
            'licenses'   : self.licenses,
            'interfaces': self.interfaces
        }

        return json.dumps(tobj)

class Licenses(dict):
    endpoint = '/objects/device/License/AllowedFeatures'

class Interfaces(dict):
    endpoint = '/objects/device/Network/Adapters'


if __name__ == '__main__':
    d = Device('192.168.102.12')
    e = Device('192.168.102.113')
    print d.dumpToJson()
    print
    print e.dumpToJson()