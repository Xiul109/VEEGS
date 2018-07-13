from numpy import arange
import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui, uic

import pyqtgraph
from pyqtgraph import PlotWidget

import csv
import os

from eeglib.eeg import defaultBands

defaultBandsNames = list(defaultBands.keys())


class ChannelSelector(QtWidgets.QGroupBox):

    def __init__(self, nChannels, parent=None, title="Channel Selector"):
        QtWidgets.QGroupBox.__init__(self, parent)
        self.setTitle(title)
        self.channel = 0
        rows = int(np.ceil(np.sqrt(nChannels)))
        grid = QtWidgets.QGridLayout()
        def setChannel(toggled, chann):
            if toggled:
                self.channel = chann
        for i in range(rows):
            for j in range(rows):
                if nChannels > 0:
                    nChannels -= 1
                    channel = i * rows + j
                    rb = QtWidgets.QRadioButton(str(channel))
                    channel = channel
                    if channel == 0:
                        rb.toggle()
                    rb.toggled.connect(
                        lambda toggled, chann=channel: setChannel(toggled, chann))
                    grid.addWidget(rb, i, j)
        self.setLayout(grid)


class PlotWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.eegSettings = parent.eegSettings
        selfdir=os.path.dirname(__file__)
        uic.loadUi(os.path.join(selfdir,"plotWindow.ui"), self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setModal(False)

        self.__initApButton()
        self.__initClose()
        self.__initLogger()

        nChannels = parent.helper.nChannels

        self.rawSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(0).layout().addWidget(self.rawSelector)

        self.decomposedSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(1).layout().addWidget(self.decomposedSelector)
        self.bandsCBs = [self.deltaCB, self.thetaCB, self.alphaCB, self.betaCB]

        self.averageBPSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(2).layout().addWidget(self.averageBPSelector)

        self.SL1Selector = ChannelSelector(
            nChannels, self, "Channel 1 Selector")
        self.tabWidget.widget(3).layout().addWidget(self.SL1Selector)
        self.SL2Selector = ChannelSelector(nChannels, self, "Channel 2 Selector")
        self.tabWidget.widget(3).layout().addWidget(self.SL2Selector)

        self.featuresSelector = ChannelSelector(
            nChannels, self)
        self.tabWidget.widget(4).layout().addWidget(self.featuresSelector)

    def __initApButton(self):
        def addPlot():
            tIndex = self.tabWidget.currentIndex()
            tab = self.tabWidget.currentWidget().accessibleName()
            text = self.nameTB.text()
            self.setWindowTitle(text if text != "" else tab)

            if tIndex == 0:
                function = lambda channel=self.rawSelector.channel: self.parentWidget(
                ).helper.getEEG().getChannel(channel)
                self.canvasClass = TimeSignalCanvas
                self.canvasArgs = (self.eegSettings["sampleRate"],
                                   self.eegSettings["windowSize"], function)
            elif tIndex == 1:
                function = lambda channel=self.decomposedSelector.channel: self.parentWidget(
                ).helper.getEEG().getSignalAtBands(channel)
                self.canvasClass = DescomposedTimeSignalCanvas
                self.canvasArgs = (self.selectedBands(),
                                   self.eegSettings["sampleRate"],
                                   self.eegSettings["windowSize"], function)
            elif tIndex == 2:
                self.canvasClass = AverageBandPowerCanvas
                self.canvasArgs = (defaultBandsNames,
                                   lambda channel=self.averageBPSelector.channel: self.parentWidget(
                                   ).helper.getEEG().getAverageBandValues(channel))
            elif tIndex == 3:
                self.canvasClass = FeaturesCanvas
                function = lambda c1=self.SL1Selector.channel, c2=self.SL2Selector.channel: {
                    "Synchronization Likelihood": self.parentWidget().helper.eeg.synchronizationLikelihood((c1, c2))}
                self.canvasArgs = (["Synchronization Likelihood"], function)
            elif tIndex == 4:
                self.canvasClass = FeaturesCanvas
                funcs, names = self.getFeaturesFuncsAndNames()
                function = lambda: {name: f() for f, name in zip(funcs, names)}
                self.canvasArgs = (names, function)
            else:
                raise Exception("That tab doesn't exist")
            self.cleanWidgets()
            self.canvasKargs = {"logFileName": self.loggerFile} \
                                    if self.loggerFile else {}
            self.addCanvas()

        self.apButton.clicked.connect(addPlot)

    def __initClose(self):
        self.finished.connect(
            lambda: self.parentWidget().deleteWinFromList(self))

    def __initLogger(self):
        self.loggerFile = None
        messageNoFile = "No file selected. Data won't be logged."
        messageFile = 'File selected:"{}" . Click here to deselect it.'
        def deselectFile(event):
            self.loggerFile = None
            self.loggerLabel.mouseReleaseEvent = lambda e: None
            self.loggerLabel.setText(messageNoFile)
        def openFileDialog():
            filename = QtWidgets.QFileDialog.getSaveFileName(
                self, filter="CSV-Files (*.csv)")
            if filename[0] != "":
                self.loggerFile = filename[0]
                self.loggerLabel.setText(messageFile.format(filename[0]))
                self.loggerLabel.mouseReleaseEvent = deselectFile

        self.loggerButton.clicked.connect(openFileDialog)

    def cleanWidgets(self):
        for _ in range(self.layout.count()):
            self.layout.takeAt(0).widget().setParent(None)

    def addCanvas(self):
        dc = PlotWidget(self)
        l = self.layout
        l.addWidget(dc)
        self.canvas = self.canvasClass(
            *self.canvasArgs, dc, **self.canvasKargs)
        self.destroyed.connect(self.canvas.closeFile)
        return dc

    def reset(self):
        if hasattr(self, "canvasClass"):
            self.cleanWidgets()
            self.addCanvas()

    def update(self):
        if hasattr(self, "canvas"):
            self.canvas.update_figure(self.parentWidget().simDelay)

    def initAnimation(self, start):
        if hasattr(self, "canvas"):
            self.canvas.initAnimation(start)

    def selectedBands(self):
        return [x.accessibleName() for x in self.bandsCBs if x.isChecked()]

    def getFeaturesFuncsAndNames(self):
        channel = self.featuresSelector.channel
        featuresFuncs = []
        featuresNames = []
        helper = self.parentWidget().helper
        if self.hfdCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().HFD(chann))
            featuresNames.append("HFD")
        if self.pfdCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().PFD(chann))
            featuresNames.append("PFD")
        if self.hjorthActivityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthActivity(chann))
            featuresNames.append("Hjorth Activity")
        if self.hjorthMobilityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthMobility(chann))
            featuresNames.append("Hjorth Mobility")
        if self.hjorthComplexityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthComplexity(chann))
            featuresNames.append("Hjorth Complexity")
        if self.engagementCB.isChecked():
            featuresFuncs.append(lambda:  helper.getEEG().engagementLevel())
            featuresNames.append("Engagement Level")

        return featuresFuncs, featuresNames


