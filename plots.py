import matplotlib
matplotlib.use('Qt5Agg')

from numpy import arange
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic

from eeglib.eeg import SampleWindow

import pyqtgraph


class ChannelSelector(QtWidgets.QGroupBox):

    def __init__(self, nChannels, parent=None):
        QtWidgets.QGroupBox.__init__(self, parent)
        self.setTitle("Channel Selector")
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
        uic.loadUi("plotWindow.ui", self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setModal(False)

        self.__initApButton()
        self.__initClose()

        electrodes = parent.helper.electrodeNumber

        self.rawSelector = ChannelSelector(electrodes, self)
        self.tabWidget.widget(0).layout().addWidget(self.rawSelector)

        self.normalizedSelector = ChannelSelector(electrodes, self)
        self.tabWidget.widget(1).layout().addWidget(self.normalizedSelector)

        self.decomposedSelector = ChannelSelector(electrodes, self)
        self.tabWidget.widget(2).layout().addWidget(self.decomposedSelector)
        self.bandsCBs = [self.deltaCB, self.thetaCB, self.alphaCB, self.betaCB]

        self.averageBPSelector = ChannelSelector(electrodes, self)
        self.tabWidget.widget(3).layout().addWidget(self.averageBPSelector)

        self.featuresSelector = ChannelSelector(electrodes, self)
        self.tabWidget.widget(4).layout().addWidget(self.featuresSelector)

    def __initApButton(self):
        def addPlot():
            tIndex = self.tabWidget.currentIndex()
            tab = self.tabWidget.tabText(tIndex)[1:]
            text = self.nameTB.text()
            self.setWindowTitle(text if text != "" else tab)

            if tIndex == 0:
                function = lambda channel=self.rawSelector.channel: self.parentWidget(
                ).helper.getEEG().getRawDataAt(channel)
                self.canvasClass = TimeSignalCanvas
                self.canvasArgs = (self.eegSettings["sampleRate"], self.eegSettings[
                                   "windowSize"], function)
            elif tIndex == 1:
                function = lambda channel=self.normalizedSelector.channel: self.parentWidget(
                ).helper.getEEG().getNormalizedDataAt(channel)
                self.canvasClass = TimeSignalCanvas
                self.canvasArgs = (self.eegSettings["sampleRate"], self.eegSettings[
                                   "windowSize"], function)
            elif tIndex == 2:
                function = lambda channel=self.decomposedSelector.channel: self.parentWidget(
                ).helper.getEEG().getBandsSignalsAt(channel)
                self.canvasClass = DescomposedTimeSignalCanvas
                self.canvasArgs = (self.eegSettings["sampleRate"], self.eegSettings[
                                   "windowSize"], self.selectedBands(), function)
            elif tIndex == 3:
                self.canvasClass = AverageBandPowerCanvas
                self.canvasArgs = (lambda channel=self.averageBPSelector.channel: self.parentWidget(
                ).helper.getEEG().getAverageBandValuesAt(channel),)
            elif tIndex == 4:
                self.canvasClass = FeaturesCanvas
                funcs, names = self.getFeaturesFuncsAndNames()
                function = lambda: [f() for f in funcs]
                self.canvasArgs = [names, function]
            else:
                raise Exception("That tab doesn't exist")
            self.cleanWidgets()
            self.addCanvas()

        self.apButton.clicked.connect(addPlot)

    def __initClose(self):
        self.finished.connect(
            lambda: self.parentWidget().deleteWinFromList(self))

    def cleanWidgets(self):
        for _ in range(self.layout.count()):
            self.layout.takeAt(0).widget().setParent(None)

    def addCanvas(self):
        dc = self.canvasClass(*self.canvasArgs, self,
                              width=5,  height=4, dpi=100)
        l = self.layout
        l.addWidget(dc)
        self.canvas = dc
        return dc

    def reset(self):
        if hasattr(self, "canvasClass"):
            self.cleanWidgets()
            self.addCanvas()

    def update(self):
        if hasattr(self, "canvas"):
            self.canvas.update_figure(self.parentWidget().delay)

    def compute_initial_figure(self, start):
        if hasattr(self, "canvas"):
            self.canvas.compute_initial_figure(start)

    def selectedBands(self):
        return [x.text()[1:] for x in self.bandsCBs if x.isChecked()]

    def getFeaturesFuncsAndNames(self):
        channel = self.featuresSelector.channel
        featuresFuncs = []
        featuresNames = []
        helper = self.parentWidget().helper
        if self.hfdCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().getHFDAt(chann))
            featuresNames.append("HFD")
        if self.pfdCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().getPFDAt(chann))
            featuresNames.append("PFD")
        if self.hjorthActivityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthActivityAt(chann))
            featuresNames.append("Hjorth Activity")
        if self.hjorthMobilityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthMobilityAt(chann))
            featuresNames.append("Hjorth Mobility")
        if self.hjorthComplexityCB.isChecked():
            featuresFuncs.append(
                lambda chann=channel: helper.getEEG().hjorthComplexityAt(chann))
            featuresNames.append("Hjorth Complexity")
        if self.engagementCB.isChecked():
            featuresFuncs.append(lambda:  helper.getEEG().engagementLevel())
            featuresNames.append("Engagement Level")

        return featuresFuncs, featuresNames


