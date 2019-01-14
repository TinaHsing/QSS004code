import os
import sys
import paramiko 
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import threading
import time
import random
import numpy as np

StartVoltage_MIN = 0
StartVoltage_MAX = 1000

VoltageStep_MIN = 1
VoltageStep_MAX = 50

Loop_MIN = 50
Loop_MAX = 1000

TimeDelay_MIN = 10
TimeDelay_MAX = 500

DAC_Constant = float(6.0/2000.0)

DC_Voltage1_MIN = 500
DC_Voltage1_MAX = 2000

DC_Voltage2_MIN = 500
DC_Voltage2_MAX = 2000

Fan_Speed_MIN = 2000
Fan_Speed_MAX = 5000


class adjustBlock():
    def __init__(self, name, minValue, maxValue):
        self.name = name
        self.min = minValue
        self.max = maxValue
        self.coarse = QSlider(Qt.Horizontal)
        self.spin = QSpinBox()
        self.adjGroupBox = QGroupBox(self.name)
        self.coarse.setRange(minValue,maxValue)
        self.coarse.valueChanged[int].connect(self.update_spin)
        self.spin.setRange(minValue, maxValue)
        self.spin.editingFinished.connect(self.update_slider)
    def adjBlockWidget(self):
        adjLayout = QHBoxLayout() 
        adjLayout.addWidget(self.coarse)
        adjLayout.addWidget(self.spin)     
        self.adjGroupBox.setLayout(adjLayout)
        self.adjGroupBox.show()
        return self.adjGroupBox
    def update_spin(self):
        a=self.coarse.value()
        self.spin.setValue(a)
    def update_slider(self):
        a=self.spin.value()
        self.coarse.setSliderPosition(a)


class outputPlot(QWidget):
    def __init__(self, parent=None):
        super(outputPlot, self).__init__(parent)
        self.figure = Figure(figsize=(6,3))
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.ax = self.figure.add_subplot(111)


