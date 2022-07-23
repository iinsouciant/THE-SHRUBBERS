#! /bin/python
# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version
#   v0.85 13-Apr-2022 Included libraries for all sensors, final pin assignments, keyboard input option,
#                     input and output instances, error handling in case of sensor not workingm

'''
Ways to run the program:
    python3 autoupdate.py
    python3 shrubber_main.py
    python3 shrubber_main.py --test
'''

from time import sleep, localtime
from os import system
from os.path import abspath, exists, dirname
import argparse

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

# log file directory
log_path = dirname(dirname(abspath(__file__)))
now = localtime()
output_file = f'{log_path}/shrubber_out_{now[0]}_{now[1]}_{now[2]}_{now[3]}-{now[4]}.txt'

# prevent overwriting previous file
file_exists = exists(abspath(output_file))
file_n = 1
while file_exists:
    output_file = f'{log_path}/shrubber_out_{now[0]}_{now[1]}_{now[2]}_{now[3]}-{now[4]}_{file_n}.txt'
    file_n += 1
    file_exists = exists(abspath(output_file))

# create file
with open(output_file, 'w') as f:
    pass

def printf(msgs, terminal=False):
    '''Save output to terminal to text file'''
    if (type(msgs) is str) or (type(msgs).__str__ is object.__str__):
        with open(output_file, 'a') as f:
            print(msgs, file=f)
        if terminal:
            print(msgs)
    else:
        for msg in msgs:
            with open(output_file, 'a') as f:
                print(msg, file=f)
            if terminal:
                print(msg)

# testing parameters
parser = argparse.ArgumentParser(description='Modify startup conditions of the program')
parser.add_argument('--test', required=False,default=False, type=bool, help='Print sensors and events')
parser.add_argument('--pygame', required=False,default=False, type=bool, help='Simulate LCD menu presses with mouse and keyboard')
parser.add_argument('--done', required=False,default=False, type=bool, help='do not run loop')
args = parser.parse_args()

if args.pygame:
    # for testing w/o buttons. simulates button input through keyboard
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((100, 100))
        no = 'yes'
    except pygame.error as e:
        printf("Pygame has not been loaded as it does not work w/o a monitor.")

if args.test:
    test_timer = LCDmenu.timer(4)
    test_timer.timer_set()
    i2c = IIC(SCL, SDA)
    with i2c:
        printf(["I2C addresses found:",
            [hex(device_address) for device_address in i2c.scan()]])   
print_time = 7

# Button wire colors: 
# Blue is a or down, yellow is b, white is up or left, green is right
# pumpm/uv is green/black solid, valve 1 is yellow/red stranded, valve 2 is blue/red solid
# pumpN is white, pumpB is green, pumpA is blue
PINS = {"res_trig": 23, 'res_echo': 24, 'A_B': 'GPIO20',
'B_B': 'GPIO0', 'L_B': 'GPIO21', 'U_B': 'GPIO5', 'D_B': 'GPIO25', 'R_B': 'GPIO16',
'pumpM': 'GPIO13', 'pumpA': 'GPIO22', 'pumpB': 'GPIO27', 'pumpN': 'GPIO17',
'valve1': 'GPIO12', 'valve2': 'GPIO1', 'uv_filter': 'GPIO6'}

pumpM = PWMLED(PINS['pumpM'])
pumpA = LED(PINS['pumpA'])
pumpB = LED(PINS['pumpB'])
pumpN = LED(PINS['pumpN'])
condP = [pumpA, pumpB, pumpN]  
UV = LED(PINS['uv_filter'])         

buttons = {k: Button(v) for k, v in PINS.items() if k[1:3] == '_B'}
valves = [LED(PINS['valve1']), LED(PINS['valve2'])]

# initialize i2c bus to use with  LCD   
try:
    LCD = LCD(I2CPCF8574Interface(I2C(), 0x27), num_rows=4, num_cols=20)
except (OSError, ValueError, AttributeError) as e:
    printf("LCD at 0x27 not detected.")
    LCD = LCDmenu.LCDdummy()

# connect to ADC through I2C bus
try:
    ads = ADS.ADS1015(I2C())
    pHsens = AnalogIn(ads, ADS.P0)  # signal at pin 0
    ECsens = AnalogIn(ads, ADS.P1)  # signal at pin 1
except (OSError, ValueError, AttributeError) as e:
    printf(["Error connecting to ADC. Check connection and ADDR pin:", e])
    ads = "dummy"
    pHsens = "dummy"
    ECsens = "dummy"

# create sonar sensor instance
sonar = hcsr04.Measurement(PINS['res_trig'], PINS['res_echo'])

# check temp sensor connecton
try:
    tempSens = TempReader()
