# state_machine/shrubber.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement a state machine to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.6 06-Nov-2021 Migration of skeleton from main file

# Butterowrth lowpass filter
from lib.butterworth import b_filter as BF
import time 

class state_machine():
    go = None  # indicates direction for turning
    start = "IDLE"
    test = False  # for printing state change and events
    test_q = "Y"
    # independent timer event
    TIMER_INTERVAL = 0.3
    timer_time = None

    def __init__(self, pump, pHsens, ECsens, buttons, sonar, LCD):
        self.state = self.start
        self.pump = pump
        self.pHsens = pHsens
        self.ECsens = ECsens
        self.bs = buttons
        self.AB = buttons[0]
        self.BB = buttons[1]
        self.UB = buttons[2]
        self.LB = buttons[3]
        self.DB = buttons[4]
        self.RB = buttons[5]
        self.s = sonar
        self.LCD = LCD
        self.timer_set()
        self.fs = BF.LowPassFilter(7)
        self.fpH = BF.LowPassFilter(5)
        self.fEC = BF.LowPassFilter(5)

    def __repr__(self):
        return "state_machine({}, {}, {}, {}, {}, {})".format(self.pump, self.pHsens,
        self.ECsens, self.bs, self.sonar, self.LCD)
    
    def __str__(self):
        return "State: {}\nWater level: {} cm\nPressure drop: {} psi\npH: {}\nEC: {} mS".format(
            self.state, self.grab_sonar(), self.grab_press(), self.grab_pH(), self.grab_EC()
        )  # dummy function names

    def __error(err_string):
        raise Exception(err_string)

    # TODO update this: pass in pause button toggle + event and it chooses next state depending on current state. 
    def evt_handler(self, evt, pause=False):
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

        self.timer_set()  # resets timer
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

    # grab methods returns filtered value
    def grab_pH(self):  # handle faulty pH
        try:
            dist = self.s.basic_distance()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self):  # handle faulty EC
        try:
            dist = self.s.basic_distance()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fEC.filter(dist)

    def grab_sonar(self):  # to handle faulty sonar connections
        try:
            dist = self.s.basic_distance()
        except Exception:
            print("The sonar is not detected.")
            dist = 0
        return self.fs.filter(dist)

# TODO prob make this it's own class to have multiple instances of the timer
    def __timer_event(self):
        if (self.timer_time is not None) and time.monotonic() >= self.timer_time:
            self.timer_time = None
            self.evt_handler(timer=True)
            if self.test:
                print(self.state)
            return True
        else:
            return False

    def timer_set(self):
        self.timer_time = time.monotonic() + self.TIMER_INTERVAL

    # can replace this with __str__
    '''def test_print(self):  
        print("Sonar distances:{0:10.2f}L {1:10.2f}F {2:10.2f}R (cm)".format(*self.grab_sonar()))
        encs = [self.encL.position, self.encR.position]
        print('Encoders:      {0:10.2f}L {1:10.2f}R pulses'.format(*encs))
        print('Magnetometer:  {0:10.2f}X {1:10.2f}Y {2:10.2f}Z uT'.format(*lis3.magnetic))
        print("Acceleration:  {0:10.2f} {1:10.2f} {2:10.2f} m/s^2".format(*lsm6.acceleration))
        print("Cliff distance:  ", self.water_height(), "cm")
        print("Cliff?         ", self.cliff_det())'''
    
    # potentially useful function for pump control
    def __pump_pwm(self, level, pump):  # input is range of percents, 0 to 100
        pump.value = float(level / 100)

    @staticmethod
    def pump_test(pumpM, pumpF, drive_time, mag=60):  # for testing each direction of the pumps
        self.pump_pwm(mag, pumpM)
        self.pump_pwm(mag, pumpF)
        time.sleep(drive_time)
        self.pump_pwm(0, pumpM)
        self.pump_pwm(0, pumpF)
        time.sleep(0.1)