# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version

# TODO import only stuff we need from library
import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04
from lib.lcd.lcd import LCD
from lib.lcd.i2c_pcf8574_interface import I2CPCF8574Interface

from lib.lcd.lcd import CursorMode

import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

import numpy as np
import math
import time

# state machine
from lib.state_machine import shrubber


import pygame
pygame.init()
screen = pygame.display.set_mode((400,400))

done = False

# placeholder pin values
PINS = {"res_trig": 'GPIO23', 'res_echo': 'GPIO24', 'A_B': 'GPIO18',
'B_B': 'GPIO27', 'U_B': 'GPIO17', 'L_B': 'GPIO22', 'D_B': 'GPIO25', 'R_B': 'GPIO5',
'pumpM': 'GPIO13', 'pumpA': 'GPIO12', 'pumpB': 'GPIO16', 'pumpN': 'GPIO26',
'valve1': 'GPIO20', 'valve2': 'GPIO21'}

pumpM = GZ.PWMLED(PINS['pumpM'])
pumpA = GZ.LED(PINS['pumpA'])
pumpB = GZ.LED(PINS['pumpB'])
pumpN = GZ.LED(PINS['pumpN'])
condP = [pumpA, pumpB, pumpN]           

buttons = []  # list of button instances
for k, v in PINS.items():
    if k[1:3] == '_B':
        buttons.append(GZ.Button(v))

valves = [GZ.LED(PINS['valve1']), GZ.LED(PINS['valve2'])]

i2c = busio.I2C(board.SCL, board.SDA)

with i2c:
    print("I2C addresses found:",
        [hex(device_address) for device_address in i2c.scan()])

try:
    ads = ADS.ADS1015(i2c)
    pHsens = AnalogIn(ads, ADS.P0)  # signal at pin 0
    ECsens = AnalogIn(ads, ADS.P1)  # signal at pin 1
    tempSens = AnalogIn(ads, ADS.P2)  # signal at pin 2
except (OSError, ValueError, AttributeError) as e:
    print("Error connecting to ADC. Check connection and ADDR pin:", e)
    ads = "dummy"
    pHsens = "dummy"
    ECsens = "dummy"
    tempSens = "dummy"

LCD = LCD(I2CPCF8574Interface(board.I2C(), 0x27), num_rows=4, num_cols=20)

sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'], temperature=20)  # example code, 20 C

# creating instance of state machine
shrub = shrubber.hydro(pumpM, pHsens, ECsens, buttons, sonar, LCD, valves, tempSens)
menu = shrubber.menu(LCD, shrub)

# testing parameters
testing = False  # to run test procedure on startup
test2 = False  # show sensor value periodically in normal operation
print_time = 7

# initializing variables
last = time.monotonic()

# will need to alter inital starting method for no keyboard/mouse
# shrub.state used to track what state pump/uv is in
while True: 
    # TODO update this. can we make this into a group of states?
    UV_test1 = None
    while testing:  # for running test procedure with some input
        if shrub.test_q != "SKIP":
            shrub.test_q = input("Test pumps? \nY or N ")
            shrub.test_q = shrub.test_q.upper()
            if (shrub.test_q == "END"):
                testing = False
                break
            if UV_test1 != "SKIP":
                UV_test0 = input("Test UV? \nY or N ")
                UV_test1 = UV_test0.upper()
                if UV_test1 == "SKIP":
                    continue  # TODO UV test function
                if (UV_test1 == "END"):
                    testing = False
                    break
                elif UV_test1 == "Y":
                    duration = float(input("How long?\n"))
                    shrub.pump_test(duration)
        elif (shrub.test_q == UV_test1):
            testing = False
            break

    # loop to run once diagnosis is done
    print("Now expecting user input")
    menu.idle()
    button_timer = shrubber.timer(.5)
    button_timer.timer_set()
    while not done:
        if button_timer.event_no_reset():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
                    break
                elif event.type == pygame.KEYDOWN:
                    print("key is pressed")
                    if event.key == pygame.K_w:
                        menu.evt_handler(evt='U_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_s:
                        menu.evt_handler(evt='D_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_d:
                        menu.evt_handler(evt='R_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_a:
                        menu.evt_handler(evt='L_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_q:
                        menu.evt_handler(evt='A_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_e:
                        menu.evt_handler(evt='B_B')
                        button_timer.timer_set()
    #while not testing:
        # print sensor values to terminal to check operation
        if time.monotonic() - last > print_time:
            last = time.monotonic() 
            if test2:
                print(shrub)
        
        '''# prevent repeat presses
        if button_timer.timer_event():
            # detect user input
            if buttons[0].is_pressed:
                menu.evt_handler(evt='A_B')
                button_timer.timer_set()
            if buttons[1].is_pressed:
                menu.evt_handler(evt='B_B')
                button_timer.timer_set()
            if buttons[2].is_pressed:
                menu.evt_handler(evt='U_B')
                button_timer.timer_set()
            if buttons[3].is_pressed:
                menu.evt_handler(evt='L_B')
                button_timer.timer_set()
            if buttons[4].is_pressed:
                menu.evt_handler(evt='D_B')
                button_timer.timer_set()
            if buttons[5].is_pressed:
                menu.evt_handler(evt='R_B')
                button_timer.timer_set()'''
        
        # wait for lack of user input to set menu to idle
        if menu.idle_timer.timer_event():
            menu.evt_handler(timer=True)

        # TODO update this to work with valve and pump timer
        if shrub.ptimer.timer_event():
            shrub.evt_handler(ptime=True)
            
        if menu.state == "IDLE" and menu.idle_printer.timer_event():
            menu.idle_print()

        # Show cursor position as a line when changing params
        if type(menu.parent) is int:
            if menu.parent <= 3:
                LCD.set_cursor_mode(CursorMode.LINE)
                menu.LCD.set_cursor_pos(1, menu.m2_hover)
        elif (menu.parent == 'pH THRESH') or (menu.parent == 'EC THRESH'):
            LCD.set_cursor_mode(CursorMode.LINE)
            menu.LCD.set_cursor_pos(1, menu.m2_hover)

        else:
            LCD.set_cursor_mode(CursorMode.HIDE)
                
