# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version

# TODO import only stuff we need from library
import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04

import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

import numpy as np
import math
import time

# state machine
from lib.state_machine import shrubber

# placeholder pin values
PINS = {"res_trig": 17, 'res_echo': 27, 'A_B': 5,
'B_B': 6, 'U_B': 0, 'L_B': 26, 'D_B': 19, 'R_B': 16,
'pump': 13}

pump = GZ.PWMLED(PINS['pump'])
buttons = []  # list of button instances
for k, v in PINS.items():
    if k[1:3] == '_B':
        buttons.append(GZ.Button(v))

# TODO LCD output for state machine with i2c

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1015(i2c)
pHsens = AnalogIn(ads, ADS.P0)  # signal at pin 0
ECsens = AnalogIn(ads, ADS.P1)  # signal at pin 1

sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'], temperature=20)  # example code, 20 C

class LCDdummy():
    '''Dummy LCD class to handle methods before incorporating real LCD library. Use for testing/troubleshooting only.'''
    def __init__(self):
        print("LCD test instance created.")
    
    def display(self, stuff):
        '''Handle string, list, tuple, int, and float inputs to put them on LCD'''
        if (type(stuff) is list) or (type(stuff) is tuple):
            for ele in stuff:
                print(ele)
        elif type(stuff) is str:
            print(stuff)
        elif (type(stuff) is int) or (type(stuff) is float):
            stuff = str(stuff)
            print(stuff)
        else:
            raise Exception("Not a valid input to display")
    
    def idle(self):
        print("Idle Mode: Want to user timer and cache system to continually show new sensor data")
    
LCD = LCDdummy()
# creating instance of state machine
shrub = shrubber.hydro(pump, pHsens, ECsens, buttons, sonar, LCD)
menu = shrubber.menu(buttons, LCD, shrub)

# testing parameters
testing = True  # to run test procedure on startup
print_time = .5

# initializing variables
last = time.monotonic()


# will need to alter inital starting method for no keyboard/mouse
# shrub.state used to track what state pump/uv is in

while True: 
    # TODO update this. can we make this into a group of states?
    UV_test1 = None
    while testing:  # for running test procedure with some input
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
                    shrubber.state_machine.pump_test(pump, duration)

    # loop to run once diagnosis is done
    while not testing2:
        if testing:
            if time.monotonic() - last > print_time:
                last = time.monotonic() 
                if testing2:
                    shrub.test_print()

        # TODO update this to incorporate menu system
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
        if menu.state != "IDLE":
            if menu.timer_time is None:  # timer acts independently and does not use locate -> doesn't change state
                menu.timer_set()
            menu.timer_event()
        # TODO update this
        if shrub.state == "FORWARD":
            shrub.forward()
            distL, distF, distR = shrub.grab_sonar()
            if (distR <= menu.sT) and (distF <= menu.sT):
                continue
            if start_button:  # only used by bluetooth
                shrub.evt_handler(None, ignite=start_button)
                start_button = False
        # TODO update this
        if shrub.state == "TURN":
            shrub.turn(shrub.go)
            distL, distF, distR = shrub.grab_sonar()
            if (distF >= menu.sT) and (shrub.cliff_det() is False):
                shrub.evt_handler()
            elif start_button:  # only used by bluetooth
                shrub.evt_handler(None, ignite=start_button)
                start_button = False
