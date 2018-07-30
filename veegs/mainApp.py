#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# General imports
from __future__ import unicode_literals
import sys
import os

import numpy as np

# PyQt imports
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal, QSemaphore

# eeglib imports
from eeglib.helpers import CSVHelper, EDFHelper

# veegs imports
from .loopTrigger import LoopTrigger
from .plots import PlotWindow
from .options import OptionsDialog
from .channelSelector import ChannelSelectorDialog

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
        self.state = "INIT"

        self.eegSettings = {}

        self.__initEEGInputs()
        self.__initBrowseButton()
        self.__initSetWindowSizeButton()
        self.__initRunInputs()
        self.__initRunButtons()
        self.__initNewPlotAction()
        self.__initOptionsAction()

        self.rtDelay = self.simDelay=1/8

        self.functions=[]
        self.windowList = []


    def __setState(self, state):
        def enabledElements(dsB, esB, rB, runEl, play):
            self.dataSourceBox.setEnabled(dsB)
            self.actionBrowse.setEnabled(dsB)
            
            self.windowSizeBox.setEnabled(esB)
            
            self.runBox.setEnabled(rB)
            
            self.startInput.setEnabled(runEl)
            self.stopInput.setEnabled(runEl)
            self.actionOptions.setEnabled(runEl)
            self.actionNewPlot.setEnabled(runEl)
            self.newPlotButton.setEnabled(runEl)
            
            self.playButton.setEnabled(play)
            self.pauseButton.setEnabled(not play)
            

        if   state == "STOP":
            enabledElements(True, True, True, True, True)
        elif state == "PLAY":
            enabledElements(False, False, True, False, False)
        elif state == "PAUSE":
            enabledElements(False, False, True, False, True)
        
        self.state = state

    def __initOptionsAction(self):
        def openOptionsDialog():
            sampleRate = self.helper.sampleRate
            
            samples  = int(np.round(self.simDelay * sampleRate))
            speedMul = self.simDelay/self.rtDelay
            
            od=OptionsDialog(parent   = self,
                             samples  = samples,
                             speedMul = speedMul)
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
            fileFilter = "CSV-Files (*.csv);; EDF-Files (*.edf)"
            filename = QtWidgets.QFileDialog.getOpenFileName(self             ,
                                               directory = self.prevBrowseDir ,
                                               filter    = fileFilter)
           
            if filename[0] != "":
                try:
                    #Settings preparation
                    ica=self.icaCB.isChecked()
                    normalize=self.normalizeCB.isChecked()
                    
                    #Helper creation
                    ext = os.path.splitext(filename[0])[1]
                    if ext == ".edf":
                        self.helper = EDFHelper(filename[0],
                                                ICA=ica, normalize=normalize)
                    else:
                        sampleRate, state = QtWidgets.QInputDialog.getInt(self,
                                "Sample Rate", "Sample Rate", value=128, min=0)
                        
                        self.helper = CSVHelper(filename[0],
                                                sampleRate=sampleRate,
                                                ICA=ica, normalize=normalize)
                    
                    # Letting the user select the channels
                    nChannels = self.helper.nChannels
                    names     = self.helper.names
                    dialog = ChannelSelectorDialog(nChannels, names, self)
                    if(dialog.exec()):
                        self.helper.selectSignals(dialog.getChannel())
                    
                    del dialog
                    
                    # Next time button clicked the dialog will be opened in
                    # prevBrowseDir
                    self.prevBrowseDir = filename[0]
                    
                    #Storing windowSize and sampleRate
                    windowSize = self.helper.eeg.windowSize
                    self.eegSettings["windowSize"] = windowSize
                    sampleRate = self.helper.sampleRate
                    self.eegSettings["sampleRate"] = self.helper.sampleRate
                    
                    #Giving feedback to user
                    self.feedBackLabel.setText("File oppened properly")
                    self.stopInput.setText(str(len(self.helper) / sampleRate))
                    self.windowSizeInput.setText(str(windowSize))
                    
                    #Unlocking locked inputs
                    self.__setState("STOP")
                    
                    #Reset plots if there where another file previously
                    self._resetPlots()
                    
                except IOError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Error opening the file",
                                                  QtWidgets.QMessageBox.Ok)
                    
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Error reading the file."+
                                                  "Incorrect format?",
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

        wsInput = self.windowSizeInput
        wsInput.setValidator(QtGui.QIntValidator())
        wsInput.textChanged.connect(lambda text: checkText(wsInput, text))

    def __initSetWindowSizeButton(self):
        def setWindowSize():  
            windowSize = int(self.windowSizeInput.text())
            self.eegSettings["windowSize"] = windowSize
            self.feedBackLabel.setText("New settings have been setted")
            self.__setState("STOP")
            self.helper.prepareEEG(windowSize)
            self._resetPlots()
            

        self.setWindowSizeButton.clicked.connect(setWindowSize)

    def __initRunInputs(self):
        self.startInput.setValidator(QtGui.QDoubleValidator())
        self.stopInput.setValidator(QtGui.QDoubleValidator())
        
    def _pause(self):
        self.semaphore.release(1)
        self.stopSignal.emit()
        self.loopThread.quit()
        self.loopThread.wait()
        
        self.__setState("PAUSE")
            
    def _stop(self):
        self._pause()
        
        self._resetPlots()
        
        self.__setState("STOP")
        
    
    def _play(self):     
        #Input values
        start = float(self.startInput.text())
        stop  = float(self.stopInput.text())
        
        #If state is PAUSE skip these steps
        if self.state != "PAUSE":
            self.timePosition = start
        
            #Iterator preparation
            sampleRate = self.eegSettings["sampleRate"]
            iterStep = sampleRate * self.simDelay
            iterStart = int(start * sampleRate)
            iterStop  = int(stop  * sampleRate)
            
            self.iterator = iter(self.helper[iterStart:iterStop:iterStep])
            
            #Next iteration to test if values are correct
            try:
                next(self.iterator)
            except StopIteration:
                QtWidgets.QMessageBox.warning(self, "Error", 
                                 "The start and stop points are too close",
                                              QtWidgets.QMessageBox.Ok)
                return
            #Initialize animations of windows
            for window in self.windowList:
                window.initAnimation(start)
        
        #Init semaphore and loopTrigger
        self.semaphore=QSemaphore(0)
        loop = LoopTrigger(self.semaphore,minDelay=self.rtDelay)
        self.loop=loop
        
        #Connect signals
        loop.sigUpdate.connect(self.__updateFields)
        loop.sigUpdate.connect(self.__playAnimation)

        self.stopSignal.connect(loop.stop)
        
        #Init thread
        self.loopThread = QThread()
        loop.moveToThread(self.loopThread)
        self.loopThread.started.connect(loop.loop)
        self.loopThread.start()
        
        #Set new state
        self.__setState("PLAY")
            
    def __initRunButtons(self):
        self.playButton .clicked.connect(self._play )
        self.stopButton .clicked.connect(self._stop )  
        self.pauseButton.clicked.connect(self._pause)

    @pyqtSlot()
    def __playAnimation(self):
        try:
            next(self.iterator)
            for function in self.functions:
                try:
                    function()
                except:
                    self.functions.remove(function)
            
            self.app.processEvents()
            self.semaphore.release(1)

        except Exception as e:
            print(e)
            self._pause()

    @pyqtSlot()
    def __updateFields(self):
        self.timePosition += self.simDelay
        self.startInput.setText("%.2f" % self.timePosition)
    
    def _resetPlots(self):
        for win in self.windowList:
            win.reset()

    def deleteWinFromList(self, win):
        self.windowList.remove(win)

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.setWindowTitle("%s" % progname)
    aw.show()
    sys.exit(qApp.exec_())
