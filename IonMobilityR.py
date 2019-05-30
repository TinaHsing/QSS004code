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
CYCLE_MAX = 125000000

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
ADC_SCAN_READ = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./ADC_MV 1 '
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
" IonMobilityR V1.03 \n\n" + \
" Copyright @ 2019 TAIP \n" + \
" Maintain by Quantaser Photonics Co. Ltd "

class adjustBlock():
	def __init__(self, name, minValue, maxValue, text, value, SetBtn):
		self.name = name
		self.min = minValue
		self.max = maxValue
		self.adjGroupBox = QGroupBox(self.name)
		self.coarse = QSlider(Qt.Horizontal)
		self.spin = QSpinBox()
		self.text = QLabel(text)
		self.value = QLabel(value)
		self.SetBtnFlag = SetBtn
		self.SetBtn = QPushButton("Set")
		self.coarse.setRange(minValue,maxValue)
		self.coarse.sliderMoved.connect(self.update_spin)
		self.spin.setRange(minValue, maxValue)
		self.spin.valueChanged.connect(self.update_slider)
		self.spin.setSingleStep(1)
	def adjBlockWidget(self):
		adjLayout = QGridLayout()
		adjLayout.addWidget(self.coarse,0,0,1,5)
		adjLayout.addWidget(self.spin,0,5,1,1)
		if (self.text.text() != ""):
			adjLayout.addWidget(self.text,1,0,1,1)
			adjLayout.addWidget(self.value,1,1,1,1)
		if (self.SetBtnFlag == True):
			adjLayout.addWidget(self.SetBtn,1,5,1,1)
		self.adjGroupBox.setLayout(adjLayout)
		self.adjGroupBox.show()
		return self.adjGroupBox
	def update_spin(self):
		a=self.coarse.value()
		self.spin.setValue(a)
	def update_slider(self):
		a=self.spin.value()
		self.coarse.setValue(a)
		self.coarse.setSliderPosition(a)

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
		self.ax.set_xlabel("Voltage Difference (V)")
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
		layout = QHBoxLayout()
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
		self.StartVoltage = adjustBlock("Start Voltage (V)", StartVoltage_MIN, StartVoltage_MAX, "", "", False)
		self.VoltageStep = adjustBlock("Voltage Step (mV)", VoltageStep_MIN, VoltageStep_MAX, "", "", False)
		self.Loop = adjustBlock("Loop", Loop_MIN, Loop_MAX, "", "", False)
		#self.TimeDelay = adjustBlock("Time Delay (ms)", TimeDelay_MIN, TimeDelay_MAX, "", "", False)
		self.MV_Number = adjustBlock("MV Average Number", MV_Numver_MIN, MV_Numver_MAX, "", "", False)
		self.AVG_time = adjustBlock("Average Times", AVG_time_MIN, AVG_time_MAX, "", "", False)
		self.text1 = QLabel("Voltage Out = ")
		self.text2 = QLabel("0 V")
		self.DCmode = QPushButton("DC mode")	# 2019.5.7
		self.StartBtn = QPushButton("Start Scan")
		self.StopBtn = QPushButton("Stop")
		self.DCmode.setEnabled(False)
		self.StartBtn.setEnabled(False)
		self.StopBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.StartVoltage.adjBlockWidget(),0,0,1,2)
		layout.addWidget(self.VoltageStep.adjBlockWidget(),1,0,1,2)
		layout.addWidget(self.Loop.adjBlockWidget(),2,0,1,2)
		#layout.addWidget(self.TimeDelay.adjBlockWidget(),1,2,1,3)
		layout.addWidget(self.MV_Number.adjBlockWidget(),0,2,1,2)
		layout.addWidget(self.AVG_time.adjBlockWidget(),1,2,1,2)
		layout.addWidget(self.text1,2,2,1,1)
		layout.addWidget(self.text2,2,3,1,1)
		layout.addWidget(self.DCmode,3,1,1,1)
		layout.addWidget(self.StartBtn,3,2,1,1)
		layout.addWidget(self.StopBtn,3,3,1,1)
		layout.setRowStretch(0, 1)
		layout.setRowStretch(1, 1)
		layout.setRowStretch(2, 1)
		layout.setRowStretch(3, 1)
		layout.setColumnStretch(0, 1)
		layout.setColumnStretch(1, 1)
		layout.setColumnStretch(2, 1)
		layout.setColumnStretch(3, 1)
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Data_Analysis_Group(QWidget):
	def __init__(self, parent=None):
		super(Data_Analysis_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Data Analysis")
		self.Threshold = adjustBlock("Threshold (mV)", Threshold_MIN, Threshold_MAX, "", "", False)
		self.Noise = adjustBlock("Width (points)", Noise_MIN, Noise_MAX, "", "", False)
		self.LoadBtn = QPushButton("Load")
		self.AnalyBtn = QPushButton("Analysis")
		self.SaveBtn = QPushButton("Save Analysis")
		#self.LoadBtn.setEnabled(False)
		self.AnalyBtn.setEnabled(False)
		self.SaveBtn.setEnabled(False)
		self.Noise.coarse.valueChanged.connect(lambda:self.NoiseChange())

	def SubBlockWidget(self):
		layout = QGridLayout()
		layout.addWidget(self.Threshold.adjBlockWidget(),0,0,1,3)
		layout.addWidget(self.Noise.adjBlockWidget(),1,0,1,3)
		layout.addWidget(self.LoadBtn,2,0,1,1)
		layout.addWidget(self.AnalyBtn,2,1,1,1)
		layout.addWidget(self.SaveBtn,2,2,1,1)
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
		self.DC_Voltage1 = adjustBlock("Fixed Voltage (V)", DC_Voltage1_MIN, DC_Voltage1_MAX, "Fixed Voltage =", "0", True)
		self.DC_Voltage2 = adjustBlock("ESI (V)", DC_Voltage2_MIN, DC_Voltage2_MAX, "ESI =", "0", True)
		#self.SubBlockWidget()
		self.DC_Voltage1.SetBtn.setEnabled(False)
		self.DC_Voltage2.SetBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.DC_Voltage1.adjBlockWidget())
		layout.addWidget(self.DC_Voltage2.adjBlockWidget())
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Fan_Control_Group(QWidget):
	def __init__(self, parent=None):
		super(Fan_Control_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Fan Control")
		self.Fan_Speed = adjustBlock("Fan Speed Setting (mV)", Fan_Speed_MIN, Fan_Speed_MAX, "Fan Speed = ", "0", True)
		self.Fan_Speed.SetBtn.setEnabled(False)

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.Fan_Speed.adjBlockWidget())
		#self.setLayout(layout)
		self.GroupBox.setLayout(layout)
		self.GroupBox.show()
		return self.GroupBox

