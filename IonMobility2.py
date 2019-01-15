import os
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import threading
import time
import daq
import smbus

StartVoltage_MIN = 0
StartVoltage_MAX = 1000

VoltageStep_MIN = 1
VoltageStep_MAX = 50

Loop_MIN = 50
Loop_MAX = 1000

TimeDelay_MIN = 10
TimeDelay_MAX = 500

DAC_Constant_S5 = 6.0/5000.0

DC_Voltage1_MIN = 500
DC_Voltage1_MAX = 2000

DC_Voltage2_MIN = 500
DC_Voltage2_MAX = 2000

Fan_Speed_MIN = 1000
Fan_Speed_MAX = 5000

SETTING_FILENAME = "set/setting.txt"
DEFAULT_FILENAME = "Signal_Read_Out.txt"

I2C_DAC1_ADDRESS = 0x60
I2C_DAC1_ADDRESS = 0x61
EEPROM_WITH_Normal =0x60
EEPROM_WITH_PD = 0x66
I2CDAC_CONV_CONST = 4095.0/5.0

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
        W=QWidget()
        picout = QLabel(w)
        logo = QPixmap("logo.png")
        picout.setPixmap(logo)
        layout = QGridLayout()
        layout.addWidget(self.canvas,0,0,1,2)
        layout.addWidget(self.toolbar,1,0,1,1)
        layout.addWidget(picout,1,1,1,1)
        self.setLayout(layout)
        self.ax = self.figure.add_subplot(111)

class Signal_Read_Group(QTabWidget):

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
        self.text.setFont(QFont("",16,QFont.Bold))
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

class HVScan_Group(QTabWidget):
    def __init__(self, parent=None, signal_read, plot, card):
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
        self.HVScanFlag = False

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
        self.GroupBox = QGroupBox("DC Voltage Control")
        self.DC_Voltage1 = adjustBlock("DC Voltage1 (V)", DC_Voltage1_MIN, DC_Voltage1_MAX)
        self.DC1_Label1 = QLabel("DC Vout1 =")
        self.DC1_Label2 = QLabel("0")
        self.SetDC1Btn = QPushButton("Set")
        self.DC_Voltage2 = adjustBlock("DC Voltage2 (V)", DC_Voltage2_MIN, DC_Voltage2_MAX)
        self.SetDC2Btn = QPushButton("Set")
        self.DC2_Label1 = QLabel("DC Vout2 =")
        self.DC2_Label2 = QLabel("0")
        #self.SubBlockWidget()

    def SubBlockWidget(self):
        layout = QGridLayout()
        layout.addWidget(self.DC_Voltage1.adjBlockWidget(),0,0,1,3)
        layout.addWidget(self.DC1_Label1,1,0,1,1)
        layout.addWidget(self.DC1_Label2,1,1,1,1)
        layout.addWidget(self.SetDC1Btn,1,2,1,1)
        layout.addWidget(self.DC_Voltage2.adjBlockWidget(),2,0,1,3)
        layout.addWidget(self.DC2_Label1,3,0,1,1)
        layout.addWidget(self.DC2_Label2,3,1,1,1)
        layout.addWidget(self.SetDC2Btn,3,2,1,1)
        #self.setLayout(layout)
        self.GroupBox.setLayout(layout)
        self.GroupBox.show()
        return self.GroupBox

class Fan_Control_Group(QTabWidget):
    def __init__(self, parent=None):
        super(Fan_Control_Group, self).__init__(parent)
        self.GroupBox = QGroupBox("Fan Control")
        self.Fan_Speed = adjustBlock("Fan Speed Setting (mV)", Fan_Speed_MIN, Fan_Speed_MAX)
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

