# butterworth/filter.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement a Butterworth Low Pass Filter to interpret a semi noisy signal
# following this as reference:
# https://github.com/curiores/ArduinoTutorials/blob/main/ButterworthFilter/Design/ButterworthFilter.ipynb
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.80 06-Nov-2021 Following discretization process of curiores
#   v0.99 28-Nov-2021 First draft implementation of filter

import numpy as np
from scipy import signal
import math


class LowPassFilter(object):
    # second order butterworth filter

    def __init__(self, cutoff, signal_frequency, degree=2):
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.fs = signal_frequency
        self.n = degree
        self.pi = np.pi
        self.yfilt = np.zeros(self.n+1)  # second to last val -> last val -> current val
        self.fil_coeff()
        self.discretization()

    def __fil_coeff(self):
        # Compute the Butterworth filter coefficents
        a = np.zeros(self.n + 1)
        gamma = self.pi / (2.0 * self.n)
        a[0] = 1  # first coeff always 1
        for k in range(self.n):
            rfac = np.cos(k * gamma) / np.sin((k+1) * gamma)
            a[k+1] = rfac*a[k]  # Other coefficients by recursion

        # Adjust for cutoff frequency
        self.c = np.zeros(self.n + 1)
        for k in range(self.n + 1):
            self.c[self.n - k] = a[k] / pow(self.wc, k)
        # coefficients are in c 
    
    def __discretization(self):
        denom = self.c
        lowPass = signal.TransferFunction(1, denom)
        dt = 1.0/self.fs
        discreteLowPass = lowPass.to_discrete(dt, method='gbt', alpha=0.5)
        self.b = discreteLowPass.num
        self.a = -discreteLowPass.den

    def filter(self, s_vals, fs):  # need to pass in signal frequency and list of 3 sensor vals
        Nb = len(self.b)  # 2nd degree so 3 long?
        filt_val = self.b[0]*s_vals[-1]
        for i in range(1, Nb):
            filt_val += self.a[i]*self.yfilt[self.n+1-i] + self.b[i]*s_vals[self.n+1-i]

        for i in range(1, len(self.yfilt)-1):  # moving the values back one so we limit the size of the vals stored
            self.yfilt[i] = self.yfilt[i+1]
        self.yfilt[-1] = filt_val

        return filt_val          
