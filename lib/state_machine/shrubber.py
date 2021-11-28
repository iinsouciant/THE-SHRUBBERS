# state_machine/shrubber.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement a state machine to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.6 06-Nov-2021 Migration of skeleton from main file

import time 

class state_machine():
    go = None  # indicates direction for turning
    start = "IDLE"
    test = False  # for printing state change and events
    test_q = "Y"
    # independent timer event
    TIMER_INTERVAL = 0.3
    timer_time = None

    def __init__(self, pumps, pHsens, ECsens, press, sonars):
        self.state = self.start
        self.pumpM = pumps[0]
        self.pumpF = pumps[1]
        self.pHsens = pHsens
        self.ECsens = ECsens
        self.press = press
        self.sM = sonars[0]
        self.sF = sonars[1]
        self.timer_set()

    def active(self, pwr=70):
        self.pump_pwm(pwr, self.pumpM)  # TODO fine tune values so they match flow rates 
        self.pump_pwm(pwr, self.pumpF)

    # TODO update this
    def get_state(self):
        if self.state == "LOCATE":
            return (self.LOCATE, 1)
        elif self.state == "TURN":
            if self.go == "LEFT":
                return (self.TURN_LEFT, 1)
            elif self.go == "RIGHT":
                return (self.TURN_RIGHT, 1)
            else:
                self.error("Locate state change handled incorrectly")
                return (self.BAD_DIRECTION, 1)  # error integer
        elif self.state == "FORWARD":
            return (self.FORWARD, 1)

    # TODO update this
    def state_change(self, ignite):
        if (ignite is True) and (self.state == "IDLE"):
            self.state = "LOCATE"
        elif (ignite is True) and (self.state != "IDLE"):
            self.state = "IDLE"
        if self.state == "LOCATE":
            self.state = "FORWARD"
            return (self.LOCATE, 0)  # this results in state number paired w/ data that trggered state change
        elif self.state == "TURN":  # TODO FIX ??
            self.state = "FORWARD"
            if self.go == "LEFT":
                return (self.TURN_LEFT, 0)
            elif self.go == "RIGHT":
                return (self.TURN_RIGHT, 0)
            else:
                self.error("Turn state change handled incorrectly")
                return (self.BAD_DIRECTION, 0)  # error integer
        elif self.state == "FORWARD":
            self.state = "TURN"
            return (self.FORWARD, 0)

    def water_height(self):  # in cm, good for ~9 to ~30
        '''
        use hcsr04sensor library for this. ex:
        hole_depth1 = 100  # cm
        liquid_depth1 = sonar1.depth(raw_measurement, hole_depth1)
        '''

    def overflow_det(self, thresh=20):  # in case water level is too high?
        height = self.water_height()
        try:
            if height >= thresh:
                return True
            else:
                return False
        except TypeError:
            return True

    # TODO update methods
    def grab_sonar(self):  # to handle faulty sonar connections
        try:
            distL = self.sL.distance
        except Exception:
            print("The left sonar is not detected.")
            distL = 0
        try:
            distR = self.sR.distance
        except Exception:
            print("The right sonar is not detected.")
            distR = 0
        return [distL, distR]

    def timer_event(self):
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

    # TODO update this
    def evt_handler(self, evt, ignite=False):
        if self.test:
            print(self.state)
            print(evt)

        # change state stuff here
        # example
        if (self.state == "IDLE") and ignite:
            self.state = "PLACEHOLDER NAME"
        elif (self.state == "MAX") and (evt == "nut"):
            self.state = "IDK"

        self.timer_set()  # resets timer
        if self.test:
            print(self.state)
            self.test_print()

    # TODO mod this for our sensors
    def test_print(self):  
        print("Sonar distances:{0:10.2f}L {1:10.2f}F {2:10.2f}R (cm)".format(*self.grab_sonar()))
        encs = [self.encL.position, self.encR.position]
        print('Encoders:      {0:10.2f}L {1:10.2f}R pulses'.format(*encs))
        print('Magnetometer:  {0:10.2f}X {1:10.2f}Y {2:10.2f}Z uT'.format(*lis3.magnetic))
        print("Acceleration:  {0:10.2f} {1:10.2f} {2:10.2f} m/s^2".format(*lsm6.acceleration))
        print("Cliff distance:  ", self.water_height(), "cm")
        print("Cliff?         ", self.cliff_det())me

    def error(err_string):
        raise Exception(err_string)

    # potentially useful function for pump control
    def pump_pwm(level, pump):  # input is range of percents, 0 to 100
        pump.value = float(level / 100)

    def pump_test(pumpM, pumpF, drive_time, mag=60):  # for testing each direction of the pumps
        self.pump_pwm(mag, pumpM)
        self.pump_pwm(mag, pumpF)
        time.sleep(drive_time)
        self.pump_pwm(0, pumpM)
        self.pump_pwm(0, pumpF)
        time.sleep(0.1)