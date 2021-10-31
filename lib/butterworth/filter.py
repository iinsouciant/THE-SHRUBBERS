# Implement a Butterworth Low Pass Filter to interpret a semi noisy signal
# following this as reference:
# https://github.com/curiores/ArduinoTutorials/blob/main/ButterworthFilter/Design/ButterworthFilter.ipynb

import numpy as np
import math


class LowPassFilter(object):

    def __init__(self, cutoff, degree=2):
        self.wc = 2*np.pi*cutoff  # cutoff frequency (rad/s)
        self.n = degree
        self.pi = np.pi

    # WIP
    def fil_coeff(self):
        # Compute the Butterworth filter coefficents
        a = np.zeros(self.n+1)
        gamma = self.pi/(2.0*self.n)
        a[0] = 1  # first coef is always 1
        for k in range(0, self.n):
            rfac = np.cos(k*gamma)/np.sin((k+1)*gamma)
            a[k+1] = rfac*a[k]  # Other coefficients by recursion

        print("Butterworth polynomial coefficients a_i:                " + str(a))

        # Adjust the cutoff frequency
        c = np.zeros(self.n+1)
        for k in range(0, self.n+1):
            c[self.n-k] = a[k]/pow(self.wc, k)

        print("Butterworth coefficients with frequency adjustment c_i: " + str(c))