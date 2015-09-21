import json
import logging
import telnetlib
import re

description = "Leitch/Harris SDI router"

lg = logging.getLogger('autoaudit')

class Device(object):
    def __init__(self, ipa):
        lg.debug('creating new Leitch at %s', ipa)
        self.info = {
            'productname'  : None,
            'ipaddress'    : ipa,
            'swversion'    : None,
            'hwversion'    : None,
            'serialnumber' : None,
            'chipid'       : None
        }

        self.user = 'leitch'
        self.passwd = 'leitchadmin'


        self.config = ''

        # now populate all the fields
        self.populate()

    def populate(self):
        # fill the info dict
        tel = telnetlib.Telnet(self.info['ipaddress'])

        # log in and grab the data
        tel.read_until('login: ')
        tel.write(self.user + '\x0d\x0a')

        tel.read_until('password: ')
        tel.write(self.passwd + '\x0d\x0a')

        tel.read_until('>\x0d\x0a>')
        tel.write('show rparm\x0d\x0a')
        data = tel.read_until('>')

        tel.close()

        # the data format is unhelpful, regex it out
        r = re.findall('Frame Type: (.+?)\r', data)
        if r: self.info['productname'] = r[0]

        r = re.findall('Software Revision: (.+?) ', data)
        if r: self.info['swversion'] = r[0]

        r = re.findall('FPGA Revision: (.+?)\r', data)
        if r: self.info['hwversion'] = r[0]

        r = re.findall('Frame Serial ID: (.+?)\r', data)
        if r: self.info['serialnumber'] = r[0]

        r = re.findall('License ID: (.+?)\r', data)
        if r: self.info['chipid'] = r[0]





        # grab a view of the crosspoints for our 'config'
        self.getConfig()

    def getConfig(self):
        tel = telnetlib.Telnet(self.info['ipaddress'])

        tel.read_until('login: ')
        tel.write(self.user + '\x0d\x0a')

        tel.read_until('password: ')
        tel.write(self.passwd + '\x0d\x0a')

        tel.read_until('>\x0d\x0a>')
        tel.write('r\x0d\x0a')

        self.config = tel.read_until('>')
        self.config = self.config.replace('>', '').strip()

        tel.close()

    def dumpToJson(self):
        tobj = {
            'info' : self.info,
        }

        return json.dumps(tobj)

if __name__ == '__main__':
    d = Device('192.168.117.26')
    print d.config
    print d.dumpToJson()
