import os
import sys
import time
import paramiko
import threading
import numpy as np 
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import scipy
from scipy.signal import find_peaks, peak_widths

import COMPort
import serial
import serial.tools.list_ports

StartVoltage_MIN = 1000
StartVoltage_MAX = 1900

VoltageStep_MIN = 200
VoltageStep_MAX = 2000

Scan_Loop_MIN = 1
Scan_Loop_MAX = 2000

Backward_MIN = 0
Backward_MAX = 50
TimeDelay_MIN = 20
TimeDelay_MAX = 10000

MV_Numver_MIN = 50
MV_Numver_MAX = 30000

AVG_time_MIN = 1
AVG_time_MAX = 100

Run_Loop_MIN = 1
Run_Loop_MAX = 1000
DAC_Constant_S5 = 6.0 / 2000.0
DAC_Constant_S5_ESI = 6.0 / 5000.0
DAC_ratio = 65535.0 / 5.0
#DAC_Average_Number = 10

DC_Voltage1_MIN = 0
DC_Voltage1_MAX = 2000

DC_Voltage2_MIN = 0
DC_Voltage2_MAX = 5000

Fan_Speed_MIN = 0
Fan_Speed_MAX = 5000

Threshold_MIN = -10*1000
Threshold_MAX = 10*1000

Noise_MIN = 1
Noise_MAX = 100

SETTING_FILEPATH = "set"
SETTING_FILENAME = "set/setting_A.txt"
READOUT_FILENAME = "Signal_Read_Out.txt"
ANALYSIS_FILENAME = "Data_Analysis.txt"
LOGO_FILENAME = "set/logo.png"
ROW_FILEPATH = "row_data"

I2CDAC_CONV_CONST = 4095.0/5.0

DAC_ESI =  "SetVoltage 1 "
DAC_SCAN = "SetVoltage 2 "
DAC_SCAN_STOP = 'SetVoltage 2 0'
DAC_DC =   "SetVoltage 4 "
DAC_FAN =  "SetVoltage 5 "
ADC_SCAN_READ = "ReadVoltage "
READ_FAN_SPEED = "ReadCounter"

Baudrate = 115200
Timeout = 0.1

TITLE_TEXT = " GRC Ion Mobility Spectrometer "
VERSION_TEXT = TITLE_TEXT + "\n" + \
" IonMobilityA V1.0 \n\n" + \
" Copyright @ 2019 TAIP \n" + \
" Maintain by Quantaser Photonics Co. Ltd "

class spinBlock():
	def __init__(self, name, minValue, maxValue, text, value, SetBtn):
		self.name = name
		self.min = minValue
		self.max = maxValue
		self.adjGroupBox = QGroupBox(self.name)
		self.spin = QSpinBox()
		self.text = QLabel(text)
		self.value = QLabel(value)
		self.SetBtnFlag = SetBtn
		self.SetBtn = QPushButton("Set")
		self.spin.setRange(minValue, maxValue)
		self.spin.setSingleStep(1)
	def spinBlockWidget(self):
		adjLayout = QGridLayout()
		adjLayout.addWidget(self.spin,0,0,1,1)
		if (self.SetBtnFlag == True):
			adjLayout.addWidget(self.SetBtn,0,1,1,1)
			if (self.text.text() != ""):
				adjLayout.addWidget(self.text,0,2,1,1)
				adjLayout.addWidget(self.value,0,3,1,1)
		elif (self.text.text() != ""):
			adjLayout.addWidget(self.text,0,1,1,1)
			adjLayout.addWidget(self.value,0,2,1,1)
		self.adjGroupBox.setLayout(adjLayout)
		self.adjGroupBox.show()
		return self.adjGroupBox

class outputPlot(QWidget):
	def __init__(self, parent=None):
		super(outputPlot, self).__init__(parent)
		self.figure = Figure(figsize=(6,3))
		self.canvas = FigureCanvas(self.figure)
		self.toolbar = NavigationToolbar(self.canvas, self)
		# w = QWidget()
		# picout = QLabel(w)
		# lg = QPixmap(LOGO_FILENAME)
		# logo = lg.scaled(500, 90, Qt.KeepAspectRatio)
		# picout.setPixmap(logo)
		layout = QGridLayout()
		layout.addWidget(self.canvas,0,0,1,2)
		layout.addWidget(self.toolbar,1,0,1,1)
		#layout.addWidget(picout,1,1,1,1)
		self.setLayout(layout)
		self.ax = self.figure.add_subplot(111)
		self.ax.set_xlabel("dV (V)")
		self.ax.set_ylabel("Voltage Output (mV)")

