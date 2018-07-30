import os
import sys

from PyQt5 import QtCore, QtWidgets, QtGui,uic

class OptionsDialog(QtWidgets.QDialog):
    """
    This is a menu for establishing especial options in the program.
    """
    def __init__(self, parent=None, samples=16, speedMul=1.0):
        QtWidgets.QDialog.__init__(self, parent)
        
        selfdir = os.path.dirname(__file__)
        uic.loadUi(os.path.join(selfdir,"optionsDialog.ui"), self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.__initInputs(samples,speedMul)
        self.__initAccepted()

    def __initInputs(self,samples,speedMul):
        self.siInput.setValidator(QtGui.QIntValidator(1, sys.maxsize))
        self.siInput.setText(str(samples))
        
        self.speedMulInput.setValidator(QtGui.QDoubleValidator(0, 
                                                        sys.float_info.max, 4))
        self.speedMulInput.setText(str(speedMul))

    def __initAccepted(self):
        def setDelays():
            samples  = float(self.siInput.text())
            speedMul = float(self.speedMulInput.text())
            
            sampleRate = self.parent().helper.sampleRate
            
            simDelay = samples/sampleRate
            rtDelay  = simDelay/speedMul if speedMul!=0 else 0
            
            self.parent().simDelay = simDelay 
            self.parent().rtDelay  = rtDelay
            

        self.buttonBox.accepted.connect(setDelays)
