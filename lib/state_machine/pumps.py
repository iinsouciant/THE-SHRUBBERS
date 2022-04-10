# state_machine/pumps.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement state machines to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.42 27-Mar-2022 Migration of hydro class from LCDmenu.py

# Butterworth lowpass filter
from lib.butterworth import b_filter as BF
from lib.DFR import DFRobot_EC as EC
from lib.DFR import DFRobot_PH as PH   
from LCDmenu import timer
from time import sleep, monotonic
import warnings

# TODO split hydro for main pump and conditioning
# TODO don't let pump run if sonar detects the reservoir as empty? note sonar range
# TODO make alternating valve method for draining
class hydro():
    '''Part of the Shrubber state machine that handles
    events passed to it, and defines and run the states as needed.'''
    start = "IDLE"
    test = False  # for printing state change and events
    test_q = "Y"
    s_thresh = 10 # cm
    # pump active, drain, and inactive times
    ptimes = [60*20, 60*10, 60*60*4]
    pn= 0
    # independent timer event for pump/UV. start on
    ptimer = timer(ptimes[pt])
    ptimer.timer_set()
    # valve open time
    vtimes = [ptimes[1]/2, ptimes[1]/2, None]*2
    vn = 0
    vtimer = timer(vtimes[vn])
    # sequences to cycle through for valve opening
    vState = ((1, 0), (0, 1), (0, 0), (0, 1), (1, 0), (0, 0))
    [topValveVal, botValveVal] = vState[vn]
    state = start

    def __init__(self, pump, sonar, valves, filter=7):
        self.pump = pump
        self.s = sonar
        self.fs = BF.LowPassFilter(filter)
        self.topValve = valves[0]
        self.botValve = valves[1]

    def __repr__(self):
        return "state_machine({}, {}, {}, {})".format(self.pump, self.s, self.topValve, self.botValve)
    
    def __str__(self):  # TODO check if we need to update this
        '''Provides formatted sensor values connected to state machine'''
        return "State: {}\nWater level: {} cm\nValve State: {}".format(
            self.state, self.water_height(), self.vState[self.vn]
        )  # dummy function names

    def __error(err_string):
        raise Exception(err_string)

    def update_settings(self, ptimes, sonar_thresh):
        self.ptimes = ptimes
        self.ptimer.new_interval_timer(ptimes[self.pn])
        # valve open time
        self.vtimes = [ptimes[1]/2, ptimes[1]/2, None]*2
        self.vtimer.new_interval_timer(vtimes[self.vn])

    # TODO update this: pass in pause button toggle + event and it chooses next state depending on current state. 
    def evt_handler(self, evt=None, ptime=False, vtime=False, pause=False):
        '''Handles the logic to choose and run the proper state
        depending on current state and event passed to it'''
        self.last_s = self.state
        if self.test:
        print(self.last_s)
            print(self.state)
            print(evt)

        # IDLE is default operating behavior
        if (self.state == "IDLE"):
            # TODO test. 
            if ptime:
                self.state = "FLOOD"
                self.pn += 1
                self.pn %= 3
                if self.pn == 0:
                    print("Pump/UV is now on. WIP")
                    self.active()
                if self.pn == 1:
                    print("Pump/UV is now idle. WIP")
                    self.pump.value = 0
                if self.pn == 2:
                    print("Valve open protocol beginning")
                    self.pump.value = 0
                    vtime=True
                self.ptimer.TIMER_INTERVAL = self.ptimes[self.pt]
                self.ptimer.timer_set()
        # example state handling
        elif (self.state == "MAX") and (evt == "nut"):
            self.state = "IDK"

        # TODO test. do we mod this to enable pump too?
        # close valves in case of flood
        if evt is not None:
            if evt == "OVERFLOW":
                self.topValve.off
                self.botValve.off
                self.state = "NO DRAIN"
            # any other events to consider?
            elif evt == "PLACEHOLDER":
                pass

        if self.state == "NO DRAIN":
            # revert the valves back to normal operation
            if evt == "NO OVERFLOW":
                self.state = self.last_s # might be better to make this just IDLE
            elif evt == "OVERFLOW":
                vtime = False

        # TODO valve events/timing so they alternate, split timing
        if vtime:
            print('Open one valve. set timer to then open other valve. change which goes first next time')
            self.vn+=1
            self.vn%=6
            [self.topValveVal, self.botValveVal] = self.vState[self.vn]
            # set new timer for being open or close
            if (self.vn == 2) or (self.vn == 5):
                # if it is not time to drain
                self.vtimer.timer_time = None
            else:
                self.vtimer.timer_set()

            # have it called once to open first valve, second time to open second valve, third time to close both
            if self.topValveVal == 0:
                self.topValve.off
            elif self.topValveVal == 1:
                self.topValve.on
            if self.botValveVal == 0:
                self.botValve.off
            elif self.botValveVal == 1:
                self.botValve.on
    
    def hydro_restart(self):
        self.state = IDLE
        self.topValve.off
        self.botValve.off
        self.pn = 0
        self.vn = 0
        self.ptimer.TIMER_INTERVAL = self.ptimes[self.pt]
        self.ptimer.timer_set()


    def active(self, pwr=30):
        self.pump.value = pwr/100  # TODO set default value to match 1 GPM 

    # TODO update this
    def water_height(self):  # in cm, good for ~9 to ~30
        hole_depth1 = 35*2.54  # 35in to cm
        return self.s.depth(self.grab_sonar(), hole_depth1)

    def overflow_det(self, thresh=self.s_thresh):  # in case water level is too high?
        height = self.water_height()
        try:
            if height >= thresh:
                return True
            else:
                return False
        except TypeError as e:
            print(e)
            return True
    
    def grab_sonar(self):
        '''Tries to grab the sonar sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.s.basic_distance()
        except Exception:
            print("The sonar is not detected.")
            warnings.WarningMessage("The sonar sensor is not detected.")
            dist = 0
        return self.fs.filter(dist)

    def pump_pwm(level, pump):
        """This method is deprecated, use GZ.PWMLED value method instead."""
        warnings.warn("use GZ.PWMLED value method and pass in float instead", DeprecationWarning)
        pump.value = level

    def pump_test(self, drive_time, mag=60):  # for testing each direction of the pumps
        self.pump.value = mag/100
        sleep(drive_time)
        self.pump.value = 0
        sleep(0.1)


class conditioner():
    '''Class to handle the state machine behavior of the nutrient solution conditioning pumps'''

    pH_High = 9
    ph_Low = 4
    EC_High = 2
    EC_Low = 0
    on_timer = timer(1)
    state = "IDLE"

    def __init__(self, conditioning_pumps, shrub, pHsens, ECsens, temp, filters=[5, 5, 5]):
        self.pumpA = conditioning_pumps[0]
        self.pumpB = conditioning_pumps[1]
        self.pumpN = conditioning_pumps[2]
        self.hydro = shrub
        self.temp = temp
        self.pHsens = pHsens
        self.ECsens = ECsens
        self.pH = PH.DFRobot_PH()
        self.EC = EC.DFRobot_EC()
        self.fpH = BF.LowPassFilter(filters[0])
        self.fEC = BF.LowPassFilter(filters[1])
        self.fTemp = BF.LowPassFilter(filters[2])
        self.filters = [self.fpH, self.fEC, self.fTemp]

    def __repr__(self):
        return "state_machine({}, {}, {}, {}, {}, {})".format(self.pumpA, self.pumpB, self.pumpC, 
        self.pHsens, self.ECsens, self.temp)

    def __str__(self):  # TODO check if we need to update this
        '''Provides formatted sensor values connected to state machine'''
        return "Channel Pump State: {}\nConditioner State: {}\nWater level: {} cm\npH: {}\
        \nEC: {} mS\nTemp: {} C".format(
            self.hydro.state, self.state, self.hydro.grab_sonar(), self.grab_pH(), self.grab_EC(), self.grab_temp()
        )

    def EC_calibration(self):
        '''Run this once the EC sensor is fully submerged in the high or low solution.
        This will then exit if it detects a value in an acceptable range.'''
        return self.EC.calibration(self.grab_EC(), self.grab_temp())
        
    def pH_calibration(self):
        '''Run this once the EC sensor is fully submerged in the high or low solution.
        This will then exit if it detects a value in an acceptable range.'''
        return self.pH.calibration(self.grab_pH())

    def grab_pH(self):
        '''Tries to grab the pH sensor value 
        without raising an exception halting the program'''
        try:
            dist = PH.readPH(self.pHsens.voltage())
        except Exception:
            print("The pH sensor is not detected.")
            warnings.WarningMessage("The pH sensor is not detected.")
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self):
        '''Tries to grab the conductivity sensor value 
        without raising an exception halting the program'''
        try:
            dist = EC.readEC(self.ECsens.voltage(), self.grab_temp)
        except Exception:  # TODO find correct exceptions here
            print("The conductivity sensor is not detected.")
            warnings.WarningMessage("The conductivity sensor is not detected.")
            dist = 0
        return self.fEC.filter(dist)

    def grab_temp(self):
        '''Tries to grab the temperature sensor value 
        without raising an exception halting the program'''
        try:
            # TODO get temp sensor library and replace
            dist = self.temp.voltage()
        except Exception:
            print("The temperature sensor is not detected.")
            warnings.WarningMessage("The temperature sensor is not detected.")
            dist = 0
        return self.fTemp.filter(dist)