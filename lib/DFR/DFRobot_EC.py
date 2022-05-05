#import sys

_kvalue = 1.0
_kvalueLow = 1.0
_kvalueHigh = 1.0
_cmdReceivedBufferIndex = 0
_voltage = 0.0
_temperature = 25.0

class DFRobot_EC():
	def begin(self):
		global _kvalueLow
		global _kvalueHigh
		try:
			with open('ecdata.txt', 'r') as f:
				kvalueLowLine = f.readline()
				kvalueLowLine = kvalueLowLine.strip('kvalueLow=')
				_kvalueLow = float(kvalueLowLine)
				kvalueHighLine = f.readline()
				kvalueHighLine = kvalueHighLine.strip('kvalueHigh=')
				_kvalueHigh = float(kvalueHighLine)
		except Exception as e:
			if e is IOError:
				print("ecdata.txt does not exist. Creating file with default settings.")
				with open('ecdata.txt', 'w') as f:
					#flist=f.readlines()
					flist = 'kvalueLow=' + str(_kvalueLow) + '\n'
					flist += 'kvalueHigh=' + str(_kvalueHigh) + '\n'
					#f=open('data.txt','w+')
					f.writelines(flist)
				print(">>>Reset EC to default parameters<<<")
			else:
				print(e)
	
	def rawEC(self, voltage):
		raw = 1000*voltage/820.0/200.0
		return raw

	def readEC(self, voltage, temperature):
		global _kvalueLow
		global _kvalueHigh
		global _kvalue
		rawEC = self.rawEC(voltage)
		valueTemp = rawEC * _kvalue
		if(valueTemp > 2.5):
			_kvalue = _kvalueHigh
		elif(valueTemp < 2.0):
			_kvalue = _kvalueLow
		value = rawEC * _kvalue
		value = value / (1.0+0.0185*(temperature-25.0))
		return value

	def calibration(self, voltage, temperature):
		if (voltage == 0.0) and (temperature == 0.0):
			return ">>Invalid sensor reading. Check wires & sensor initialization.<<"
		else:
			rawEC = self.rawEC(voltage)
			if (rawEC > 0.9 and rawEC < 1.9):
				compECsolution = 1.413*(1.0+0.0185*(temperature-25.0))
				KValueTemp = 820.0*200.0*compECsolution/1000.0/voltage
				round(KValueTemp, 2)
				#print(">>>Buffer Solution:1.413us/cm")
				f = open('ecdata.txt', 'r+')
				flist = f.readlines()
				flist[0] = 'kvalueLow=' + str(KValueTemp) + '\n'
				f = open('ecdata.txt', 'w+')
				f.writelines(flist)
				f.close()
				#print(">>>EC:1.413us/cm Calibration completed")
				return "1.413us/cm calibration completed"
			elif (rawEC > 9 and rawEC < 16.8):
				compECsolution = 12.88*(1.0+0.0185*(temperature-25.0))
				KValueTemp = 820.0*200.0*compECsolution/1000.0/voltage
				#print(">>>Buffer Solution:12.88ms/cm")
				f = open('ecdata.txt', 'r+')
				flist = f.readlines()
				flist[1] = 'kvalueHigh=' + str(KValueTemp) + '\n'
				f = open('ecdata.txt', 'w+')
				f.writelines(flist)
				f.close()
				#print(">>>EC:12.88ms/cm Calibration completed")
				return "12.88ms/cm calibration completed"
			else:
				return ">>>Buffer solution out of range. Measurement discarded<<<"
			
	def reset(self):
		_kvalueLow = 1.0
		_kvalueHigh = 1.0
		try:
			f = open('ecdata.txt', 'r+')
			flist = f.readlines()
			flist[0] = 'kvalueLow=' + str(_kvalueLow) + '\n'
			flist[1] = 'kvalueHigh=' + str(_kvalueHigh) + '\n'
			f = open('ecdata.txt', 'w+')
			f.writelines(flist)
			f.close()
			print(">>>Reset to default parameters<<<")
		except IOError:
			f = open('ecdata.txt', 'w')
			#flist=f.readlines()
			flist = 'kvalueLow=' + str(_kvalueLow) + '\n'
			flist += 'kvalueHigh=' + str(_kvalueHigh) + '\n'
			#f=open('data.txt','w+')
			f.writelines(flist)
			f.close()
			print(">>>Reset to default parameters<<<")
	

if __name__ == '__main__':
	from time import sleep
	ecSens = DFRobot_EC()
	for i in range(5):
		sleep(3)
		print(ecSens.readEC())