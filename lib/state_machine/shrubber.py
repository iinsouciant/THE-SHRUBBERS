# state_machine/shrubber.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement state machines to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.60 06-Nov-2021 Migration of skeleton from main file
#   v0.65 17-Feb-2022 Drafting menu state machine to interact with hydro

# Butterowrth lowpass filter
from xml.etree.ElementPath import ops
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
    
    # TODO for ebb and flow may want to make an alternate version for hours/min?

# TODO split hydro for main pump and conditioning
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
        self.pump.value(pwr)  # TODO fine tune values so they match flow rates 

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
        
    def EC_calibration(self, temp=22):
        '''Run this once the EC sensor is fully submerged in the high or low solution.
        This will then exit if it detects a value in an acceptable range.'''
        return self.EC.calibration(self.ECsens.voltage(), temp)
        
    def pH_calibration(self, temp=22):
        '''Run this once the EC sensor is fully submerged in the high or low solution.
        This will then exit if it detects a value in an acceptable range.'''
        return self.pH.calibration(self.pHsens.voltage(), temp)

    # TODO update/supplement grabs with calculations to interpret voltage
    def grab_pH(self):
        '''Tries to grab the pH sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.pHsens.voltage()
        except Exception:
            print("The pH sensor is not detected.")
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self):
        '''Tries to grab the conductivity sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.ECsens.voltage()
        except Exception:
            print("The conductivity sensor is not detected.")
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
    ops = ("Flood timer", "Drain timer", "Active pump timer",
        "pH thresholds", "EC thresholds", "Gap from top", 
        "Calibrate pH", "Calibrate EC", "Toggle pump/UV", 
        "Toggle nutrient conditioners")
    parent = start
    child = ops
    m1_hover = 0
    m2_hover = 0
    # independent timer event to time out LCD
    ap = 120
    ip = 240
    # Sensor threshold values
    pHH = 9
    pHL = 4
    ECH = 2
    ECL = 0
    sT = 10

    def __init__(self, LCD, shrub):
        self.state = self.start
        self.LCD = LCD
        self.shrub = shrub

        # on boot, check to see if state machine settings exist. if not create w/ default settings
        try:
            with open('Settings.csv', 'r') as f:
                settings = csv.reader(f)
                self.ft = int(settings[0][1])
                self.dt = int(settings[1][1])
                self.ap = int(settings[2][1])
                self.pHH = int(settings[3][2])
                self.pHL = int(settings[3][1])
                self.ECH = int(settings[4][2])
                self.ECL = int(settings[4][1])
                self.sT = int(settings[5][1])
        except IOError:
            print("Settings.txt does not exist. Creating file with default settings.")
            with open(r"Settings.csv", 'w') as f:
                rows = [['Flood Timer', self.ft], 
                    ['Drain Timer', self.dt], 
                    ['Active Pump Timer', self.ap], 
                    ['pH High Threshold', self.pHH], 
                    ['pH Low Threshold', self.pHL], 
                    ['EC High Threshold', self.ECH], 
                    ['EC Low Threshold', self.ECL],
                    ['Gap from top', self.sT]] 
                settings = csv.writer(f)
                settings.writerows(rows)

    # TODO quick way to write to correct line without having to read and store whole file?
    def write2settings(self):
        pass

    def idle(self):
        self.parent = self.start
        self.child = self.ops
        # special lcd state to scroll sensor data while non blocking. maybe multiprocessing? maybe just have send on timer
        self.LCD.idle()  
        self.state = "IDLE"

    def A_at_m1(self):
        # TODO make the pump timings show in H:M:S and allow them to use left and right to choose which digit to change
        self.parent = ops[self.m1_hover]
        if self.m1_hover <= 5:
            self.state = "WRITE"
            self.child = None
            self.m2_hover = 0
            with open('Settings.csv', 'r') as cfg:
                og = csv.reader(cfg)
                rows = [row for row in og]
            self.LCD.display(rows[self.m1_hover])
            # TODO show sublevel to pick low/high threshold values then allow increments. L/R to move decimal place
        
        # TODO test calibration menus
        if self.m1_hover == 7:
            # sets logic to handle A or B input on next loop
            self.child = "EC CONFIRM"
            self.LCD.display("Press A once EC is fully submerged in solution")

        if self.m1_hover == 6:
            self.child = "pH CONFIRM"
            self.LCD.display("Press A once EC is fully submerged in solution")

        # TODO finish menu logic for toggle pump/uv and peristaltic
        if self.m1_hover == 8:
            pass

    def evt_handler(self, evt=None, timer=False):  # TODO finish logic
        if len(evt) == 2:  # in case we want to do somethign with shortscuts?
            evt2 = evt[1]
            evt = evt[0]

        if evt is not None:
            pass  # need to a way to also restart timer instance

        # whenever there has been no user input for a while, go back to idle
        if timer:
            self.idle()
        
        # the idle level of the menu
        if (self.child == self.ops) and (self.parent == self.start):
            # wait for user input to start menu
            if (evt == "U_B") or (evt == "D_B") or (evt == "L_B") or (evt == "R_B") \
                or (evt == "A_B") or (evt == "B_B"):
                self.timer_set()
                self.parent = self.start
                self.m1_hover = 0
                self.child = self.ops[0]
                # potentially blocking depending on how we implement LCD, maybe threading library to help
                self.LCD.display(self.ops[0]) 
        
        # first level of menu showing configuration options
        if self.child in self.ops:
            if (evt == "B_B") or (evt == "L_B"):
                self.idle()
            if (evt == "A_B") or (evt == "R_B"):
                self.A_at_m1()
            if (evt == "U_B"):
                self.m1_hover += 1
                # resets the selected option back to 0 if it goes too high
                self.m1_hover %= len(ops)
            if (evt == "D_B"):
                self.m1_hover -= 1
                if self.m1_hover < 0:
                    self.m1_hover = len(ops) - 1
        
        # second level submenus to confirm calibration of sensors
        if self.child == "EC_CONFIRM":
            if (evt == "A_B") or (evt == "R_B"):
                self.LCD.display(self.shrub.EC_calibration())
                self.parent = self.start
                self.child = self.ops[self.m1_hover]
            if (evt == "B_B") or (evt == "L_B"):
                self.parent = self.start
                self.child = self.ops[self.m1_hover]

        if self.child == "PH_CONFIRM":
            if (evt == "A_B") or (evt == "R_B"):
                self.LCD.display(self.shrub.pH_calibration())
                self.parent = self.start
                self.child = self.ops[self.m1_hover]
            if (evt == "B_B") or (evt == "L_B"):
                self.parent = self.start
                self.child = self.ops[self.m1_hover]