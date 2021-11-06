# Implement a Butterworth Low Pass Filter to interpret a semi noisy signal
# following this as reference:
# https://github.com/curiores/ArduinoTutorials/blob/main/ButterworthFilter/Design/ButterworthFilter.ipynb

import numpy as np
from scipy import signal
import math


class LowPassFilter(object):

    def __init__(self, cutoff, degree=2):
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.n = degree
        self.pi = np.pi

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

 # next step is to create some kind of small buffer system 
 # so it can read small set of data and filter then move to next buffer and repeat