import os
import sys
import time
import paramiko
import threading
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
DC_Voltage2_MAX = 4000

Fan_Speed_MIN = 0
Fan_Speed_MAX = 5000

CYCLE_MIN = 125000
CYCLE_MAX = 1250000

INT_CYCLE_MIN = 125000
INT_CYCLE_MAX = 125000000

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
CYCLE_CONST = 8.0/1000000.0

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
" IonMobilityR V1.04 \n\n" + \
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
		w=QWidget()
		picout = QLabel(w)
		lg = QPixmap(LOGO_FILENAME)
		logo = lg.scaled(500, 90, Qt.KeepAspectRatio)
		picout.setPixmap(logo)
		layout = QGridLayout()
		layout.addWidget(self.canvas,0,0,1,2)
		layout.addWidget(self.toolbar,1,0,1,1)
		layout.addWidget(picout,1,1,1,1)
		self.setLayout(layout)
		self.ax = self.figure.add_subplot(111)
		self.ax.set_xlabel("delta V")
		self.ax.set_ylabel("Voltage Output (V)")

class Signal_Read_Group(QWidget):
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
		self.text.setFont(QFont("",16,QFont.Bold))
		self.SaveBtn = QPushButton("Save Signal Data")
		#self.SubBlockWidget()
		self.SaveBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.text)
		layout.addWidget(self.SaveBtn)
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
		layout = QHBoxLayout()
		layout.addWidget(self.StartVoltage.spinBlockWidget())
		layout.addWidget(self.VoltageStep.spinBlockWidget())
		layout.addWidget(self.Loop.spinBlockWidget())
		#layout.addWidget(self.TimeDelay.spinBlockWidget())
		layout.addWidget(self.text1)
		layout.addWidget(self.text2)
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
		self.LoadBtn = QPushButton("Load")
		self.AnalyBtn = QPushButton("Analysis")
		self.SaveBtn = QPushButton("Save Analysis")
		#self.LoadBtn.setEnabled(False)
		self.AnalyBtn.setEnabled(False)
		self.SaveBtn.setEnabled(False)
		self.Noise.spin.valueChanged.connect(lambda:self.NoiseChange())

	def SubBlockWidget(self):
		layout = QHBoxLayout()
		layout.addWidget(self.Threshold.spinBlockWidget())
		layout.addWidget(self.Noise.spinBlockWidget())
		layout.addWidget(self.LoadBtn)
		layout.addWidget(self.AnalyBtn)
		layout.addWidget(self.SaveBtn)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

def NoiseChange(self):
		self.AnalyBtn.setEnabled(True)

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
		layout = QHBoxLayout()
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
		self.ResetCycle = spinBlock("Reset Cycle", CYCLE_MIN, CYCLE_MAX, "Reset Time =", "0 (ms)", False)
		self.HoldCycle = spinBlock("Hold Cycle", CYCLE_MIN, CYCLE_MAX, "Hold Time =", "0 (ms)", False)
		self.IntCycle = spinBlock("Int Cycle", INT_CYCLE_MIN, INT_CYCLE_MAX, "Int Time =", "0 (ms)", False)
		#self.SubBlockWidget()

	def SubBlockWidget(self):
		layout = QHBoxLayout()
		layout.addWidget(self.ResetCycle.spinBlockWidget())
		layout.addWidget(self.HoldCycle.spinBlockWidget())
		layout.addWidget(self.IntCycle.spinBlockWidget())
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
		connectLayout = QVBoxLayout()
		connectLayout.addWidget(self.connectIP)
		connectLayout.addWidget(self.connectStatus)
		connectLayout.addWidget(self.connectBtn)
		self.connectGroupBox.setLayout(connectLayout)
		self.connectGroupBox.show()
		return self.connectGroupBox

