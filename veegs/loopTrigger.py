import time

from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QApplication


class LoopTrigger(QObject):
    """
    This class is used to synchronize the plotting of all of the graphs in a
    similar way than QTimer, but it waits until all the plots has been painted.
    """
    sigUpdate=pyqtSignal()

    def __init__(self,semaphore, minDelay=0.1):
        super().__init__()
        self.minDelay = minDelay
        self.doLoop = True
        self.app= QApplication.instance()
        self.semaphore=semaphore

    @pyqtSlot()
    def loop(self):
        while self.doLoop:
            t = time.time() + self.minDelay
            
            self.sigUpdate.emit()
            self.semaphore.acquire(1)
            
            waitTime = t - time.time()
            if waitTime > 0:
                time.sleep(waitTime)
            
            self.app.processEvents()

    @pyqtSlot()
    def stop(self):
        self.doLoop = False
