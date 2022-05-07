# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version
#   v0.85 13-Apr-2022 Included libraries for all sensors, final pin assignments, keyboard input option,
#                     input and output instances, error handling in case of sensor not workingm

# TODO automate run on boot with pkg install script
# https://www.tomshardware.com/how-to/run-script-at-boot-raspberry-pi

from gpiozero import Button, PWMLED, LED
from lib.hcsr04sensor import sensor as hcsr04
from lib.DS18B20 import TempReader
from lib.lcd.lcd import LCD
from lib.lcd.i2c_pcf8574_interface import I2CPCF8574Interface
from lib.lcd.lcd import CursorMode


from board import SCL, SDA, I2C
from busio import I2C as IIC
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


# state machine
import lib.state_machine.LCDmenu as LCDmenu
from lib.state_machine import pumps

# import numpy as np
# import math
from time import sleep, time
from os import system

try:
    # for testing w/o buttons. simulates button input through keyboard
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((100, 100))
except pygame.error as e:
    print("Pygame has not been loaded as it does not work w/o a monitor.")

# Button wire colors: 
# Blue is a or down, yellow is b, white is up or left, green is right
# pumpm/uv is green/black solid, valve 1 is yellow/red stranded, valve 2 is blue/red solid
# pumpN is white, pumpB is green, pumpA is blue
PINS = {"res_trig": 23, 'res_echo': 24, 'A_B': 'GPIO20',
'B_B': 'GPIO0', 'L_B': 'GPIO5', 'U_B': 'GPIO21', 'D_B': 'GPIO25', 'R_B': 'GPIO16',
'pumpM': 'GPIO13', 'pumpA': 'GPIO22', 'pumpB': 'GPIO27', 'pumpN': 'GPIO17',
'valve1': 'GPIO12', 'valve2': 'GPIO1', 'uv_filter': 'GPIO6'}

pumpM = PWMLED(PINS['pumpM'])
pumpA = LED(PINS['pumpA'])
pumpB = LED(PINS['pumpB'])
pumpN = LED(PINS['pumpN'])
condP = [pumpA, pumpB, pumpN]  
UV = LED(PINS['uv_filter'])         

buttons = [Button(v) for k, v in PINS.items() if k[1:3] == '_B']
valves = [LED(PINS['valve1']), LED(PINS['valve2'])]

# testing parameters
test2 = False  # show sensor value periodically in normal operation
if test2:
    test_timer = LCDmenu.timer(4)
    test_timer.timer_set()
    i2c = IIC(SCL, SDA)
    with i2c:
        print("I2C addresses found:",
            [hex(device_address) for device_address in i2c.scan()])   
print_time = 7
# initialize i2c bus to use with ADC for analog input and send communicate with LCD   
try:
    LCD = LCD(I2CPCF8574Interface(I2C(), 0x27), num_rows=4, num_cols=20)
except (OSError, ValueError, AttributeError) as e:
    print("LCD at 0x27 not detected.")
    '''
    from os import system
    sleep(4)
    system("sudo reboot")
    quit()'''
    LCD = LCDmenu.LCDdummy()

try:
    ads = ADS.ADS1015(I2C())
    pHsens = AnalogIn(ads, ADS.P0)  # signal at pin 0
    ECsens = AnalogIn(ads, ADS.P1)  # signal at pin 1
except (OSError, ValueError, AttributeError) as e:
    print("Error connecting to ADC. Check connection and ADDR pin:", e)
    ads = "dummy"
    pHsens = "dummy"
    ECsens = "dummy"

sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'])

try:
    tempSens = TempReader()
except IndexError as e:
    #print("1-Wire connection is bad.\
    #    Try checkng connection. Attempting reboot to fix.")
    print(e)
    LCD.print(
        "1-Wire connection is bad. Try checkng connection. " +
        "Attempting reboot to fix."
    )
    sleep(5)
    #system("sudo reboot")
    # TODO output file to document this for better troubleshooting
    tempSens = "dummy instance"


# creating instance of state machine
shrub = pumps.hydro(pumpM, sonar, valves, UV, test=test2)
condition = pumps.conditioner(condP, shrub, pHsens, ECsens, tempSens, test=test2)
shrub.conditioner = condition
menu = LCDmenu.menu(LCD, shrub, condition, test=test2)

# initializing variables
button_timer = LCDmenu.timer(.15)

# shrub.state used to track what state pump/uv is in

print("Now expecting user input")
menu.idle()
button_timer.timer_set()

done = False

# TODO when finished, reduce loop time for easier user input
try:
    while (not done):
        
        if test2:
            a = str(condition)
            b = str(shrub)
            if test_timer.timer_event():
                print(a)
                print(b)
                test_timer.timer_set()
        
        # prevent repeat events for one press
        if button_timer.event_no_reset():
            # press A and B to turn on all outputs for a short period
            if buttons[0].is_pressed and buttons[1].is_pressed:
                menu.evt_handler(evt="TEST")
                button_timer.timer_set()
            # detect user input
            elif buttons[0].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='A_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            elif buttons[1].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='B_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            elif buttons[2].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='L_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            elif buttons[3].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='R_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            elif buttons[4].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='D_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            elif buttons[5].is_pressed:
                #start_time = time()
                menu.evt_handler(evt='U_B')
                button_timer.timer_set()
                #print(f'Execution time of menu event handler: {time()-start_time}')
            '''try:
                # simulate button presses w/ keyboard input
                for event in pygame.event.get():
                    if (event.type == pygame.QUIT):
                        done = True
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
                            LCD.clear()
                            print("Esc exits program. Goodbye")
                            LCD.print("Esc exits program. Goodbye")
            except Exception as e:
                pass  # headless running of pi prevents use of pygame'''
        
        # wait for lack of user input to set menu to idle
        if menu.idle_timer.timer_event():
            menu.evt_handler(timer=True)

        # check for pump flood drain cycle timing
        if shrub.hydroTimer.timer_event():
            shrub.evt_handler(evt='TIME')

        # check for pump flood drain cycle timing
        if condition.on_timer.timer_event():
            shrub.evt_handler(evt='ON TIMER')
        
        #start_time = time()
        # grab all sensor values to pass to butterworth filter with higher frequency
        temp = condition.sensOutOfRange()
        if condition.wait_timer.event_no_reset():
            # timer is reset in event handler as long as the pumps are not being paused
            for event in temp:
                if event is not None:
                    condition.evt_handler(evt=event)
        #print(f'Execution time of sensor checks: {time()-start_time}')

        # use sonar to see if the reservoir is dangerously full, stop valves. 
        # should hopefully prevent repeat events
        test_overflow = shrub.overflow_det()
        if test_overflow and (shrub.overflowCondition != "OVERFLOW"):
            shrub.evt_handler(evt="OVERFLOW")
            condition.evt_handler(evt="OVERFLOW")
        # allow valves to open up again
        elif (shrub.overflowCondition == "OVERFLOW") and (not test_overflow):
            shrub.evt_handler(evt="NO OVERFLOW")
            condition.evt_handler(evt="NO OVERFLOW")
            
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
    LCD.print("Something caused the state machine to break. Exiting program and rebooting")
    sleep(4)
    # TODO insert save all settings, states, and timer values to file before reboot
    system("sudo reboot")
except Exception as e:
    LCD.print(f'Fatal error: {e}')
    sleep(4)
    # TODO insert save all settings, states, and timer values to file before reboot
    #system("sudo reboot")