# butterworth/b_filter.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement a Butterworth Low Pass Filter to interpret a semi noisy signal
# following this as reference:
# https://github.com/curiores/ArduinoTutorials/blob/main/ButterworthFilter/Design/ButterworthFilter.ipynb
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.80 06-Nov-2021 Following discretization process of curiores
#   v0.99 28-Nov-2021 First draft implementation of filter
#   v1.00 15-Feb-2022 Working version to take in a single value at a time. Only tested w/ 2nd order

import numpy as np
from scipy import signal


class LowPassFilter(object):
    '''Creates a low pass filter on initialization for different sensors.
    Use filter(sensor_value) to utilize the low pass filter.
    recalc() will allow you to modify your instance of the filter. '''

    # will want to fine tune sample frequency default value depending on loop time of program
    def __init__(self, cutoff, sample_frequency=500, degree=2):
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.sf = sample_frequency
        self.n = degree
        self.recalc(self.sf)

    def __fil_coeff(self):
        # Compute the Butterworth filter coefficents
        a = np.zeros(self.n + 1)
        gamma = np.pi / (2.0 * self.n)
        a[0] = 1  # first coeff always 1
        for k in range(self.n):
            rfac = np.cos(k * gamma) / np.sin((k+1) * gamma)
            a[k+1] = rfac*a[k] 

        # Adjust for cutoff frequency
        B = np.zeros(self.n + 1)
        for k in range(self.n + 1):
            B[self.n - k] = a[k] / pow(self.wc, k)
            return B
        # coefficients stored in b 
    
    def __discretization(self, B):
        denom = B
        lowPass = signal.TransferFunction(1, denom)
        dt = 1.0/self.sf
        discreteLowPass = lowPass.to_discrete(dt, method='gbt', alpha=0.5)
        self.num = discreteLowPass.num
        self.den = -discreteLowPass.den
    
    def recalc(self, sampling_freq, cutoff):
        '''Calculate the discretized coefficients by providing
         a new sampling frequency and cutoff frequency'''
        self.sf = sampling_freq
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.__discretization(self.__fil_coeff())
        print("Coefficients calculated!")

    def filter(self, s_val):
        '''Pass in your new sensor value to return the next filtered value.'''
        Nb = len(self.num)
        # check if we have prior values to pass into filter
        try:
            self.f_vals
        except AttributeError:
            self.f_vals = [0]*self.n
            self.s_vals = [0]*self.n
        
        # use coeffs and prior discrete values to get new filtered value
        filt_new = self.num[0]*s_val
        for f, y, a, b in zip(reversed(self.f_vals), reversed(self.s_vals), self.den[1:], self.num[1:]):
            filt_new += a*f + b*y
    
        # maintain list length n-long
        self.f_vals.append(filt_new)
        self.s_vals.append(s_val)
        self.f_vals.pop(0)
        self.s_vals.pop(0)

        return filt_new
        

# run this to test 
if __name__ == "__main__":
    import math
    import matplotlib.pyplot as plt

    plt.rcParams["figure.figsize"] = 10, 5
    plt.rcParams["font.size"] = 16
    plt.rcParams.update({"text.usetex": True, "font.family": "sans-serif", 
    "font.sans-serif": ["Helvetica"]})
    
    # Generate a signal
    samplingFreq = 1000   # sampled at 1 kHz = 1000 samples / second
    tlims = [0, 1]        # in seconds
    signalFreq = [2, 50]  # Cycles / second
    signalMag = [1, 0.2]  # magnitude of each sine
    t = np.linspace(tlims[0], tlims[1], (tlims[1]-tlims[0])*samplingFreq)
    y = signalMag[0]*np.sin(2*math.pi*signalFreq[0]*t) + signalMag[1]*np.sin(2*math.pi*signalFreq[1]*t)
    test = LowPassFilter(5, samplingFreq)
    yf = np.zeros(len(t))
    for i in range(len(t)):
        if i == 0:
            print("First calc starting!")
        if i == 1:
            print("First calc over!")
        yf[i] = test.filter(y[i])
    # View the result
    # Plot the signal
    plt.figure()
    plt.plot(t, y)
    plt.plot(t, yf)
    plt.ylabel("$y(t)$")
    plt.xlim([min(t), max(t)])
    plt.show(block=True)