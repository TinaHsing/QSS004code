from cffi import FFI

ffi = FFI()
with open("_bdaqctrl.h") as fin:
	ffi.cdef(fin.read())

bdaqctrl = ffi.dlopen("libbiodaq.so")


class Card:
	def __init__(self):
		#initialization for PCM-3810
		self.info = ffi.new("DeviceInformation *")
		self.info.Description = "PCM-3810,BID#0"
		self.info.DeviceNumber = -1
		self.info.DeviceMode = bdaqctrl.ModeWriteWithReset
		self.info.ModuleIndex = 0
		
		#=========initialization for Analog output===========
		self.ao= bdaqctrl.AdxInstantAoCtrlCreate()
		assert bdaqctrl.Success == bdaqctrl.InstantAoCtrl_setSelectedDevice(self.ao, self.info)
		self.ao_channels = bdaqctrl.InstantAoCtrl_getChannels(self.ao)
		ao_ch0 = bdaqctrl.ICollection_getItem(self.ao_channels, 0)
		ao_ch1 = bdaqctrl.ICollection_getItem(self.ao_channels, 1)	
		
		assert bdaqctrl.Success == bdaqctrl.AnalogChannel_setValueRange(ao_ch0, bdaqctrl.V_0To5) #set the output voltage range to 0~5V
		assert bdaqctrl.Success == bdaqctrl.AnalogChannel_setValueRange(ao_ch1, bdaqctrl.V_0To5) #set the output voltage range to 0~5V
		
		# ========initialization for Analog input===========
		self.ai=bdaqctrl.AdxInstantAiCtrlCreate()
		assert bdaqctrl.Success == bdaqctrl.InstantAiCtrl_setSelectedDevice(self.ai, self.info)
		self.ai_channels = bdaqctrl.InstantAiCtrl_getChannels(self.ai)
		self.buffer = ffi.new("double []",1) # get buffer for only one channel
		ai_ch0 = bdaqctrl.ICollection_getItem(self.ai_channels, 0)

		# ========initialization for Frequency counter ========
		self.fc=bdaqctrl.AdxFreqMeterCtrlCreate()
		assert bdaqctrl.Success == bdaqctrl.FreqMeterCtrl_setSelectedDevice(self.fc, self.info)
		assert bdaqctrl.Success == bdaqctrl.FreqMeterCtrl_setChannel(self.fc, 0) # set Channel 0 for frequency counter
		assert bdaqctrl.Success == bdaqctrl.FreqMeterCtrl_setCollectionPeriod(self.fc,0) # ??? set Collection Period =0??

	@property
	def ao_channel_count(self):
		return bdaqctrl.InstantAoCtrl_getChannelCount(self.ao)

	def writeAoValue(self, channel_id, value):
		assert bdaqctrl.Success == bdaqctrl.InstantAoCtrl_WriteAny(self.ao,channel_id,1,ffi.NULL,ffi.new("double *", value))

	@property
	def ai_channel_count(self):
		return bdaqctrl.InstantAiCtrl_getChannelCount(self.ai)

	#read only one channel data
	def readAiValue(self, channel):
		assert bdaqctrl.Success == bdaqctrl.InstantAiCtrl_ReadAny(self.ai,channel,1,ffi.NULL,self.buffer)
		return self.buffer[0]

	def enableCounter(self, enstate):
		bdaqctrl.FreqMeterCtrl_setEnabled(self.fc, enstate)
		ssert bdaqctrl.Success == bdaqctrl.FreqMeterCtrl_setEnabled(self.fc, enstate)
	
	def readFreq(self):
		return bdaqctrl.FreqMeterCtrl_getValue(self.fc)



if __name__ == "__main__":

	daqcard = Card()
	print ("ao channel count =")
	print (daqcard.ao_channel_count)
	print ("ai channel count =")
	print (daqcard.ai_channel_count)
	print (daqcard.readAiValue(0))
	daqcard.writeAoValue(0, 0.5)
	daqcard.writeAoValue(1, 0.3)
	daqcard.readAiValue(0)
	daqcard.enableCounter(True)
	daqcard.readFreq()
	daqcard.enableCounter(False)