class Integrator_Group(QWidget):
	def __init__(self, parent=None):
		super(Integrator_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("Integrator Group")
		self.ResetCycle = adjustBlock("Reset Cycle", CYCLE_MIN, CYCLE_MAX, "Reset Time =", "0 (ms)", False)
		self.HoldCycle = adjustBlock("Hold Cycle", CYCLE_MIN, CYCLE_MAX, "Hold Time =", "0 (ms)", False)
		self.IntCycle = adjustBlock("Int Cycle", CYCLE_MIN, CYCLE_MAX, "Int Time =", "0 (ms)", False)
		#self.SubBlockWidget()

	def SubBlockWidget(self):
		layout = QVBoxLayout()
		layout.addWidget(self.ResetCycle.adjBlockWidget())
		layout.addWidget(self.HoldCycle.adjBlockWidget())
		layout.addWidget(self.IntCycle.adjBlockWidget())
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


class mainWindow(QMainWindow):
	def __init__(self, parent=None):
		super (mainWindow, self).__init__(parent)
		self.setWindowTitle(TITLE_TEXT)
		self.resize(1280,840)
		self.move(50,50)
		self.ip = connectBlock()
		self.HVScan = HVScan_Group()
		self.DC_Voltage = DC_Voltage_Group()
		self.Fan_Control = Fan_Control_Group()
		self.Integrator = Integrator_Group()
		self.Signal_Read = Signal_Read_Group()
		self.Data_Analysis = Data_Analysis_Group()
		self.plot = outputPlot()
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
		self.HVScan.DCmode.clicked.connect(lambda:self.DCmode())
		self.HVScan.StartBtn.clicked.connect(lambda:self.StartScan())
		self.HVScan.StopBtn.clicked.connect(lambda:self.StopScan())
		#self.Vout1 = 0
		#self.Vout2 = 0.0
		self.DCmodeFlag = False
		self.HVScanFlag = False

		#DC_Voltage
		self.DC_Voltage.DC_Voltage1.SetBtn.clicked.connect(lambda:self.SetDC1())
		self.DC_Voltage.DC_Voltage2.SetBtn.clicked.connect(lambda:self.SetDC2())

		#Fan_Control
		self.Fan_Control.Fan_Speed.SetBtn.clicked.connect(lambda:self.SetFanSpeed())
		self.FanSpeedFlag = False

		#Signal_Read
		self.Signal_Read.SaveBtn.clicked.connect(lambda:self.SaveData())
		self.data = []
		self.dv = []

		#Data_Analysis
		self.Data_Analysis.LoadBtn.clicked.connect(lambda:self.LoadData())
		self.Data_Analysis.AnalyBtn.clicked.connect(lambda:self.AnalysisData())
		self.Data_Analysis.SaveBtn.clicked.connect(lambda:self.SaveAnaData())
		self.Data_Analysis.Threshold.coarse.valueChanged.connect(lambda:self.ShowThreshold())
		self.analist = []

		#ExitProg
		#self.Signal_Read.ExitBtn.clicked.connect(lambda:self.ExitProg())

	def main_UI(self):
		mainLayout = QGridLayout()
		mainLayout.addWidget(self.HVScan.SubBlockWidget(),0,0,2,2)
		mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),2,0,1,2)
		mainLayout.addWidget(self.DC_Voltage.SubBlockWidget(),0,2,2,1)
		mainLayout.addWidget(self.Fan_Control.SubBlockWidget(),2,2,1,1)
		mainLayout.addWidget(self.Integrator.SubBlockWidget(),0,3,3,1)
		mainLayout.addWidget(self.ip.connectBlockWidget(),0,4,1,1)
		mainLayout.addWidget(self.Data_Analysis.SubBlockWidget(),1,4,2,1)
		mainLayout.addWidget(self.plot,3,0,1,5)
		mainLayout.setRowStretch(0, 1)
		mainLayout.setRowStretch(1, 1)
		mainLayout.setRowStretch(2, 1)
		mainLayout.setRowStretch(3, 5)
		mainLayout.setColumnStretch(0, 1)
		mainLayout.setColumnStretch(1, 1)
		mainLayout.setColumnStretch(2, 1)
		mainLayout.setColumnStretch(3, 1)
		mainLayout.setColumnStretch(4, 1)
		self.setCentralWidget(QWidget(self))
		self.centralWidget().setLayout(mainLayout)

	def aboutBox(self):
		versionBox = QMessageBox()
		versionBox.about(self, "Version", VERSION_TEXT)

	def LoadPreset(self):
		if os.path.exists(SETTING_FILENAME):
			self.SettingData = [line.rstrip('\n') for line in open(SETTING_FILENAME)]
		self.ip.connectIP.setText(str(self.SettingData[0]))
		self.HVScan.StartVoltage.coarse.setValue(int(self.SettingData[1]))
		self.HVScan.StartVoltage.spin.setValue(int(self.SettingData[1]))
		self.HVScan.VoltageStep.coarse.setValue(int(self.SettingData[2]))
		self.HVScan.VoltageStep.spin.setValue(int(self.SettingData[2]))
		self.HVScan.Loop.coarse.setValue(int(self.SettingData[3]))
		self.HVScan.Loop.spin.setValue(int(self.SettingData[3]))
		#self.HVScan.TimeDelay.coarse.setValue(int(self.SettingData[4]))
		#self.HVScan.TimeDelay.spin.setValue(int(self.SettingData[4]))
		self.DC_Voltage.DC_Voltage1.coarse.setValue(int(self.SettingData[5]))
		self.DC_Voltage.DC_Voltage1.spin.setValue(int(self.SettingData[5]))
		self.DC_Voltage.DC_Voltage2.coarse.setValue(int(self.SettingData[6]))
		self.DC_Voltage.DC_Voltage2.spin.setValue(int(self.SettingData[6]))
		self.Fan_Control.Fan_Speed.coarse.setValue(int(self.SettingData[7]))
		self.Fan_Control.Fan_Speed.spin.setValue(int(self.SettingData[7]))
		self.HVScan.MV_Number.coarse.setValue(int(self.SettingData[8]))
		self.HVScan.MV_Number.spin.setValue(int(self.SettingData[8]))
		self.HVScan.AVG_time.coarse.setValue(int(self.SettingData[9]))
		self.HVScan.AVG_time.spin.setValue(int(self.SettingData[9]))
		self.Integrator.ResetCycle.coarse.setValue(int(self.SettingData[10]))
		self.Integrator.ResetCycle.spin.setValue(int(self.SettingData[10]))
		self.Integrator.HoldCycle.coarse.setValue(int(self.SettingData[11]))
		self.Integrator.HoldCycle.spin.setValue(int(self.SettingData[11]))
		self.Integrator.IntCycle.coarse.setValue(int(self.SettingData[12]))
		self.Integrator.IntCycle.spin.setValue(int(self.SettingData[12]))

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
			self.HVScan.DCmode.setEnabled(True)
			self.HVScan.StartBtn.setEnabled(True)
			#self.HVScan.StopBtn.setEnabled(True)
			self.DC_Voltage.DC_Voltage1.SetBtn.setEnabled(True)
			self.DC_Voltage.DC_Voltage2.SetBtn.setEnabled(True)
			self.Fan_Control.Fan_Speed.SetBtn.setEnabled(True)