class Signal_Read_Group(QWidget):
	def __init__(self, parent=None):
		super(Signal_Read_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Signal Read (mV)")
		self.text = QLabel("0")
		pe = QPalette()
		pe.setColor(QPalette.WindowText,Qt.yellow)
		self.text.setAutoFillBackground(True)
		pe.setColor(QPalette.Window,Qt.black)
		#pe.setColor(QPalette.Background,Qt.black)
		self.text.setPalette(pe)
		self.text.setAlignment(Qt.AlignCenter)
		self.text.setFont(QFont("",16,QFont.Bold))
		self.checkbox = QCheckBox("Save Row File")
		self.SaveDataBtn = QPushButton("Save Signal Data")
		#self.SubBlockWidget()
		self.SaveDataBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.text,0,0,2,2)
		layout.addWidget(self.checkbox,0,2,1,1)
		layout.addWidget(self.SaveDataBtn,1,2,1,1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class HVScan_Group(QWidget):
	def __init__(self, parent=None):
		super(HVScan_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("High Voltage Scan")
		self.StartVoltage = spinBlock("Start Voltage (V)", StartVoltage_MIN, StartVoltage_MAX, "", "", False)
		self.VoltageStep = spinBlock("Voltage Step (mV)", VoltageStep_MIN, VoltageStep_MAX, "", "", False)
		self.Loop = spinBlock("Total Steps", Scan_Loop_MIN, Scan_Loop_MAX, "", "", False)
		self.Back = spinBlock("Backward points", Backward_MIN, Backward_MAX, "", "", False)
		self.TimeDelay = spinBlock("Time Delay (ms)", TimeDelay_MIN, TimeDelay_MAX, "", "", False)
		self.text1 = QLabel("Voltage Out = ")
		self.text2 = QLabel("0 V")
		self.reset = QPushButton("Reset")
		self.reset.setEnabled(False)

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.StartVoltage.spinBlockWidget(),0,0,1,2)
		layout.addWidget(self.VoltageStep.spinBlockWidget(),0,2,1,2)
		layout.addWidget(self.Loop.spinBlockWidget(),1,0,1,2)
		layout.addWidget(self.Back.spinBlockWidget(),1,2,1,2)
		layout.addWidget(self.TimeDelay.spinBlockWidget(),2,0,2,2)
		layout.addWidget(self.text1,2,2,1,1)
		layout.addWidget(self.text2,2,3,1,1)
		layout.addWidget(self.reset,3,3,1,1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Data_Sampling_Group(QWidget):
	def __init__(self, parent=None):
		super(Data_Sampling_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Data Sampling")

		# self.frame = QGroupBox("Channel")
		# self.chBtn1 = QRadioButton("CH 0", self.frame)
		# self.chBtn1.setChecked(True)  # select by default
		# self.chBtn2 = QRadioButton("CH 1", self.frame)

		self.frame2 = QGroupBox("Polarity")
		self.poBtn1 = QRadioButton("Positive", self.frame2)
		self.poBtn1.setChecked(True)  # select by default
		self.poBtn2 = QRadioButton("Negative", self.frame2)

		self.MV_Number = spinBlock("ADC Average Points", MV_Numver_MIN, MV_Numver_MAX, "", "", False)
		self.AVG_time = spinBlock("Average Times", AVG_time_MIN, AVG_time_MAX, "", "", False)

		self.frame3 = QGroupBox("Scan Accumulate")
		self.acBtn1 = QRadioButton("Yes", self.frame3)
		self.acBtn2 = QRadioButton("No", self.frame3)
		self.acBtn2.setChecked(True)  # select by default

		self.Run_Loop = spinBlock("Accumulate Loops", Run_Loop_MIN, Run_Loop_MAX, "", "", False)

	def SubBlockWidget(self):
		# frameLayout1 = QHBoxLayout()
		# frameLayout1.addWidget(self.chBtn1)
		# frameLayout1.addWidget(self.chBtn2)
		# self.frame.setLayout(frameLayout1)

		frameLayout2 = QHBoxLayout()
		frameLayout2.addWidget(self.poBtn1)
		frameLayout2.addWidget(self.poBtn2)
		self.frame2.setLayout(frameLayout2)

		frameLayout3 = QHBoxLayout()
		frameLayout3.addWidget(self.acBtn1)
		frameLayout3.addWidget(self.acBtn2)
		self.frame3.setLayout(frameLayout3)

		layout = QGridLayout()
		#layout.addWidget(self.frame,0,0,1,1)
		#layout.addWidget(self.frame2,0,1,1,1)
		layout.addWidget(self.MV_Number.spinBlockWidget(),0,0,1,1)
		layout.addWidget(self.AVG_time.spinBlockWidget(),0,1,1,1)
		layout.addWidget(self.frame3,1,0,1,1)
		layout.addWidget(self.Run_Loop.spinBlockWidget(),1,1,1,1)
		layout.addWidget(self.frame2,2,0,1,1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Data_Analysis_Group(QWidget):
	def __init__(self, parent=None):
		super(Data_Analysis_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Data Analysis")
		self.Threshold = spinBlock("Threshold (mV)", Threshold_MIN, Threshold_MAX, "", "", False)
		self.Noise = spinBlock("Width (points)", Noise_MIN, Noise_MAX, "", "", False)

	def SubBlockWidget(self):
		layout = QHBoxLayout()
		layout.addWidget(self.Threshold.spinBlockWidget())
		layout.addWidget(self.Noise.spinBlockWidget())
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class DC_Voltage_Group(QWidget):
	def __init__(self, parent=None):
		super(DC_Voltage_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("DC Voltage Control")
		self.DC_Voltage1 = spinBlock("Fixed Voltage (V)", DC_Voltage1_MIN, DC_Voltage1_MAX, "Fixed Voltage =", "0", True)
		self.DC_Voltage2 = spinBlock("ESI (V)", DC_Voltage2_MIN, DC_Voltage2_MAX, "ESI =", "0", True)
		#self.SubBlockWidget()
		self.DC_Voltage1.SetBtn.setEnabled(False)
		self.DC_Voltage2.SetBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.DC_Voltage1.spinBlockWidget())
		layout.addWidget(self.DC_Voltage2.spinBlockWidget())
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Fan_Control_Group(QWidget):
	def __init__(self, parent=None):
		super(Fan_Control_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Fan Control")
		self.Fan_Speed = spinBlock("Fan Speed Setting (mV)", Fan_Speed_MIN, Fan_Speed_MAX, "Fan Speed = ", "0", True)
		self.Fan_Speed.SetBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.Fan_Speed.spinBlockWidget())
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class connectBlock():
	def __init__(self):
		self.connectGroupBox = QGroupBox("USB Connection")
		self.connectStatus = QLabel()
		self.connectBtn = QPushButton("Connect")
		self.connectStatus.setAlignment(Qt.AlignLeft)

	def connectBlockWidget(self):   
		connectLayout = QVBoxLayout()
		connectLayout.addWidget(self.connectStatus)
		connectLayout.addWidget(self.connectBtn)
		self.connectGroupBox.setLayout(connectLayout)
		self.connectGroupBox.show()
		return self.connectGroupBox

class picTabSetting(QTabWidget):
	def __init__(self, parent=None):
		super(picTabSetting, self).__init__(parent)
		self.picTab1 = QWidget()
		self.picTab2 = QWidget()
		self.addTab(self.picTab1,"Voltage Scan")
		self.addTab(self.picTab2,"Data Analysis")
		self.plot = outputPlot()
		self.plot2 = outputPlot()
		self.picTab1UI()
		self.picTab2UI()

	def picTab1UI(self):
		piclayout = QVBoxLayout()
		piclayout.addWidget(self.plot)
		self.picTab1.setLayout(piclayout)

	def picTab2UI(self):
		piclayout = QVBoxLayout()
		piclayout.addWidget(self.plot2)
		self.picTab2.setLayout(piclayout)

class msTabSetting(QTabWidget):
	def __init__(self, parent=None):
		super(msTabSetting, self).__init__(parent)
		self.msTab1 = QWidget()
		self.msTab2 = QWidget()
		self.addTab(self.msTab1,"Voltage Setting")
		self.addTab(self.msTab2,"Data Sampling and Analysis")

		#Tab1
		self.HVScan = HVScan_Group()
		self.DC_Voltage = DC_Voltage_Group()
		#Tab2
		self.Fan_Control = Fan_Control_Group()
		self.Data_Sampling = Data_Sampling_Group()
		self.Data_Analysis = Data_Analysis_Group()
		self.LoadBtn = QPushButton("Load")
		self.AnalyBtn = QPushButton("Analysis")
		self.SaveAnaBtn = QPushButton("Save Analysis")
		#self.Text = QLabel("")

		#self.LoadBtn.setEnabled(False)
		self.AnalyBtn.setEnabled(False)
		self.SaveAnaBtn.setEnabled(False)

		self.msTab1UI()
		self.msTab2UI()

	def msTab1UI(self):
		tablayout = QVBoxLayout()
		tablayout.addWidget(self.HVScan.SubBlockWidget())
		tablayout.addWidget(self.DC_Voltage.SubBlockWidget())
		self.msTab1.setLayout(tablayout)

	def msTab2UI(self):
		tablayout = QGridLayout()
		tablayout.addWidget(self.Fan_Control.SubBlockWidget(),0,0,1,3)
		tablayout.addWidget(self.Data_Sampling.SubBlockWidget(),1,0,1,3)
		tablayout.addWidget(self.Data_Analysis.SubBlockWidget(),2,0,1,3)
		tablayout.addWidget(self.LoadBtn,3,0,1,1)
		tablayout.addWidget(self.AnalyBtn,3,1,1,1)
		tablayout.addWidget(self.SaveAnaBtn,3,2,1,1)
		#tablayout.addWidget(self.Text,4,0,1,1)
		self.msTab2.setLayout(tablayout)


class mainWindow(QMainWindow):
	def __init__(self, parent=None):
		super (mainWindow, self).__init__(parent)
		self.setWindowTitle(TITLE_TEXT)
		self.resize(1280,840)
		self.move(50,50)
		self.com = connectBlock()
		self.pic = picTabSetting()
		self.ms = msTabSetting()
		self.Signal_Read = Signal_Read_Group()
		self.DCmode = QPushButton("DC mode")	# 2019.5.7
		self.StartBtn = QPushButton("Start Scan")
		self.StopBtn = QPushButton("Stop")
		w = QWidget()
		self.picout = QLabel(w)
		lg = QPixmap(LOGO_FILENAME)
		logo = lg.scaled(500, 90, Qt.KeepAspectRatio)
		self.picout.setPixmap(logo)

		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(False)

		self.usb = COMPort.FT232(Baudrate, Timeout)
		self.setButtonStatus()
		self.SettingData = [0 for i in range(0, 13)]
		self.LoadPreset()
		#self.VoltageChange()
		menu_about = QAction("&Version", self)
		menu_about.triggered.connect(self.aboutBox)
		mainMenu = self.menuBar()
		aboutMenu = mainMenu.addMenu("&About")
		aboutMenu.addAction(menu_about)
		self.main_UI()

		#connect
		self.com.connectBtn.clicked.connect(lambda:self.buildConnect())

		#HVScan
		self.DCmode.clicked.connect(lambda:self.RunDCmode())
		self.StartBtn.clicked.connect(lambda:self.StartScan())
		self.StopBtn.clicked.connect(lambda:self.StopScan())
		#self.Vout1 = 0
		#self.Vout2 = 0.0
		self.DCmodeFlag = False
		self.HVScanFlag = False
		# self.ms.HVScan.StartVoltage.spin.valueChanged.connect(lambda:self.VoltageChange())
		# self.ms.HVScan.VoltageStep.spin.valueChanged.connect(lambda:self.VoltageChange())
		# self.ms.HVScan.Loop.spin.valueChanged.connect(lambda:self.VoltageChange())
		self.ms.HVScan.reset.clicked.connect(lambda:self.VoltageReset())

		#DC_Voltage
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.clicked.connect(lambda:self.SetDC1())
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.clicked.connect(lambda:self.SetDC2())

		#Fan_Control
		self.ms.Fan_Control.Fan_Speed.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
		self.FanSpeedFlag = False

		#Signal_Read
		self.Signal_Read.SaveDataBtn.clicked.connect(lambda:self.SaveData())
		#self.data = []
		self.data = np.empty(0)
		#self.dv = []
		self.dv = np.empty(0)
		self.alldata = np.empty(0)
		self.run_index = 0
		self.row_path = ROW_FILEPATH

		#Data_Analysis
		self.ms.LoadBtn.clicked.connect(lambda:self.LoadData())
		self.ms.AnalyBtn.clicked.connect(lambda:self.AnalysisData())
		self.ms.SaveAnaBtn.clicked.connect(lambda:self.SaveAnaData())
		self.ms.Data_Analysis.Threshold.spin.valueChanged.connect(lambda:self.ShowThreshold())
		self.ms.Data_Analysis.Noise.spin.valueChanged.connect(lambda:self.NoiseChange())
		#self.data2 = []
		self.data2 = np.empty(0)
		#self.dv2 = []
		self.dv2 = np.empty(0)
		#self.analist = []
		self.analist = np.empty(0)


	def main_UI(self):
		mainLayout = QGridLayout()
		mainLayout.addWidget(self.pic,0,0,10,1)
		mainLayout.addWidget(self.com.connectBlockWidget(),0,1,1,3)
		mainLayout.addWidget(self.ms,1,1,5,3)
		mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),6,1,2,3)
		mainLayout.addWidget(self.DCmode,8,1,1,1)
		mainLayout.addWidget(self.StartBtn,8,2,1,1)
		mainLayout.addWidget(self.StopBtn,8,3,1,1)
		mainLayout.addWidget(self.picout,9,1,1,3)
		mainLayout.setRowStretch(0, 1)
		mainLayout.setRowStretch(1, 1)
		mainLayout.setRowStretch(2, 1)
		mainLayout.setRowStretch(3, 1)
		mainLayout.setRowStretch(4, 1)
		mainLayout.setRowStretch(5, 1)
		mainLayout.setRowStretch(6, 1)
		mainLayout.setRowStretch(7, 1)
		mainLayout.setRowStretch(8, 1)
		mainLayout.setRowStretch(9, 1)
		mainLayout.setColumnStretch(0, 8)
		mainLayout.setColumnStretch(1, 1)
		mainLayout.setColumnStretch(2, 1)
		mainLayout.setColumnStretch(3, 1)
		self.setCentralWidget(QWidget(self))
		self.centralWidget().setLayout(mainLayout)

	def aboutBox(self):
		versionBox = QMessageBox()
		versionBox.about(self, "Version", VERSION_TEXT)

	def LoadPreset(self):
		if os.path.exists(SETTING_FILENAME):
			self.SettingData = [line.rstrip('\n') for line in open(SETTING_FILENAME)]
		#self.ip.connectIP.setText(str(self.SettingData[0]))
		self.ms.HVScan.StartVoltage.spin.setValue(int(self.SettingData[1]))
		self.ms.HVScan.VoltageStep.spin.setValue(int(self.SettingData[2]))
		self.ms.HVScan.Loop.spin.setValue(int(self.SettingData[3]))
		self.ms.HVScan.TimeDelay.spin.setValue(int(self.SettingData[4]))
		self.ms.DC_Voltage.DC_Voltage1.spin.setValue(int(self.SettingData[5]))
		self.ms.DC_Voltage.DC_Voltage2.spin.setValue(int(self.SettingData[6]))
		self.ms.Fan_Control.Fan_Speed.spin.setValue(int(self.SettingData[7]))
		self.ms.Data_Sampling.MV_Number.spin.setValue(int(self.SettingData[8]))
		self.ms.Data_Sampling.AVG_time.spin.setValue(int(self.SettingData[9]))

#connect
	def setButtonStatus(self):
		#print( "setButtonStatus = " + str(self.usb.find_com) )
		pe = QPalette()
		if (self.usb.find_com):
			pe.setColor(QPalette.WindowText,Qt.black)
			self.com.connectStatus.setPalette(pe)
			self.com.connectStatus.setText("Device connected")
			self.com.connectBtn.setEnabled(False)
			self.DCmode.setEnabled(True)
			self.StartBtn.setEnabled(True)
			#self.StopBtn.setEnabled(True)
			self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(True)
			self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(True)
			self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(True)
		else:
			pe.setColor(QPalette.WindowText,Qt.red)
			self.com.connectStatus.setPalette(pe)
			self.com.connectStatus.setText("Can't find correct COM port")
			self.com.connectBtn.setEnabled(True)
			self.DCmode.setEnabled(False)
			self.StartBtn.setEnabled(False)
			#self.StopBtn.setEnabled(False)
			self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(False)
			self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(False)
			self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(False)

	def checkConnectStatus(self):
		if (self.usb.find_com == False):
			#print "com not find"
			self.setButtonStatus()

	def buildConnect(self):
		self.usb = COMPort.FT232(Baudrate, Timeout)
		self.setButtonStatus()


#DCmode
	def RunDCmode(self):	# 2019.5.7
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		self.SettingData[1] = startValue
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		Vout1 = startValue
		Vout2 = float(startValue) * DAC_Constant_S5 * DAC_ratio
		cmd = DAC_SCAN + str(Vout2)
		print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(cmd)
		#line = self.usb.readBinary()
		#print line
		self.ms.HVScan.text2.setText(str(Vout1)+" (V)")
		self.ms.HVScan.text2.show()

		#self.SetCycle()

		self.DCmodeFlag = True
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		#self.data = []
		self.data = np.empty(0)
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(True)
		self.ms.HVScan.reset.setEnabled(False)
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(False)
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(False)
		self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(False)


#HVScan
	def VoltageReset(self):
		#cmd = DAC_SCAN + "0"
		#print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(DAC_SCAN_STOP)
		print DAC_SCAN_STOP
		self.ms.HVScan.text2.setText("0 (V)")
		self.ms.HVScan.text2.show()

	def VoltageOut(self):
		TD_value_float = float(self.ms.HVScan.TimeDelay.spin.value()/1000.0)
		# if self.ms.Data_Sampling.chBtn2.isChecked():
		# 	Channel_str = '1 '
		# else:
		# 	Channel_str = '0 '
		MV_Number_str = str(self.ms.Data_Sampling.MV_Number.spin.value())
		AVG_time_value = int(self.ms.Data_Sampling.AVG_time.spin.value())
		Fix_Vol_value = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		#i = 0	# 2019.5.7
		if (self.HVScanFlag == True):
			i = int(self.SettingData[12]) * (-1)
		else:
			i = 0
		loopValue = self.ms.HVScan.Loop.spin.value()
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		stepValue = float(self.ms.HVScan.VoltageStep.spin.value())/1000.0
		#self.data = []
		self.data = np.empty(0)
		#self.dv = []
		self.dv = np.empty(0)
		#start_time = time.time()*1000
		reg_EOI = 0
		whileHVScanFlag = False
		whileDCmodeFlag = False
		row_data = np.empty(0)
		while (i < loopValue) or (self.HVScanFlag == True) or (self.DCmodeFlag == True):
			#tmp_str = "run " + str(self.run_index)
			#print tmp_str

			if (self.HVScanFlag):
				whileHVScanFlag = True
			elif (self.DCmodeFlag):
				whileDCmodeFlag = True
			if ( (i < loopValue) & (self.HVScanFlag == True) ) or (self.DCmodeFlag == True):
				if (self.HVScanFlag == True):
					Vout1 = startValue + stepValue * i
					Vout2 = float(Vout1) * DAC_Constant_S5 * DAC_ratio
					cmd = DAC_SCAN + str(Vout2)
					print cmd
					#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
					self.usb.writeBinary(cmd)
					#line = self.usb.readBinary()
					#print line
					self.ms.HVScan.text2.setText(str(Vout1)+" (V)")
					self.ms.HVScan.text2.show()

				time.sleep(TD_value_float)
				#stdin, stdout, stderr = self.ip.ssh.exec_command(ADC_SCAN_READ)
				#cmd = ADC_SCAN_READ + Channel_str + MV_Number_str + ADC_SCAN_READ_gain
				cmd = ADC_SCAN_READ + MV_Number_str
				print cmd
				SR_read_Total = 0.0

				for j in range(0, AVG_time_value):
					SR_read = 0.0
					#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
					#for line in stdout:
						#SR_read = float(line)
						#print "for j " + str(j) + " : " + str(SR_read)
					#self.usb.writeBinary(ADC_SCAN_READ)
					self.usb.writeBinary(cmd)
					line = self.usb.readBinary()
					#print line
					while (line == ''):
						line = self.usb.readBinary()
						#print line
					SR_read = float(line)
					SR_read_Total = SR_read_Total + SR_read
				#print "while i " + str(i) + " : " + str(SR_read_Total)
				#SR_read = SR_read_Total / AVG_time_value / DAC_ratio * 2
				SR_read = SR_read_Total / AVG_time_value / DAC_ratio * 2 * float(self.SettingData[10])

				#for testing
				#SR_read = (1000 + self.run_index + i) * float(self.SettingData[10])
				#print SR_read
				#print i

				if (i >= 0):	# 2019.5.7
					#self.data.append(SR_read)
					if ( (whileHVScanFlag) and self.Signal_Read.checkbox.isChecked() ):
						row_data = np.append(row_data, SR_read)

					if ( (whileDCmodeFlag) or (self.run_index == 1)):
						self.data = np.append(self.data, SR_read)
					else:
						self.data[i] = SR_read
					#print(self.data[i])

					if (whileHVScanFlag):
						newVaule = i*stepValue + startValue - Fix_Vol_value
						#print(newVaule)
						#self.dv.append(newVaule)
						if (self.run_index == 1):
							self.dv = np.append(self.dv, newVaule)
					elif (whileDCmodeFlag):
						#self.dv.append(i)
						self.dv = np.append(self.dv, i)
					#print(str(i)+","+str(self.HVScanFlag)+","+str(self.DCmodeFlag)+","+str(self.dv[i]))

					#add avg data , 2019.8.19
					if (whileHVScanFlag):
						if ( (i >= (loopValue-1)) and self.Signal_Read.checkbox.isChecked() ):
							if not os.path.isdir(self.row_path):
								os.mkdir(self.row_path)
							row_file = str(self.row_path) + "\\" + str(self.run_index) + ".txt"
							SaveData = [str(line) + '\n' for line in row_data] 
							fo = open(row_file, "w+")
							fo.writelines(SaveData)
							fo.close()

						if self.ms.Data_Sampling.acBtn1.isChecked():
							if (self.run_index == 1):
								self.alldata = np.append(self.alldata, self.data[i])
							else:
								self.alldata[i] = self.alldata[i] + self.data[i]
								self.data[i] = self.alldata[i] / self.run_index
							#print self.alldata[i]
							#print self.data[i]
							#print "----------"

				self.pic.plot.ax.clear()
				if (whileHVScanFlag):
					self.pic.plot.ax.set_xlabel("dV (V)")
				elif (whileDCmodeFlag):
					self.pic.plot.ax.set_xlabel("index")
				self.pic.plot.ax.set_ylabel("Voltage Output (mV)")
				self.pic.plot.ax.plot(self.dv,self.data, '-')
				self.pic.plot.canvas.draw()
				self.Signal_Read.text.setText(str("%2.4f"%SR_read))
				self.Signal_Read.text.show()
				i = i + 1
				#add loop always , 2019.8.19
				if ( whileHVScanFlag and (i >= loopValue) ):
					row_data = np.empty(0)
					self.run_index = self.run_index + 1
					#i = 0
					i = int(self.SettingData[12]) * (-1)
					#add Run_Loop , 2019.8.21
					if ( self.run_index > self.SettingData[11] ):
						self.StopScan()
			# elif (self.HVScanFlag == True):
			# 	#end_time = time.time()*1000
			# 	#diff_time = end_time - start_time
			# 	#print diff_time
			# 	time.sleep(TD_value_float)
			# 	#stdin, stdout, stderr = self.ip.ssh.exec_command(ADC_SCAN_READ)
			# 	cmd = ADC_SCAN_READ + MV_Number_str + ADC_SCAN_READ_gain
			# 	#print cmd
			# 	stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
			# 	for line in stdout:
			# 		SR_read = float(line)
			# 		#print SR_read
			# 	self.Signal_Read.text.setText(str("%2.4f"%SR_read))
			# 	self.Signal_Read.text.show()
			elif (self.HVScanFlag == True):
				self.StopScan()
			else:
				i = loopValue
 

	def StartScan(self):
		#self.SettingData[0] = self.ip.connectIP.text()
		self.SettingData[1] = self.ms.HVScan.StartVoltage.spin.value()
		self.SettingData[2] = self.ms.HVScan.VoltageStep.spin.value()
		self.SettingData[3] = self.ms.HVScan.Loop.spin.value()
		self.SettingData[4] = self.ms.HVScan.TimeDelay.spin.value()
		# if self.ms.Data_Sampling.chBtn2.isChecked():
		# 	self.SettingData[4] = 1
		# else:
		# 	self.SettingData[4] = 0
		self.SettingData[5] = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		self.SettingData[6] = self.ms.DC_Voltage.DC_Voltage2.spin.value()
		self.SettingData[7] = self.ms.Fan_Control.Fan_Speed.spin.value()
		self.SettingData[8] = self.ms.Data_Sampling.MV_Number.spin.value()
		self.SettingData[9] = self.ms.Data_Sampling.AVG_time.spin.value()
		if self.ms.Data_Sampling.poBtn2.isChecked():
			self.SettingData[10] = -1
		else:
			self.SettingData[10] = 1
		self.SettingData[11] = self.ms.Data_Sampling.Run_Loop.spin.value()
		self.SettingData[12] = self.ms.HVScan.Back.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		self.HVScanFlag = True
		#self.data = []
		self.data = np.empty(0)
		self.alldata = np.empty(0)
		self.run_index = 1
		if (self.Signal_Read.checkbox.isChecked()):
			row_path = QFileDialog.getExistingDirectory(self,"Save Row Data","./")
			if (row_path != ''):
				self.row_path = row_path
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(True)
		self.ms.HVScan.reset.setEnabled(False)
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(False)
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(False)
		self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(False)


	def StopScan(self):
		self.DCmodeFlag = False
		self.HVScanFlag = False
		val = self.ms.HVScan.StartVoltage.spin.value()
		self.ms.HVScan.text2.setText(str(val)+" (V)")
		#stdin, stdout, stderr = self.ip.ssh.exec_command(DAC_SCAN_STOP)
		#startValue = self.ms.HVScan.StartVoltage.spin.value()
		#Vout1 = startValue
		#Vout2 = float(startValue) * DAC_Constant_S5
		#cmd = DAC_SCAN + str(Vout2)
		#print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(DAC_SCAN_STOP)
		print DAC_SCAN_STOP
		#line = self.usb.readBinary()
		#print line
		#self.FanSpeedFlag = False
		self.DCmode.setEnabled(True)
		self.StartBtn.setEnabled(True)
		self.StopBtn.setEnabled(False)
		self.Signal_Read.SaveDataBtn.setEnabled(True)
		self.ms.AnalyBtn.setEnabled(True)
		self.ms.HVScan.reset.setEnabled(True)
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(True)
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(True)
		self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(True)


#DC_Voltage
	def SetDC1(self):## Fixed Voltage
		value1 = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		DC1_value_out = value1 * DAC_Constant_S5 * DAC_ratio
		cmd = DAC_DC + str(DC1_value_out)
		print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(cmd)
		#line = self.usb.readBinary()
		#print line
		self.ms.DC_Voltage.DC_Voltage1.value.setText(str(value1))

	def SetDC2(self): ##ESI
		value2 = self.ms.DC_Voltage.DC_Voltage2.spin.value()
		DC2_value_out = value2 * DAC_Constant_S5_ESI * DAC_ratio
		cmd = DAC_ESI + str(DC2_value_out)
		print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(cmd)
		#line = self.usb.readBinary()
		#print line
		self.ms.DC_Voltage.DC_Voltage2.value.setText(str(value2))


#Fan_Control
	def FanSpeedOut(self):
		while (self.FanSpeedFlag == True):
			self.usb.writeBinary(READ_FAN_SPEED)
			line = self.usb.readBinary()
			#print line
			while (line == ''):
				line = self.usb.readBinary()
				#print line
			Fan_Speed = int(line)
			self.ms.Fan_Control.Fan_Speed.value.setText(str(Fan_Speed))
			self.ms.Fan_Control.Fan_Speed.value.show()
			time.sleep(1)

	def SetFanSpeed(self):
		value3 = self.ms.Fan_Control.Fan_Speed.spin.value()
		FS_value = float(value3)/1000.0 * DAC_ratio
		cmd = DAC_FAN + str(FS_value)
		print cmd
		#stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.usb.writeBinary(cmd)
		#line = self.usb.readBinary()
		#print line
		if (value3 == 0):
			self.FanSpeedFlag = False
			#print "False 1"
		else:
			if (self.FanSpeedFlag == False):
				#print "False 2"
				gt2 = threading.Thread(target = self.FanSpeedOut)
				gt2.start()
			self.FanSpeedFlag = True
			#print "True"

#Signal_Read
	def SaveData(self):
		#SaveData = [str(line) + '\n' for line in self.data] 
		SaveFileName = QFileDialog.getSaveFileName(self,"Save Signal Data",READOUT_FILENAME,"Text Files (*.txt)")
		if (SaveFileName != ''):
			fo = open(SaveFileName, "w+")
			number = len(self.data)
			for i in range (0, number):
				fo.write(str("%2.4f" %self.dv[i])+","+str("%2.4f" %self.data[i])+"\n")
			fo.close()

#Data_Analysis
	def LoadData(self):
		#self.data2 = []
		self.data2 = np.empty(0)
		#self.dv2 = []
		self.dv2 = np.empty(0)
		data2max = 0
		data2min = 0
		OpenFileName = QFileDialog.getOpenFileName(self,"Load Signal Data","","Text Files (*.txt)")
		if os.path.exists(OpenFileName):
			temp = [line.rstrip('\n') for line in open(OpenFileName)]
			for a in temp:
				b = a.split(',')
				#self.dv2.append(float(b[0]))
				self.dv2 = np.append(self.dv2, float(b[0]))
				#self.data2.append(float(b[1]))
				self.data2 = np.append(self.data2, float(b[1]))
			data2max = max(self.data2)
			data2min = min(self.data2)
			self.ms.Data_Analysis.Threshold.spin.setRange(data2min, data2max)
			self.pic.plot2.ax.clear()
			self.pic.plot2.ax.set_xlabel("dV (V)")
			self.pic.plot2.ax.set_ylabel("Voltage Output (mV)")
			self.pic.plot2.ax.plot(self.dv2,self.data2, '-')
			self.pic.plot2.canvas.draw()
			self.ms.AnalyBtn.setEnabled(True)

	def AnalysisData(self):
		value1 = float(self.ms.Data_Analysis.Threshold.spin.value())
		value2 = float(self.ms.Data_Analysis.Noise.spin.value())

		peaks, _= find_peaks(self.data2, height = value1, width = value2)
		#print peaks
		peak_num = len(peaks)
		results_half = peak_widths(self.data2, peaks, rel_height = 0.5)
		#print results_half

		self.pic.plot2.ax.clear()
		self.pic.plot2.ax.set_xlabel("dV (V)")
		self.pic.plot2.ax.set_ylabel("Voltage Output (mV)")
		self.pic.plot2.ax.plot(self.dv2,self.data2, '-')
		self.pic.plot2.canvas.draw()

		#self.analist = []
		self.analist = np.empty(0)
		for index in peaks:
			xvalue = self.dv2[index]
			#self.analist.append(xvalue)
			self.analist = np.append(self.analist, xvalue)
			yvalue = self.data2[index]
			#self.analist.append(yvalue)
			self.analist = np.append(self.analist, yvalue)
			#ratio = yvalue / xvalue
			#list.append(ratio)
			#self.analist.append(0.0)
			#self.analist.append(0.0)
			self.analist = np.append(self.analist, 0.0)
			self.analist = np.append(self.analist, 0.0)

		for i in xrange(0, peak_num):
			#print results_half[0][i]
			deltax = results_half[0][i]
			xvalue = self.analist[4*i+0]
			yvalue = self.analist[4*i+1]
			self.analist[4*i+2] = deltax
			#ratio = yvalue / deltax
			#ratio = xvalue / deltax
			ratio = xvalue
			self.analist[4*i+3] = ratio
			self.pic.plot2.ax.axvline(x=xvalue, color='k')
			self.pic.plot2.ax.text(xvalue, yvalue, str("%2.3f" %ratio), fontsize=12)
			self.pic.plot2.canvas.draw()

		#print self.analist
		self.ms.AnalyBtn.setEnabled(False)
		self.ms.SaveAnaBtn.setEnabled(True)

	def SaveAnaData(self):
		SaveFileName = QFileDialog.getSaveFileName(self,"Save Analysis Data",ANALYSIS_FILENAME,"Text Files (*.txt)")
		if (SaveFileName != ''):
			fo = open(SaveFileName, "w+")
			number = len(self.analist)
			fo.write("peak_X, peak_Y, width, ratio")
			for i in range (0, number):
				if (i % 4) == 0:
					fo.write("\n")
				else:
					fo.write(", ")
				fo.write(str("%2.4f" %self.analist[i]))
			fo.write("\n")
			fo.close()
			self.ms.SaveAnaBtn.setEnabled(False)

	def ShowThreshold(self):
		value = float(self.ms.Data_Analysis.Threshold.spin.value())
		self.pic.plot2.ax.clear()
		self.pic.plot2.ax.set_xlabel("dV (V)")
		self.pic.plot2.ax.set_ylabel("Voltage Output (mV)")
		self.pic.plot2.ax.plot(self.dv2, self.data2, '-')
		self.pic.plot2.ax.axhline(y=value, color='r')
		self.pic.plot2.canvas.draw()
		self.ms.AnalyBtn.setEnabled(True)

	def NoiseChange(self):
		self.ms.AnalyBtn.setEnabled(True)
		

if __name__ == '__main__':
	app = QApplication(sys.argv)
	main = mainWindow()
	main.show()
	os._exit(app.exec_())
