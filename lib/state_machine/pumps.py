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
from lib.state_machine.LCDmenu import timer
from time import sleep, monotonic
import warnings

# TODO split hydro for main pump and conditioning
# TODO don't let pump run if sonar detects the reservoir as empty? note sonar range
# TODO make alternating valve method for draining
class hydro():
    '''Part of the Shrubber state machine that handles
    events passed to it, and defines and run the states as needed.'''
    test = False  # for printing state change and events
    # channel flooded, drained, and  pump active times
    ptimes = [60*60*3, 60*60*3.5, 60*20]
    valveDrainTime = 60*20
    actual_times = []
    # sequences to cycle through for valve opening
    pVals = (   1,      0,      0,      0,      0) * 2
    vVals = ((0, 0), (0, 0), (1, 0), (0, 1), (0, 0), (0, 0), (0, 0), (0, 1), (1, 0), (0, 0))

    pPause = False
    vPause = False
    overflowCondition = "NO OVERFLOW"
    userToggle = False

    hydro_state = 0
    pumpVal = pVals[hydro_state]
    [topValveVal, botValveVal] = vVals[hydro_state]
    hydroTimer = timer(actual_times[hydro_state])

    # TODO update w/ actual measurement
    hole_depth = 35*2.54  # 35in to cm
    s_thresh = 10  # cm

    def __init__(self, pump, sonar, valves, UV, filter=200):
        self.pump = pump
        self.s = sonar
        self.fs = BF.LowPassFilter(filter)
        self.topValve = valves[0]
        self.botValve = valves[1]
        self.UV = UV
        # join valve and channel pump times together to create simple sequence
        self.__ptimes2actual()

    def __repr__(self):
        return "state_machine({}, {}, {}, {})".format(self.pump, self.s, self.topValve, self.botValve)
    
    def __str__(self):  # TODO check if we need to update this  
        '''Provides formatted sensor values connected to state machine'''
        if self.test:
            print(self.vtimer.timer_time)
        return "State: {}\nWater level: {} cm\nValves active? {}\nValve State: {}".format(
            self.state, self.water_height(), self.vtimer.timer_time, 
            self.vVals[self.vn]
        )

    def __error(err_string):
        raise Exception(err_string)

    # TODO test
    def update_settings(self, ptimes, sonar_thresh):
        self.__ptimes2actual(ptimes)
        self.hydroTimer.new_interval_timer(self.actual_times[self.hydro_state])
        self.s_thresh = sonar_thresh
    
    # TODO test
    def __ptimes2actual(self, ptimes):
        self.ptimes = ptimes
        self.actual_times[0] = ptimes[2]  # pump fill channel
        self.actual_times[1] = ptimes[0]  # pump stop and leaved channel flooded
        self.actual_times[2] = self.valveDrainTime  # first valve open
        self.actual_times[3] = self.valveDrainTime  # first valve close second valve open
        self.actual_times[4] = ptimes[1] - 2 * self.valveDrainTime  # close both valves
        self.actual_times *= 2

    # TODO test 
    def evt_handler(self, evt=None, pumpPause=None, valvePause=None):
        '''Handles the logic to choose and run the proper state
        depending on current state and event passed to it'''
        if self.test:
            print(f'user shut off: {self.userToggle}')
            print(f'overflow condition: {self.overflowCondition}')
            print(evt)
        
        if evt is not None:
            if evt == 'TEST':
                self.topValve.on
                self.botValve.on
                self.active()
                sleep(6)
                self.topValve.off
                self.botValve.off
                self.active(pwr=0)

            elif evt == "OVERFLOW":
                valvePause = True
                self.overflowCondition = evt
                '''if self.test:
                    print("Top valve: off")
                    print("Bottom valve: off")'''
            elif (evt == "NO OVERFLOW") and (self.overflowCondition == "OVERFLOW"):
                self.overflowCondition = evt
                # prevent overflow condition from overriding the user toggling our outputs
                if self.userToggle is False:
                    valvePause = False
                    #pumpPause = False

            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                if self.userToggle:
                    pumpPause = True
                    valvePause = True
                elif not self.userToggle:
                    pumpPause = False
                    valvePause = False

            # TODO want some kind of event to start pump/uv/valve at will for testing
            elif evt == "PLACEHOLDER":
                pass

            # to stop the valves and pumps in case of emergency. 
            # stored in values to retain behavior across multiple events
            if pumpPause:
                self.pPause = True
            elif pumpPause is False:
                self.pPause = False
            if valvePause:
                self.vPause = True
            elif valvePause is False:
                self.vPause = False
            
            # go to next pump and valve state
            if evt == "TIME":
                self.hydro_state += 1
                self.hydro_state %= 10
                self.pumpVal = self.pVals[self.hydro_state]
                [self.topValveVal, self.botValveVal] = self.vVals[self.hydro_state]
                self.hydroTimer.timer_set(new=self.actual_times[self.hydro_state])

                if self.pumpVal and not self.pPause:
                    self.active()
                else:
                    self.active(pwr=0)
                if not self.vPause:
                    if self.topValveVal:
                        self.topValve.on
                    else:
                        self.topValve.off
                    if self.botValveVal:
                        self.botValve.on
                    else:
                        self.botValve.off
        
        if self.test:
            print(f'new user shut off: {self.userToggle}')
            print(f'new overflow condition: {self.overflowCondition}')
            print(f'top valve state: {self.topValve}')
            print(f'bot valve state: {self.botValve}')
    
    # TODO test. any reason to use this?
    def hydro_restart(self):
        self.topValve.off
        self.botValve.off
        self.hydro_state = 0
        self.overflowCondition = False
        self.userToggle = False
        if self.test:
            print("Top valve: off")
            print("Bottom valve: off")

    def active(self, pwr=30):
        if pwr >= 100:
            pwr = 100
        self.pump.value = pwr/100  # TODO set default value to match 1 GPM 
        if pwr <= 0:
            self.UV.value = 0
        else:
            self.UV.value = 1

    def water_height(self):  # in cm, good for ~9 to ~30
        return self.s.depth(self.grab_sonar(), self.hole_depth)

    def overflow_det(self, thresh=None):  # in case water level is too high?
        if thresh is None:
            thresh = self.s_thresh
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
        '''Tries to grab the sonar sensor value without 
        raising an exception halting the program. The reliable range is 9 to 32 cm.'''
        try:
            # might want to lower sample_wait to reduce loop time of menu for better user input
            dist = self.s.raw_distance(sample_size=5, sample_wait=0.01)
        except (SystemError, UnboundLocalError) as e:
            print(f"The sonar is not detected: {e}")
            warnings.warn("The sonar sensor is not detected.")
            dist = 50
        # limiting valid measurements
        if dist >= self.hole_depth:
            dist = self.hole_depth
        elif dist < 0:
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

    test = True
    pH_High = 9
    ph_Low = 4
    EC_High = 2
    EC_Low = 0
    on_timer = timer(3)
    wait_timer = timer(15)
    wait_timer.timer_set()
    userToggle = False
    overflowCondition = "NO OVERFLOW"

    def __init__(self, conditioning_pumps, shrub, pHsens, ECsens, temp, filters=[200, 200, 200]):
        self.pumps = conditioning_pumps
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
        return "Channel Pump State: {}\nPump States: {:.2f} A {:.2f} B {:.2f} N\nWater level: {} cm\npH: {}\
        \nEC: {} mS\nTemp: {} C".format(
            self.hydro.state, self.pumpA.value, self.pumpB.value, self.pumpN.value,  
            self.hydro.grab_sonar(), self.grab_pH(), self.grab_EC(), self.grab_temp(unit="C")
        )
    
    def evt_handler(self, evt=None):
        if self.test:
            print(f'user shut off: {self.userToggle}')
            print(f'overflow condition: {self.overflowCondition}')
            print(evt)
        
        if evt is not None:
            if evt == "OVERFLOW":
                pumpPause = True
                self.overflowCondition = evt
                '''if self.test:
                    print("Top valve: off")
                    print("Bottom valve: off")'''
            elif (evt == "NO OVERFLOW") and (self.overflowCondition == "OVERFLOW"):
                self.overflowCondition = evt
                # prevent overflow condition from overriding the user toggling our outputs
                if self.userToggle is False:
                    pumpPause = False

            # TODO while on timer or wait timer is false, do not take low or high ec/ph values. handle this in shrubber_main
            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                if self.userToggle:
                    pumpPause = True
                elif not self.userToggle:
                    pumpPause = False
            elif evt == "ON TIMER":
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)

            # TODO want some kind of event to start pump at will for testing or maintenance
            elif evt == "TEST":
                pass

            # to stop the valves and pumps in case of emergency. 
            # stored in values to retain behavior across multiple events
            if pumpPause:
                self.pPause = True
            elif pumpPause is False:
                self.pPause = False
            
            if self.pPause:
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)
            # wait for reservoir to mix a little before turning on pumps again
            elif (self.wait_timer.event_no_reset()) and (pumpPause is False):
                if (evt == "LOW EC"):
                    self.pump_active(self.pumpN)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_set()
                elif (evt == "LOW PH"):
                    self.pump_active(self.pumpA)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_set()
                elif (evt == "HIGH PH"):
                    self.pump_active(self.pumpB)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_set()

        else:
            print('Invalid event: '+evt)

    def pump_active(self, pump, pwr=60):
        '''PWM % value to output to motor of pump'''
        if pwr >= 100:
            pwr = 100
        elif pwr <= 0:
            pwr = 0
        pump.value = pwr/100

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
            dist = self.pH.readPH(self.pHsens.voltage)
            if self.test:
                print(f'ph voltage reading: {self.pHsens.voltage:.3f}')
        except Exception as e:
            print(f"The pH sensor is not detected: {e}")
            warnings.warn("The pH sensor is not detected")
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self):
        '''Tries to grab the conductivity sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.EC.readEC(self.ECsens.voltage, self.grab_temp())
            if self.test:
                print(f'ec voltage reading: {self.ECsens.voltage:.3f}')
        except Exception as e:  # TODO find correct exceptions here
            print(f"The conductivity sensor is not detected: {e}")
            warnings.warn("The conductivity sensor is not detected")
            dist = 0
        return self.fEC.filter(dist)

    def grab_temp(self, unit="F"):
        '''Tries to grab the temperature sensor value 
        without raising an exception halting the program'''
        try:
            if unit == 'C':
                dist = float(self.temp.read_temp()['temp_c'])
            elif unit == 'F':
                dist = float(self.temp.read_temp()['temp_f'])
        except Exception as e:
            print(f"The temperature sensor is not detected: {e}")
            warnings.warn("The temperature sensor is not detected")
            dist = 0
        return self.fTemp.filter(dist)

    def sensOutOfRange(self):
        if self.grab_pH >= self.pH_High:
            return 'HIGH PH'
        elif self.grab_pH <= self.ph_Low:
            return 'LOW PH'
        elif self.grab_EC <= self.EC_Low:
            return 'LOW EC'
        else:
            return None