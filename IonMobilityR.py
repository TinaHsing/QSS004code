import os
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import threading
import time
import paramiko
import scipy

StartVoltage_MIN = 1000
StartVoltage_MAX = 1900

VoltageStep_MIN = 200
VoltageStep_MAX = 2000

Loop_MIN = 1
Loop_MAX = 2000

TimeDelay_MIN = 100
TimeDelay_MAX = 500

DAC_Constant_S5 = 6.0/5000.0
DAC_Average_Number = 10

DC_Voltage1_MIN = 0
DC_Voltage1_MAX = 2000

DC_Voltage2_MIN = 0
DC_Voltage2_MAX = 4000

Fan_Speed_MIN = 0
Fan_Speed_MAX = 5000

SETTING_FILEPATH = "set"
SETTING_FILENAME = "set/setting.txt"
DEFAULT_FILENAME = "Signal_Read_Out.txt"

I2CDAC_CONV_CONST = 4095.0/5.0

VERSION = "IonMobilityR V1.00"
DAC_SCAN = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 1 '
DAC_DC = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 2 '
DAC_ESI = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 3 '
DAC_FAN = 'LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 4 '



class adjustBlock():
	def __init__(self, name, minValue, maxValue):
		self.name = name
		self.min = minValue
		self.max = maxValue
		self.coarse = QSlider(Qt.Horizontal)
		self.spin = QSpinBox()
		self.adjGroupBox = QGroupBox(self.name)
		self.coarse.setRange(minValue,maxValue)
		self.coarse.sliderMoved.connect(self.update_spin)
		self.spin.setRange(minValue, maxValue)
		self.spin.valueChanged.connect(self.update_slider)
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
		w=QWidget()
		picout = QLabel(w)
		lg = QPixmap("logo.png")
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
                self.text.setFont(QFont("",16,QFont.Bold))
                self.SaveBtn = QPushButton("Save")
                self.ExitBtn = QPushButton("Exit")
		#self.SubBlockWidget()

        def SubBlockWidget(self):
                layout = QGridLayout()
                layout.addWidget(self.text,0,0,2,1)
                layout.addWidget(self.SaveBtn,0,1,1,1)
                layout.addWidget(self.ExitBtn,1,1,1,1)
		#self.setLayout(layout)
                self.GroupBox.setLayout(layout)
                self.GroupBox.show()
                return self.GroupBox

class HVScan_Group(QTabWidget):
	def __init__(self, parent=None):
		super(HVScan_Group, self).__init__(parent)
		self.GroupBox = QGroupBox("High Voltage Scan")
		self.StartVoltage = adjustBlock("Start Voltage (V)", StartVoltage_MIN, StartVoltage_MAX)
		self.VoltageStep = adjustBlock("Voltage Step (mV)", VoltageStep_MIN, VoltageStep_MAX)
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
		self.DC_Voltage1 = adjustBlock("Fixed Voltage (V)", DC_Voltage1_MIN, DC_Voltage1_MAX)
		self.DC1_Label1 = QLabel("Fixed Voltage =")
		self.DC1_Label2 = QLabel("0")
		self.SetDC1Btn = QPushButton("Set")
		self.DC_Voltage2 = adjustBlock("ESI (V)", DC_Voltage2_MIN, DC_Voltage2_MAX)
		self.SetDC2Btn = QPushButton("Set")
		self.DC2_Label1 = QLabel("ESI =")
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
    

    def buildConnect(self):
        global ConnectionStatus
        self.host = "rp-"+str(self.connectIP.text())+".local"
        try:
            self.ssh.connect(self.host, HOST_PORT, HOST_NAME, HOST_PWD)
        except:
            self.connectStatus.setText("SSH connection failed")
            self.connectStatus.show()
        else:
            stdin, stdout, stderr = self.ssh.exec_command('cat /opt/redpitaya/fpga/red_pitaya_top_v2.bit > /dev/xdevcfg')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 1 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 2 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 3 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 4 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 5 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 6 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 7 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 8 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 9 0')
            stdin, stdout, stderr = self.ssh.exec_command('LD_LIBRARY_PATH=/opt/redpitaya/lib ./DAC 10 0')
            pe = QPalette()
            pe.setColor(QPalette.WindowText,Qt.black)
            self.connectStatus.setPalette(pe)
            self.connectStatus.setText("Connection build")
            self.connectStatus.show()
            ConnectionStatus = True

		
