# state_machine/pumps.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement state machines to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.42 27-Mar-2022 Migration of hydro class from LCDmenu.py
#   v0.85 13-Apr-2022 First draft state machines. Sequence approach for simple loop of operation
#                     for the channel pump and valves, few conditions to check when enabling or
#                     disabling outputs. Nothing to stop timer dictating state. Conditioner
#                     only checks for values out of range or potentially harmful conditions before 
#                     operation. Next steps: save state to file periodically in case of brief shutoff

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
    # channel flooded, drained, and  pump active times
    ptimes = [60*60*3, 60*60*3.5, 60*20]
    valveDrainTime = 60*20
    actual_times = [ptimes[2], 0, 0, 0, 0]
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

    # limits how often the sonar sensor is grabbed to reduce use of sleep
    sonar_timer = timer(2)
    sonar_timer.timer_set()
    last_sonar = 0

    # TODO update w/ actual measurement
    hole_depth = 35*2.54  # 35in to cm
    s_thresh = 14  # cm

    str_timer = timer(10)
    str_timer.timer_set()

    def __init__(self, pump, sonar, valves, UV, filter=200, test=False):
        self.pump = pump
        self.s = sonar
        self.fs = BF.LowPassFilter(filter)
        self.topValve = valves[0]
        self.botValve = valves[1]
        self.UV = UV
        # join valve and channel pump times together to create simple sequence
        self.__ptimes2actual(self.ptimes)

        self.test = test  # for printing state change and events

    def __repr__(self):
        return "state_machine({}, {}, {}, {})".format(self.pump, self.s, self.topValve, self.botValve)
    
    def __str__(self):  # TODO check if we need to update this  
        '''Provides formatted sensor values connected to state machine'''
        if self.test and self.str_timer.timer_event():
            print(f'next cycle timer: {self.hydroTimer.time_remaining()}')
            self.str_timer.timer_set()
        return "Pump: {}\nValves: {}, {}\nWater level: {} cm\nValves paused? {}\n".format(
            self.pumpVal, self.botValveVal, self.topValveVal, self.water_height(), self.vPause
        )

    def __error(err_string):
        raise Exception(err_string)

    def update_settings(self, ptimes, max_level, cycle=None):
        self.__ptimes2actual(ptimes)
        self.hydroTimer.new_interval_timer(self.actual_times[self.hydro_state])
        self.s_thresh = self.hole_depth-max_level
        # TODO test
        if cycle is not None:
            self.hydro_state = cycle[0]
            self.hydroTimer = timer(cycle[1])
            self.hydroTimer.timer_set()
    
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
            print(f'shrub user shut off: {self.userToggle}')
            print(f'shrub overflow condition: {self.overflowCondition}')
            print(f'new shrub event: {evt}')
        
        # getting stuck on no overflow even when it should be overflow
        if evt is not None:
            if evt == 'TEST':
                self.topValve.on()
                self.botValve.on()
                self.active()
                sleep(6)
                self.topValve.off()
                self.botValve.off()
                self.active(pwr=0)
                if self.pumpVal: self.active()
                if self.topValveVal: self.topValve.on()
                if self.botValveVal: self.botValve.on()

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
                    pumpPause = False

            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                if self.userToggle:
                    pumpPause = True
                    valvePause = True
                elif not self.userToggle:
                    pumpPause = False
                    valvePause = False

            # to stop the valves and pumps in case of emergency. 
            # stored in values to retain behavior across multiple events
            self.pPause = True if pumpPause else False
            self.vPause = True if valvePause else False
            
            # go to next pump and valve state
            if evt == "TIME":
                self.hydro_state += 1
                self.hydro_state %= 10
                self.pumpVal = self.pVals[self.hydro_state]
                [self.topValveVal, self.botValveVal] = self.vVals[self.hydro_state]
                self.hydroTimer.timer_set(new=self.actual_times[self.hydro_state])

                self.active if (self.pumpVal and (not self.pPause)) else self.active(pwr=0)
                if (not self.vPause) and (self.overflowCondition != "OVERFLOW"):
                    self.topValve.on() if self.topValveVal else self.topValve.off()
                    self.botValve.on() if self.botValveVal else self.botValve.off()
        
        if self.test:
            print(f'new user shut off: {self.userToggle}')
            print(f'new overflow condition: {self.overflowCondition}')
            print(f'top valve state: {self.topValveVal}')
            print(f'bot valve state: {self.botValveVal}')
    
    #  any reason to use this?
    def hydro_restart(self):
        self.topValve.off()
        self.botValve.off()
        self.hydro_state = 0
        self.overflowCondition = False
        self.userToggle = False
        if self.test: print("Top valve: off\nBottom valve: off") 

    def active(self, pwr=40):
        if pwr >= 100:
            pwr = 100 
        elif pwr <= 0:
            pwr = 0
        self.pump.value = pwr/100  # TODO set default value to match 1 GPM 
        self.UV.value = 0 if pwr == 0 else 1

    def water_height(self) -> float:  # in cm, good for ~9 to ~30
        return self.s.depth(self.grab_sonar(), self.hole_depth)

    def overflow_det(self, height_thresh=None) -> bool:  # in case water level is too high?
        height_thresh = (self.hole_depth - self.s_thresh) if height_thresh is None else height_thresh
        height = self.water_height()
        try:
            return True if height >= height_thresh else False
        except TypeError as e:
            print(e)
            return True
    
    def grab_sonar(self) -> float:
        '''Tries to grab the sonar sensor value without 
        raising an exception halting the program. The reliable range is 9 to 32 cm.'''
        # timer to limit sample rate for faster loop time
        if self.sonar_timer.timer_event():
            try:
                self.s.temperature = self.conditioner.grab_temp(unit='C')
                dist = self.s.raw_distance(sample_size=10, sample_wait=0.01)
            except (SystemError, UnboundLocalError) as e:
                print(f"The sonar is not detected: {e}")
                warnings.warn("The sonar sensor is not detected.")
                dist = 50
            # limiting valid measurements
            if dist >= self.hole_depth:
                dist = self.hole_depth
            elif dist < 0:
                dist = 0
            self.last_sonar = self.fs.filter(dist)
            self.sonar_timer.timer_set()
            if self.test:
                print(f'New sonar value: {self.last_sonar}')
        else:
            if self.test:
                #print(f'Old sonar value grabbed: {self.last_sonar}')
                pass

        return self.last_sonar

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
    on_timer = timer(3)
    wait_timer = timer(15)
    wait_timer.timer_set()
    userToggle = False
    overflowCondition = "NO OVERFLOW"
    pPause = False
    therm_timer = timer(5)
    therm_timer.timer_set()
    last_therm_val = 0
    EC_print = timer(5)
    EC_print.timer_set()
    ph_print = timer(5)
    ph_print.timer_set()
    evt_print = timer(1.5)
    evt_print.timer_set()

    def __init__(self, conditioning_pumps, shrub, pHsens, ECsens, temp, filters=[200, 200, .5], test=False):
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
        self.fTemp_C = BF.LowPassFilter(filters[2])
        self.fTemp_F = BF.LowPassFilter(filters[2])
        self.filters = [self.fpH, self.fEC, self.fTemp_C]
        self.test = test

    def __repr__(self):
        return "state_machine({}, {}, {}, {}, {}, {})".format(self.pumpA, self.pumpB, self.pumpC, 
        self.pHsens, self.ECsens, self.temp)

    def __str__(self):
        '''Provides formatted sensor values connected to state machine'''
        return "Pump States: {:.2f} A {:.2f} B {:.2f} N\nWater level: {} cm\npH: {}\
        \nEC: {} mS\nTemp: {} C".format(
            self.pumpA.value, self.pumpB.value, self.pumpN.value,  
            self.hydro.grab_sonar(), self.grab_pH(), self.grab_EC(test=True), self.grab_temp(unit="C")
        )
    
    def update_settings(self, pH_High, pH_Low, EC_High, EC_Low):
        self.pH_High = pH_High
        self.pH_Low = pH_Low
        self.EC_High = EC_High
        self.EC_Low = EC_Low
    
    def evt_handler(self, evt=None):
        if self.test and self.evt_print.event_no_reset():
            print(f'cond user shut off: {self.userToggle}')
            print(f'cond overflow condition: {self.overflowCondition}')
            print(f'new cond event: {evt}')
            self.evt_print.timer_set()

        pumpPause = None

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

            # TODO while on timer or wait timer is false, do not take low or high ec/ph values.
            # handle this in shrubber_main
            
            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                if self.userToggle:
                    pumpPause = True
                elif not self.userToggle:
                    pumpPause = False

            # when pump is done pumping, turn all off
            elif evt == "ON TIMER":
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)

            # start pump at will for testing or maintenance
            elif evt == "TEST":
                for pump in self.pumps:
                    self.pump_active(pump)
                sleep(6)
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)

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
            elif (self.wait_timer.event_no_reset()) and (self.pPause is False):
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
        if self.test and self.evt_print.timer_event():
            print(f'new pump vals: \nnutrient: {self.pumpN.is_active} \
acid: {self.pumpA.is_active} base: {self.pumpB.is_active}')
            self.evt_print.timer_set()

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
            if self.test and self.ph_print.timer_event():
                print(f'ph voltage reading: {self.pHsens.voltage:.3f}')
                self.ph_print.timer_set()
        except Exception as e:
            if self.ph_print.timer_event():
                print(f"The pH sensor is not detected: {e}")
                warnings.warn("The pH sensor is not detected")
                self.ph_print.timer_set()
            dist = 0
        return self.fpH.filter(dist)

    def grab_EC(self, test=False) -> float:
        '''Tries to grab the conductivity sensor value 
        without raising an exception halting the program'''
        try:
            dist = self.EC.readEC(self.ECsens.voltage, self.grab_temp())*1000
            if self.test or test:
                if self.EC_print.timer_event():
                    print(f'ec voltage reading: {self.ECsens.voltage:.3f}')
                    self.EC_print.timer_set()
        except Exception as e:  # TODO find correct exceptions here
            if self.EC_print.timer_event():
                self.EC_print.timer_set()
                print(f"The conductivity sensor is not detected: {e}")
                warnings.warn("The conductivity sensor is not detected")
            dist = 0
        return self.fEC.filter(dist)

    def grab_temp(self, unit="F") -> float:
        '''Tries to grab the temperature sensor value 
        without raising an exception halting the program'''
        if self.therm_timer.timer_event():
            self.therm_timer.timer_set()
            try:
                if unit == 'C':
                    dist = float(self.temp.read_temp()['temp_c'])
                elif unit == 'F':
                    dist = float(self.temp.read_temp()['temp_f'])
                else:
                    print("invalid unit. Try 'F' or 'C'")
            except Exception as e:
                # TODO maybe have a protocol to restart the system to relaunch the 1-wire 
                # or try to cd back into the sensor and get readings again. currently,
                # once it disconnects it stays disconnected until program rescans
                print(f"The temperature sensor is not detected: {e}")
                warnings.warn("The temperature sensor is not detected")
                dist = 0
            self.last_therm_val = dist
        else:
            dist = self.last_therm_val
        if unit == 'F':
            return self.fTemp_F.filter(dist)
        elif unit == 'C':
            return self.fTemp_C.filter(dist)

    def sensOutOfRange(self):
        solutions = [None, None, None]
        pH_val = self.grab_pH()
        if (pH_val >= self.pH_High) and (self.on_timer.time_remaining() is not None):
            solutions[0] = 'HIGH PH'
        elif (pH_val <= self.ph_Low) and (self.on_timer.time_remaining() is not None):
            solutions[1] = 'LOW PH'
        solutions[2] = 'LOW EC' if (self.grab_EC() <= self.EC_Low) \
            and (self.on_timer.time_remaining() is not None) else None
        return solutions