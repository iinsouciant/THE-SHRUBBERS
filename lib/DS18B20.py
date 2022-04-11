# Slightly modified version from adafruit website&forums
# https://cdn-learn.adafruit.com/downloads/pdf/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing.pdf
# https://forums.raspberrypi.com/viewtopic.php?t=35508
import os
import glob
from time import sleep

class TempReader(object):
    '''Raspberry pi module to use 1-Wire interface to read
    temperature from a DS18B20. Ensure the 1-Wire interface is enabled 
    in the RPi configuration settings. temp_sensor_pin should always be 28'''
    def __init__(self, temp_sensor_pin=28):
        os.system('/sbin/modprobe w1-therm')
 
        self.temp_sensor_pin = temp_sensor_pin
        self.base_dir = '/sys/bus/w1/devices/'
        try:
            self.device_folder = glob.glob(
                self.base_dir + '28*')[0]
            #print(glob.glob(self.base_dir + '28*'))
        except AttributeError:
            raise Exception("The temperature sensor is undetected.")
        self.device_file = self.device_folder + '/w1_slave'

    def read_temp_raw(self):
        f = open(self.device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

    def read_temp(self):
        ''' Gives dictionary of Celsius and Farenheit reading'''
        lines = self.read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
            sleep(0.1)
            lines = self.read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string)/1000.0
            temp_f = (temp_c * 9.0/5.0) + 32.0
        tempdict = {
            'temp_c': temp_c,
            'temp_f': temp_f
        }
        return tempdict
    
if __name__ == '__main__':
    tempSens = TempReader()
    for i in range(5):
        tempSens.read_temp()
        sleep(5)