class BaseCanvas():
    timeField = "time(s)"

    def __init__(self, func, plot, logFileName=None):
        self.func = func
        self.axes = plot
        if logFileName:
            self.logMode = True
            self.logFileName = logFileName
            self.logFile = open(self.logFileName, "w")
            self.initLogFile()
        else:
            self.logMode = False

    def initAnimation(self, start):
        self.sec = start

    def update_figure(self, delay):
        self.sec += delay

    def closeFile(self):
        if self.logMode:
            self.logFile.close()

    def initLogFile(self, fieldnames=[]):
        self.writer = csv.DictWriter(self.logFile, fieldnames=fieldnames)
        self.writer.writeheader()


class TimeSignalCanvas(BaseCanvas):
    signalField = "signal"

    def __init__(self, sampleRate, windowSize, *args, **kwargs):
        self.__initAttributes__(sampleRate, windowSize)

        BaseCanvas.__init__(self, *args, **kwargs)

    def initLogFile(self):
        self.fieldnames = [self.timeField, self.signalField]
        super().initLogFile(self.fieldnames)

    def __initAttributes__(self, sampleRate, windowSize):
        self.sampleRate = sampleRate
        self.windowSize = windowSize

        self.duration = self.windowSize / self.sampleRate
        self.arange = arange(0, self.duration, self.duration / self.windowSize)

    def makePlot(self, x, y):
        self.plot = self.axes.plot(x, y, clear=True)

    def getXY(self):
        y = self.func()
        s1 = self.sec
        x = self.arange + s1
        return x, y

    def write(self, fieldnames, data):
        self.writer.writerows(
            [{field: value[i] for field, value in zip(fieldnames, data)} for i in range(len(data[0]))])

    def initAnimation(self, start):
        super().initAnimation(start)
        x, y = self.getXY()
        self.makePlot(x, y)
        if self.logMode:
            self.write(self.fieldnames, [x, y])

    def update_figure(self, delay):
        super().update_figure(delay)
        newDataStart = -int(self.sampleRate * (delay))
        x, y = self.getXY()
        self.makePlot(x, y)
        if self.logMode:
            self.write(self.fieldnames, [x[newDataStart:], y[newDataStart:]])


