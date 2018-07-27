"""
This module defines classes related to plotting graphs
"""

import numpy as np

from PyQt5 import QtCore, QtWidgets, uic

import pyqtgraph as pg

import os

from itertools import combinations

from eeglib.eeg import defaultBands
import eeglib.wrapper as wrap

from .channelSelector import ChannelSelector, Synchronizer

defaultBandsNames = list(defaultBands.keys())

#Tabs names
rawTab   = "Raw"
bandsTab = "Average Band Power"
fftTab   = "FFT"
c1Tab    = "One Channel Features"
c2Tab    = "Two Channels Features"
c0Tab    = "Channeless Features"


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

        self.__initApButton()
        self.__initClose()
        
        nChannels = parent.helper.nChannels
        names     = parent.helper.names
        self.__addSelectors(nChannels, names)

    def __addSelectors(self, nChannels, names = None):
        synchronizer = Synchronizer()
        #Raw data
        self.baseSelector = ChannelSelector(nChannels, self, names)
        self.rawTab.layout().addWidget(self.baseSelector)
        self.baseSelector.synchronize(synchronizer)
        
        #Average Band Power
        self.averageBPSelector = ChannelSelector(nChannels, self, names)
        self.averagePowerBandTab.layout().addWidget(self.averageBPSelector)
        self.averageBPSelector.synchronize(synchronizer)
        
        # FFT
        self.fftSelector = ChannelSelector(nChannels,self, names)
        self.fftTab.layout().addWidget(self.fftSelector)
        self.fftSelector.synchronize(synchronizer)
        
        #One Channel Features
        self.featuresSelector = ChannelSelector(nChannels, self, names)
        self.oneChannelTab.layout().addWidget(self.featuresSelector)
        self.featuresSelector.synchronize(synchronizer)
        
        #Two Channel Features
        self.C2Selector = ChannelSelector(nChannels, self, names)
        self.twoChannelsTab.layout().addWidget(self.C2Selector)
        self.C2Selector.synchronize(synchronizer)
    
    def __initApButton(self):
        def addPlot():
            # Name of current tab
            tabName = self.tabWidget.tabText(self.tabWidget.currentIndex())
            # In order to fix a posible bug that occurs with KDE the "&"
            # symbols in the texts must be erased
            tabName = tabName.replace("&","")
            
            text = self.nameTB.text()
            self.setWindowTitle(text if text != "" else tabName)
           
            #Error flags
            channelError = featureError = False
            
            #Channel selected
            channel = self.baseSelector.getChannel()
            
            #Raw data
            if tabName == rawTab:
                self.canvasClass = TimeSignalCanvas;
                    
                self.canvasArgs = (channel,)
                
                channelError = len(channel)==0
                
            #Average Band Power
            elif tabName == bandsTab:
                self.canvasClass = BandValuesCanvas
                
                self.canvasArgs = (channel,)
                
                channelError = len(channel)==0
            
            #FFT
            elif tabName == fftTab:
                self.canvasClass = FFTCanvas
                
                self.canvasArgs = (channel,)
                
                channelError = len(channel)==0
            
            #One Channel Features
            elif tabName == c1Tab:
                self.canvasClass = FeaturesCanvas
                
                funcs, names = self._getFeatures1CFuncsAndNames()
                
                self.canvasArgs = (funcs, names, channel)
                
                channelError = len(channel) == 0
                featureError = len(names) == 0
                
            #Two Channel Features
            elif tabName == c2Tab:
                self.canvasClass = TwoChannelsCanvas
                
                funcs, names = self._getFeatures2CFuncsAndNames()
                
                self.canvasArgs = (funcs, names, channel)
                
                channelError = len(channel) < 2
                featureError = len(names) == 0
            
            #Channeless Features
            elif tabName == c0Tab:
                self.canvasClass = ChannelessCanvas
                
                funcs, names = self._getFeatures0CFuncsAndNames()
                
                self.canvasArgs = (funcs, names, None)
                
                featureError = len(names) == 0          
            
            #Error
            else:
                raise Exception("The selected tab doesn't exist")
            
            if not channelError and not featureError:
                self.cleanWidgets()
                self.addCanvas()
            elif channelError:
                QtWidgets.QMessageBox.warning(self, "Error",
                                           "You have to select more channels.",
                                           QtWidgets.QMessageBox.Ok)
            elif featureError:
                QtWidgets.QMessageBox.warning(self, "Error",
                                 "You have to select at least one(1) feature.",
                                 QtWidgets.QMessageBox.Ok)

        self.apButton.clicked.connect(addPlot)

    def __initClose(self):
        parent = self.parentWidget()
        self.finished.connect(lambda: parent.deleteWinFromList(self))

    def cleanWidgets(self):
        for _ in range(self.layout.count()):
            self.layout.takeAt(0).widget().setParent(None)

    def addCanvas(self):
        graphLayout = pg.GraphicsLayoutWidget()
        self.layout.addWidget(graphLayout)
        
        self.canvas = self.canvasClass(*self.canvasArgs       , 
                                       self.parent().helper   ,
                                       graphLayout            )

    def reset(self):
        if hasattr(self, "canvas"):
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

    def _getFeatures1CFuncsAndNames(self):
        featuresFuncs = []
        featuresNames = []
        
        #HFD
        if self.hfdCB.isChecked():
            featuresFuncs.append("HFD")
            featuresNames.append("HFD")
        #PFD    
        if self.pfdCB.isChecked():
            featuresFuncs.append("PFD")
            featuresNames.append("PFD")
        #Hjorth Activity    
        if self.hjorthActivityCB.isChecked():
            featuresFuncs.append("hjorthActivity")
            featuresNames.append("Hjorth Activity")
        #Hjorth Mobility   
        if self.hjorthMobilityCB.isChecked():
            featuresFuncs.append("hjorthMobility")
            featuresNames.append("Hjorth Mobility")
        #Hjorth Complexity
        if self.hjorthComplexityCB.isChecked():
            featuresFuncs.append("hjorthComplexity")
            featuresNames.append("Hjorth Complexity")
        #Sample Entropy
        if self.mseCB.isChecked():
            featuresFuncs.append("MSE")
            featuresNames.append("Sample Entropy")
        #Lempel-Ziv Complexity
        if self.lzcCB.isChecked():
            featuresFuncs.append("LZC")
            featuresNames.append("Lempel-Ziv Complexity")
        #Detrended Fluctuation Analysis
        if self.dfaCB.isChecked():
            featuresFuncs.append("DFA")
            featuresNames.append("Detrended Fluctuation Analysis")
        #Engagement
        if self.engagementCB.isChecked():
            featuresFuncs.append("engagementLevel")
            featuresNames.append("Engagement")

        return featuresFuncs, featuresNames
    
    def _getFeatures0CFuncsAndNames(self):
        featuresFuncs = []
        featuresNames = []
        
        #Engagement
        if self.engagementCB.isChecked():
            featuresFuncs.append("engagementLevel")
            featuresNames.append("Engagement")
            
        return featuresFuncs, featuresNames
    
    def _getFeatures2CFuncsAndNames(self):
        featuresFuncs = []
        featuresNames = []
        
        #Synchronization Likelihood
        if self.slCB.isChecked():
            featuresFuncs.append("synchronizationLikelihood")
            featuresNames.append("Synchronization Likelihood")
        #Cross Correlation Coeficient
        if self.cccCB.isChecked():
            featuresFuncs.append("CCC")
            featuresNames.append("CCC")
        
        return featuresFuncs, featuresNames


