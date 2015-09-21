import time

from PySide.QtCore import *

import devices.util as util
import PingTask

class ScanTask(QThread):
    """
       QThread to manage a scan of multiple addresses
       using a QThreadPool. Because QTP's waitForDone
       method blocks, it cannot be run in the main thread.
       Hence, it is outsourced to this thread!
       str sipa: start IP address for the scan
       str fipa: finish IP address for the scan
       QDir dir: where to put the result directory
       QObject parent: the parent for this thread
    """
    # signals need to be class vars, not instance vars
    stepComplete = Signal(int)
    def __init__(self, sipa, fipa, rdir, ignoreUnk=True, includeLocalhost=False, parent=None):
        self.sipa = sipa
        self.fipa = fipa
        self.rdir = rdir
        self.ignoreUnk = ignoreUnk
        self.includeLocalhost = includeLocalhost
        self.timetaken = 0
        # number of steps required to complete this task
        self.steps = util.addrtolong(fipa) - util.addrtolong(sipa) + 1
        # add one if we check ourself
        self.steps = (self.steps + 1) if self.includeLocalhost else self.steps

        super(ScanTask, self).__init__(parent)

        self.__stop = False

    def run(self):
        qtp = QThreadPool()
        t1 = time.time()

        for ipa in util.genrange(self.sipa, self.fipa):
            if self.__stop:
                break

            tsk = PingTask.PingTask(ipa, self.rdir, self.ignoreUnk, self.parent())
            tsk.complete.connect(self.subTaskComplete)
            # don't want to overload the thread queue
            # so we will try and push a new task to the pool
            # if there is no space, wait half a sec and try again
            while not qtp.tryStart(tsk):
                time.sleep(0.5)

        # check localhost if needed
        if self.includeLocalhost:
            tsk = PingTask.PingTask('127.0.0.1', self.rdir, self.ignoreUnk)
            tsk.complete.connect(self.subTaskComplete)
            while not qtp.tryStart(tsk):
                time.sleep(0.5)

        qtp.waitForDone()
        t2 = time.time()
        self.timetaken = t2-t1

    def subTaskComplete(self):
        """
            called every time a subtask (PingTask) is complete
            emits a stepComplete Signal, essentially forwarding
            on the signal to avoid passing around loads of refs
        """
        self.stepComplete.emit(1)

    def makeResultsDir(self, qdir):
        """
            create a directory to store the results in
            QDir qdir: the directory the result will be made in
            out: a QDir with the location
        """

        rdir = QDir( qdir.filePath(time.strftime("%Y-%m-%d_%H-%M-%S")) )
        if not rdir.exists():
            rdir.mkdir(rdir.absolutePath())
        return rdir

    def stopScan(self):
        """
            set the internal __stop flag so that
            we stop pushing tasks into the thread pool
            and eventually quit.
        """
        self.__stop = True
