#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys
import os
import random

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal, QSemaphore

from eeglib.helpers import CSVHelper

from loopTrigger import LoopTrigger
from plots import *
from options import OptionsDialog

progname = "VEEGS"

# States
states = {
    "INITIAL":      0,
    "WAIT_EEG_S":   1,
    "WAIT_PLAY":    2,
    "WAIT_STOP":    3,
}


class ApplicationWindow(QtWidgets.QMainWindow):

    stopSignal = pyqtSignal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi("mainwindow.ui", self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.eegSettings = {}

        self.__initEEGSettingsInputs()
        self.__initBrowseButton()
        self.__initSetEEGSettingsButton(self.setEEGSettingsButton)
        self.__initRunInputs()
        self.__initRunButtons()
        self.__initNewPlotAction()
        self.__initOptionsAction()

        self.rtDelay = self.simDelay=0.1

        self.functions=[]
        self.windowList = []

    def __setState(self, state):
        def enabledElements(dsB, esB, rB, playEl=True):
            self.dataSourceBox.setEnabled(dsB)
            self.actionBrowse.setEnabled(dsB)
            self.EEGSettingsBox.setEnabled(esB)
            self.runBox.setEnabled(rB)
            self.playButton.setEnabled(playEl)
            self.startInput.setEnabled(playEl)
            self.stopInput.setEnabled(playEl)
            self.actionNewPlot.setEnabled(rB and playEl)
            self.newPlotButton.setEnabled(rB and playEl)
            self.actionOptions.setEnabled(playEl)

        if state == states["WAIT_EEG_S"]:
            enabledElements(True, True, False)
        elif state == states["WAIT_PLAY"]:
            enabledElements(True, True, True)
        elif state == states["WAIT_STOP"]:
            enabledElements(False, False, True, False)

    def __initOptionsAction(self):
        def openOptionsDialog():
            od=OptionsDialog(parent=self, rtDelay=self.rtDelay,simDelay=self.simDelay)
            od.show()
        self.actionOptions.triggered.connect(openOptionsDialog)

    def __initNewPlotAction(self):
        def newPlotWindow():
            pw = PlotWindow(self)
            self.windowList.append(pw)
            self.functions.append(pw.update)
            pw.show()

        self.actionNewPlot.triggered.connect(newPlotWindow)
        self.newPlotButton.clicked.connect(newPlotWindow)

    def __initBrowseButton(self):
        def openFileDialog():
            filename = QtWidgets.QFileDialog.getOpenFileName(
                self, filter="CSV-Files (*.csv)")
            if filename[0] != "":
                try:
                    self.helper = CSVHelper(filename[0])
                    self.__setState(states["WAIT_EEG_S"])
                    self.feedBackLabel.setText("File oppened properly")
                    self.stopInput.setText(str(len(self.helper) / 128))
                except IOError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Error opening the file",
                                                  QtWidgets.QMessageBox.Ok)
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Error reading the file. Incorrect format?",
                                                  QtWidgets.QMessageBox.Ok)
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Error",
                                                  "Unexpected Error\n" +
                                                  str(e),
                                                  QtWidgets.QMessageBox.Ok)

        self.browseButton.clicked.connect(openFileDialog)
        self.actionBrowse.triggered.connect(openFileDialog)

    def __initEEGSettingsInputs(self):
        def checkText(inputLine, text):
            if text == "":
                enabled = False
                styleSheet = "background: rgb(210, 30, 100, 160)"
            else:
                enabled = True
                styleSheet = ""
            inputLine.setStyleSheet(styleSheet)
            self.setEEGSettingsButton.setEnabled(enabled)

        srInput = self.sampleRateInput
        srInput.setValidator(QtGui.QIntValidator())
        srInput.textChanged.connect(lambda text: checkText(srInput, text))

        wsInput = self.windowSizeInput
        wsInput.setValidator(QtGui.QIntValidator())
        wsInput.textChanged.connect(lambda text: checkText(wsInput, text))

    def __initSetEEGSettingsButton(self, button):
        def setEEGSettings():
            self.eegSettings["sampleRate"] = int(self.sampleRateInput.text())
            self.eegSettings["windowSize"] = int(self.windowSizeInput.text())
            self.windowFunction = self.windowFunctionCB.currentText()
            self.feedBackLabel.setText("New settings have been setted")
            self.__setState(states["WAIT_PLAY"])
            self.helper.prepareEEG(
                self.eegSettings["windowSize"], self.eegSettings["sampleRate"])
            for win in self.windowList:
                win.reset()

        button.clicked.connect(setEEGSettings)

    def __initRunInputs(self):
        self.startInput.setValidator(QtGui.QDoubleValidator())
        self.stopInput.setValidator(QtGui.QDoubleValidator())

    def __initRunButtons(self):
        def play():
            self.__setState(states["WAIT_STOP"])

            self.play(float(self.startInput.text()),
                      float(self.stopInput.text()))

        self.playButton.clicked.connect(play)
        self.stopButton.clicked.connect(self.stop)

    def stop(self):
        self.__setState(states["WAIT_PLAY"])

        self.semaphore.release(1)
        self.stopSignal.emit()
        self.loopThread.quit()
        self.loopThread.wait()

    def play(self, start, stop):
        sr = self.eegSettings["sampleRate"]
        step = sr * self.simDelay
        self.timePosition = start
        self.helper.prepareIterator(
            step, int(start * sr), int(stop * sr))
        self.iterator = self.helper.__iter__()
        try:
            self.iterator.__next__()
        except:
            QtWidgets.QMessageBox.warning(self, "Error",
                                          "The start and stop points are too close",
                                          QtWidgets.QMessageBox.Ok)

        for window in self.windowList:
            window.initAnimation(start)

        self.semaphore=QSemaphore(0)
        loop = LoopTrigger(self.semaphore,minDelay=self.rtDelay)
        self.loopThread = QThread()
        loop.moveToThread(self.loopThread)

        loop.sigUpdate.connect(self.__updateFields)
        loop.sigUpdate.connect(self.__playAnimation)

        self.stopSignal.connect(loop.stop)

        self.loop=loop
        self.loopThread.started.connect(loop.loop)
        self.loopThread.start()


    @pyqtSlot()
    def __playAnimation(self):
        try:
            self.iterator.__next__()
            self.helper.auxPoint,"/",self.helper.endPoint
            for f in self.functions:
                try:
                    f()
                except:
                    self.functions.remove(f)
            qApp.processEvents()
            self.semaphore.release(1)
        except:
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