class i2cDac:
    def __init__(self, bus):
        self.i2cbus=smbus.SMBus(bus) # in this case use SMBus(0)

    def DacInit(self, address):
        self.i2cbus.write_byte_data(address)
        self.i2cbus.write_byte_data(EEPROM_WITH_Normal)
        self.i2cbus.write_byte_data(0)
        self.i2cbus.write_byte_data(0)
    def DacSet(self, address, value):
        dacout = int(value*I2CDAC_CONV_CONST)
        out = dacout.to_bytes(2, byteorder ="big")
        self.i2cbus.write_byte_data(address)
        self.i2cbus.write_byte_data(out[0])
        self.i2cbus.write_byte_data(out[1])
    def DacClose(self, address):
         self.i2cbus.write_byte_data(address)
         self.i2cbus.write_byte_data(EEPROM_WITH_PD)
         self.i2cbus.write_byte_data(0)
         self.i2cbus.write_byte_data(0)
        
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
        self.I2C = i2cDac(0)
        self.I2C.DacInit(I2C_DAC1_ADDRESS)
        self.I2C.DacInit(I2C_DAC2_ADDRESS)
        self.SettingData = loadPreset.Load()

        #HVScan
        self.HVScan.StartBtn.clicked.connect(lambda:self.StartScan())
        self.HVScan.StopBtn.clicked.connect(lambda:self.StopScan())
        #self.Vout1 = 0
        #self.Vout2 = 0.0
        self.HVScanFlag = False

        #DC_Voltage
        self.DC_Voltage.SetDC1Btn.clicked.connect(lambda:self.SetDC1())
        self.DC_Voltage.SetDC2Btn.clicked.connect(lambda:self.SetDC2())

        #Fan_Control
        self.Fan_Control.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
        self.FanSpeedFlag = False

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

    def LoadPreset(self):
        self.SettingData = [0 for i in range(0, 7)]
        if os.path.exists(SETTING_FILENAME):
            self.SettingData = [line.rstrip('\n') for line in open(SETTING_FILENAME)]

        self.HVScan.StartVoltage.coarse.setValue( int(self.SettingData[0]))
        self.HVScan.VoltageStep.coarse.setValue( int(self.SettingData[1]))
        self.HVScan.Loop.coarse.setValue(int(self.SettingData[2]))
        self.HVScan.TimeDelay.coarse.setValue(int(self.SettingData[3]))
        self.DC_Voltage.DC_Voltage1.coarse.setValue(int(self.SettingData[4]))
        self.DC_Voltage.DC_Voltage2.coarse.setValue(int(self.SettingData[5]))
        self.Fan_Control.Fan_Speed.coarse.setValue(int(self.SettingData[6]))

#HVScan
    def VoltageOut(self):
        TD_value_float = float(self.HVScan.TimeDelay.spin.value()/1000.0)
        i = 0
        loopValue = self.HVScan.Loop.spin.value()
        startValue = self.HVScan.StartVoltage.spin.value()
        stepValue = self.HVScan.VoltageStep.spin.value()
        while (i < loopValue) & (self.HVScanFlag == True):
            Vout1 = startValue + stepValue * i
            Vout2 = float(Vout1) * DAC_Constant_S5
            self.card.writeAoValue(0, Vout2)
            self.HVScan.text2.setText(str(Vout1))
            self.HVScan.text2.show()
            #Signal_Read
            SR_read = self.card.readAiValue(0)
            #print(SR_read)
            self.Signal_Read.text.setText(str(SR_read))
            self.Signal_Read.text.show()
            #plot
            self.data.append(SR_read)
            if ( i % 50 == 0 ):
                self.plot.ax.clear()
                self.plot.ax.plot(self.data, '-')
                self.plot.canvas.draw()
            time.sleep(TD_value_float)
            i = i + 1

    def StartScan(self):
        self.SettingData[0] = self.HVScan.StartVoltage.spin.value()
        self.SettingData[1] = self.HVScan.VoltageStep.spin.value()
        self.SettingData[2] = self.HVScan.Loop.spin.value()
        self.SettingData[3] = self.HVScan.TimeDelay.spin.value()
        self.SettingData[4] = self.DC1_value
        self.SettingData[5] = self.DC2_value
        self.SettingData[6] = self.FS_value
        #print(self.SettingData)
        SettingData = [str(line) + '\n' for line in self.SettingData] 
        fo = open(SETTING_FILENAME, "w+")
        fo.writelines(SettingData)
        fo.close()
        self.HVScanFlag = True
        gt1 = threading.Thread(target = self.VoltageOut)
        gt1.start()
        self.data = []

    def StopScan(self):
        self.HVScanFlag = False
        self.HVScan.text2.setText("0")
        self.card.writeAoValue(0, 0)
        self.FanSpeedFlag = False
        self.card.enableCounter(False)

#DC_Voltage
    def SetDC1(self):
        value1= self.DC_Voltage.DC_Voltage1.spin.value()
        DC1_value_out =  value1 * DAC_Constant_S5
        self.I2C.DacSet(I2C_DAC1_ADDRESS, DC1_value_out)
        self.DC_Voltage.DC1_Label2.setText(str(value1))

    def SetDC2(self):
        value2 = self.DC_Voltage.DC_Voltage2.spin.value()
        DC2_value_out = value2 * DAC_Constant_S5
        self.I2C.DacSet(I2C_DAC2_ADDRESS, DC2_value_out)
        self.DC_Voltage.DC2_Label2.setText(str(value2))

#Fan_Control
    def FanSpeedOut(self):
        while (self.FanSpeedFlag == True):
            FS_read = self.card.readFreq()
            #print(FS_read)
            self.Fan_Control.text2.setText(str(FS_read))
            self.Fan_Control.text2.show()
            time.sleep(1)

    def SetFanSpeed(self):
        FS_value = float(self.Fan_Control.Fan_Speed.spin.value())/1000.0
        self.card.writeAoValue(1, FS_value)
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