except IndexError as e:
    printf(["1-Wire connection is bad.\
        Try checkng connection. Attempting reboot to fix.", e])
    LCD.print(
        "1-Wire connection is bad. Try checkng connection. "
    )
    sleep(5)
    tempSens = "dummy instance"


# creating instance of state machines
shrub = pumps.hydro(pumpM, sonar, valves, UV, test=args.test, output=output_file)
condition = pumps.conditioner(condP, shrub, pHsens, ECsens, tempSens, test=args.test, output=output_file)
# pass in instance of conditioner to have them communicate
shrub.conditioner = condition
menu = LCDmenu.menu(LCD, shrub, condition, test=args.test, output=output_file)

# timer to wait between accepting button presses to prevent repeats
button_timer = LCDmenu.timer(.175)
# timer to automatically save pump cycle timings to file
saveCycleTime = LCDmenu.timer(60*1)

printf("Now expecting user input")
menu.idle()
button_timer.timer_set()
saveCycleTime.timer_set()

done = args.done

for _ in range(5):
    # TODO when finished, reduce loop time for easier user input
    try:
        while (not done):
            
            if args.test:
                a = str(condition)
                b = str(shrub)
                if test_timer.timer_event():
                    printf(a)
                    printf(b)
                    test_timer.timer_set()
            
            # prevent repeat events for one press
            if button_timer.event_no_reset():
                # press A and B to turn on all outputs for a short period
                if buttons['A_B'].is_pressed and buttons['B_B'].is_pressed:
                    menu.evt_handler(evt="TEST")
                    button_timer.timer_set()
                # detect user input
                elif buttons['A_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='A_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                elif buttons['B_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='B_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                elif buttons['L_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='L_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                elif buttons['R_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='R_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                elif buttons['D_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='D_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                elif buttons['U_B'].is_pressed:
                    #start_time = time()
                    menu.evt_handler(evt='U_B')
                    button_timer.timer_set()
                    #print(f'Execution time of menu event handler: {time()-start_time}')
                if args.pygame:
                    try:
                        # simulate button presses w/ keyboard input
                        for event in pygame.event.get():
                            if (event.type == pygame.QUIT):
                                done = True
                                break
                            elif event.type == pygame.KEYDOWN:
                                printf("key is pressed")
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
                                    printf("Esc exits program. Goodbye")
                                    LCD.print("Esc exits program. Goodbye")
                    except Exception as e:
                        pass  # headless running of pi prevents use of pygame

            # wait for lack of user input to set menu to idle
            if menu.idle_timer.timer_event():
                menu.evt_handler(timer=True)

            # check for pump flood-drain cycle progess
            if shrub.hydroTimer.timer_event():
                shrub.evt_handler(evt='TIME')

            # turn the conditioners on or off
            if condition.on_timer.timer_event():
                condition.evt_handler(evt='ON TIMER')
            
            # grab all sensor values to pass to butterworth filter with higher frequency
            temp = condition.sensOutOfRange()
            if condition.wait_timer.event_no_reset():
                # timer is reset in event handler as long as the pumps are not being paused
                for event in temp:
                    if event is not None:
                        condition.evt_handler(evt=event)

            # use sonar to see if the reservoir is dangerously full, stop valves.
            test_overflow = shrub.overflow_det()
            # check to see if the shrub already detects overflow to prevent repeated events
            if test_overflow and (shrub.overflowCondition != "OVERFLOW"):
                shrub.evt_handler(evt="OVERFLOW")
                condition.evt_handler(evt="OVERFLOW")
            # allow valves to open up again if not overflowing
            elif (shrub.overflowCondition == "OVERFLOW") and (not test_overflow):
                shrub.evt_handler(evt="NO OVERFLOW")
                condition.evt_handler(evt="NO OVERFLOW")
            
            # if menu is idle then print next sensor data to LCD
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
            
            # save pump cycle state after some time
            if saveCycleTime.timer_event():
                menu.saveParamChange(cycle=True)
                    
        printf("State machine loop broken. Attempting relaunch")
        LCD.print("State machine loop broken. Attempting relaunch")
        sleep(4)
    except Exception as e:
        LCD.print(f'Fatal error: {e}\n')
        printf(f'Fatal error: {e}\n')

        import logging
        # get current time to make unique file name
        now = localtime()
        log_file = f'{log_path}shrub_error_{now[0]}_{now[1]}_{now[2]}_{now[3]}-{now[4]}.log'
        # create new file
        with open(log_file,'w') as fp:
            pass
        # save error to file
        logging.basicConfig(filename=log_file,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(name)s %(message)s')
        logger=logging.getLogger(__name__)
        logger.error(e)
        
        sleep(60)
        LCD.print('Reboot system and check wire connections')
        system('python /home/pi/THE-SHRUBBERS/autoupdate.py --no-shrub')