class msTabSetting(QTabWidget):
	def __init__(self, parent=None):
		super(msTabSetting, self).__init__(parent)
		self.tab1 = QWidget()
		self.tab2 = QWidget()
		self.tab3 = QWidget()
		self.tab4 = QWidget()
		self.tab5 = QWidget()
		self.addTab(self.tab1,"High Voltage Setting")
		self.addTab(self.tab2,"DC Voltage Setting")
		self.addTab(self.tab3,"Data Sampling and Fan")
		self.addTab(self.tab4,"Gain Setting")
		self.addTab(self.tab5,"Data Analysis")

		#Tab1
		self.HVScan = HVScan_Group()
		#Tab2
		self.DC_Voltage = DC_Voltage_Group()
		#Tab3
		self.Data_Sampling = Data_Sampling_Group()
		self.Fan_Control = Fan_Control_Group()
		#Tab4
		self.Integrator = Integrator_Group()
		#Tab5
		self.Data_Analysis = Data_Analysis_Group()

		self.Tab1UI()
		self.Tab2UI()
		self.Tab3UI()
		self.Tab4UI()
		self.Tab5UI()

	def Tab1UI(self):
		tablayout = QHBoxLayout()
		tablayout.addWidget(self.HVScan.SubBlockWidget())
		self.tab1.setLayout(tablayout)

	def Tab2UI(self):
		tablayout = QHBoxLayout()
		tablayout.addWidget(self.DC_Voltage.SubBlockWidget())
		self.tab2.setLayout(tablayout)

	def Tab3UI(self):
		tablayout = QHBoxLayout()
		tablayout.addWidget(self.Data_Sampling.SubBlockWidget())
		tablayout.addWidget(self.Fan_Control.SubBlockWidget())
		self.tab3.setLayout(tablayout)

	def Tab4UI(self):
		tablayout = QHBoxLayout()
		tablayout.addWidget(self.Integrator.SubBlockWidget())
		self.tab4.setLayout(tablayout)

	def Tab5UI(self):
		tablayout = QHBoxLayout()
		tablayout.addWidget(self.Data_Analysis.SubBlockWidget())
		self.tab5.setLayout(tablayout)


class mainWindow(QMainWindow):
	def __init__(self, parent=None):
		super (mainWindow, self).__init__(parent)
		self.setWindowTitle(TITLE_TEXT)
		self.resize(1280,840)
		self.move(50,50)
		self.ms = msTabSetting()
		self.ip = connectBlock()
		self.Signal_Read = Signal_Read_Group()
		self.plot = outputPlot()
		self.DCmode = QPushButton("DC mode")	# 2019.5.7
		self.StartBtn = QPushButton("Start Scan")
		#self.StopBtn = QPushButton("Stop")

		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		#self.StopBtn.setEnabled(False)

		self.SettingData = [0 for i in range(0, 13)]
		self.LoadPreset()
		menu_about = QAction("&Version", self)
		menu_about.triggered.connect(self.aboutBox)
		mainMenu = self.menuBar()
		aboutMenu = mainMenu.addMenu("&About")
		aboutMenu.addAction(menu_about)
		self.main_UI()

		#connect
		self.ip.connectBtn.clicked.connect(lambda:self.buildConnect())

		#HVScan
		self.DCmode.clicked.connect(lambda:self.DCmode())
		self.StartBtn.clicked.connect(lambda:self.StartScan())
		#self.StopBtn.clicked.connect(lambda:self.StopScan())
		#self.Vout1 = 0
		#self.Vout2 = 0.0
		self.DCmodeFlag = False
		self.HVScanFlag = False

		#DC_Voltage
		self.ms.DC_Voltage.DC_Voltage1.SetBtn.clicked.connect(lambda:self.SetDC1())
		self.ms.DC_Voltage.DC_Voltage2.SetBtn.clicked.connect(lambda:self.SetDC2())

		#Fan_Control
		self.ms.Fan_Control.Fan_Speed.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
		self.ms.FanSpeedFlag = False

		#Signal_Read
		self.Signal_Read.SaveBtn.clicked.connect(lambda:self.SaveData())
		self.data = []
		self.dv = []

		#Data_Analysis
		self.ms.Data_Analysis.LoadBtn.clicked.connect(lambda:self.LoadData())
		self.ms.Data_Analysis.AnalyBtn.clicked.connect(lambda:self.AnalysisData())
		self.ms.Data_Analysis.SaveBtn.clicked.connect(lambda:self.SaveAnaData())
		self.ms.Data_Analysis.Threshold.spin.valueChanged.connect(lambda:self.ShowThreshold())
		self.analist = []

		self.ms.Integrator.ResetCycle.spin.valueChanged.connect(lambda:self.ShowResetCycle())
		self.ms.Integrator.HoldCycle.spin.valueChanged.connect(lambda:self.ShowHoldCycle())
		self.ms.Integrator.IntCycle.spin.valueChanged.connect(lambda:self.ShowIntCycle())

		#ExitProg
		#self.Signal_Read.ExitBtn.clicked.connect(lambda:self.ExitProg())

	def main_UI(self):
		mainLayout = QGridLayout()
		mainLayout.addWidget(self.ms,0,0,2,4)
		mainLayout.addWidget(self.DCmode,0,4,1,1)
		mainLayout.addWidget(self.StartBtn,1,4,1,1)
		mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),0,5,2,1)
		mainLayout.addWidget(self.ip.connectBlockWidget(),0,6,2,1)
		mainLayout.addWidget(self.plot,2,0,1,7)
		mainLayout.setRowStretch(0, 1)
		mainLayout.setRowStretch(1, 1)
		mainLayout.setRowStretch(2, 8)
		mainLayout.setColumnStretch(0, 1)
		mainLayout.setColumnStretch(1, 1)
		mainLayout.setColumnStretch(2, 1)
		mainLayout.setColumnStretch(3, 1)
		mainLayout.setColumnStretch(4, 1)
		mainLayout.setColumnStretch(5, 1)
		mainLayout.setColumnStretch(6, 1)
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
		self.ms.Integrator.ResetCycle.spin.setValue(int(self.SettingData[10]))
		self.ms.Integrator.HoldCycle.spin.setValue(int(self.SettingData[11]))
		self.ms.Integrator.IntCycle.spin.setValue(int(self.SettingData[12]))

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
				#self.StopBtn.setEnabled(True)
				self.ms.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(True)
				self.ms.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(True)
				self.ms.Fan_Control.Fan_Speed.SetBtn.setEnabled(True)

