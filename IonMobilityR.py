import os
import sys
import time
import paramiko
import threading
import numpy as np 
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import scipy
from scipy.signal import find_peaks, peak_widths


StartVoltage_MIN = 1000
StartVoltage_MAX = 1900

VoltageStep_MIN = 200
VoltageStep_MAX = 2000

Loop_MIN = 1
Loop_MAX = 2000

#TimeDelay_MIN = 0
#TimeDelay_MAX = 10000

MV_Numver_MIN = 50
MV_Numver_MAX = 30000

AVG_time_MIN = 1
AVG_time_MAX = 100

DAC_Constant_S5 = 6.0/5000.0
#DAC_Average_Number = 10

DC_Voltage1_MIN = 0
DC_Voltage1_MAX = 2000

DC_Voltage2_MIN = 0
DC_Voltage2_MAX = 5000

Fan_Speed_MIN = 0
Fan_Speed_MAX = 5000

#CYCLE_MIN = 125000
#CYCLE_MAX = 1250000

#INT_CYCLE_MIN = 125000
#INT_CYCLE_MAX = 125000000
INT_CYCLE_MIN = 1
INT_CYCLE_MAX = 10000

Threshold_MIN = -10*1000
Threshold_MAX = 10*1000

Noise_MIN = 1
Noise_MAX = 100

SETTING_FILEPATH = "set"
SETTING_FILENAME = "set/setting.txt"
READOUT_FILENAME = "Signal_Read_Out.txt"
ANALYSIS_FILENAME = "Data_Analysis.txt"
LOGO_FILENAME = "set/logo.png"

I2CDAC_CONV_CONST = 4095.0/5.0
#CYCLE_CONST = 8.0/1000000.0
CYCLE_CONST = 125000	#1000000/8

DAC_SCAN = 		'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 1 '
#ADC_SCAN_READ = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./ADC_MV 0 10 1'
ADC_SCAN_READ = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./ADC_MV '
ADC_SCAN_READ_gain = ' 1'
#DAC_SCAN_STOP = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 1 0'
DAC_DC = 		'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 2 '
DAC_ESI = 		'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 3 '
DAC_FAN = 		'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 4 '

SCAN_REG_CMD = 		'/opt/redpitaya/bin/monitor 0x40200044 '
RESET_CYCLE_CMD = 	'/opt/redpitaya/bin/monitor 0x40200048 '
HOLD_CYCLE_CMD = 	'/opt/redpitaya/bin/monitor 0x4020004C '
INT_CYCLE_CMD = 	'/opt/redpitaya/bin/monitor 0x40200050 '
REG_EOI_CMD = 		'/opt/redpitaya/bin/monitor 0x40200054'

HOST_NAME = "root"
HOST_PWD = "root"
HOST_PORT = 22