#DCmode
	def SetCycle(self):
		cmd = RESET_CYCLE_CMD + str(self.SettingData[10])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		CycleValue = float(self.SettingData[10]) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.Integrator.ResetCycle.value.setText(CycleText)
		time.sleep(0.001)

		cmd = HOLD_CYCLE_CMD + str(self.SettingData[11])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		CycleValue = float(self.SettingData[11]) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.Integrator.HoldCycle.value.setText(CycleText)
		time.sleep(0.001)

		cmd = INT_CYCLE_CMD + str(self.SettingData[12])
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		CycleValue = float(self.SettingData[12]) * CYCLE_CONST
		CycleText = str(CycleValue) + ' (ms)'
		self.Integrator.IntCycle.value.setText(CycleText)
		time.sleep(0.001)


	def DCmode(self):	# 2019.5.7
		startValue = self.HVScan.StartVoltage.spin.value()
		self.SettingData[1] = startValue
		self.SettingData[10] = self.Integrator.ResetCycle.spin.value()
		self.SettingData[11] = self.Integrator.HoldCycle.spin.value()
		self.SettingData[12] = self.Integrator.IntCycle.spin.value()
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
		self.HVScan.text2.setText(str(Vout1)+" (V)")
		self.HVScan.text2.show()

		self.SetCycle()

		self.DCmodeFlag = True
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.data = []
		self.HVScan.DCmode.setEnabled(False)
		self.HVScan.StartBtn.setEnabled(False)
		self.HVScan.StopBtn.setEnabled(True)