#DCmode
	def ShowResetCycle(self):
		TempCycleValue = self.ms.Integrator.ResetCycle.spin.value()
		CycleValue = float(TempCycleValue) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.ms.Integrator.ResetCycle.value.setText(CycleText)

	def ShowHoldCycle(self):
		TempCycleValue = self.ms.Integrator.HoldCycle.spin.value()
		CycleValue = float(TempCycleValue) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.ms.Integrator.HoldCycle.value.setText(CycleText)

	def ShowIntCycle(self):
		TempCycleValue = self.ms.Integrator.IntCycle.spin.value()
		CycleValue = float(TempCycleValue) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.ms.Integrator.IntCycle.value.setText(CycleText)

	def SetCycle(self):
		cmd = RESET_CYCLE_CMD + str(self.SettingData[10])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ShowResetCycle()

		cmd = HOLD_CYCLE_CMD + str(self.SettingData[11])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ShowHoldCycle()

		cmd = INT_CYCLE_CMD + str(self.SettingData[12])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ShowIntCycle()


	def DCmode(self):	# 2019.5.7
		startValue = self.ms.HVScan.StartVoltage.spin.value()
		self.SettingData[1] = startValue
		self.SettingData[10] = self.ms.Integrator.ResetCycle.spin.value()
		self.SettingData[11] = self.ms.Integrator.HoldCycle.spin.value()
		self.SettingData[12] = self.ms.Integrator.IntCycle.spin.value()
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
		self.data = []
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		#self.StopBtn.setEnabled(True)