class BaseCanvas():
    timeField = "time(s)"

    def __init__(self, channels, helper, layout):
        self.layout   = layout
        self.channels = channels
        self.helper   = helper
        
        if channels:
            self.channelsNames = [self.helper.names[i] for i in self.channels]
        else:
            self. channelsNames = None

    def initAnimation(self, start):
        self.sec = start

    def update_figure(self, delay):
        self.sec += delay


class TimeSignalCanvas(BaseCanvas):
    signalField = "signal"

    def __init__(self, *args,):
        super().__init__(*args)
        
        self.windowSize = self.helper.eeg.windowSize
        self.sampleRate = self.helper.sampleRate
        self.wsSeconds = self.windowSize/self.sampleRate
        
        self.plotters=[self.layout.addPlot(row=i, col=0, title=name) 
                        for i, name in enumerate(self.channelsNames)]

    
    def initAnimation(self, start):
        super().initAnimation(start)
        self.start = start
        self.end   = start + self.wsSeconds
        
        self.sStart = int(start*self.sampleRate)
        
        self.makePlot()
    
    def update_figure(self, delay):
        super().update_figure(delay)
        self.end += delay
        
        self.makePlot()
        
    def makePlot(self):
        sEnd = int(self.end*self.sampleRate)
        
        ys = self.helper.data[self.channels, self.sStart:sEnd]
        x  = np.linspace(self.start, self.end, len(ys[0]))
        
        for plotter, y in zip(self.plotters, ys):
            plotter.setRange(xRange=(self.end-self.wsSeconds,self.end))
            plotter.plot(x,y, clear=True)


