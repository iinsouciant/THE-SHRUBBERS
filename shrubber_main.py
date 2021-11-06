# shrubber_main.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.50 30-Oct-2021 Finding code examples to use for this project
#   v0.60 06-Nov-2021 Copying over class and logic for state machine with some edits. not working version

import gpiozero as GZ
from lib.hcsr04sensor import sensor as hcsr04
import time

# Butterowrth lowpass filter
import numpy as np
import math
# if we do implement the discrete filter in real time, we will need to create a buffer system
# this will let us not use up all the memory storing values

F_trig_pin = 13  # placeholder value
F_echo_pin = 14  # placeholder value

M_trig_pin = 15  # placeholder value
M_echo_pin = 16  # placeholder value

pumpM_pin = 23  # placeholder value
pumpF_pin = 24  # placeholder value

pumpM = GZ.PWMLED(pumpM_pin)
pumpF = GZ.PWMLED(pumpF_pin)
pumps = [pumpM, pumpF]

'''
sonarF = hcsr04.Measurement(F_trig_pin, F_echo_pin, temperature=20)  # example code, 20 C
sonarM = hcsr04.Measurement(M_trig_pin, M_echo_pin, temperature=20)  # example code, 20 C
sonars = [sonarM, sonarF]

# gives cm, default sample size is 11 readings
raw_measurement = sonar1.raw_distance()  # can lower it by `sample_wait` and filter it with low pass
# could also used `sonar1.basic_distance(...)`
# can then use the height to calc water volume

# alternatively if we know initial hole depth we can use this method instead
hole_depth1 = 100  # cm
liquid_depth1 = sonar1.depth(raw_measurement, hole_depth1)
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
    pump.throttle = float(level / 100)  # will need to change this to PWM method


def motor_test(pumpM, pumpF, drive_time, mag=60):  # for testing each direction of the motors
    drive = drive_time / 2
    pump_pwm(mag, pumpM)
    pump_pwm(mag, pumpF)
    time.sleep(drive)
    pump_pwm(-mag, pumpM)
    pump_pwm(-mag, pumpF)
    time.sleep(drive)
    pump_pwm(0, pumpM)
    pump_pwm(0, pumpF)
    time.sleep(0.1)


# state machine skeleton from goomba project
class state_machine():
    go = None  # indicates direction for turning
    start = "IDLE"
    test = False
    # independent timer event
    DATA_SEND_INTERVAL = 0.3
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


    def active(self, pwr=70):
        pump_pwm(pwr, self.pumpM)  # TODO fine tune values so they match flow rates 
        pump_pwm(pwr, self.pumpF)

    def get_state(self):
        if self.state == "LOCATE":
            return (self.LOCATE, 1)
        elif self.state == "TURN":
            if shrub.go == "LEFT":
                return (self.TURN_LEFT, 1)
            elif shrub.go == "RIGHT":
                return (self.TURN_RIGHT, 1)
            else:
                error("Locate state change handled incorrectly")
                return (self.BAD_DIRECTION, 1)  # error integer
        elif self.state == "FORWARD":
            return (self.FORWARD, 1)

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
            if shrub.go == "LEFT":
                return (self.TURN_LEFT, 0)
            elif shrub.go == "RIGHT":
                return (self.TURN_RIGHT, 0)
            else:
                error("Turn state change handled incorrectly")
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
        dist = self.water_height()
        try:
            if dist >= thresh:
                return True
            else:
                return False
        except TypeError:
            return True

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
        try:
            distF = self.sF.distance
        except Exception:
            print("The front sonar is not detected.")
            distF = 0
        return [distL, distF, distR]

    def timer_event(self):
        if (self.timer_time is not None) and time.monotonic() >= self.timer_time:
            self.timer_time = None
            self.evt_handler(timer=True)
            if self.test:
                print(shrub.state)
            return True
        else:
            return False

    def timer_set(self):
        self.timer_time = time.monotonic() + self.DATA_SEND_INTERVAL

    def evt_handler(self, ignite=False):
        # change state stuff here
        # example
        if (self.state == "IDLE") and ignite:
            self.state = "PLACEHOLDER NAME"
        elif (self.state == "MAX") and (self.go == True):
            self.state = "IDK"
            thing = 1

        self.timer_set()  # resets timer
        if testing2:
            print(thing)

    def test_print(self):  # TODO mod this for our sensors
        print("Sonar distances:{0:10.2f}L {1:10.2f}F {2:10.2f}R (cm)".format(*self.grab_sonar()))
        encs = [self.encL.position, self.encR.position]
        print('Encoders:      {0:10.2f}L {1:10.2f}R pulses'.format(*encs))
        print('Magnetometer:  {0:10.2f}X {1:10.2f}Y {2:10.2f}Z uT'.format(*lis3.magnetic))
        print("Acceleration:  {0:10.2f} {1:10.2f} {2:10.2f} m/s^2".format(*lsm6.acceleration))
        print("Cliff distance:  ", self.water_height(), "cm")
        print("Cliff?         ", self.cliff_det())


# testing parameters
testing = True  # to show state
testing2 = False  # to show sensor data
print_time = .5
test_q = "Y"

# initializing variables
last = time.monotonic()
i = 0
s_thold = 25  # in cm

# creating instance of state machine
shrub = state_machine(pumps, pHsens, ECsens, press, sonars)

#will need t oalter inital starting method since we prob won't have a keyboard for input
while True: 
    if testing:
        shrub.test = True
    while (test_q == "Y") or (test_q == "SKIP"):  # for running test procedure with some input
        shrub.test_print()
        dists = shrub.grab_sonar()
        cliff = shrub.water_height()

        time.sleep(print_time)
        if test_q != "SKIP":
            mot_test0 = input("Test motors? \nY or N ")
            mot_test1 = mot_test0.upper()
            test_q = mot_test0.upper()
            if (mot_test1 == "END"):
                break
            if mot_test1 != "SKIP":
                uart_test0 = input("Test UART? \nY or N ")
                uart_test1 = uart_test0.upper()
                if uart_test1 == "SKIP":
                    test_q = uart_test1
                if (uart_test1 == "END"):
                    break
                elif mot_test1 == "Y":
                    duration = float(input("How long? "))
                    motor_test(pumpF, pumpM, duration)

    while (test_q != "Y") and (test_q != "SKIP"):
        if testing:
            if time.monotonic() - last > print_time:
                last = time.monotonic()
                if shrub.state == "TURN":
                    print(shrub.go)
                if testing2:
                    shrub.test_print()
        if shrub.state == "IDLE":
            shrub.forward(speed=0)
            if start_button:  # some trigger to start the system
                shrub.evt_handler(ignite=start_button)
            start_button = False

        if shrub.state != "IDLE":
            if shrub.timer_time is None:  # timer acts independently and does not use locate -> doesn't change state
                shrub.timer_set()
            shrub.timer_event()

        if shrub.state == "FORWARD":
            shrub.forward()
            distL, distF, distR = shrub.grab_sonar()
            if (distR <= s_thold) and (distF <= s_thold):
                shrub.evt_handler()
                shrub.go = "LEFT"
            elif (distL <= s_thold) and (distF <= s_thold):
                shrub.evt_handler()
                shrub.go = "RIGHT"
            elif (distF <= s_thold):
                shrub.evt_handler()
                shrub.go = "RIGHT"
            if shrub.cliff_det() is True:
                shrub.evt_handler()
                shrub.go = "RIGHT"
            if start_button is True:  # only used by bluetooth
                shrub.state = "IDLE"
                start_button = False

        if shrub.state == "TURN":
            shrub.turn(shrub.go)
            distL, distF, distR = shrub.grab_sonar()
            if (distF >= s_thold) and (shrub.cliff_det() is False):
                shrub.evt_handler()
            elif start_button is True:  # only used by bluetooth
                shrub.state = "IDLE"
                start_button = False
