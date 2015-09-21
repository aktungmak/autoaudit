import os
import time

print "setting up copy protection...",
# update copy protection
with open("cpyprot.py", "r+") as f:
    # skip first line
    f.readline()
    rest = f.read()

    new = "EXPIRY_DATE = %d\n" % (time.time()+2592000)

    f.seek(0)

    f.write(new)
    f.write(rest)
    print "done"


print "deleting old pyc files...",
os.popen("del *.pyc")
print "done"

print "building executable...",
os.popen(r"C:\Python27\Scripts\pyinstaller.exe main.py -F -s -w -i C:\svn\TechSupport\trunk\reflexmonitor\favicon.ico")
print "done"

print "cleaning up copy protection...",
# clean up copy protection
with open("cpyprot.py", "r+") as f:
    # skip first line
    f.readline()
    rest = f.read()

    new = "EXPIRY_DATE = %d\n" % (2147483647)

    f.seek(0)

    f.write(new)
    f.write(rest)
    print "done"

