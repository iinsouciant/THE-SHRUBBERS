# butterworth/filter.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement a Butterworth Low Pass Filter to interpret a semi noisy signal
# following this as reference:
# https://github.com/curiores/ArduinoTutorials/blob/main/ButterworthFilter/Design/ButterworthFilter.ipynb
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.80 06-Nov-2021 Following discretization process of curiores

import numpy as np
from scipy import signal
import math


class LowPassFilter(object):
    # second order butterworth filter

    def __init__(self, cutoff, degree=2):
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.n = degree
        self.pi = np.pi
        self.yfilt = np.zeros(3)  # second to last val -> last val -> current val
        self.y = np.zeros(3)  # second to last val -> last val -> current val

    # WIP
    def fil_coeff(self):
        # Compute the Butterworth filter coefficents
        a = np.zeros(self.n + 1)
        gamma = self.pi / (2.0 * self.n)
        a[0] = 1  # first coeff always 1
        for k in range(self.n):
            rfac = np.cos(k * gamma) / np.sin((k+1) * gamma)
            a[k+1] = rfac*a[k]  # Other coefficients by recursion

        # Adjust for cutoff frequency
        c = np.zeros(self.n + 1)
        for k in range(self.n + 1):
            c[self.n - k] = a[k] / pow(self.wc, k)
        
        return c  # coefficients are in c 
    
    def discretization(self, fs):
        denom = self.fil_coeff()
        lowPass = signal.TransferFunction(1, denom)
        dt = 1.0/fs
        discreteLowPass = lowPass.to_discrete(dt, method='gbt', alpha=0.5)
        b = discreteLowPass.num
        a = -discreteLowPass.den

    # manually pass in the last two values and buffer them with main loop?

    '''
    # Filter the signal
Nb = len(b)
yfilt = np.zeros(len(y));  where y is the original signal
for m in range(3,len(y)): prob get rid of this line to just get single val/small vector?
    yfilt[m] = b[0]*y[m];
    for i in range(1,Nb):
        yfilt[m] += a[i]*yfilt[m-i] + b[i]*y[m-i];
    would need previous and one before that value of filtered and unfiltered each
    in addition to current signal value
    '''