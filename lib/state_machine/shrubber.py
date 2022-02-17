# state_machine/shrubber.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement state machines to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.60 06-Nov-2021 Migration of skeleton from main file
#   v0.65 17-Feb-2022 Drafting menu state machine to interact with hydro

# Butterowrth lowpass filter
from lib.butterworth import b_filter as BF
from lib.DFR import DFRobot_EC as EC
from lib.DFR import DFRobot_PH as PH
import time
import csv
import warnings

class timer():
    '''Creates a nonblocking timer to trigger a timer event when checked'''
    timer_time = None

    def __init__(self, interval):
        self.TIMER_INTERVAL = interval

    def __timer_event(self):
        if (self.timer_time is not None) and time.monotonic() >= self.timer_time:
            self.timer_time = None
            self.evt_handler(None, timer=True)
            return True
        else:
            return False

    def timer_set(self):
        self.timer_time = time.monotonic() + self.TIMER_INTERVAL

class hydro():
    '''Part of the Shrubber state machine that handles
    events passed to it, and defines and run the states as needed.'''
    go = None  # indicates direction for turning
    start = "IDLE"
    test = False  # for printing state change and events
    test_q = "Y"
    # independent timer event
    active_timer = timer(0.1)
    active_timer.timer_set()

    def __init__(self, pump, pHsens, ECsens, buttons, sonar, LCD):
        self.state = self.start
        self.pump = pump
        self.bs = buttons
        self.AB = buttons[0]
        self.BB = buttons[1]
        self.UB = buttons[2]
        self.LB = buttons[3]
        self.DB = buttons[4]
        self.RB = buttons[5]
        self.s = sonar
        self.LCD = LCD
        self.fs = BF.LowPassFilter(7)
        self.fpH = BF.LowPassFilter(5)
        self.fEC = BF.LowPassFilter(5)
        self.pHsens = pHsens
        self.pH = PH.DFRobot_PH()
        self.ECsens = ECsens
        self.EC = EC.DFRobot_EC()

    def __repr__(self):
        return "state_machine({}, {}, {}, {}, {}, {})".format(self.pump, self.pHsens,
        self.ECsens, self.bs, self.sonar, self.LCD)
    
    def __str__(self):
        '''Provides formatted sensor values connected to state machine'''
        return "State: {}\nWater level: {} cm\nPressure drop: {} psi\npH: {}\nEC: {} mS".format(
            self.state, self.grab_sonar(), self.grab_press(), self.grab_pH(), self.grab_EC()
        )  # dummy function names

    def __error(err_string):
        raise Exception(err_string)

    # TODO update this: pass in pause button toggle + event and it chooses next state depending on current state. 
    def evt_handler(self, evt, timer=False, pause=False):
        '''Handles the logic to choose and run the proper state
        depending on current state and event passed to it'''
        self.last_s = self.state
        if self.test:
            print(self.state)
            print(evt)

        # change state stuff here
        # example
        if (self.state == "IDLE") and pause:
            self.state = self.last_s
        elif (self.state == "MAX") and (evt == "nut"):
            self.state = "IDK"

        self.active_timer.timer_set()  # resets timer
        if self.test:
            print(self.state)
            self.test_print()

    def active(self, pwr=30):
        self.pump_pwm(pwr, self.pumpM)  # TODO fine tune values so they match flow rates 
        self.pump_pwm(pwr, self.pumpF)

    def water_height(self):  # in cm, good for ~9 to ~30
        hole_depth1 = 35*2.54  # 35in to cm
        return self.s.depth(self.grab_sonar(), hole_depth1)

    def overflow_det(self, thresh=15):  # in case water level is too high?
        height = self.water_height()
        try:
            if height >= thresh:
                return True
            else:
                return False
        except TypeError:
            return True

    # TODO update/supplement grabs with calculations to interpret voltage
    def grab_pH(self):
        '''Tries to grab the pH sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.s.voltage()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self):
        '''Tries to grab the conductivity sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.s.voltage()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fEC.filter(dist)

    def grab_sonar(self):
        '''Tries to grab the sonar sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.s.basic_distance()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fs.filter(dist)

    # can replace this with __str__
    '''def test_print(self):  
        print("Sonar distances:{0:10.2f}L {1:10.2f}F {2:10.2f}R (cm)".format(*self.grab_sonar()))
        encs = [self.encL.position, self.encR.position]
        print('Encoders:      {0:10.2f}L {1:10.2f}R pulses'.format(*encs))
        print('Magnetometer:  {0:10.2f}X {1:10.2f}Y {2:10.2f}Z uT'.format(*lis3.magnetic))
        print("Acceleration:  {0:10.2f} {1:10.2f} {2:10.2f} m/s^2".format(*lsm6.acceleration))
        print("Cliff distance:  ", self.water_height(), "cm")
        print("Cliff?         ", self.cliff_det())'''

    def pump_pwm(self, level, pump):
        """This method is deprecated, use GZ.PWMLED value method instead."""
        warnings.warn("use GZ.PWMLED value method instead", DeprecationWarning)
        pump.value(level)

    def pump_test(self, pumpM, pumpF, drive_time, mag=60):  # for testing each direction of the pumps
        self.pump_pwm(mag, pumpM)
        self.pump_pwm(mag, pumpF)
        time.sleep(drive_time)
        self.pump_pwm(0, pumpM)
        self.pump_pwm(0, pumpF)
        time.sleep(0.1)


class menu():
    ''' Implement a menu state machine x levels deep to allow the user to
    configure the shrubber state machine without blocking operations elsewhere
    and simultaneously output information to the LCD screen.'''
    start = "IDLE"
    ops = ("Active pump timer", "Inactive pump timer", "pH thresholds", 
        "EC thresholds", )
    parent = start
    child = ops
    m1_hover = 0
    m2_hover = 0
    # independent timer event to time out LCD
    ap = 120
    ip = 240
    pHH = 9
    pHL = 4
    ECH = 2
    ECL = 0
    sT = 10

    def __init__(self, buttons, LCD, shrub):
        self.state = self.start
        #self.bs = buttons
        self.AB = buttons[0]
        self.BB = buttons[1]
        self.UB = buttons[2]
        self.LB = buttons[3]
        self.DB = buttons[4]
        self.RB = buttons[5]
        self.LCD = LCD
        self.shrub = shrub

        try:
            with open('Settings.csv', 'r') as f:
                settings = csv.reader(f)
                self.ap = int(settings[0][1])
                self.ip = int(settings[1][1])
                self.pHH = int(settings[2][2])
                self.pHL = int(settings[2][1])
                self.ECH = int(settings[3][2])
                self.ECL = int(settings[3][1])
                self.sT = int(settings[4][1])
        except IOError:
            print("Settings.txt does not exist. Creating file with default settings.")
            with open(r"Settings.csv", 'w') as f:
                rows = [ ['Active Pump Timer', self.ap], 
                    ['Inactive Pump Timer', self.ip], 
                    ['pH High Threshold', self.pHH], 
                    ['pH Low Threshold', self.pHL], 
                    ['EC High Threshold', self.ECH], 
                    ['EC Low Threshold', self.ECL],
                    ['Water from top', self.sT] ] 
                settings = csv.writer(f)
                settings.writerows(rows)

    def write2settings(self):
        pass
    
    def evt_handler(self, evt, timer=False):
        if timer:
            self.parent = self.start
            self.child = self.ops
            self.LCD.idle()

        if (self.child == self.ops) and (self.parent == self.start):
            if self.U_B.is_pressed or self.D_B.is_pressed or self.L_B.is_pressed or self.R_B.is_pressed \
                or self.A_B.is_pressed or self.B_B.is_pressed:
                self.timer_set()
                self.parent == self.start
                self.child == self.ops[1]
                self.m1_hover = 0
                # potentially blocking depending on how we implement LCD, maybe threading library to help
                self.LCD.run(self.ops[0]) 
        
        if self.child in self.ops:
            if self.B_B.is_pressed:
                self.parent = self.start
                self.child = self.ops
                self.LCD.idle()
            if self.A_B.is_pressed:
                pass

