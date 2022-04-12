# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version

# TODO import only stuff we need from library
import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04
from lib.DS18B20 import TempReader
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
import lib.state_machine.LCDmenu as LCDmenu
from lib.state_machine import pumps

import warnings

try:
    # for testing w/o buttons. simulates button input through keyboard
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((100, 100))
except pygame.error as e:
    print("Pygame will not load headlessly")

done = False

# placeholder pin values
PINS = {"res_trig": 23, 'res_echo': 24, 'A_B': 'GPIO7',
'B_B': 'GPIO0', 'U_B': 'GPIO5', 'L_B': 'GPIO16', 'D_B': 'GPIO20', 'R_B': 'GPIO21',
'pumpM': 'GPIO13', 'pumpA': 'GPIO22', 'pumpB': 'GPIO27', 'pumpN': 'GPIO17',
'valve1': 'GPIO12', 'valve2': 'GPIO1', 'uv_filter': 'GPIO6'}

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

# initialize i2c bus to use with ADC for analog input and send communicate with LCD
i2c = busio.I2C(board.SCL, board.SDA)
with i2c:
    print("I2C addresses found:",
        [hex(device_address) for device_address in i2c.scan()])
        
try:
    LCD = LCD(I2CPCF8574Interface(board.I2C(), 0x27), num_rows=4, num_cols=20)
except OSError as e:
    warnings.warn("LCD at 0x27 not detected.")
    '''
    from os import system
    time.sleep(4)
    system("sudo shutdown -h now")
    quit()'''

try:
    ads = ADS.ADS1015(board.I2C())
    pHsens = AnalogIn(ads, ADS.P0)  # signal at pin 0
    ECsens = AnalogIn(ads, ADS.P1)  # signal at pin 1
except (OSError, ValueError, AttributeError) as e:
    print("Error connecting to ADC. Check connection and ADDR pin:", e)
    ads = "dummy"
    pHsens = "dummy"
    ECsens = "dummy"

sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'], temperature=20)  # example code, 20 C
tempSens = TempReader()

# creating instance of state machine
shrub = pumps.hydro(pumpM, sonar, valves)
condition = pumps.conditioner(condP, shrub, pHsens, ECsens, tempSens)
menu = LCDmenu.menu(LCD, shrub, condition)

# testing parameters
testing = False  # to run test procedure on startup
test2 = True  # show sensor value periodically in normal operation
if test2:
    test_timer = LCDmenu.timer(4)
    test_timer.timer_set()
print_time = 7

# initializing variables
last = time.monotonic()
button_timer = LCDmenu.timer(.25)

# shrub.state used to track what state pump/uv is in

print("Now expecting user input")
menu.idle()
button_timer.timer_set()

while (not done) and (not testing):
    if test2:
        if test_timer.timer_event():
            print(condition)
            print(shrub)
            test_timer.timer_set()
    # prevent repeat events for one press
    if button_timer.event_no_reset():
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
            button_timer.timer_set()
        try:
            # simulate button presses w/ keyboard input
            for event in pygame.event.get():
                if (event.type == pygame.QUIT):
                    done = True
                    testing = True
                    break
                elif event.type == pygame.KEYDOWN:
                    print("key is pressed")
                    if (event.key == pygame.K_w) or (event.key == pygame.K_UP):
                        menu.evt_handler(evt='U_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_s or (event.key == pygame.K_DOWN):
                        menu.evt_handler(evt='D_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_d or (event.key == pygame.K_RIGHT):
                        menu.evt_handler(evt='R_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_a or (event.key == pygame.K_LEFT):
                        menu.evt_handler(evt='L_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_q or (event.key == pygame.K_z):
                        menu.evt_handler(evt='A_B')
                        button_timer.timer_set()
                    if event.key == pygame.K_e or (event.key == pygame.K_x):
                        menu.evt_handler(evt='B_B')
                        button_timer.timer_set()
                    if (event.key == pygame.K_ESCAPE):
                        done = True
                        testing = True
                        LCD.clear()
                        print("Esc exits program. Goodbye")
                        LCD.print("Esc exits program. Goodbye")
        except Exception as e:
            pass  # headless running of pi prevents use of pygame

    # print sensor values to terminal to check operation
    if time.monotonic() - last > print_time:
        last = time.monotonic() 
        if test2:
            print(f"menu state: {menu.state}")
    
    # wait for lack of user input to set menu to idle
    if menu.idle_timer.timer_event():
        menu.evt_handler(timer=True)

    # check for pump flood drain cycle timing
    if shrub.ptimer.timer_event():
        shrub.evt_handler(ptime=True)

    # check for pump flood drain cycle timing
    if shrub.vtimer.timer_event():
        shrub.evt_handler(vtime=True)

    # if the reservoir is dangerously full, stop valves. 
    # should hopefully prevent repeat events
    if shrub.overflow_det() and (shrub.state != "NO DRAIN"):
        shrub.evt_handler(evt="OVERFLOW")
    # allow valves to open up again
    if (shrub.state == "NO DRAIN") and not shrub.overflow_det:
        shrub.evt_handler(evt="NO OVERFLOW")
        
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
            
print("Something caused the state machine to break. Exiting program")
LCD.print("Something caused the state machine to break. Exiting program")
