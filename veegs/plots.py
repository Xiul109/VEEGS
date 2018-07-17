"""
This module defines classes related to plotting graphs
"""
from numpy import arange
import numpy as np

from PyQt5 import QtCore, QtWidgets, uic

import pyqtgraph
from pyqtgraph import PlotWidget

import csv
import os

from eeglib.eeg import defaultBands

defaultBandsNames = list(defaultBands.keys())


class ChannelSelector(QtWidgets.QGroupBox):
    """
    This is a widget to select the channel to use when using a feature.
    """
    def __init__(self, nChannels, parent=None, title="Channel Selector"):
        QtWidgets.QGroupBox.__init__(self, parent)
        
        self.setTitle(title)
        self.channel = 0        #Default Channel
        
        #Number of rows of the layout. It's the squared root of the number of
        #channels
        rows = int(np.ceil(np.sqrt(nChannels)))
        
        grid = QtWidgets.QGridLayout()
        
        #This is a callback that change the channel when another one is
        #selected
        def setChannel(toggled, chann):
            if toggled:
                self.channel = chann
        
        #This loop go through the rows and adds a radioButton for each channel
        for i in range(rows):
            for j in range(rows):
                if nChannels > 0:  #Checking if all the channels has ben added
                    nChannels -= 1
                    
                    channel = i * rows + j
                    rb = QtWidgets.QRadioButton(str(channel))
                    
                    if channel == 0: #Default channel: 0
                        rb.toggle()
                        
                    rb.toggled.connect(
                     lambda toggled, chann=channel: setChannel(toggled, chann))
                    
                    grid.addWidget(rb, i, j)
                    
        self.setLayout(grid)


