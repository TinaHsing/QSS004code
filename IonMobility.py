import os
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import threading
import time
#import daq
#import smbus

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

SETTING_FILENAME = "setting.txt"
DEFAULT_FILENAME = "Signal_Read_Out.txt"

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
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
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
        #self.SubBlockWidget()

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


class DC_Voltage_Group(QTabWidget):
    def __init__(self, parent=None):
        super(DC_Voltage_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("DC Voltage Group")
        self.DC_Voltage1 = adjustBlock("DC Voltage1 (V)", DC_Voltage1_MIN, DC_Voltage1_MAX)
        self.SetDC1Btn = QPushButton("Set")
        self.DC_Voltage2 = adjustBlock("DC Voltage2 (V)", DC_Voltage2_MIN, DC_Voltage2_MAX)
        self.SetDC2Btn = QPushButton("Set")
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


class Fan_Control_Group(QTabWidget):
    def __init__(self, parent=None):
        super(Fan_Control_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("Fan Control Group")
        self.Fan_Speed = adjustBlock("Fan Speed Setting (rpm)", Fan_Speed_MIN, Fan_Speed_MAX)
        self.text1 = QLabel("Fan Speed = ")
        self.text2 = QLabel("0")
        self.SetBtn = QPushButton("Set")
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


class Signal_Read_Group(QTabWidget):
    def __init__(self, parent=None):
        super(Signal_Read_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("Signal Read")
        self.text = QLabel("0")
        pe = QPalette()
        pe.setColor(QPalette.WindowText,Qt.yellow)
        self.text.setAutoFillBackground(True)
        pe.setColor(QPalette.Window,Qt.black)
        #pe.setColor(QPalette.Background,Qt.black)
        self.text.setPalette(pe)
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setFont(QFont("",12,QFont.Bold))
        self.SaveBtn = QPushButton("Save")
        #self.SubBlockWidget()

    def SubBlockWidget(self):
        layout = QHBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(self.SaveBtn)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox


class mainWindow(QWidget):
    def __init__(self, parent=None):
        super (mainWindow, self).__init__(parent)
        self.setWindowTitle("Ion Mobility")
        self.resize(1280,760)
        self.move(50,50)
        self.HVScan = HVScan_Group()
        self.DC_Voltage = DC_Voltage_Group()
        self.Fan_Control = Fan_Control_Group()
        self.Signal_Read = Signal_Read_Group()
        self.plot = outputPlot()
        self.card = daq.Card()
        self.I2C = smbus.SMBus(0)

        self.SettingData = [0, 0, 0, 0, 0, 0, 0]
        if os.path.exists(SETTING_FILENAME):
            self.SettingData = [line.rstrip('\n') for line in open(SETTING_FILENAME)]
        #print(self.SettingData)

        #HVScan
        self.HVScan.StartBtn.clicked.connect(lambda:self.StartScan())
        self.HVScan.StopBtn.clicked.connect(lambda:self.StopScan())
        self.Vout1 = 0
        self.Vout2 = 0.0
        self.HVScanFlag = False
        self.SV_value = int(self.SettingData[0])
        self.VS_value = int(self.SettingData[1])
        self.Loop_value = int(self.SettingData[2])
        self.TD_value = int(self.SettingData[3])
        self.HVScan.StartVoltage.coarse.setValue(self.SV_value)
        self.HVScan.StartVoltage.spin.setValue(self.SV_value)
        self.HVScan.VoltageStep.coarse.setValue(self.VS_value)
        self.HVScan.VoltageStep.spin.setValue(self.VS_value)
        self.HVScan.Loop.coarse.setValue(self.Loop_value)
        self.HVScan.Loop.spin.setValue(self.Loop_value)
        self.HVScan.TimeDelay.coarse.setValue(self.TD_value)
        self.HVScan.TimeDelay.spin.setValue(self.TD_value)
        #DC_Voltage
        self.DC_Voltage.SetDC1Btn.clicked.connect(lambda:self.SetDC1())
        self.DC_Voltage.SetDC2Btn.clicked.connect(lambda:self.SetDC2())
        self.DC1_value = int(self.SettingData[4])
        self.DC2_value = int(self.SettingData[5])
        self.DC_Voltage.DC_Voltage1.coarse.setValue(self.DC1_value)
        self.DC_Voltage.DC_Voltage1.spin.setValue(self.DC1_value)
        self.DC_Voltage.DC_Voltage2.coarse.setValue(self.DC2_value)
        self.DC_Voltage.DC_Voltage2.spin.setValue(self.DC2_value)
        #Fan_Control
        self.Fan_Control.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
        self.FanSpeedFlag = False
        self.FS_value = int(self.SettingData[6])
        self.Fan_Control.Fan_Speed.coarse.setValue(self.FS_value)
        self.Fan_Control.Fan_Speed.spin.setValue(self.FS_value)
        #Signal_Read
        self.Signal_Read.SaveBtn.clicked.connect(lambda:self.SaveData())
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

#HVScan
    def VoltageOut(self):
        TD_value_float = float(self.TD_value/1000.0)
        i = 0
        while (i < self.Loop_value) & (self.HVScanFlag == True):
            self.Vout1 = self.SV_value + self.VS_value * i
            self.Vout2 = float(self.Vout1) * DAC_Constant
            #OutStr = str(i) + " : " + str(self.Vout1) + " , " + str(self.Vout2)
            #print(OutStr)
            self.card.writeAoValue(0, self.Vout2)
            self.HVScan.text2.setText(str(self.Vout1))
            self.HVScan.text2.show()
            #Signal_Read
            SR_read = self.card.readAiValue(0)
            #print(SR_read)
            self.Signal_Read.text.setText(str(SR_read))
            self.Signal_Read.text.show()
            #plot
            self.data.append(SR_read)
            self.plot.ax.clear()
            if ( i % 50 == 0 ):
                self.plot.ax.plot(self.data, '-')
                self.plot.canvas.draw()
            time.sleep(TD_value_float)
            i = i + 1

    def StartScan(self):
        self.SV_value = self.HVScan.StartVoltage.spin.value()
        self.VS_value = self.HVScan.VoltageStep.spin.value()
        self.Loop_value = self.HVScan.Loop.spin.value()
        self.TD_value = self.HVScan.TimeDelay.spin.value()
        self.SettingData[0] = self.SV_value
        self.SettingData[1] = self.VS_value
        self.SettingData[2] = self.Loop_value
        self.SettingData[3] = self.TD_value
        self.SettingData[4] = self.DC1_value
        self.SettingData[5] = self.DC2_value
        self.SettingData[6] = self.FS_value
        #print(self.SettingData)
        SettingData = [str(line) + '\n' for line in self.SettingData] 
        fo = open(SETTING_FILENAME, "w+")
        fo.writelines(SettingData)
        fo.close()

        self.Vout1 = 0
        self.Vout2 = 0.0
        self.HVScanFlag = True
        gt1 = threading.Thread(target = self.VoltageOut)
        gt1.start()
        #plot
        self.data = []
        self.plot.ax.clear()
        self.plot.ax.plot(self.data, '*-')
        self.plot.canvas.draw()

    def StopScan(self):
        self.Vout1 = 0
        self.Vout2 = 0.0
        self.HVScanFlag = False
        self.HVScan.text2.setText("0")
        self.FanSpeedFlag = False
        self.card.enableCounter(False)

#DC_Voltage
    def SetDC1(self):
        self.DC1_value = self.DC_Voltage.DC_Voltage1.spin.value()
        DC1_value_out = self.DC1_value * DAC_Constant
        #print(DC1_value_out)
        self.card.writeAoValue(1, DC1_value_out)

    def SetDC2(self):
        self.DC2_value = self.DC_Voltage.DC_Voltage2.spin.value()
        DC2_value_out = int(self.DC2_value * DAC_Constant / 5 * 16383)
        DC2_L = DC2_value_out & 0xFF
        DC2_H = int(DC2_value_out / 256)
        #OutStr = str(DC2_value_out) + " , " + str(DC2_H) + " , " + str(DC2_L)
        #print(OutStr)
        self.I2C.write_byte_data(0x60, DC2_H, DC2_L)

#Fan_Control
    def FanSpeedOut(self):
        while (self.FanSpeedFlag == True):
            FS_read = self.card.readFreq()
            print(FS_read)
            self.Fan_Control.text2.setText(str(FS_read))
            self.Fan_Control.text2.show()
            time.sleep(1)

    def SetFanSpeed(self):
        self.FS_value = self.Fan_Control.Fan_Speed.spin.value()
        FS_L = self.FS_value & 0xFF
        FS_H = int(self.FS_value / 256)
        #OutStr = str(FS_value) + " , " + str(FS_H) + " , " + str(FS_L)
        #print(OutStr)
        self.I2C.write_byte_data(0x61, FS_H, FS_L)
        self.FanSpeedFlag = True
        self.card.enableCounter(True)
        gt2 = threading.Thread(target = self.FanSpeedOut)
        gt2.start()

#Signal_Read
    def SaveData(self):
        SaveData = [str(line) + '\n' for line in self.data] 
        #fo = open(DEFAULT_FILENAME, "w+")
        SaveFileName = QFileDialog.getSaveFileName(self,
                                        "Save Signal Data",
                                        "./" + DEFAULT_FILENAME,
                                        "Text Files (*.txt)")
        fo = open(SaveFileName, "w+")
        fo.writelines(SaveData)
        fo.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    main = mainWindow()
    main.show()
    os._exit(app.exec_())
