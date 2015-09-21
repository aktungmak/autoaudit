EXPIRY_DATE = 2147483647
import os
import random
import sys
import time

def versionHasExpired():
    "confirm that this copy has not expired"
    now = time.time()
    # This will stop working after 19th Jan 2038
    if now > EXPIRY_DATE:
        return True
    else:
        return False

def haraKiri():
    "destroy this executable"
    exe = sys.argv[0]
    size = os.path.getsize(exe)
    f = open(exe, 'w')
    random.seed(time.time())
    for i in range(1024):
        f.seek(random.randint(0, size))
        f.write(random.randint(0, 255))

if __name__ == '__main__':
    print versionHasExpired()