class PlotWindow(QtWidgets.QDialog):
    """
    This class allows the user choose what he wants to plot.
    """
    
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        
        selfdir=os.path.dirname(__file__)
        uic.loadUi(os.path.join(selfdir,"plotWindow.ui"), self)
        
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setModal(False)
        
        self.eegSettings = parent.eegSettings
        nChannels = parent.helper.nChannels

        self.__initApButton()
        self.__initClose()
        self.__initLogger()
        
        self.__addSelectors(nChannels)

    def __addSelectors(self, nChannels):
        #Raw data
        self.rawSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(0).layout().addWidget(self.rawSelector)
        
        #Decomposed signal
        self.decomposedSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(1).layout().addWidget(self.decomposedSelector)
        self.bandsCBs = [self.deltaCB, self.thetaCB, self.alphaCB, self.betaCB]
        
        #Average Band Power
        self.averageBPSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(2).layout().addWidget(self.averageBPSelector)
        
        #One Channel Features
        self.featuresSelector = ChannelSelector(nChannels, self)
        self.tabWidget.widget(3).layout().addWidget(self.featuresSelector)
        
        #Two Channel Features
        name = "Channel %d Selector"
        self.C1Selector = ChannelSelector(nChannels, self, name%1)
        self.tabWidget.widget(4).layout().addWidget(self.C1Selector)
        
        self.C2Selector = ChannelSelector(nChannels, self, name%2)
        self.tabWidget.widget(4).layout().addWidget(self.C2Selector)
    
    def __initApButton(self):
        def addPlot():
            tIndex = self.tabWidget.currentIndex()
            
            tabName = self.tabWidget.currentWidget().accessibleName()
            text = self.nameTB.text()
            self.setWindowTitle(text if text != "" else tabName)
            
            eeg = self.parentWidget().helper.eeg
            
            #Raw data
            if tIndex == 0:
                self.canvasClass = TimeSignalCanvas
                
                channel = self.rawSelector.channel
                function = lambda : eeg.getChannel(channel)
                    
                self.canvasArgs = (self.eegSettings["sampleRate"],
                                   self.eegSettings["windowSize"],
                                   function                      )
                
            #Decomposed data
            elif tIndex == 1:
                self.canvasClass = DescomposedTimeSignalCanvas
                
                channel = self.decomposedSelector.channel
                function = lambda : eeg.getSignalAtBands(channel)
                          
                self.canvasArgs = (self.selectedBands(),
                                   self.eegSettings["sampleRate"],
                                   self.eegSettings["windowSize"],
                                   function                      )
                
            #Average Band Power
            elif tIndex == 2:
                self.canvasClass = FeaturesCanvas
                
                channel = self.averageBPSelector.channel
                function = lambda : eeg.getAverageBandValues(channel)
                
                self.canvasArgs = (defaultBandsNames,
                                   function         )
            
            #One Channel Features
            elif tIndex == 3:
                self.canvasClass = FeaturesCanvas
                
                funcs, names = self.getFeatures1CFuncsAndNames()
                function = lambda: {name: f() for f, name in zip(funcs, names)}
                
                self.canvasArgs = (names, function)
                
            #Two Channel Features
            elif tIndex == 4:
                self.canvasClass = FeaturesCanvas
                            
                funcs, names = self.getFeatures2CFuncsAndNames()
                function = lambda: {name: f() for f, name in zip(funcs, names)}
                
                self.canvasArgs = (names, function)
            
            
            
            #Error
            else:
                raise Exception("The selected tab doesn't exist")
            
            
            self.cleanWidgets()
            self.canvasKargs = {"logFileName": self.loggerFile} \
                                    if self.loggerFile else  {}
            self.addCanvas()

        self.apButton.clicked.connect(addPlot)

    def __initClose(self):
        parent = self.parentWidget()
        self.finished.connect(lambda: parent.deleteWinFromList(self))

    def __initLogger(self):
        self.loggerFile = None
        
        messageNoFile = "No file selected. Data won't be logged."
        messageFile = 'File selected:"{}" . Click here to deselect it.'
        
        def deselectFile(event):
            self.loggerFile = None
            self.loggerLabel.mouseReleaseEvent = lambda e: None
            self.loggerLabel.setText(messageNoFile)
            
        def openFileDialog():
            prevDir = self.parentWidget().prevSaveDir
            filename = QtWidgets.QFileDialog.getSaveFileName(self             ,
                                               directory = prevDir            ,
                                               filter    = "CSV-Files (*.csv)")
            
            if filename[0] != "":
                self.parentWidget().prevSaveDir = filename[0]
                self.loggerFile = filename[0]
                
                self.loggerLabel.setText(messageFile.format(filename[0]))
                self.loggerLabel.mouseReleaseEvent = deselectFile

        self.loggerButton.clicked.connect(openFileDialog)

    def cleanWidgets(self):
        for _ in range(self.layout.count()):
            self.layout.takeAt(0).widget().setParent(None)

    def addCanvas(self):
        plotter = PlotWidget(self)
        
        l = self.layout
        l.addWidget(plotter)
        
        self.canvas = self.canvasClass(
            *self.canvasArgs, plotter, **self.canvasKargs)
        
        self.destroyed.connect(self.canvas.closeFile)
        
        return plotter

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

    def getFeatures1CFuncsAndNames(self):
        channel = self.featuresSelector.channel
        
        featuresFuncs = []
        featuresNames = []
        
        eeg = self.parentWidget().helper.eeg
        #HFD
        if self.hfdCB.isChecked():
            featuresFuncs.append(lambda :                 eeg.HFD(channel))
            featuresNames.append("HFD")
        #PFD    
        if self.pfdCB.isChecked():
            featuresFuncs.append(lambda :                 eeg.PFD(channel))
            featuresNames.append("PFD")
        #Hjorth Activity    
        if self.hjorthActivityCB.isChecked():
            featuresFuncs.append(lambda :      eeg.hjorthActivity(channel))
            featuresNames.append("Hjorth Activity")
        #Hjorth Mobility   
        if self.hjorthMobilityCB.isChecked():
            featuresFuncs.append(lambda :      eeg.hjorthMobility(channel))
            featuresNames.append("Hjorth Mobility")
        #Hjorth Complexity
        if self.hjorthComplexityCB.isChecked():
            featuresFuncs.append(lambda :    eeg.hjorthComplexity(channel))
            featuresNames.append("Hjorth Complexity")
        #Sample Entropy
        if self.mseCB.isChecked():
            featuresFuncs.append(lambda :                 eeg.MSE(channel))
            featuresNames.append("Sample Entropy")
        #Lempel-Ziv Complexity
        if self.lzcCB.isChecked():
            featuresFuncs.append(lambda : eeg.LZC(channel, normalize=True))
            featuresNames.append("Lempel-Ziv Complexity")
        #Detrended Fluctuation Analysis
        if self.dfaCB.isChecked():
            featuresFuncs.append(lambda :                 eeg.DFA(channel))
            featuresNames.append("Detrended Fluctuation Analysis")
        #Engagement
        if self.engagementCB.isChecked():
            featuresFuncs.append(lambda:             eeg.engagementLevel())
            featuresNames.append("Engagement Level")

        return featuresFuncs, featuresNames
    
    def getFeatures2CFuncsAndNames(self):
        c1, c2 = self.C1Selector.channel, self.C2Selector.channel
        
        featuresFuncs = []
        featuresNames = []
        
        eeg = self.parentWidget().helper.eeg
        #Synchronization Likelihood
        if self.slCB.isChecked():
            featuresFuncs.append(lambda:eeg.synchronizationLikelihood((c1,c2)))
            featuresNames.append("Synchronization Likelihood")
        #Cross Correlation Coeficient
        if self.cccCB.isChecked():
            featuresFuncs.append(lambda :                     eeg.CCC((c1,c2)))
            featuresNames.append("CCC")
        
        return featuresFuncs, featuresNames