#HVScan
	def VoltageOut(self):
		#TD_value_float = float(self.HVScan.TimeDelay.spin.value()/1000.0)
		MV_Number_str = str(self.HVScan.MV_Number.spin.value())
		AVG_time_value = int(self.HVScan.AVG_time.spin.value())
		Fix_Vol_value = self.DC_Voltage.DC_Voltage1.spin.value()
		#i = 0	# 2019.5.7
		if (self.HVScanFlag == True):
			i = -3
		else:
			i = 0
		loopValue = self.HVScan.Loop.spin.value()
		startValue = self.HVScan.StartVoltage.spin.value()
		stepValue = float(self.HVScan.VoltageStep.spin.value())/1000.0
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
					self.HVScan.text2.setText(str(Vout1)+" (V)")
					self.HVScan.text2.show()

				cmd = SCAN_REG_CMD + '1'
				#print cmd
				stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
				time.sleep(0.001)
				cmd = SCAN_REG_CMD + '0'
				#print cmd
				stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
				time.sleep(0.001)

				while (reg_EOI == 0):
					stdin, stdout, stderr = self.ip.ssh.exec_command(REG_EOI_CMD)
					for line in stdout:
						#print line
						reg_EOI = int(line[9])
						#print 'reg_EOI = ' + str(reg_EOI)
					time.sleep(0.001)

				#time.sleep(TD_value_float)
				#SR_read = self.card.readAiAve(0, DAC_Average_Number)
				#stdin, stdout, stderr = self.ip.ssh.exec_command(ADC_SCAN_READ)
				cmd = ADC_SCAN_READ + MV_Number_str + ADC_SCAN_READ_gain
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
			elif (self.HVScanFlag == True):
				self.StopScan()
			else:
				i = loopValue


	def StartScan(self):
		#self.SettingData[0] = self.ip.connectIP.text()
		self.SettingData[1] = self.HVScan.StartVoltage.spin.value()
		self.SettingData[2] = self.HVScan.VoltageStep.spin.value()
		self.SettingData[3] = self.HVScan.Loop.spin.value()
		#self.SettingData[4] = self.HVScan.TimeDelay.spin.value()
		self.SettingData[5] = self.DC_Voltage.DC_Voltage1.spin.value()
		self.SettingData[6] = self.DC_Voltage.DC_Voltage2.spin.value()
		self.SettingData[7] = self.Fan_Control.Fan_Speed.spin.value()
		self.SettingData[8] = self.HVScan.MV_Number.spin.value()
		self.SettingData[9] = self.HVScan.AVG_time.spin.value()
		self.SettingData[10] = self.Integrator.ResetCycle.spin.value()
		self.SettingData[11] = self.Integrator.HoldCycle.spin.value()
		self.SettingData[12] = self.Integrator.IntCycle.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()

		self.SetCycle()

		self.HVScanFlag = True
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.data = []
		self.HVScan.DCmode.setEnabled(False)
		self.HVScan.StartBtn.setEnabled(False)
		self.HVScan.StopBtn.setEnabled(True)


	def StopScan(self):
		self.DCmodeFlag = False
		self.HVScanFlag = False
		val = self.HVScan.StartVoltage.spin.value()
		self.HVScan.text2.setText(str(val)+" (V)")
		#self.card.writeAoValue(0,float(val)*DAC_Constant_S5)
		#stdin, stdout, stderr = self.ip.ssh.exec_command(DAC_SCAN_STOP)
		startValue = self.HVScan.StartVoltage.spin.value()
		Vout1 = startValue
		Vout2 = float(startValue) * DAC_Constant_S5
		cmd = DAC_SCAN + str(Vout2)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		#self.FanSpeedFlag = False
		#self.card.enableCounter(False)
		self.HVScan.DCmode.setEnabled(True)
		self.HVScan.StartBtn.setEnabled(True)
		self.HVScan.StopBtn.setEnabled(False)
		self.Signal_Read.SaveBtn.setEnabled(True)
		self.Data_Analysis.AnalyBtn.setEnabled(True)