TITLE_TEXT = " GRC Ion Mobility Spectrometer "
VERSION_TEXT = TITLE_TEXT + "\n" + \
" IonMobilityR V1.07 \n\n" + \
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
		self.SaveDataBtn = QPushButton("Save Signal Data")
		#self.SubBlockWidget()
		self.SaveDataBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.text,0,0,3,2)
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
		self.Loop = spinBlock("Loop", Loop_MIN, Loop_MAX, "", "", False)
		#self.TimeDelay = spinBlock("Time Delay (ms)", TimeDelay_MIN, TimeDelay_MAX, "", "", False)
		self.text1 = QLabel("Voltage Out = ")
		self.text2 = QLabel("0 V")

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.StartVoltage.spinBlockWidget(),0,0,1,2)
		layout.addWidget(self.VoltageStep.spinBlockWidget(),0,2,1,2)
		layout.addWidget(self.Loop.spinBlockWidget(),1,0,1,2)
		#layout.addWidget(self.TimeDelay.spinBlockWidget())
		layout.addWidget(self.text1,1,2,1,1)
		layout.addWidget(self.text2,1,3,1,1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Data_Sampling_Group(QWidget):
	def __init__(self, parent=None):
		super(Data_Sampling_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Data Sampling")
		self.frame = QGroupBox("Channel")
		self.radioBtn1 = QRadioButton("CH 0", self.frame)
		self.radioBtn1.setChecked(True)  # select by default
		self.radioBtn2 = QRadioButton("CH 1", self.frame)
		self.MV_Number = spinBlock("MV Average Number", MV_Numver_MIN, MV_Numver_MAX, "", "", False)
		self.AVG_time = spinBlock("Average Times", AVG_time_MIN, AVG_time_MAX, "", "", False)

	def SubBlockWidget(self):
		frameLayout = QHBoxLayout()
		frameLayout.addWidget(self.radioBtn1)
		frameLayout.addWidget(self.radioBtn2)
		self.frame.setLayout(frameLayout)

		layout = QHBoxLayout()
		layout.addWidget(self.frame)
		layout.addWidget(self.MV_Number.spinBlockWidget())
		layout.addWidget(self.AVG_time.spinBlockWidget())
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

class Integrator_Group(QWidget):
	def __init__(self, parent=None):
		super(Integrator_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Integrator Group")
		#self.ResetCycle = spinBlock("Reset Cycle", CYCLE_MIN, CYCLE_MAX, "Reset Time =", "0 (ms)", False)
		#self.HoldCycle = spinBlock("Hold Cycle", CYCLE_MIN, CYCLE_MAX, "Hold Time =", "0 (ms)", False)
		#self.IntCycle = spinBlock("Int Cycle (ms)", INT_CYCLE_MIN, INT_CYCLE_MAX, "", "", False)
		self.vText0 = QLabel("Voltage (V)")
		self.vText1 = QLabel("Start Voltage")
		self.vText2 = QSpinBox()
		self.vText3 = QSpinBox()
		self.vText4 = QSpinBox()
		self.vText5 = QLabel("Stop Voltage")
		self.gText0 = QLabel("Int Cycle (ms)")
		self.gValue1 = QSpinBox()
		self.gValue2 = QSpinBox()
		self.gValue3 = QSpinBox()
		self.gValue4 = QSpinBox()
		self.gValue1.setRange(INT_CYCLE_MIN, INT_CYCLE_MAX)
		self.gValue2.setRange(INT_CYCLE_MIN, INT_CYCLE_MAX)
		self.gValue3.setRange(INT_CYCLE_MIN, INT_CYCLE_MAX)
		self.gValue4.setRange(INT_CYCLE_MIN, INT_CYCLE_MAX)
		#self.SubBlockWidget()

	def SubBlockWidget(self):
		layout = QGridLayout()
		#layout.addWidget(self.ResetCycle.spinBlockWidget())
		#layout.addWidget(self.HoldCycle.spinBlockWidget())
		#layout.addWidget(self.IntCycle.spinBlockWidget())
		layout.addWidget(self.vText0,0,0,1,1)
		layout.addWidget(self.vText1,1,0,1,1)
		layout.addWidget(self.vText2,2,0,1,1)
		layout.addWidget(self.vText3,3,0,1,1)
		layout.addWidget(self.vText4,4,0,1,1)
		layout.addWidget(self.vText5,5,0,1,1)
		layout.addWidget(self.gText0,0,1,1,1)
		layout.addWidget(self.gValue1,1,1,1,1)
		layout.addWidget(self.gValue2,2,1,1,1)
		layout.addWidget(self.gValue3,3,1,1,1)
		layout.addWidget(self.gValue4,4,1,1,1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox


class connectBlock():
	def __init__(self):
		self.connectGroupBox = QGroupBox("Connection")
		self.connectIP = QLineEdit()
		self.connectStatus = QLabel()
		self.connectBtn = QPushButton("Connect")
		self.ssh = paramiko.SSHClient()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		pe = QPalette()
		pe.setColor(QPalette.WindowText,Qt.red)
		self.connectStatus.setPalette(pe)
		self.connectStatus.setText("Connect first !")

	def connectBlockWidget(self):   
		connectLayout = QGridLayout()
		connectLayout.addWidget(self.connectIP,0,0,1,2)
		connectLayout.addWidget(self.connectBtn,0,2,1,1)
		connectLayout.addWidget(self.connectStatus,1,0,1,3)
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
		self.Fan_Control = Fan_Control_Group()
		#Tab2
		self.Data_Sampling = Data_Sampling_Group()
		self.Integrator = Integrator_Group()
		self.Data_Analysis = Data_Analysis_Group()

		self.msTab1UI()
		self.msTab2UI()

	def msTab1UI(self):
		tablayout = QVBoxLayout()
		tablayout.addWidget(self.HVScan.SubBlockWidget())
		tablayout.addWidget(self.DC_Voltage.SubBlockWidget())
		tablayout.addWidget(self.Fan_Control.SubBlockWidget())
		self.msTab1.setLayout(tablayout)

	def msTab2UI(self):
		tablayout = QVBoxLayout()
		tablayout.addWidget(self.Data_Sampling.SubBlockWidget())
		tablayout.addWidget(self.Integrator.SubBlockWidget())
		tablayout.addWidget(self.Data_Analysis.SubBlockWidget())
		self.msTab2.setLayout(tablayout)


class mainWindow(QMainWindow):
	def __init__(self, parent=None):
		super (mainWindow, self).__init__(parent)
		self.setWindowTitle(TITLE_TEXT)
		self.resize(1280,840)
		self.move(50,50)
		self.pic = picTabSetting()
		self.ms = msTabSetting()
		self.ip = connectBlock()
		self.Signal_Read = Signal_Read_Group()
		self.DCmode = QPushButton("DC mode")	# 2019.5.7
		self.StartBtn = QPushButton("Start Scan")
		self.StopBtn = QPushButton("Stop")
		self.LoadBtn = QPushButton("Load")
		self.AnalyBtn = QPushButton("Analysis")
		self.SaveAnaBtn = QPushButton("Save Analysis")
		w = QWidget()
		self.picout = QLabel(w)
		lg = QPixmap(LOGO_FILENAME)
		logo = lg.scaled(500, 90, Qt.KeepAspectRatio)
		self.picout.setPixmap(logo)

		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(False)
		#self.LoadBtn.setEnabled(False)
		self.AnalyBtn.setEnabled(False)
		self.SaveAnaBtn.setEnabled(False)

		self.SettingData = [0 for i in range(0, 13)]
		self.LoadPreset()
		self.VoltageChange()
		menu_about = QAction("&Version", self)
		menu_about.triggered.connect(self.aboutBox)
		mainMenu = self.menuBar()
		aboutMenu = mainMenu.addMenu("&About")
		aboutMenu.addAction(menu_about)
		self.main_UI()

		#connect
		self.ip.connectBtn.clicked.connect(lambda:self.buildConnect())

		#HVScan
		self.DCmode.clicked.connect(lambda:self.RunDCmode())
		self.StartBtn.clicked.connect(lambda:self.StartScan())
		self.StopBtn.clicked.connect(lambda:self.StopScan())
		#self.Vout1 = 0
		#self.Vout2 = 0.0
		self.DCmodeFlag = False
		self.HVScanFlag = False
		self.ms.HVScan.StartVoltage.spin.valueChanged.connect(lambda:self.VoltageChange())
		self.ms.HVScan.VoltageStep.spin.valueChanged.connect(lambda:self.VoltageChange())
		self.ms.HVScan.Loop.spin.valueChanged.connect(lambda:self.VoltageChange())

		#DC_Voltage
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.clicked.connect(lambda:self.SetDC1())
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.clicked.connect(lambda:self.SetDC2())

		#Fan_Control
		self.ms.Fan_Control.Fan_Speed.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
		self.ms.FanSpeedFlag = False

		#Signal_Read
		self.Signal_Read.SaveDataBtn.clicked.connect(lambda:self.SaveData())
		#self.data = []
		self.data = np.empty(0)
		#self.dv = []
		self.dv = np.empty(0)
		self.alldata = np.empty(0)
		self.run_index = 0

		#Data_Analysis
		self.LoadBtn.clicked.connect(lambda:self.LoadData())
		self.AnalyBtn.clicked.connect(lambda:self.AnalysisData())
		self.SaveAnaBtn.clicked.connect(lambda:self.SaveAnaData())
		self.ms.Data_Analysis.Threshold.spin.valueChanged.connect(lambda:self.ShowThreshold())
		self.ms.Data_Analysis.Noise.spin.valueChanged.connect(lambda:self.NoiseChange())
		#self.data2 = []
		self.data2 = np.empty(0)
		#self.dv2 = []
		self.dv2 = np.empty(0)
		#self.analist = []
		self.analist = np.empty(0)

		#self.ms.Integrator.ResetCycle.spin.valueChanged.connect(lambda:self.ShowResetCycle())
		#self.ms.Integrator.HoldCycle.spin.valueChanged.connect(lambda:self.ShowHoldCycle())
		#self.ms.Integrator.IntCycle.spin.valueChanged.connect(lambda:self.ShowIntCycle())
		self.ms.Integrator.vText2.valueChanged.connect(lambda:self.IntVoltageChange2())
		self.ms.Integrator.vText3.valueChanged.connect(lambda:self.IntVoltageChange3())
		#self.ms.Integrator.vText4.valueChanged.connect(lambda:self.IntVoltageChange())


	def main_UI(self):
		mainLayout = QGridLayout()
		mainLayout.addWidget(self.pic,0,0,12,1)
		mainLayout.addWidget(self.ip.connectBlockWidget(),0,1,1,3)
		mainLayout.addWidget(self.ms,1,1,6,3)
		mainLayout.addWidget(self.DCmode,7,1,1,1)
		mainLayout.addWidget(self.StartBtn,7,2,1,1)
		mainLayout.addWidget(self.StopBtn,7,3,1,1)
		mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),8,1,2,3)
		mainLayout.addWidget(self.LoadBtn,10,1,1,1)
		mainLayout.addWidget(self.AnalyBtn,10,2,1,1)
		mainLayout.addWidget(self.SaveAnaBtn,10,3,1,1)
		mainLayout.addWidget(self.picout,11,1,1,3)
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
		mainLayout.setRowStretch(10, 1)
		mainLayout.setRowStretch(11, 1)
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
		self.ip.connectIP.setText(str(self.SettingData[0]))
		self.ms.HVScan.StartVoltage.spin.setValue(int(self.SettingData[1]))
		self.ms.HVScan.VoltageStep.spin.setValue(int(self.SettingData[2]))
		self.ms.HVScan.Loop.spin.setValue(int(self.SettingData[3]))
		#self.HVScan.TimeDelay.spin.setValue(int(self.SettingData[4]))
		self.ms.DC_Voltage.DC_Voltage1.spin.setValue(int(self.SettingData[5]))
		self.ms.DC_Voltage.DC_Voltage2.spin.setValue(int(self.SettingData[6]))
		self.ms.Fan_Control.Fan_Speed.spin.setValue(int(self.SettingData[7]))
		self.ms.Data_Sampling.MV_Number.spin.setValue(int(self.SettingData[8]))
		self.ms.Data_Sampling.AVG_time.spin.setValue(int(self.SettingData[9]))
		#self.ms.Integrator.ResetCycle.spin.setValue(int(self.SettingData[10]))
		#self.ms.Integrator.HoldCycle.spin.setValue(int(self.SettingData[11]))
		#self.ms.Integrator.IntCycle.spin.setValue(int(self.SettingData[12]))

#connect
	def buildConnect(self):
		self.ip.host = "rp-"+str(self.ip.connectIP.text())+".local"
		#print self.ip.host
		try:
			self.ip.ssh.connect(self.ip.host, HOST_PORT, HOST_NAME, HOST_PWD)
		except:
			self.ip.connectStatus.setText("SSH connection failed")
			self.ip.connectStatus.show()
		else:
			stdin, stdout, stderr = self.ip.ssh.exec_command('cat /root/int_GB.bit > /dev/xdevcfg')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 1 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 2 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 3 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 4 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 5 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 6 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 7 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 8 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 9 0')
			stdin, stdout, stderr = self.ip.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 10 0')

			self.SettingData[0] = self.ip.connectIP.text()
			#print(self.SettingData)
			SettingData = [str(line) + '\n' for line in self.SettingData] 
			if not os.path.isdir(SETTING_FILEPATH):
				os.mkdir(SETTING_FILEPATH)
			fo = open(SETTING_FILENAME, "w+")
			fo.writelines(SettingData)
			fo.close()

			pe = QPalette()
			pe.setColor(QPalette.WindowText,Qt.black)
			self.ip.connectStatus.setPalette(pe)
			self.ip.connectStatus.setText("Connection build")
			self.ip.connectStatus.show()
			self.ip.connectBtn.setEnabled(False)
			self.DCmode.setEnabled(True)
			self.StartBtn.setEnabled(True)
			self.StopBtn.setEnabled(True)
			self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(True)
			self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(True)
			self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(True)

	# def ShowResetCycle(self):
	# 	TempCycleValue = self.ms.Integrator.ResetCycle.spin.value()
	# 	CycleValue = float(TempCycleValue) * CYCLE_CONST
	# 	CycleText = str(CycleValue) + ' (ms)'
	# 	self.ms.Integrator.ResetCycle.value.setText(CycleText)

	# def ShowHoldCycle(self):
	# 	TempCycleValue = self.ms.Integrator.HoldCycle.spin.value()
	# 	CycleValue = float(TempCycleValue) * CYCLE_CONST
	# 	CycleText = str(CycleValue) + ' (ms)'
	# 	self.ms.Integrator.HoldCycle.value.setText(CycleText)

	# def ShowIntCycle(self):
	# 	TempCycleValue = self.ms.Integrator.IntCycle.spin.value()
	# 	CycleValue = float(TempCycleValue) * CYCLE_CONST
	# 	CycleText = str(CycleValue) + ' (ms)'
	# 	self.ms.Integrator.IntCycle.value.setText(CycleText)

	def SetCycle(self):
		#cmd = RESET_CYCLE_CMD + str(self.SettingData[10])
		cmd = RESET_CYCLE_CMD + "125000"
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		#self.ShowResetCycle()

		#cmd = HOLD_CYCLE_CMD + str(self.SettingData[11])
		cmd = HOLD_CYCLE_CMD + "125000"
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		#self.ShowHoldCycle()

		#cmd = INT_CYCLE_CMD + str(int(self.SettingData[12])*CYCLE_CONST)
		gValue1 = self.ms.Integrator.gValue1.value() * CYCLE_CONST
		cmd = INT_CYCLE_CMD + str(gValue1)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		#self.ShowIntCycle()


#DCmode
	def RunDCmode(self):	# 2019.5.7
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		self.SettingData[1] = startValue
		#self.SettingData[10] = self.ms.Integrator.ResetCycle.spin.value()
		#self.SettingData[11] = self.ms.Integrator.HoldCycle.spin.value()
		#self.SettingData[12] = self.ms.Integrator.IntCycle.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		Vout1 = startValue
		Vout2 = float(startValue) * DAC_Constant_S5
		cmd = DAC_SCAN + str(Vout2)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ms.HVScan.text2.setText(str(Vout1)+" (V)")
		self.ms.HVScan.text2.show()

		self.SetCycle()

		self.DCmodeFlag = True
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		#self.data = []
		self.data = np.empty(0)
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(True)

#Integrator
	def IntVoltageChange2(self):
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		stepValue = float(self.ms.HVScan.VoltageStep.spin.value())/1000.0
		loopValue = self.ms.HVScan.Loop.spin.value()
		stopValue = startValue + stepValue * loopValue

		voltage2 = self.ms.Integrator.vText2.value()

		if ((stopValue - voltage2) > 1):
			self.ms.Integrator.vText3.setRange(voltage2+1, stopValue-1)

	def IntVoltageChange3(self):
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		stepValue = float(self.ms.HVScan.VoltageStep.spin.value())/1000.0
		loopValue = self.ms.HVScan.Loop.spin.value()
		stopValue = startValue + stepValue * loopValue

		voltage3 = self.ms.Integrator.vText3.value()

		if ((stopValue - voltage3) > 1):
			self.ms.Integrator.vText4.setRange(voltage3+1, stopValue-1)

#HVScan
	def VoltageChange(self):
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		stepValue = float(self.ms.HVScan.VoltageStep.spin.value())/1000.0
		loopValue = self.ms.HVScan.Loop.spin.value()
		stopValue = startValue + stepValue * loopValue
		self.ms.Integrator.vText1.setText("Start Voltage = "+str(startValue))
		self.ms.Integrator.vText2.setRange(startValue, stopValue-1)
		self.ms.Integrator.vText3.setRange(startValue, stopValue-1)
		self.ms.Integrator.vText4.setRange(startValue, stopValue-1)
		self.ms.Integrator.vText5.setText("Stop Voltage = "+str(stopValue))

		if ((stopValue - startValue) >= 2):
			self.ms.Integrator.vText2.setEnabled(True)
			self.ms.Integrator.gValue2.setEnabled(True)
			self.ms.Integrator.vText2.setRange(startValue+1, stopValue-1)
		else:
			self.ms.Integrator.vText2.setEnabled(False)
			self.ms.Integrator.gValue2.setEnabled(False)

		if ((stopValue - startValue) >= 3):
			self.ms.Integrator.vText3.setEnabled(True)
			self.ms.Integrator.gValue3.setEnabled(True)
			self.ms.Integrator.vText3.setRange(startValue+2, stopValue-1)
		else:
			self.ms.Integrator.vText3.setEnabled(False)
			self.ms.Integrator.gValue3.setEnabled(False)

		if ((stopValue - startValue) >= 4):
			self.ms.Integrator.vText4.setEnabled(True)
			self.ms.Integrator.gValue4.setEnabled(True)
			self.ms.Integrator.vText4.setRange(startValue+3, stopValue-1)
		else:
			self.ms.Integrator.vText4.setEnabled(False)
			self.ms.Integrator.gValue4.setEnabled(False)

	def VoltageOut(self):
		#TD_value_float = float(self.HVScan.TimeDelay.spin.value()/1000.0)
		if self.ms.Data_Sampling.radioBtn2.isChecked():
			Channel_str = '1 '
		else:
			Channel_str = '0 '
		MV_Number_str = str(self.ms.Data_Sampling.MV_Number.spin.value())
		AVG_time_value = int(self.ms.Data_Sampling.AVG_time.spin.value())
		Fix_Vol_value = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		#i = 0	# 2019.5.7
		if (self.HVScanFlag == True):
			i = -3
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
		while (i < loopValue) or (self.HVScanFlag == True) or (self.DCmodeFlag == True):
			if (self.HVScanFlag):
				whileHVScanFlag = True
			elif (self.DCmodeFlag):
				whileDCmodeFlag = True
			if ( (i < loopValue) & (self.HVScanFlag == True) ) or (self.DCmodeFlag == True):
				if (self.HVScanFlag == True):
					Vout1 = startValue + stepValue * i
					Vout2 = float(Vout1) * DAC_Constant_S5
					cmd = DAC_SCAN + str(Vout2)
					#print cmd
					stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
					self.ms.HVScan.text2.setText(str(Vout1)+" (V)")
					self.ms.HVScan.text2.show()

					#2019.6.25
					voltage2 = self.ms.Integrator.vText2.value()
					voltage3 = self.ms.Integrator.vText3.value()
					voltage4 = self.ms.Integrator.vText4.value()

					if (Vout1 == voltage2) and (self.ms.Integrator.vText2.isEnabled):
						gValue2 = self.ms.Integrator.gValue2.value() * CYCLE_CONST
						cmd = INT_CYCLE_CMD + str(gValue2)
						#print cmd
						stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)

					if (Vout1 == voltage3) and (self.ms.Integrator.vText3.isEnabled):
						gValue3 = self.ms.Integrator.gValue3.value() * CYCLE_CONST
						cmd = INT_CYCLE_CMD + str(gValue3)
						#print cmd
						stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)

					if (Vout1 == voltage4) and (self.ms.Integrator.vText4.isEnabled):
						gValue4 = self.ms.Integrator.gValue4.value() * CYCLE_CONST
						cmd = INT_CYCLE_CMD + str(gValue4)
						#print cmd
						stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)

				cmd = SCAN_REG_CMD + '1'
				#print cmd
				stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
				# time.sleep(0.001)
				# cmd = SCAN_REG_CMD + '0'
				# #print cmd
				# stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)

				while (reg_EOI == 0):
					stdin, stdout, stderr = self.ip.ssh.exec_command(REG_EOI_CMD)
					for line in stdout:
						#print line
						reg_EOI = int(line[9])
						#print 'reg_EOI = ' + str(reg_EOI)

				#time.sleep(TD_value_float)
				#stdin, stdout, stderr = self.ip.ssh.exec_command(ADC_SCAN_READ)
				cmd = ADC_SCAN_READ + Channel_str + MV_Number_str + ADC_SCAN_READ_gain
				#print cmd
				SR_read_Total = 0.0
				for j in range(0, AVG_time_value):
					SR_read = 0.0
					stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
					for line in stdout:
						SR_read = float(line)
						#print "for j " + str(j) + " : " + str(SR_read)
					SR_read_Total = SR_read_Total + SR_read
				#print "while i " + str(i) + " : " + str(SR_read_Total)
				SR_read = SR_read_Total / AVG_time_value * (-1000)

				if (i >= 0):	# 2019.5.7
					#self.data.append(SR_read)
					self.data = np.append(self.data, SR_read)
					#print(self.data[i])

					if (whileHVScanFlag):
						newVaule = i*stepValue + startValue - Fix_Vol_value
						#print(newVaule)
						#self.dv.append(newVaule)
						self.dv = np.append(self.dv, newVaule)
					elif (whileDCmodeFlag):
						#self.dv.append(i)
						self.dv = np.append(self.dv, i)
					#print(str(i)+","+str(self.HVScanFlag)+","+str(self.DCmodeFlag)+","+str(self.dv[i]))

				if (0):	#(whileHVScanFlag):
					data_len = len(self.data)
					print "=========="
					print data_len
					print "get data"
					print self.data

					draw_len = data_len
					self.run_index = self.run_index + 1
					print self.run_index

					alldata_len = len(self.alldata)
					print alldata_len

					if (alldata_len == 0):
						for i in range(0, data_len):
							#self.alldata.append(self.data[i])
							self.alldata = np.append(self.alldata, self.data[i])
					else:
						if (data_len > alldata_len):
							draw_len = alldata_len
						elif (alldata_len > data_len):
							draw_len = data_len
						for i in range(0, draw_len):
							self.alldata[i] = self.alldata[i] + self.data[i]

					print "all data"
					print self.alldata

					#for i in range(0, draw_len):
					#    self.data[i] = self.alldata[i] / self.run_index
					self.data = self.alldata / self.run_index
					data_len = len(self.data)
					while (data_len > draw_len):
						self.data = np.delete(self.data, -1)
						self.dv = np.delete(self.dv, -1)
						data_len = len(self.data)

					print "avg data"
					print self.data

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
		#self.SettingData[4] = self.HVScan.TimeDelay.spin.value()
		if self.ms.Data_Sampling.radioBtn2.isChecked():
			self.SettingData[4] = 1
		else:
			self.SettingData[4] = 0
		self.SettingData[5] = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		self.SettingData[6] = self.ms.DC_Voltage.DC_Voltage2.spin.value()
		self.SettingData[7] = self.ms.Fan_Control.Fan_Speed.spin.value()
		self.SettingData[8] = self.ms.Data_Sampling.MV_Number.spin.value()
		self.SettingData[9] = self.ms.Data_Sampling.AVG_time.spin.value()
		#self.SettingData[10] = self.ms.Integrator.ResetCycle.spin.value()
		#self.SettingData[11] = self.ms.Integrator.HoldCycle.spin.value()
		#self.SettingData[12] = self.ms.Integrator.IntCycle.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		self.SetCycle()

		self.HVScanFlag = True
		#self.data = []
		self.data = np.empty(0)
		self.alldata = np.empty(0)
		self.run_index = 0
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(True)


	def StopScan(self):
		self.DCmodeFlag = False
		self.HVScanFlag = False
		val = self.ms.HVScan.StartVoltage.spin.value()
		self.ms.HVScan.text2.setText(str(val)+" (V)")
		#stdin, stdout, stderr = self.ip.ssh.exec_command(DAC_SCAN_STOP)
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		Vout1 = startValue
		Vout2 = float(startValue) * DAC_Constant_S5
		cmd = DAC_SCAN + str(Vout2)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		#self.FanSpeedFlag = False
		self.DCmode.setEnabled(True)
		self.StartBtn.setEnabled(True)
		self.StopBtn.setEnabled(False)
		self.Signal_Read.SaveDataBtn.setEnabled(True)
		self.AnalyBtn.setEnabled(True)