class DescomposedTimeSignalCanvas(TimeSignalCanvas):

    def __init__(self, bands, *args, **kwargs):
        self.bands = bands

        TimeSignalCanvas.__init__(self, *args, **kwargs)

        self.axes.addLegend()
        self.legend = self.axes.getPlotItem().legend

    def initLogFile(self):
        self.fieldnames = [self.timeField] + self.bands
        BaseCanvas.initLogFile(self, self.fieldnames)

    def makeSubplot(self, x, i, band, y):
        return self.axes.plot(x, y, name=band, pen=pyqtgraph.mkPen(pyqtgraph.intColor(3 * i, 13)))

    def makeSubplots(self, x, ys):
        self.plots = [self.makeSubplot(x, i, band, y) for i, (band, y) in enumerate(
            ys.items())]

    def getXY(self):
        x, ys = super().getXY()
        return x, {band: values for band, values in ys.items() if band in self.bands}

    def initAnimation(self, start):
        BaseCanvas.initAnimation(self, start)
        if hasattr(self, "plots"):
            self.cleanSubplots()
        x, ys = self.getXY()
        self.makeSubplots(x, ys)
        if self.logMode:
            self.write(self.fieldnames, [x] + list(ys.values()))

    def update_figure(self, delay):
        BaseCanvas.update_figure(self, delay)
        newDataStart = -int(self.sampleRate * (delay))
        self.cleanSubplots()
        x, ys = self.getXY()
        self.makeSubplots(x, ys)
        if self.logMode:
            self.write(self.fieldnames, [v[newDataStart:]
                                         for v in [x] + list(ys.values())])

    def cleanSubplots(self):
        for plot, band in zip(self.plots, self.bands):
            plot.clear()
            self.legend.removeItem(band)


class AverageBandPowerCanvas(BaseCanvas):

    def __init__(self, bands, *args, **kwargs):
        self.bands = bands
        BaseCanvas.__init__(self, *args, **kwargs)
        self.xAxe = self.axes.getAxis("bottom")
        self.x = list(range(len(bands)))
        self.sum = {band: 0 for band in bands}
        self.names = {band: band for band in bands}
        self.count = 0

    def initLogFile(self):
        self.fieldnames = [self.timeField] + self.bands
        super().initLogFile(self.fieldnames)

    def makePlot(self, data, names):
        self.xAxe.setTicks([list(zip(self.x, names))])
        self.plot = self.axes.plot(
            self.x, list(data.values()), symbol="o", clear=True)

    def update_figure(self, delay):
        super().update_figure(delay)
        data = self.func()
        self.count += 1
        for band in data:
            self.sum[band] += data[band]
            self.names[band] = band + \
                ": {:.4f}".format(self.sum[band] / self.count)
        self.makePlot(data, list(self.names.values()))
        if self.logMode:
            self.write([self.sec] + list(data.values()))

    def initAnimation(self, start):
        super().initAnimation(start)
        self.update_figure(0)

    def write(self, data):
        row = {fieldname: d for fieldname, d in zip(self.fieldnames, data)}
        self.writer.writerow(row)


class FeaturesCanvas(BaseCanvas):

    def __init__(self, featuresNames, *args, **kwargs):
        self.__initAttributes__(featuresNames)

        BaseCanvas.__init__(self, *args, **kwargs)

        self.legend = self.axes.addLegend()

    def __initAttributes__(self, featuresNames):
        self.featuresNames = featuresNames
        self.nFeatures = len(featuresNames)
        self.data = {name: [] for name in featuresNames}
        self.time = []
        self.legendNames = {name: name for name in featuresNames}

    def initLogFile(self):
        self.fieldnames = [self.timeField] + self.featuresNames
        super().initLogFile(self.fieldnames)

    def makePlots(self):
        for plot, (fName, data) in zip(self.plots, self.data.items()):
            plot.setData(self.time, data)
            for sample, label in self.legend.items:
                if sample.item == plot:
                    label.setText(self.legendNames[fName])

    def initAnimation(self, start):
        super().initAnimation(start)
        self.initMeansData()
        if hasattr(self, "plots"):
            for p in self.plots:
                p.clear()
        self.plots = [self.axes.plot(self.time, self.data[name], name=name, pen=pyqtgraph.mkPen(
            pyqtgraph.intColor(3 * i, self.nFeatures * 3))) for i, name in enumerate(self.featuresNames)]
        self.update_figure(0)

    def initMeansData(self):
        self.sum = {name: 0 for name in self.featuresNames}
        self.count = 0

    def update_figure(self, delay):
        self.sec += delay
        self.count += 1
        currentTime = self.sec
        self.time.append(currentTime)
        data = self.func()
        for fName, fValue in data.items():
            self.data[fName].append(fValue)
            self.sum[fName] += fValue
            self.legendNames[fName] = fName + \
                ": {:.4f}".format(self.sum[fName] / self.count)
        self.makePlots()
        if self.logMode:
            data[self.timeField] = currentTime
            self.write(data)

    def write(self, data):
        self.writer.writerow(data)
