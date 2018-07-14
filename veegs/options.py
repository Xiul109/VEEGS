import os

from PyQt5 import QtCore, QtWidgets, QtGui,uic

class OptionsDialog(QtWidgets.QDialog):
    """
    This is a menu for establishing especial options in the program.
    """
    def __init__(self, parent=None, rtDelay=0.1, simDelay=0.1):
        QtWidgets.QDialog.__init__(self, parent)
        
        selfdir = os.path.dirname(__file__)
        uic.loadUi(os.path.join(selfdir,"optionsDialog.ui"), self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.__initInputs(rtDelay,simDelay)
        self.__initAccepted()

    def __initInputs(self,rtDelay,simDelay):
        self.rtInput.setValidator(  QtGui.QDoubleValidator() )
        self.rtInput.setText(  str(rtDelay)  )
        
        self.simInput.setValidator( QtGui.QDoubleValidator() )
        self.simInput.setText( str(simDelay) )

    def __initAccepted(self):
        def setDelays():
            self.parent().rtDelay  = float(self.rtInput.text() )
            self.parent().simDelay = float(self.simInput.text())

        self.buttonBox.accepted.connect(setDelays)