class FeaturesCanvas(BaseCanvas):
    def _wrapperFeatureName(self, name):
        return "_"+name+"_%d" 
    
    def _initWrapper(self, funcsNames):
        self.wrapper = wrap.Wrapper(self.helper, flat = True)
        
        for func in funcsNames:
            self.wrapper.addFeature(func, self.channels)
            
        self.funcsNames = [self._wrapperFeatureName(name)
                           for name in self.wrapper.featuresNames()]
    
    def _createPlotters(self):
        self.plotters=[self.layout.addPlot(row=i, col=0, title=name) 
                        for i, name in enumerate(self.channelsNames)]
        for plotter in self.plotters:
            plotter.addLegend()

    def __init__(self, funcsNames, featuresNames, *args):
        super().__init__(*args)
        
        self._initWrapper(funcsNames)
        self._createPlotters()
        
        self.featuresNames = featuresNames
        
        self.time = []
        


    def initAnimation(self, start):
        super().initAnimation(start)
        self.wrapper.reset()
        self.update_figure(0)


    def update_figure(self, delay):
        super().update_figure(delay)
        self.time.append(self.sec)
        
        self.clear()
        
        self.makePlot()
        
    def makePlot(self):
        self.wrapper.getFeatures()
        data = self.wrapper.getStoredFeatures()
        
        for i, plotter in enumerate(self.plotters):
            for (j,featureName), funcName in zip(enumerate(self.featuresNames),
                                                           self.funcsNames):
                #The color of the plotting of each feature
                pen=pg.mkPen(pg.intColor(j))
                
                #Get the data asociated to one feature
                dataName = self.getDataName(funcName, i)
                d=data[dataName]
                
                #Get the mean value of the data
                mean = np.mean(d)
                legend = featureName+": %.3f"%mean
                
                #Plot the data
                plotter.plot(self.time, d, pen = pen, name=legend)
    
    def getDataName(self, funcName,i):
        return funcName%i

    
    def clear(self):
        for plotter in self.plotters:
            plotter.clear()
            
            # This is done due to a bug in pyqtgraph
            # In the next version will be fixed
            labels = [label.text for _, label in plotter.legend.items]
            
            for label in labels:
                plotter.legend.removeItem(label)     

class BandValuesCanvas(FeaturesCanvas):
    def __init__(self, *args):
        super().__init__(["getAverageBandValues"], defaultBandsNames, *args)
        
    def _wrapperFeatureName(self, name):
        return super()._wrapperFeatureName(name) + "_%s"
    
    def makePlot(self):
        self.wrapper.getFeatures()
        data = self.wrapper.getStoredFeatures()
        
        for i, plotter in enumerate(self.plotters):
            for j, featureName in enumerate(self.featuresNames):
                pen=pg.mkPen(pg.intColor(j))
                
                dataName = self.funcsNames[0]%(i, featureName)
                d = data[dataName]
                
                mean = np.mean(d)
                legend = featureName+": %.3f"%mean
                
                plotter.plot(self.time, d, pen = pen, name=legend)

class TwoChannelsCanvas(FeaturesCanvas):
    def __init__(self, *args):
        super().__init__(*args)
        self.channels = list(combinations(self.channels, 2))
    
    def _createPlotters(self):
        self.plotters=[]
        
        combs = list(combinations(self.channelsNames,2))
        size = int(np.ceil(np.sqrt(len(combs))))
        
        for i, name in enumerate(combs):
            self.plotters.append(self.layout.addPlot(row=i//size, 
                                                     col=i%size, 
                                                     title=name))
            
        for plotter in self.plotters:
            plotter.addLegend()
    
    def _wrapperFeatureName(self, name):
        return "_"+name+"_(%d, %d)"
        
    def getDataName(self, funcName,i):
        return funcName%self.channels[i]

class ChannelessCanvas(FeaturesCanvas):
    def _initWrapper(self, funcsNames):
        self.wrapper = wrap.Wrapper(self.helper, flat = True)
        
        for func in funcsNames:
            self.wrapper.addFeature(func)
            
        self.funcsNames = ["_"+name for name in self.wrapper.featuresNames()]
    
    def _createPlotters(self):
        self.plotters=[self.layout.addPlot()]
  
        self.plotters[0].addLegend()
        
    def getDataName(self, funcName,i):
        return funcName
                  

class FFTCanvas(BaseCanvas):
    def __init__(self, *args):
        super().__init__(*args)
        
        windowSize = self.windowSize = self.helper.eeg.windowSize
        sampleRate = self.sampleRate = self.helper.sampleRate
        
        self.x = (np.arange(windowSize//2)+1)*sampleRate/windowSize
        
        self.plotters=[self.layout.addPlot(row=i, col=0, title=name) 
                        for i, name in enumerate(self.channelsNames)]
    
    def initAnimation(self, start):
        super().initAnimation(start)
        self.update_figure(0)
    
    def update_figure(self, delay):
        super().update_figure(delay)
        
        ffts = self.helper.eeg.getMagnitudes(self.channels)
        ffts = ffts[:,1:self.windowSize//2+1]
        
        for plotter, fft in zip(self.plotters, ffts):
            plotter.plot(self.x,fft,clear=True)
        

        
        