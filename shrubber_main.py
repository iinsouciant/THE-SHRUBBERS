# shrubber_main.py - ME 106 GOOMBA Project Code
# nRF52840 Feathersense microcontroller. no TriplerBaseBoard.
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project

import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04
import time

# Butterowrth lowpass filter
import numpy as np
import math

R1_trig_pin = 13  # placeholder value
R1_echo_pin = 14  # placeholder value

R3_trig_pin = 15  # placeholder value
R3_echo_pin = 16  # placeholder value
'''
sonar1 = hcsr04.Measurement(R1_trig_pin, R1_echo_pin, temperature=20)  # example code, 20 C

# gives cm, default sample size is 11 readings
raw_measurement = sonar1.raw_distance()  # can lower it by `sample_wait` and filter it with low pass
# could also used `sonar1.basic_distance(...)`
# can then use the height to calc water volume

# alternatively if we know initial hole depth we can use this method instead
hole_depth1 = 100  # cm
liquid_depth1 = sonar1.depth(raw_measurement, hole_depth1)
'''

# PWM use via GPIO Zero
led = GZ.PWMLED(2)

last_t = 0
dt = 0.05
dim = 0
dm = 1
end = False
while end is not True:
    if (time.monotonic() > (last_t + dt)) and (dim < 100):
        led.value = dim/100
        dim += dm
        last_t = time.monotonic()

    elif (time.monotonic() > (last_t + dt)) and (dim >= 100):
        last_t = time.monotonic()
        print("Script terminated")
        end = True

    else:
        a = dim  # do stuff here

# note that in the case of program crash, raise exception so clean up pin state

# we could try and approximate flow rate
# for both the reservoirs to monitor when the filtration needs to be swapped?
# approx derivative withbackwards differencing?