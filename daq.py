from cffi import FFI

ffi = FFI()
with open("_bdaqctrl.h") as fin:
	ffi.cdef(fin.read())

badqctrl = ffi.dlopen("libbiodaq.so")


class Card:
	def __init__(self, dev_info):
		self.info = ffi.new("DeviceInformation *")
		self.info.Description = dev_info
		self.info.DeviceNumber = -1
		self.info.DeviceMode = bdaqctrl.ModeWriteWithReset
		self.info.ModuleIndex = 0
		self.ao= bdaqctrl.AdxInstantAoCtrlCreate()
		assert bdaqctrl.Success == bdaqctrl.InstantAoCtrl_setSelectedDevice(self.ao, self.info)
		self.ai=bdaqctrl.AdxInstantAiCtrlCreate()
		assert bdaqctrl.Success == bdaqctrl.InstantAiCtrl_setSelectedDevice(self.ao, self.info)

	@property
    def ao_channel_count(self):
    	return bdaqctrl.InstantAoCtrl_getChannelCount(self.ao)

    def setAoRange(self, channel_id, mode):
    	channel = bdaqctrl.ICollection_getItem(self.channels, channel_id) 	
    	assert bdaqctrl.Success == bdaqctrl.AnalogChannel_setValueRange(channel, mode)

    def writeAoValue(self, channel_id, value):
    	assert bdaqctrl.Success == bdaqctrl.InstantAoCtrl_WriteAny(
            self.ao,
            channel_id,
            1,
            ffi.NULL,
            ffi.new("double *", value),
        )

if __name__ == "__main__":

	daqcard = Card("PCM-3810,BID#0")
	print "channel count ="
	print daqcard.ao_channel_count
	daqcard.setAoRange(0,bdaqctrl.V_0To10)
	print "set Ao Range sucess!"
	daqcard.writeAoValue(0, 0.5)







