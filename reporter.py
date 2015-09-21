import json
import logging
import pdb

from PySide.QtCore import *
from PySide.QtGui import *

import util

def getAvailableFields(path):
    res = []
    devicedicts = []

    rdir = QDir(path)
    dirs = rdir.entryInfoList(filters=QDir.Dirs|QDir.NoDotAndDotDot)
    for d in dirs:
        fname = d.absoluteDir().filePath('{0}/{0}_data.json'.format(d.fileName()))
        try:
            with open(fname, 'r') as f:
                devicedicts.append(json.loads(f.read()))
        except (IOError, ValueError) as e:
            continue

    for devicedict in devicedicts:
        for path in util.yieldPath(devicedict):
            res.append(path)
    json.dump(devicedicts, open('dump.json', 'w'))
    res = list(set(res))
    return res

def uniqheads(l):
    return list(set(map(lambda x: x[0], l)))

def filterchop(l, s):
    return map(lambda x: x[1:], filter(lambda x: x[0] == s, l))

def tail(l):
    return l[1:]

if __name__ == '__main__':
    aflds = getAvailableFields("C:\\Users\\greenj\\Dropbox\\autoaudit\\phase4\\dist\\2015-07-03_14-31-11")

    clms = []

    srcspc = aflds
    path = []
    while True:
        print uniqheads(srcspc)
        a = raw_input(" ".join(path+["> "]))
        path.append(a)
        srcspc = map(tail, filter(lambda x: x[0] == a, srcspc))
        srcspc = filter(lambda x: len(x) > 0, srcspc)

        if len(srcspc) == 0:
            print "path is: ", path
            paths.append(path)
            break


    # while a:
    #     srcspc = aflds
    #     while len(srcspc):
    #         a = raw_input("> ")
    #         srcspc = filterchop(srcspc, a)