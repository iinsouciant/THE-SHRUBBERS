#import time
#import sys

_temperature      = 25.0
_acidVoltage      = 2032.44
_neutralVoltage   = 1500.0
class DFRobot_PH():
	
	def begin(self):
		global _acidVoltage
		global _neutralVoltage
		try:
			with open('phdata.txt', 'r') as f:
				neutralVoltageLine = f.readline()
		#		print neutralVoltageLine
				neutralVoltageLine = neutralVoltageLine.strip('neutralVoltage=')
				_neutralVoltage    = float(neutralVoltageLine)
				acidVoltageLine    = f.readline()
		#		print acidVoltageLine
				acidVoltageLine    = acidVoltageLine.strip('acidVoltage=')
				_acidVoltage       = float(acidVoltageLine)
		except IOError as e:
			if e is IOError:
				print("phdata.txt does not exist. Creating file with default settings.")
			with open('phdata.txt', 'w') as f:
				#flist=f.readlines()
				flist   ='neutralVoltage='+ str(_neutralVoltage) + '\n'
				flist  +='acidVoltage='+ str(_acidVoltage) + '\n'
				#f=open('data.txt','w+')
				f.writelines(flist)
			print(">>>Reset pH to default parameters<<<")

	def readPH(self, voltage, temperature=0):
		slope = -5.6548
		intercept = 15.509
		_phValue = slope*(voltage)+intercept
		round(_phValue, 3)
		return _phValue

	# TODO adapt ph calibration from arduino code
	def calibration(self, voltage):
		if (voltage == 0):
			return ">>Invalid sensor reading. Check wires & sensor initialization.<<"
		else:
			if (voltage > 1322 and voltage < 1678):
				print(">>>Buffer Solution:7.0")
				f=open('phdata.txt','r+')
				flist=f.readlines()
				flist[0]='neutralVoltage='+ str(voltage) + '\n'
				f=open('phdata.txt','w+')
				f.writelines(flist)
				f.close()
				print(">>>PH:7.0 Calibration completed")
				#time.sleep(2.0)
				return ">>>PH:7.0 Calibration completed"
			elif (voltage > 1854 and voltage < 2210):
				print(">>>Buffer Solution:4.0")
				f=open('phdata.txt','r+')
				flist=f.readlines()
				flist[1]='acidVoltage='+ str(voltage) + '\n'
				f=open('phdata.txt','w+')
				f.writelines(flist)
				f.close()
				print(">>>PH:4.0 Calibration completed")
				#time.sleep(2.0)
				return ">>>PH:4.0 Calibration completed"
			else:
				return ">>New calibration not translated from C++ to Python. WIP<<"
				#return ">>>Buffer solution out of range. Measurement discarded<<<"

	def reset(self):
		_acidVoltage    = 2032.44
		_neutralVoltage = 1500.0
		try:
			f=open('phdata.txt','r+')
			flist=f.readlines()
			flist[0]='neutralVoltage='+ str(_neutralVoltage) + '\n'
			flist[1]='acidVoltage='+ str(_acidVoltage) + '\n'
			f=open('phdata.txt','w+')
			f.writelines(flist)
			f.close()
			print(">>>Reset to default parameters<<<")
		except:
			f=open('phdata.txt','w')
			#flist=f.readlines()
			flist   ='neutralVoltage='+ str(_neutralVoltage) + '\n'
			flist  +='acidVoltage='+ str(_acidVoltage) + '\n'
			#f=open('data.txt','w+')
			f.writelines(flist)
			f.close()
			print(">>>Reset to default parameters<<<")

	def atlas_readPH(self,voltage):
		# read pH values using equation from Atlas Sci
		volt_val = voltage/4096 * 3.3   # get value in Volts from 12-bit ADC
		phVal = (-5.6548 * volt_val) + 15.509
		round(phVal,2)
		return(phVal)