#HVScan
	def VoltageOut(self):
		#TD_value_float = float(self.HVScan.TimeDelay.spin.value()/1000.0)
		if self.Setting.radioBtn2.isChecked():
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
		self.data = []
		self.dv = []
		#start_time = time.time()*1000
		reg_EOI = 0
		while (i < loopValue) or (self.HVScanFlag == True) or (self.DCmodeFlag == True):
				if ( (i < loopValue) & (self.HVScanFlag == True) ) or (self.DCmodeFlag == True):
						if (self.HVScanFlag == True):
								Vout1 = startValue + stepValue * i
								Vout2 = float(Vout1) * DAC_Constant_S5
								#self.card.writeAoValue(1, Vout2)
								cmd = DAC_SCAN + str(Vout2)
								#print cmd
								stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
								self.ms.HVScan.text2.setText(str(Vout1)+" (V)")
								self.ms.HVScan.text2.show()

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
						#SR_read = self.card.readAiAve(0, DAC_Average_Number)
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
						SR_read = SR_read_Total / AVG_time_value

						if (i >= 0):	# 2019.5.7
								self.data.append(SR_read)
								if (self.HVScanFlag == True):
										self.dv.append(i*stepValue + startValue - Fix_Vol_value)
								else:
										self.dv.append(i)

						self.plot.ax.clear()
						self.plot.ax.plot(self.dv,self.data, '-')
						self.plot.canvas.draw()
						self.Signal_Read.text.setText(str("%2.4f"%SR_read))
						self.Signal_Read.text.show()
						i = i + 1
				 # elif (self.HVScanFlag == True):
				 # 	#end_time = time.time()*1000
				 # 	#diff_time = end_time - start_time
				 # 	#print diff_time
				 # 	time.sleep(TD_value_float)
				 # 	#SR_read = self.card.readAiAve(0,DAC_Average_Number )
				 # 	#stdin, stdout, stderr = self.ip.ssh.exec_command(ADC_SCAN_READ)
				 # 	cmd = ADC_SCAN_READ + MV_Number_str + ADC_SCAN_READ_gain
				 # 	#print cmd
				 # 	stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
				 # 	for line in stdout:
				 # 		SR_read = float(line)
				 # 		#print SR_read
				 # 	self.Signal_Read.text.setText(str("%2.4f"%SR_read))
				 # 	self.Signal_Read.text.show()
				#elif (self.HVScanFlag == True):
						#self.StopScan()
				else:
						i = loopValue


	def StartScan(self):
		#self.SettingData[0] = self.ip.connectIP.text()
		self.SettingData[1] = self.ms.HVScan.StartVoltage.spin.value()
		self.SettingData[2] = self.ms.HVScan.VoltageStep.spin.value()
		self.SettingData[3] = self.ms.HVScan.Loop.spin.value()
		#self.SettingData[4] = self.HVScan.TimeDelay.spin.value()
		if self.Setting.radioBtn2.isChecked():
			self.SettingData[4] = 1
		else:
			self.SettingData[4] = 0
		self.SettingData[5] = self.ms.DC_Voltage.DC_Voltage1.spin.value()
		self.SettingData[6] = self.ms.DC_Voltage.DC_Voltage2.spin.value()
		self.SettingData[7] = self.ms.Fan_Control.Fan_Speed.spin.value()
		self.SettingData[8] = self.ms.Data_Sampling.MV_Number.spin.value()
		self.SettingData[9] = self.ms.Data_Sampling.AVG_time.spin.value()
		self.SettingData[10] = self.ms.Integrator.ResetCycle.spin.value()
		self.SettingData[11] = self.ms.Integrator.HoldCycle.spin.value()
		self.SettingData[12] = self.ms.Integrator.IntCycle.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
				os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		self.SetCycle()

		self.HVScanFlag = True
		self.data = []
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		#self.StopBtn.setEnabled(True)