class BaseCanvas():
    timeField = "time(s)"

    def __init__(self, func, plot, logFileName=None):
        self.func = func
        self.plotter = plot
        
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
        self.plot = self.plotter.plot(x, y, clear=True)

    def getXY(self):
        y = self.func()
        x = self.arange + self.sec
        
        return x, y

    def write(self, fieldnames, data):
        self.writer.writerows(
            [{field: value[i] for field, value in zip(fieldnames, data)} 
                              for i in range(len(data[0]))             ]
            )

    def initAnimation(self, start):
        super().initAnimation(start)
        
        x, y = self.getXY()
        self.makePlot(x, y)
        
        if self.logMode:
            self.write(self.fieldnames, [x, y])

    def update_figure(self, delay):
        super().update_figure(delay)
        
        x, y = self.getXY()
        self.makePlot(x, y)
        
        if self.logMode:
            newDataStart = -int(self.sampleRate * (delay))
            self.write(self.fieldnames, [x[newDataStart:], y[newDataStart:]])


class DescomposedTimeSignalCanvas(TimeSignalCanvas):

    def __init__(self, bands, *args, **kwargs):
        self.bands = bands

        TimeSignalCanvas.__init__(self, *args, **kwargs)

        self.plotter.addLegend()
        self.legend = self.plotter.getPlotItem().legend

    def initLogFile(self):
        self.fieldnames = [self.timeField] + self.bands
        
        BaseCanvas.initLogFile(self, self.fieldnames)

    def makeSubplot(self, x, i, band, y):
        pen = pyqtgraph.mkPen(pyqtgraph.intColor(3 * i, 13))
        return self.plotter.plot(x,      y, 
                                 name=band, 
                                 pen=pen  )

    def makeSubplots(self, x, ys):
        self.plots = [self.makeSubplot(x, i, band, y) for i, (band, y) 
                                                      in enumerate(ys.items())]

    def getXY(self):
        x, ys = super().getXY()
        
        return x, {band: values for band, values 
                                in ys.items() 
                                if band in self.bands}

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
        
        self.cleanSubplots()
        
        x, ys = self.getXY()
        self.makeSubplots(x, ys)
        
        if self.logMode:
            newDataStart = -int(self.sampleRate * (delay))
            self.write(self.fieldnames, [v[newDataStart:]
                                         for v in [x] + list(ys.values())])

    def cleanSubplots(self):
        for plot, band in zip(self.plots, self.bands):
            plot.clear()
            self.legend.removeItem(band)


class AverageBandPowerCanvas(BaseCanvas):

    def __init__(self, bands, *args, **kwargs):
        BaseCanvas.__init__(self, *args, **kwargs)
        
        self.xAxe = self.plotter.getAxis("bottom")
        
        self.bands = bands
        self.x = list(range(len(bands)))
        
        self.sum = {band: 0 for band in bands}
        self.names = {band: band for band in bands}
        
        self.count = 0

    def initLogFile(self):
        self.fieldnames = [self.timeField] + self.bands
        super().initLogFile(self.fieldnames)

    def makePlot(self, data, names):
        self.xAxe.setTicks([list(zip(self.x, names))])
        
        self.plot = self.plotter.plot(self.x, list(data.values()), 
                                      symbol="o", clear=True     )

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

        self.legend = self.plotter.addLegend()

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
                
        self.plots = []
        
        for i, name in enumerate(self.featuresNames):
            pen=pyqtgraph.mkPen(pyqtgraph.intColor(3 * i, self.nFeatures * 3))
            self.plots.append(self.plotter.plot(self.time, self.data[name], 
                                                name=name, pen=pen        )
                             )
        
        self.update_figure(0)

    def initMeansData(self):
        self.sum = {name: 0 for name in self.featuresNames}
        self.count = 0

    def update_figure(self, delay):
        self.sec += delay
        currentTime = self.sec
        self.time.append(currentTime)
        
        self.count += 1
        
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