class BaseCanvas(FigureCanvas):

    def __init__(self, func, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        self.func = func

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self, start):
        pass

    def update_figure(self):
        pass

    def play(self):
        pass

    def pause(self):
        pass


class TimeSignalCanvas(BaseCanvas):

    def __init__(self, sampleRate, windowSize, *args, dataAlpha=0.85, dataBoundsMultiplier=0.03, **kwargs):
        self.__initAttributes__(sampleRate, windowSize,
                                dataAlpha, dataBoundsMultiplier)

        BaseCanvas.__init__(self, *args, **kwargs)

        self.axes = self.fig.add_subplot(111)

    def __initAttributes__(self, sampleRate, windowSize, dataAlpha, dataBoundsMultiplier):
        self.sampleRate = sampleRate
        self.windowSize = windowSize
        self.dataAlpha = dataAlpha
        self.dataBoundsMultiplier = dataBoundsMultiplier

        self.duration = self.windowSize / self.sampleRate
        self.arange = arange(0, self.duration, self.duration / self.windowSize)

    def makePlot(self, y, first=False):
        if first:
            self.dataUpperBound = max(y) * (1 + self.dataBoundsMultiplier)
            self.dataLowerBound = min(y) * (1 - self.dataBoundsMultiplier)
        else:
            self.dataUpperBound = self.dataUpperBound * \
                self.dataAlpha + max(y) * (1 - self.dataAlpha) * \
                (1 + self.dataBoundsMultiplier)
            self.dataLowerBound = self.dataLowerBound * \
                self.dataAlpha + min(y) * (1 - self.dataAlpha) * \
                (1 - self.dataBoundsMultiplier)

        s1 = self.ms / 1000
        x = self.arange + s1
        self.axes.set_ylim([self.dataLowerBound, self.dataUpperBound])
        self.axes.plot(x, y)

    def compute_initial_figure(self, start):
        self.ms = start
        self.makePlot(self.func(), True)

    def update_figure(self, delay):
        self.ms += delay
        self.axes.cla()
        self.makePlot(self.func())
        self.draw()


class DescomposedTimeSignalCanvas(BaseCanvas):

    def __init__(self, sampleRate, windowSize, bands, *args, **kwargs):
        self.__initAttributes__(sampleRate, windowSize)

        BaseCanvas.__init__(self, *args, **kwargs)

        self.bands = bands
        nBands = len(bands)
        self.subplots = {band: self.fig.add_subplot(
            nBands, 1, i + 1, title=band) for i, band in enumerate(bands)}

    def __initAttributes__(self, sampleRate, windowSize):
        self.sampleRate = sampleRate
        self.windowSize = windowSize

        self.duration = self.windowSize / self.sampleRate
        self.arange = arange(0, self.duration, self.duration / self.windowSize)

    def makeSubplot(self, subplot, y):
        s1 = self.ms / 1000
        x = self.arange + s1
        subplot.plot(x, y)

    def makeSubplots(self):
        for key, y in self.func().items():
            if key in self.bands:
                self.makeSubplot(self.subplots[key], y)

    def compute_initial_figure(self, start):
        self.ms = start
        self.makeSubplots()

    def update_figure(self, delay):
        self.ms += delay
        self.cleanSubplots()
        self.makeSubplots()
        self.draw()

    def cleanSubplots(self):
        for band, subplot in self.subplots.items():
            subplot.cla()
            subplot.set_title(band, fontsize=12, y=1.08)


class AverageBandPowerCanvas(BaseCanvas):

    def __init__(self, *args, **kwargs):

        BaseCanvas.__init__(self, *args, **kwargs)

        self.axes = self.fig.add_subplot(111)

    def makePlot(self):
        data = self.func()
        bands = list(data.keys())
        x = np.arange(len(bands))
        self.axes.set_xticks(x)
        self.axes.set_xticklabels(bands)
        self.axes.bar(x, list(data.values()))

    def compute_initial_figure(self, start):
        self.makePlot()

    def update_figure(self, delay):
        self.axes.cla()
        self.makePlot()
        self.draw()


class FeaturesCanvas(BaseCanvas):

    def __init__(self, featuresNames, *args, **kwargs):
        self.__initAttributes__(featuresNames)

        BaseCanvas.__init__(self, *args, **kwargs)

        self.axes = self.fig.add_subplot(111)

    def __initAttributes__(self, featuresNames, innerWindowSize=64):

        self.innerWindowSize = innerWindowSize
        self.featuresNames = featuresNames
        self.nFeatures = len(featuresNames)

    def makePlots(self):
        s1 = self.ms / 1000
        x = self.arange + s1
        for i, name in enumerate(self.featuresNames):
            y = list(reversed(self.slidingWindow.getComponentAt(i)))
            self.axes.plot(x, y, label=name)
        self.axes.legend()

    def compute_initial_figure(self, start):
        self.ms = start
        self.firstCall = True
        self.slidingWindow = SampleWindow(self.innerWindowSize, self.nFeatures)

    def update_figure(self, delay):
        if self.firstCall:
            duration = delay * self.innerWindowSize / 1000
            self.ms -= int(duration * 1000)
            self.arange = arange(0, duration, duration / self.innerWindowSize)
            self.firstCall = False
        self.ms += delay
        self.axes.cla()
        data = self.func()
        self.slidingWindow.add(data)
        self.makePlots()
        self.draw()