#DC_Voltage
	def SetDC1(self):## Fixed Voltage
		value1 = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		DC1_value_out = value1 * DAC_Constant_S5
		cmd = DAC_DC + str(DC1_value_out)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ms.DC_Voltage.DC_Voltage1.value.setText(str(value1))

	def SetDC2(self): ##ESI
		value2 = self.ms.DC_Voltage.DC_Voltage2.spin.value()
		DC2_value_out = value2 * DAC_Constant_S5
		cmd = DAC_ESI + str(DC2_value_out)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ms.DC_Voltage.DC_Voltage2.value.setText(str(value2))


#Fan_Control
#	def FanSpeedOut(self):
#		while (self.FanSpeedFlag == True):
#			#print(FS_read)
#			self.Fan_Control.text2.setText(str(FS_read))
#			self.Fan_Control.text2.show()
#			time.sleep(1)

	def SetFanSpeed(self):
		value3 = self.ms.Fan_Control.Fan_Speed.spin.value()
		FS_value = float(value3)/1000.0
		cmd = DAC_FAN + str(FS_value)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ms.Fan_Control.Fan_Speed.value.setText(str(value3))
		#self.FanSpeedFlag = True
		#gt2 = threading.Thread(target = self.FanSpeedOut)
		#gt2.start()

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
			self.AnalyBtn.setEnabled(True)

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
		self.AnalyBtn.setEnabled(False)
		self.SaveAnaBtn.setEnabled(True)

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
			self.SaveAnaBtn.setEnabled(False)

	def ShowThreshold(self):
		value = float(self.ms.Data_Analysis.Threshold.spin.value())
		self.pic.plot2.ax.clear()
		self.pic.plot2.ax.set_xlabel("dV (V)")
		self.pic.plot2.ax.set_ylabel("Voltage Output (mV)")
		self.pic.plot2.ax.plot(self.dv2, self.data2, '-')
		self.pic.plot2.ax.axhline(y=value, color='r')
		self.pic.plot2.canvas.draw()
		self.AnalyBtn.setEnabled(True)

	def NoiseChange(self):
		self.AnalyBtn.setEnabled(True)
		

if __name__ == '__main__':
	app = QApplication(sys.argv)
	main = mainWindow()
	main.show()
	os._exit(app.exec_())
