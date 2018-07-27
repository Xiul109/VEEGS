from PyQt5 import QtWidgets
import numpy as np

class ChannelSelector(QtWidgets.QGroupBox):
    """
    This is a widget to select the channel to use when using a feature.
    """
    def __init__(self, nChannels, parent=None, names = None,
                                   title="Channel Selector"):
        QtWidgets.QGroupBox.__init__(self, parent)
        
        self.setTitle(title)
        self.channel = set()        #Default Channel
        
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
         
        self.selectAll = QtWidgets.QCheckBox("Select All")
        layout.addWidget(self.selectAll)        
        layout.addWidget(self._initInnerCBs(nChannels, names))
        
        self.nChannels = nChannels
        
        def toggleAll(toggled):
            for cb in self.cbs:
                cb.setChecked(toggled)
            
        self.selectAll.toggled.connect(toggleAll)
        
    def _initInnerCBs(self, nChannels, names):
        container = QtWidgets.QFrame()
        container.setFrameStyle(QtWidgets.QFrame.Plain | 
                                QtWidgets.QFrame.Panel  )

        grid = QtWidgets.QGridLayout()
        container.setLayout(grid)
        
        #Number of rows of the layout. It's the squared root of the number of
        #channels
        rows = int(np.ceil(np.sqrt(nChannels)))
        
        #This is a callback that change the channel when another one is
        #selected
        def setChannel(toggled, chann):
            if toggled:
                self.channel.add(chann)
            elif chann in self.channel:
                self.channel.remove(chann)
        
        self.cbs = []
        #This loop go through the rows and adds a checkBox for each channel
        for i in range(rows):
            for j in range(rows):
                if nChannels > 0:  #Checking if all the channels has ben added
                    nChannels -= 1
                    
                    channel = i * rows + j
                    if names:
                        name = names[channel]
                    else:
                        name=str(channel)
                        
                    rb = QtWidgets.QCheckBox(name)
                        
                    rb.toggled.connect(
                     lambda toggled, chann=channel: setChannel(toggled, chann))
                    
                    self.cbs.append(rb)
                    grid.addWidget(rb, i, j)
        
        return container
    
    def synchronize(self, synchronizer):
        f = lambda _:synchronizer.synchronizeChannel(self.channel)
        synchronizer.selectors.append(self)
        for cb in self.cbs:
            cb.clicked.connect(f)
        self.selectAll.clicked.connect(synchronizer.synchronizeSelectAll)
    
    def setChannel(self, channel):
        self.channel = channel
        for i, cb in enumerate(self.cbs):
            if i in channel:
                checked = True
            else:
                checked = False
            cb.setChecked(checked)
    
    def getChannel(self):
        return list(self.channel)
    
class Synchronizer():
    def __init__(self):
        self.selectors = []
        
    def synchronizeChannel(self, channels):
        for selector in self.selectors:
            selector.setChannel(channels)
    
    def synchronizeSelectAll(self, state):
        for selector in self.selectors:
            selector.selectAll.setChecked(state)
            
class ChannelSelectorDialog(QtWidgets.QDialog):
    def __init__(self, nChannels, names, parent=None):
        super().__init__(parent)
        
        #Add layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        #Add channelSelector widget
        self.channelSelector = ChannelSelector(nChannels, names = names)
        layout.addWidget(self.channelSelector)
        self.channelSelector.selectAll.setChecked(True)
        
        #Add buttons
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok  |
                                             QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
    
    def getChannel(self):
        return list(self.channelSelector.channel)