import socket
import httplib
import logging

lg = logging.getLogger('autoaudit')

def longtoaddr(x):
    return '.'.join(map(str, [(x & (255 << o)) >> o for o in range(24, -1, -8)]))

def addrtolong(addr):
    addr = map(long, addr.split('.'))
    return (addr[0] << 24) + (addr[1] << 16) + (addr[2] << 8) + (addr[3])

def genrange(start, finish):
    startlong  = addrtolong(start)
    finishlong = addrtolong(finish)
    while startlong < finishlong+1:
        yield longtoaddr(startlong)
        startlong += 1

def makeHttpRequest(ipa, uri, method='GET', body='', auth=None, port=80):
    try:
        if auth is None:
            # default token for VPC series
            auth = {"Authorization": "Basic cm9vdDp2aXBlcg=="}
        ipa = ':'.join([ipa,str(port)])
        conn = httplib.HTTPConnection(ipa, timeout=5)
        conn.request(method, uri, body, auth)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
    except httplib.HTTPException as e:
        lg.error("HTTP Error '%s' from %s", e, ipa)
        return ''
    except socket.timeout:
        lg.error("timeout making HTTP %s request to %s...", method, ipa)
        return ''
    except socket.error as e:
        lg.error("error making HTTP %s request to %s: %s", method, ipa, e)
    else:
        return body

def secondsToMinSec(seconds):
    "takes a float number of seconds and converts to MM:SS"
    mins = seconds // 60
    secs = seconds % 60

    return "%d:%.2f" % (mins, secs)

# these definitions are used for building tuple paths from nested dicts
def isLeaf(node):
    return not isinstance(node, dict)
def yieldPath(node, path=()):
    for k, v in node.items():
        if isLeaf(v):
            yield path+(str(k),)
        else:
            for p in yieldPath(v, path+(k,)):
                yield p

# this gets a key from a nested dict based on a "path" list
# useful for processing XPO3 json responses
def getp(pathlist, dictonary):
    try:
        return reduce(dict.__getitem__, pathlist, dictonary)
    except (KeyError, TypeError) as e:
        return None

def head(l):
    return l[0]
def tail(l):
    return l[1:]