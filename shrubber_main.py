# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version
#   v1.00 15-Feb-2022 Working version to take in a single value at a time. Only tested w/ 2nd order

import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04
import time


import numpy as np
import math

# state machine
from lib.state_machine import shrubber

# placeholder values
PINS = {"res_trig": 13, 'res_echo': 14, 'A_B': 15,
'B_B': 16, 'U_B': 17, 'L_B': 18, 'D_B': 19, 'R_B': 20,
'pump': 23, 'display?': 26}

pump = GZ.PWMLED(PINS['pump'])
buttons = []  # list of button instances
for k, v in PINS.items():
    if k[1:3] == '_B':
        buttons.append(GZ.Button(v))
# TODO LCD output for state machine
LCD = "filler"


'''
sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'], temperature=20)  # example code, 20 C

# gives cm, default sample size is 11 readings
raw_measurement = sonarM.raw_distance()  # can lower it by `sample_wait` and filter it with low pass
# could also used `sonarM.basic_distance(...)`
# can then use the height to calc water volume

# alternatively if we know initial hole depth we can use this method instead
hole_depth1 = 100  # cm
liquid_depth1 = sonarM.depth(raw_measurement, hole_depth1)
'''

# example PWM use via GPIO Zero
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

'''
we could try and approximate flow rate
for both the reservoirs to monitor when the filtration needs to be swapped?
approx derivative with backwards differencing?
I've only seen pressure drop as an indicator, not flow rate tho
'''

def error(err_string):
    raise Exception(err_string)

# potentially useful function for pump control
def pump_pwm(level, pump):  # input is range of percents, 0 to 100
    pump.value = float(level / 100)


# testing parameters
testing = True  # to show state
testing2 = True  # to determine if we run beginning test q's
print_time = .5

# initializing variables
last = time.monotonic()
s_thold = 25  # in cm

# creating instance of state machine
shrub = shrubber(pump, pHsens, ECsens, buttons, sonar, LCD)

# will need to alter inital starting method since we prob won't have a keyboard for input
# shrub.state used t otrack what state it is in
# shrub.go can be used as a parameter to change between certain methods
# might be able to condense that to just a parameter in event handler
while True: 
    # TODO update this. can we make this into a group of states?
    UV_test1 = None
    while testing2:  # for running test procedure with some input
        shrub.test_print()
        time.sleep(print_time)
        if shrub.test_q != "SKIP":
            shrub.test_q = input("Test pumps? \nY or N ")
            shrub.test_q = shrub.test_q.upper()
            if (shrub.test_q == "END"):
                testing2 = False
                break
            if UV_test1 != "SKIP":
                UV_test0 = input("Test UV? \nY or N ")
                UV_test1 = UV_test0.upper()
                if UV_test1 == "SKIP":
                    continue  # TODO UV test function
                if (UV_test1 == "END"):
                    break
                elif UV_test1 == "Y":
                    duration = float(input("How long?\n"))
                    state_machine.pump_test(pump, duration)

    # loop to run once diagnosis is done
    while not testing2:
        if testing:
            if time.monotonic() - last > print_time:
                last = time.monotonic() 
                if testing2:
                    shrub.test_print()

        # TODO update this
        if shrub.state == "IDLE":
            shrub.forward(speed=0)
            if start_button:  # some trigger to start the system
                shrub.evt_handler(None, ignite=start_button)
            start_button = False
        # TODO update this
        if shrub.state != "IDLE":
            if shrub.timer_time is None:  # timer acts independently and does not use locate -> doesn't change state
                shrub.timer_set()
            shrub.timer_event()
        # TODO update this
        if shrub.state == "FORWARD":
            shrub.forward()
            distL, distF, distR = shrub.grab_sonar()
            if (distR <= s_thold) and (distF <= s_thold):
                continue
            if start_button:  # only used by bluetooth
                shrub.evt_handler(None, ignite=start_button)
                start_button = False
        # TODO update this
        if shrub.state == "TURN":
            shrub.turn(shrub.go)
            distL, distF, distR = shrub.grab_sonar()
            if (distF >= s_thold) and (shrub.cliff_det() is False):
                shrub.evt_handler()
            elif start_button:  # only used by bluetooth
                shrub.evt_handler(None, ignite=start_button)
                start_button = False
