import serial
import serial.tools.list_ports
import platform
ft232_name_in_mac = "0403:6001"
ft232_name_in_win = "VID_0403+PID_6001"
#ft232_name_in_win = "USB VID:PID=2341:0043"	#Arduino Uno

class FT232:
	def __init__(self, baudrate, timeout):
		self.baudrate = baudrate
		self.timeout = timeout
		self.cp = 0
		self.port = serial.Serial()
		self.find_com = self.checkCom()
		self.port = self.comDetect()
		if (self.find_com == True):
			self.port.flush()

	def checkCom(self):
		find_com = False
		portlist = serial.tools.list_ports.comports()
		os = platform.system()
		#print os
		for a in portlist:
			if os == 'Darwin':
				if ft232_name_in_mac in a[2]:
					self.cp = a[0]
			elif os == "Windows":
				if ft232_name_in_win in a[2]:
					self.cp = a[0]
				elif ft232_name_in_mac in a[2]:
					self.cp = a[0]
#		print(a)
#		print( "cp = " + str(self.cp) )
		if self.cp != 0:
			find_com = True

		return find_com

	def comDetect(self):
		ser = serial.Serial()
		if (self.find_com == True):
			ser = serial.Serial(self.cp)
			ser.baudrate = self.baudrate
			ser.timeout = self.timeout
		return ser

	def writeBinary(self, data):
		data_list = data + '\n'
		#print data_list
		self.port.write(data_list)

	def readBinary(self):
		data = self.port.readline()
		print data
		return data