#DC_Voltage
	def SetDC1(self):## Fixed Voltage
		value1 = self.DC_Voltage.DC_Voltage1.spin.value()
		DC1_value_out = value1 * DAC_Constant_S5
		cmd = DAC_DC + str(DC1_value_out)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.DC_Voltage.DC_Voltage1.value.setText(str(value1))

	def SetDC2(self): ##ESI
		value2 = self.DC_Voltage.DC_Voltage2.spin.value()
		DC2_value_out = value2 * DAC_Constant_S5
		cmd = DAC_ESI + str(DC2_value_out)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.DC_Voltage.DC_Voltage2.value.setText(str(value2))


#Fan_Control
#	def FanSpeedOut(self):
#		while (self.FanSpeedFlag == True):
#			FS_read = self.card.readFreq()
#			#print(FS_read)
#			self.Fan_Control.text2.setText(str(FS_read))
#			self.Fan_Control.text2.show()
#			time.sleep(1)

	def SetFanSpeed(self):
		value3 = self.Fan_Control.Fan_Speed.spin.value()
		FS_value = float(value3)/1000.0
		#self.card.writeAoValue(0, FS_value)
		cmd = DAC_FAN + str(FS_value)
		#print cmd
		stdin, stdout, stderr = self.ip.ssh.exec_command(cmd)
		self.Fan_Control.Fan_Speed.value.setText(str(value3))
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
			self.Data_Analysis.AnalyBtn.setEnabled(True)

	def AnalysisData(self):
		value1 = float(self.Data_Analysis.Threshold.spin.value() / 1000.0)
		value2 = float(self.Data_Analysis.Noise.spin.value())

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
		self.Data_Analysis.AnalyBtn.setEnabled(False)
		self.Data_Analysis.SaveBtn.setEnabled(True)

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
			self.Data_Analysis.SaveBtn.setEnabled(False)

	def ShowThreshold(self):
		value = float(self.Data_Analysis.Threshold.spin.value() / 1000.0)
		self.plot.ax.clear()
		self.plot.ax.plot(self.dv, self.data, '-')
		self.plot.ax.axhline(y=value, color='r')
		self.plot.canvas.draw()
		self.Data_Analysis.AnalyBtn.setEnabled(True)

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