class mainWindow(QMainWindow):
	def __init__(self, parent=None):
		super (mainWindow, self).__init__(parent)
		self.setWindowTitle(" GRC Ion Mobility Spectrometer ")
		self.resize(1280,840)
		self.move(50,50)
		self.ip = connectBlock()
		self.HVScan = HVScan_Group()
		self.DC_Voltage = DC_Voltage_Group()
		self.Fan_Control = Fan_Control_Group()
		self.Signal_Read = Signal_Read_Group()
		self.plot = outputPlot()
		self.SettingData = [0 for i in range(0, 7)]
		self.LoadPreset()
		menu_about = QAction("&About", self)
		menu_about.triggered.connect(self.aboutBox)
		mainMenu = self.menuBar()
		mainMenu.addMenu("&About")
		mainMenu.addAction(menu_about)


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
		self.dv =[]
		self.main_UI()

		# ExitProg
		self.Signal_Read.ExitBtn.clicked.connect(lambda:self.ExitProg())

	def main_UI(self):
		mainLayout = QGridLayout()
		mainLayout.addWidget(self.HVScan.SubBlockWidget(),0,0,2,2)
		mainLayout.addWidget(self.DC_Voltage.SubBlockWidget(),0,2,2,1)
		mainLayout.addWidget(self.Fan_Control.SubBlockWidget(),0,3,1,1)
		mainLayout.addWidget(self.ip.connectBlockWidget(), 0,4, 1, 1)
		mainLayout.addWidget(self.Signal_Read.SubBlockWidget(),1,3,1,1)
		mainLayout.addWidget(self.plot,2,0,2,5)
		mainLayout.setRowStretch(0, 1)
		mainLayout.setRowStretch(1, 1)
		mainLayout.setRowStretch(2, 5)
		mainLayout.setColumnStretch(0, 1)
		mainLayout.setColumnStretch(1, 1)
		mainLayout.setColumnStretch(2, 1)
		mainLayout.setColumnStretch(3, 1)
		self.setCentralWidget(QWidget(self))
		self.centralWidget().setLayout(mainLayout)

	def aboutBox(self):
		QMassageBox.about(self, VERSION)


	def LoadPreset(self):
		
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
		stepValue = float(self.HVScan.VoltageStep.spin.value())/1000.0
		self.data =[]
		self.dv=[]
		while (i < loopValue) or (self.HVScanFlag == True):
                        if (i < loopValue) & (self.HVScanFlag == True):
                                Vout1 = startValue + stepValue * i
                                Vout2 = float(Vout1) * DAC_Constant_S5
                                #self.card.writeAoValue(1, Vout2)
                                cmd = DAC_SCAN+str(Vout2)
                                print cmd
                                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                                self.HVScan.text2.setText(str(Vout1))
                                self.HVScan.text2.show()
                                time.sleep(TD_value_float)
                                SR_read = self.card.readAiAve(0,DAC_Average_Number )
                                self.data.append(SR_read)
                                self.dv.append(i*stepValue)
                                self.plot.ax.clear()
                                self.plot.ax.plot(self.dv,self.data, '-')
                                self.plot.canvas.draw()
                                self.Signal_Read.text.setText(str("%2.4f"%SR_read))
                                self.Signal_Read.text.show()
                                i = i + 1
                        elif (self.HVScanFlag == True):
                                time.sleep(TD_value_float)
                                SR_read = self.card.readAiAve(0,DAC_Average_Number )
                                self.Signal_Read.text.setText(str("%2.4f"%SR_read))
                                self.Signal_Read.text.show()

                        else:
                                i=loopValue
 

	def StartScan(self):
		self.SettingData[0] = self.HVScan.StartVoltage.spin.value()
		self.SettingData[1] = self.HVScan.VoltageStep.spin.value()
		self.SettingData[2] = self.HVScan.Loop.spin.value()
		self.SettingData[3] = self.HVScan.TimeDelay.spin.value()
		self.SettingData[4] = self.DC_Voltage.DC_Voltage1.spin.value()
		self.SettingData[5] = self.DC_Voltage.DC_Voltage2.spin.value()
		self.SettingData[6] = self.Fan_Control.Fan_Speed.spin.value()
		#print(self.SettingData)
		SettingData = [str(line) + '\n' for line in self.SettingData] 
		if not os.path.isdir(SETTING_FILEPATH):
			os.mkdir(SETTING_FILEPATH)
		fo = open(SETTING_FILENAME, "w+")
		fo.writelines(SettingData)
		fo.close()
		self.HVScanFlag = True
		gt1 = threading.Thread(target = self.VoltageOut)
		gt1.start()
		self.data = []

	def StopScan(self):
		self.HVScanFlag = False
		val =self.HVScan.StartVoltage.spin.value()
		self.HVScan.text2.setText(str(val))
		self.card.writeAoValue(0,float(val)*DAC_Constant_S5)
		#self.FanSpeedFlag = False
		#self.card.enableCounter(False)

#DC_Voltage
	def SetDC1(self):## Fixed Voltage
		value1= self.DC_Voltage.DC_Voltage1.spin.value()
		DC1_value_out =  value1 * DAC_Constant_S5
		cmd = DAC_DC + str(DC1_value_out)
		


	def SetDC2(self): ##ESI
		value2 = self.DC_Voltage.DC_Voltage2.spin.value()
		DC2_value_out = value2 * DAC_Constant_S5


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
		self.card.writeAoValue(0, FS_value)
		self.FanSpeedFlag = True
		self.card.enableCounter(True)
		gt2 = threading.Thread(target = self.FanSpeedOut)
		gt2.start()

#Signal_Read
	def SaveData(self):
		SaveData = [str(line) + '\n' for line in self.data] 
		SaveFileName = QFileDialog.getSaveFileName(self,"Save Signal Data","./" + DEFAULT_FILENAME,"Text Files (*.txt)")
		fo = open(SaveFileName, "w+")
		number = len(self.data)
		for i in range (0, number):
                        fo.write(str("%2.4f" %self.dv[i])+","+str("%2.4f" %self.data[i])+"\n")
		fo.close()
	def ExitProg(self):
                self.FanSpeedFlag = False
                self.card.enableCounter(False)
                self.card.writeAoValue(0, 0)
                self.card.writeAoValue(1, 0)
                self.I2C.DacClose(I2C_DAC1_ADDRESS)
                self.I2C.DacClose(I2C_DAC2_ADDRESS)
                self.close()

		
		

if __name__ == '__main__':
	app = QApplication(sys.argv)
	main = mainWindow()
	main.show()
	os._exit(app.exec_())