class HVScan_Group(QTabWidget):
    def __init__(self, parent=None):
        super(HVScan_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("High Voltage Scan")
        self.StartVoltage = adjustBlock("Start Voltage (V)", StartVoltage_MIN, StartVoltage_MAX)
        self.VoltageStep = adjustBlock("Voltage Step (V)", VoltageStep_MIN, VoltageStep_MAX)
        self.Loop = adjustBlock("Loop", Loop_MIN, Loop_MAX)
        self.TimeDelay = adjustBlock("Time Delay (ms)", TimeDelay_MIN, TimeDelay_MAX)
        self.text1 = QLabel("Voltage Out = ")
        self.text2 = QLabel("0")
        self.StartBtn = QPushButton("Start")
        self.StopBtn = QPushButton("Stop")
        self.StartBtn.clicked.connect(lambda:self.StartScan())
        self.StopBtn.clicked.connect(lambda:self.StopScan())
        #self.SubBlockWidget()
        self.Vout1 = 0
        self.Vout2 = 0.0
        self.Scan = True

    def SubBlockWidget(self):
        layout = QGridLayout()
        layout.addWidget(self.StartVoltage.adjBlockWidget(),0,0,1,2)
        layout.addWidget(self.VoltageStep.adjBlockWidget(),0,2,1,2)
        layout.addWidget(self.Loop.adjBlockWidget(),1,0,1,2)
        layout.addWidget(self.TimeDelay.adjBlockWidget(),1,2,1,2)
        layout.addWidget(self.text1,2,0,1,1)
        layout.addWidget(self.text2,2,1,1,1)
        layout.addWidget(self.StartBtn,2,2,1,1)
        layout.addWidget(self.StopBtn,2,3,1,1)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox

    def VoltageOut(self):
        SV_value = self.StartVoltage.spin.value()
        VS_value = self.VoltageStep.spin.value()
        Loop_value = self.Loop.spin.value()
        TD_value = float(self.TimeDelay.spin.value()/1000.0)
        i = 0
        while (i < Loop_value) & (self.Scan == True):
            self.Vout1 = SV_value + VS_value * i
            self.Vout2 = float(self.Vout1) * DAC_Constant
            self.text2.setText(str(self.Vout1))
            self.text2.show()
            #OutStr = str(i) + " : " + str(self.Vout1) + " , " + str(self.Vout2)
            #print OutStr
            time.sleep(TD_value)
            i = i + 1

    def StartScan(self):
        self.Vout1 = 0
        self.Vout2 = 0
        self.Scan = True
        gt = threading.Thread(target = self.VoltageOut)
        gt.start()

    def StopScan(self):
        self.Vout1 = 0
        self.Vout2 = 0
        self.text2.setText("0")
        self.Scan = False


class DC_Voltage_Group(QTabWidget):
    def __init__(self, parent=None):
        super(DC_Voltage_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("DC Voltage Group")
        self.DC_Voltage1 = adjustBlock("DC Voltage1 (V)", DC_Voltage1_MIN, DC_Voltage1_MAX)
        self.SetDC1Btn = QPushButton("Set")
        self.SetDC1Btn.clicked.connect(lambda:self.SetDC1())
        self.DC_Voltage2 = adjustBlock("DC Voltage2 (V)", DC_Voltage2_MIN, DC_Voltage2_MAX)
        self.SetDC2Btn = QPushButton("Set")
        self.SetDC2Btn.clicked.connect(lambda:self.SetDC2())
        #self.SubBlockWidget()

    def SubBlockWidget(self):
        layout = QVBoxLayout()
        layout.addWidget(self.DC_Voltage1.adjBlockWidget())
        layout.addWidget(self.SetDC1Btn)
        layout.addWidget(self.DC_Voltage2.adjBlockWidget())
        layout.addWidget(self.SetDC2Btn)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox

    def SetDC1(self):
        DC1_value = self.DC_Voltage1.spin.value()
        print DC1_value

    def SetDC2(self):
        DC2_value = self.DC_Voltage2.spin.value()
        print DC2_value


class Fan_Control_Group(QTabWidget):
    def __init__(self, parent=None):
        super(Fan_Control_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("Fan Control Group")
        self.Fan_Speed = adjustBlock("Fan Speed Setting (rpm)", Fan_Speed_MIN, Fan_Speed_MAX)
        self.text1 = QLabel("Fan Speed = ")
        self.text2 = QLabel("0")
        self.SetBtn = QPushButton("Set")
        self.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
        #self.SubBlockWidget()

    def SubBlockWidget(self):
        layout = QGridLayout()
        layout.addWidget(self.Fan_Speed.adjBlockWidget(),0,0,1,3)
        layout.addWidget(self.text1,1,0,1,1)
        layout.addWidget(self.text2,1,1,1,1)
        layout.addWidget(self.SetBtn,1,2,1,1)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox

    def SetFanSpeed(self):
        FS_value = self.Fan_Speed.spin.value()
        print FS_value


class Signal_Read_Group(QTabWidget):
    def __init__(self, parent=None):
        super(Signal_Read_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("Signal Read Group")
        self.text = QLabel("Signal Read Display")
        #self.SubBlockWidget()

    def SubBlockWidget(self):
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox


class mainWindow(QWidget):
    def __init__(self, parent=None):
        super (mainWindow, self).__init__(parent)
        self.setWindowTitle("New UI")
        self.resize(1280,760)
        self.move(50,50)
        self.HVScan = HVScan_Group()
        self.DC_Voltage = DC_Voltage_Group()
        self.Fan_Control = Fan_Control_Group()
        self.Signal_Read = Signal_Read_Group()
        self.plot = outputPlot()
        self.data = []
        self.main_UI()

    def main_UI(self):
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.HVScan.SubBlockWidget(),0,0,2,2)
        mainLayout.addWidget(self.DC_Voltage.SubBlockWidget(),0,2,2,1)
        mainLayout.addWidget(self.Fan_Control.SubBlockWidget(),0,3,1,1)
        mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),1,3,1,1)
        mainLayout.addWidget(self.plot,2,0,2,4)
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 5)
        mainLayout.setColumnStretch(0, 1)
        mainLayout.setColumnStretch(1, 1)
        mainLayout.setColumnStretch(2, 1)
        mainLayout.setColumnStretch(3, 1)
        self.setLayout(mainLayout)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    main = mainWindow()
    main.show()
    os._exit(app.exec_())
