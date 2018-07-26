#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# General imports
from __future__ import unicode_literals
import sys
import os

# PyQt imports
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal, QSemaphore

# eeglib imports
from eeglib.helpers import CSVHelper

# veegs imports
from .loopTrigger import LoopTrigger
from .plots import PlotWindow
from .options import OptionsDialog

# Name of the program to display
progname = "VEEGS"


class ApplicationWindow(QtWidgets.QMainWindow):
    """
    Main window of the application
    """
    stopSignal = pyqtSignal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        selfdir=os.path.dirname(__file__)
        uic.loadUi(os.path.join(selfdir,"mainwindow.ui"), self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.app= QtWidgets.QApplication.instance()

        self.eegSettings = {}

        self.__initEEGInputs()
        self.__initBrowseButton()
        self.__initSetWindowSizeButton()
        self.__initRunInputs()
        self.__initRunButtons()
        self.__initNewPlotAction()
        self.__initOptionsAction()

        self.rtDelay = self.simDelay=0.1

        self.functions=[]
        self.windowList = []

    #Revisar
    def __setState(self, state):
        def enabledElements(dsB, esB, rB, playEl=True):
            self.dataSourceBox.setEnabled(dsB)
            self.actionBrowse.setEnabled(dsB)
            self.windowSizeBox.setEnabled(esB)
            self.runBox.setEnabled(rB)
            self.playButton.setEnabled(playEl)
            self.startInput.setEnabled(playEl)
            self.stopInput.setEnabled(playEl)
            self.actionNewPlot.setEnabled(rB and playEl)
            self.newPlotButton.setEnabled(rB and playEl)
            self.actionOptions.setEnabled(playEl)

        if state == "WAIT_PLAY":
            enabledElements(True, True, True)
        elif state == "WAIT_STOP":
            enabledElements(False, False, True, False)

    def __initOptionsAction(self):
        def openOptionsDialog():
            od=OptionsDialog(parent=self,
                             rtDelay=self.rtDelay, 
                             simDelay=self.simDelay)
            od.show()
            
        self.actionOptions.triggered.connect(openOptionsDialog)

    def __initNewPlotAction(self):
        def newPlotWindow():
            pw = PlotWindow(self)
            self.windowList.append(pw)
            self.functions.append(pw.update)
            pw.show()
        
        self.prevSaveDir = ""
        self.actionNewPlot.triggered.connect(newPlotWindow)
        self.newPlotButton.clicked.connect(newPlotWindow)

    def __initBrowseButton(self):
        def openFileDialog():
            filename = QtWidgets.QFileDialog.getOpenFileName(self             ,
                                               directory = self.prevBrowseDir ,
                                               filter    = "CSV-Files (*.csv)")
            print("Archivo:", filename)
            
            if filename[0] != "":
                try:
                    sampleRate = self.eegSettings["sampleRate"] = int(
                                                   self.sampleRateInput.text())
                    
                    ica=self.icaCB.isChecked()
                    normalize=self.normalizeCB.isChecked()
                    
                    self.helper = CSVHelper(filename[0], sampleRate=sampleRate,
                                            ICA=ica, normalize=normalize)
                    
                    self.prevBrowseDir = filename[0]
                    
                    windowSize = self.helper.eeg.windowSize
                    self.eegSettings["windowSize"] = windowSize
                    
                    self.feedBackLabel.setText("File oppened properly")
                    self.stopInput.setText(str(len(self.helper) / sampleRate))
                    self.windowSizeInput.setText(str(windowSize))
                    
                    self.__setState("WAIT_PLAY")
                    
                except IOError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Error opening the file",
                                                  QtWidgets.QMessageBox.Ok)
                    
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                      "Error reading the \
                                                      file. Incorrect format?",
                                                  QtWidgets.QMessageBox.Ok)
                    
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Unexpected Error\n" +
                                                  str(e),
                                                  QtWidgets.QMessageBox.Ok)

        self.prevBrowseDir = ""
        self.browseButton.clicked.connect(openFileDialog)
        self.actionBrowse.triggered.connect(openFileDialog)

    def __initEEGInputs(self):
        def checkText(inputLine, text):
            if text == "":
                enabled = False
                styleSheet = "background: rgb(210, 30, 100, 160)"
            else:
                enabled = True
                styleSheet = ""
            
            inputLine.setStyleSheet(styleSheet)
            self.setWindowSizeButton.setEnabled(enabled)

        srInput = self.sampleRateInput
        srInput.setValidator(QtGui.QIntValidator())
        srInput.textChanged.connect(lambda text: checkText(srInput, text))

        wsInput = self.windowSizeInput
        wsInput.setValidator(QtGui.QIntValidator())
        wsInput.textChanged.connect(lambda text: checkText(wsInput, text))

    def __initSetWindowSizeButton(self):
        def setWindowSize():  
            windowSize = int(self.windowSizeInput.text())
            self.eegSettings["windowSize"] = windowSize
            self.feedBackLabel.setText("New settings have been setted")
            self.__setState("WAIT_PLAY")
            self.helper.prepareEEG(windowSize)
            for win in self.windowList:
                win.reset()

        self.setWindowSizeButton.clicked.connect(setWindowSize)

    def __initRunInputs(self):
        self.startInput.setValidator(QtGui.QDoubleValidator())
        self.stopInput.setValidator(QtGui.QDoubleValidator())

    def __initRunButtons(self):
        def play():
            self.__setState("WAIT_STOP")

            self.play(float(self.startInput.text()),
                      float(self.stopInput.text()))

        self.playButton.clicked.connect(play)
        self.stopButton.clicked.connect(self.stop)

    def stop(self):
        self.__setState("WAIT_PLAY")

        self.semaphore.release(1)
        self.stopSignal.emit()
        self.loopThread.quit()
        self.loopThread.wait()

    def play(self, start, stop):
        self.timePosition = start
        
        sampleRate = self.eegSettings["sampleRate"]
        iterStep = sampleRate * self.simDelay
        iterStart = int(start * sampleRate)
        iterStop  = int(stop  * sampleRate)
        
        self.iterator = iter(self.helper[iterStart:iterStop:iterStep])
        
        try:
            self.iterator.__next__()
        except:
            QtWidgets.QMessageBox.warning(self, "Error", "The start and stop\
                                                         points are too close",
                                          QtWidgets.QMessageBox.Ok)

        for window in self.windowList:
            window.initAnimation(start)

        self.semaphore=QSemaphore(0)
        loop = LoopTrigger(self.semaphore,minDelay=self.rtDelay)
        self.loop=loop

        loop.sigUpdate.connect(self.__updateFields)
        loop.sigUpdate.connect(self.__playAnimation)

        self.stopSignal.connect(loop.stop)

        self.loopThread = QThread()
        loop.moveToThread(self.loopThread)
        self.loopThread.started.connect(loop.loop)
        self.loopThread.start()


    @pyqtSlot()
    def __playAnimation(self):
        try:
            self.iterator.__next__()
            for function in self.functions:
                try:
                    function()
                except:
                    self.functions.remove(function)
            
            self.app.processEvents()
            self.semaphore.release(1)

        except Exception as e:
            print(e)
            self.stop()

    @pyqtSlot()
    def __updateFields(self):
        self.timePosition += self.simDelay
        self.startInput.setText("%.2f" % self.timePosition)

    def deleteWinFromList(self, win):
        self.windowList.remove(win)

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.setWindowTitle("%s" % progname)
    aw.show()
    sys.exit(qApp.exec_())