# def StopScan(self):
# 	self.DCmodeFlag = False
# 	self.HVScanFlag = False
# 	val = self.HVScan.StartVoltage.spin.value()
# 	self.HVScan.text2.setText(str(val)+" (V)")
# 	#self.card.writeAoValue(0,float(val)*DAC_Constant_S5)
# 	#stdin, stdout, stderr = self.ip.ssh.exec_command(DAC_SCAN_STOP)
# 	startValue = self.HVScan.StartVoltage.spin.value()
# 	Vout1 = startValue
# 	Vout2 = float(startValue) * DAC_Constant_S5
# 	cmd = DAC_SCAN + str(Vout2)
# 	#print cmd
# 	stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
# 	#self.FanSpeedFlag = False
# 	#self.card.enableCounter(False)
# 	self.DCmode.setEnabled(True)
# 	self.StartBtn.setEnabled(True)
# 	#self.StopBtn.setEnabled(False)
# 	self.Signal_Read.SaveBtn.setEnabled(True)
# 	self.Data_Analysis.AnalyBtn.setEnabled(True)


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
#			FS_read = self.card.readFreq()
#			#print(FS_read)
#			self.Fan_Control.text2.setText(str(FS_read))
#			self.Fan_Control.text2.show()
#			time.sleep(1)

	def SetFanSpeed(self):
		value3 = self.ms.Fan_Control.Fan_Speed.spin.value()
		FS_value = float(value3)/1000.0
		#self.card.writeAoValue(0, FS_value)
		cmd = DAC_FAN + str(FS_value)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.ms.Fan_Control.Fan_Speed.value.setText(str(value3))
		#self.FanSpeedFlag = True
		#self.card.enableCounter(True)
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
		self.data = []
		self.dv = []
		OpenFileName = QFileDialog.getOpenFileName(self,"Load Signal Data","","Text Files (*.txt)")
		if os.path.exists(OpenFileName):
				temp = [line.rstrip('\n') for line in open(OpenFileName)]
				for a in temp:
						b = a.split(',')
						self.dv.append(float(b[0]))
						self.data.append(float(b[1]))
				self.plot.ax.clear()
				self.plot.ax.plot(self.dv,self.data, '-')
				self.plot.canvas.draw()
				self.ms.Data_Analysis.AnalyBtn.setEnabled(True)

	def AnalysisData(self):
		value1 = float(self.ms.Data_Analysis.Threshold.spin.value() / 1000.0)
		value2 = float(self.ms.Data_Analysis.Noise.spin.value())

		peaks, _= find_peaks(self.data, height = value1, width = value2)
		#print peaks
		peak_num = len(peaks)
		results_half = peak_widths(self.data, peaks, rel_height = 0.5)
		#print results_half

		self.plot.ax.clear()
		self.plot.ax.plot(self.dv,self.data, '-')
		self.plot.canvas.draw()

		self.analist = []
		for index in peaks:
				xvalue = self.dv[index]
				self.analist.append(xvalue)
				yvalue = self.data[index]
				self.analist.append(yvalue)
				#ratio = yvalue / xvalue
				#list.append(ratio)
				self.analist.append(0.0)

		for i in xrange(0, peak_num):
				#print results_half[0][i]
				deltax = results_half[0][i]
				self.analist[3*i+2] = deltax
				xvalue = self.analist[3*i+0]
				yvalue = self.analist[3*i+1]
				#ratio = yvalue / deltax
				ratio = xvalue / deltax
				self.plot.ax.axvline(x=xvalue, color='k')
				self.plot.ax.text(xvalue, yvalue, str("%2.3f" %ratio), fontsize=12)
				self.plot.canvas.draw()

		#print self.analist
		self.ms.Data_Analysis.AnalyBtn.setEnabled(False)
		self.ms.Data_Analysis.SaveBtn.setEnabled(True)

	def SaveAnaData(self):
		SaveFileName = QFileDialog.getSaveFileName(self,"Save Analysis Data",ANALYSIS_FILENAME,"Text Files (*.txt)")
		if (SaveFileName != ''):
				fo = open(SaveFileName, "w+")
				number = len(self.analist)
				fo.write("peak_X, peak_Y, width")
				for i in range (0, number):
						if (i % 3) == 0:
								fo.write("\n")
						else:
								fo.write(", ")
						fo.write(str("%2.4f" %self.analist[i]))
				fo.write("\n")
				fo.close()
				self.ms.Data_Analysis.SaveBtn.setEnabled(False)

	def ShowThreshold(self):
		value = float(self.ms.Data_Analysis.Threshold.spin.value() / 1000.0)
		self.plot.ax.clear()
		self.plot.ax.plot(self.dv, self.data, '-')
		self.plot.ax.axhline(y=value, color='r')
		self.plot.canvas.draw()
		self.ms.Data_Analysis.AnalyBtn.setEnabled(True)

#	def ExitProg(self):
#                self.FanSpeedFlag = False
#                self.card.enableCounter(False)
#                self.card.writeAoValue(0, 0)
#                self.card.writeAoValue(1, 0)
#                self.I2C.DacClose(I2C_DAC1_ADDRESS)
#                self.I2C.DacClose(I2C_DAC2_ADDRESS)
#                self.close()		
		

if __name__ == '__main__':
	app = QApplication(sys.argv)
	main = mainWindow()
	main.show()
	os._exit(app.exec_())
