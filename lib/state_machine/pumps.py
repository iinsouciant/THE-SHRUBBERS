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


from lib.butterworth import b_filter as BF
from lib.DFR import DFRobot_EC as EC
from lib.DFR import DFRobot_PH as PH   
from lib.state_machine.LCDmenu import timer
from time import sleep
import warnings

class EventError(Exception):
    '''Invalid event received by event handler'''
    pass

class TimerError(Exception):
    '''Invalid timer duration received'''
    pass

class hydro():
    '''Part of the Shrubber state machine that handles
    events passed to it, and defines and run the states as needed.'''
    # channel flooded, drained, and  pump active times
    ptimes = [60*60*3, 60*60*3.5, 60*20]
    # how long to leave each valve open to drain channels
    valveDrainTime = 60*15

    actual_times = [ptimes[2], 0, 0, 0, 0]
    # sequences to cycle through for valve opening
    pVals = (   1,      0,      0,      0,      0) * 2
    vVals = ((0, 0), (0, 0), (1, 0), (0, 1), (0, 0), (0, 0), (0, 0), (0, 1), (1, 0), (0, 0))

    # flags to pause outputs due to event or user
    pPause = False
    vPause = False
    overflowCondition = "NO OVERFLOW"
    userToggle = False
    valveToggle = False

    # tracking current state of outputs
    hydro_state = 0
    pumpVal = pVals[hydro_state]
    [topValveVal, botValveVal] = vVals[hydro_state]
    hydroTimer = timer(actual_times[hydro_state])

    # limits how often the sonar sensor is grabbed to reduce loop time
    sonar_timer = timer(2)
    sonar_timer.timer_set()
    last_sonar = 0

    # TODO update w/ actual measurement
    hole_depth = 35*2.54  # 35in to cm
    s_thresh = 8  # cm

    str_timer = timer(10)
    str_timer.timer_set()

    # counter to trigger outputs during startup process
    n = 0

    def __init__(self, pump, sonar, valves, UV, filter=200, test=False):
        self.pump = pump
        self.s = sonar
        self.fs = BF.LowPassFilter(.5)
        self.topValve = valves[0]
        self.botValve = valves[1]
        self.UV = UV
        # join valve and channel pump times together to create simple sequence
        self.actual_times = self.__ptimes2actual(self.ptimes)

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

    # called once w/ startup of LCDmenu reading Settings.csv
    def update_settings(self, ptimes, max_level, cycle=None):
        self.actual_times = self.__ptimes2actual(ptimes)
        self.hydroTimer.new_interval_timer(self.actual_times[self.hydro_state])
        self.s_thresh = self.hole_depth-max_level
        # TODO test
        if cycle is not None:
            self.hydro_state = cycle[0]
            self.hydroTimer = timer(cycle[1])
            self.hydroTimer.timer_set()
        # enable outputs on startup once new operating values are passed in from LCDmenu
        if self.n == 0:
            self.n += 1
            self.pumpVal = self.pVals[self.hydro_state]
            [self.topValveVal, self.botValveVal] = self.vVals[self.hydro_state]
            self.hydroTimer = timer(self.actual_times[self.hydro_state])
            self.hydroTimer.timer_set()
            
            if self.pumpVal: self.active()
            self.topValve.on() if self.topValveVal else self.topValve.off()
            self.botValve.on() if self.botValveVal else self.botValve.off()
    
    def __ptimes2actual(self, ptimes) -> list:
        '''Convert condensed list from user settings to list for timers to use'''
        # TODO implement logic to handle 0 timer length and/or limit min
        self.ptimes = ptimes
        actual_times = []
        self.valveDrainTime = min(ptimes[2] / 2, 60*15)  # not sure how we want the behavior or the valves to be
        actual_times[0] = ptimes[2]  # pump fill channel
        actual_times[1] = ptimes[0]  # pump stop and leaved channel flooded
        actual_times[2] = self.valveDrainTime  # first valve open
        actual_times[3] = self.valveDrainTime  # first valve close second valve open
        actual_times[4] = ptimes[1] - 2 * self.valveDrainTime  # close both valves
        if actual_times[4] < 0:
            actual_times[4] = 0
        actual_times *= 2
        for time in actual_times:
            assert time >= 0
        return actual_times
        
    
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
                self.testOutputs(time=6)

            elif evt == "OVERFLOW":
                self.vPause = True
                self.overflowCondition = evt
                if self.test:
                    print("Top valve: off")
                    print("Bottom valve: off")
                    
            elif (evt == "NO OVERFLOW") and (self.overflowCondition == "OVERFLOW"):
                self.overflowCondition = evt
                # prevent overflow condition from overriding the user toggling our outputs
                self.vPause = True if self.userToggle else False
                self.pPause = True if self.userToggle else False

            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                self.pPause = self.userToggle
                self.vPause = self.userToggle

            if self.pPause:
                self.active(pwr=0)
            # if to prevent sudden switch on off
            if evt != 'VALVE TOGGLE':
                if self.vPause:
                    self.topValve.off()
                    self.botValve.off()

            # user override the pause conditions
            if evt == 'VALVE TOGGLE':
                self.valveToggle = not self.valveToggle
                self.topValve.on() if self.valveToggle else self.topValve.off()
                self.botValve.on() if self.valveToggle else self.botValve.off()
            
            # go to next pump and valve state
            elif evt == "TIME":
                self.hydro_state += 1
                self.hydro_state %= 10
                self.pumpVal = self.pVals[self.hydro_state]
                [self.topValveVal, self.botValveVal] = self.vVals[self.hydro_state]
                self.hydroTimer.timer_set(new=self.actual_times[self.hydro_state])

                self.active() if (self.pumpVal and (not self.pPause)) else self.active(pwr=0)
                if (not self.vPause) and (self.overflowCondition != "OVERFLOW"):
                    self.topValve.on() if self.topValveVal else self.topValve.off()
                    self.botValve.on() if self.botValveVal else self.botValve.off()
            
            # re-enable outputs if they were meant to be on after overflow is cleared
            elif evt == 'NO OVERFLOW':
                if self.vPause is False:
                    self.topValve.on() if self.topValveVal else self.topValve.off()
                    self.botValve.on() if self.botValveVal else self.botValve.off()
        
        if self.test:
            print(f'new user shut off: {self.userToggle}')
            print(f'new overflow condition: {self.overflowCondition}')
            print(f'top valve state: {self.topValveVal}')
            print(f'bot valve state: {self.botValveVal}')
    
    #  any reason to use this?
    def hydro_restart(self):
        '''Shuts off vakves and resets user toggling'''
        self.topValve.off()
        self.botValve.off()
        self.hydro_state = 0
        self.overflowCondition = False
        self.userToggle = False
        if self.test: print("Top valve: off\nBottom valve: off") 

    def active(self, pwr=80):
        '''Sets the pump and UV power level'''
        if pwr >= 100:
            val = 100 
        elif pwr <= 0:
            val = 0
        else:
            val = pwr
        self.pump.value = val/100  # TODO set default value to match 1 GPM 
        self.UV.value = 0 if val == 0 else 1

    def water_height(self, hole_depth=None) -> float:
        '''Estimate the water level (cm) in the reservoir given the hole depth.
        Recommended for a range of 9 to 30 cm from the sonar sensor for most accurate 
        readings.'''
        self.hole_depth = self.hole_depth if hole_depth is None else hole_depth
        return self.s.depth(self.grab_sonar(), self.hole_depth)

    def overflow_det(self, height_thresh=None) -> bool:
        '''Check to see if the water level is higher than the acceptable value'''
        height_thresh = (self.hole_depth - self.s_thresh) if height_thresh is None else height_thresh
        height = self.water_height()
        try:
            return True if height >= height_thresh else False
        except TypeError as e:
            print(e)
            return True
    
    def grab_sonar(self) -> float:
        '''Tries to grab the sonar sensor value without raising 
        an exception halting the program. The reliable range is 
        9 to 32 cm.'''
        # timer to limit sample rate for faster loop time
        if self.sonar_timer.timer_event():
            try:
                self.s.temperature = self.conditioner.grab_temp(unit='C')
                dist = self.s.raw_distance(sample_size=10, sample_wait=0.01)
            except (SystemError, UnboundLocalError) as e:
                print(f"The sonar is not detected: {e}")
                warnings.warn("The sonar sensor is not detected.")
                dist = 50
            # limiting valid range of measurements
            if dist >= self.hole_depth:
                dist = self.hole_depth
            elif dist < 0:
                dist = 0
            self.last_sonar = dist
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

    def testOutputs(self, time=float, mag=30):
        '''Test to see if the outputs turn on'''
        self.topValve.on()
        self.botValve.on()
        self.active(mag)
        self.conditioner.evt_handler(evt='TEST')
        self.topValve.off()
        self.botValve.off()
        self.active(pwr=0)
        sleep(2)
        if self.pumpVal: self.active()
        if self.topValveVal: self.topValve.on()
        if self.botValveVal: self.botValve.on()


class conditioner():
    '''Class to handle the state machine behavior of the nutrient solution conditioning pumps'''
    # default threshold values
    pH_High = 9
    ph_Low = 4
    EC_High = 2
    EC_Low = 0
    # how long to run the conditioning pumps for
    on_timer = timer(3)
    # wait for the reservoir to mix before checking if values are out of range
    wait_timer = timer(15)
    wait_timer.timer_set()
    userToggle = False
    overflowCondition = "NO OVERFLOW"
    pPause = False
    # how often to check temp to increase loop time
    therm_timer = timer(5)
    therm_timer.timer_set()
    last_therm_val = 0
    # how often to print EC values for readability during testing
    EC_print = timer(5)
    EC_print.timer_set()
    # how often to print pH values for readability during testing
    ph_print = timer(5)
    ph_print.timer_set()
    # how often to print event values for readability during testing
    evt_print = timer(1.5)
    evt_print.timer_set()

    def __init__(self, conditioning_pumps, shrub, pHsens, ECsens, temp, filters=[200, 200, .5], test=False):
        self.pumps = conditioning_pumps
        self.pumpA = conditioning_pumps[0]
        self.pumpB = conditioning_pumps[1]
        self.pumpN = conditioning_pumps[2]
        # instance of channel pump state machine for interactions between the two state machines
        self.hydro = shrub
        self.temp = temp
        # analog voltage readings
        self.pHsens = pHsens
        self.ECsens = ECsens
        # sensor classes that output voltage to measurement values
        self.pH = PH.DFRobot_PH()
        self.EC = EC.DFRobot_EC()
        
        self.fpH = BF.LowPassFilter(filters[0])
        self.fEC = BF.LowPassFilter(filters[1])
        self.fTemp_C = BF.LowPassFilter(filters[2])
        self.fTemp_F = BF.LowPassFilter(filters[2])

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
        '''Take saved user settings and update instance operation'''
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
            
            # user toggle overrides overflow until next loop where overflow event is passed. change this?
            elif evt == "USER TOGGLE":
                self.userToggle = not self.userToggle
                pumpPause = True if self.userToggle else False

            # when pump is done pumping, turn all off
            elif evt == "ON TIMER":
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)
                self.wait_timer.timer_set()

            # start pump at will for testing or maintenance
            elif evt == "TEST":
                for pump in self.pumps:
                    self.pump_active(pump)
                sleep(6)
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)

            elif (evt != "LOW EC") and (evt != "LOW PH") and (evt != "LOW EC"):
                raise EventError('Invalid event: '+evt)

            # to stop the valves and pumps in case of emergency. 
            # stored in values to retain behavior across multiple events
            self.pPause = pumpPause if pumpPause is not None else self.pPause
            
            if self.pPause:
                for pump in self.pumps:
                    self.pump_active(pump, pwr=0)

            # wait for reservoir to mix a little before turning on pumps again
            else:
                if (evt == "LOW EC"):
                    self.pump_active(self.pumpN)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_event()
                elif (evt == "LOW PH"):
                    self.pump_active(self.pumpA)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_event()
                elif (evt == "HIGH PH"):
                    self.pump_active(self.pumpB)
                    self.on_timer.timer_set()
                    self.wait_timer.timer_event()

        else:
            # if no sensor out of range it will pass in a none event
            pass

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

    def grab_pH(self) -> float:
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
            # check if it is time to access temp
            # limited as it requires accessing file system and slows loop
            self.therm_timer.timer_set()
            try:
                if unit == 'C':
                    dist = float(self.temp.read_temp()['temp_c'])
                elif unit == 'F':
                    dist = float(self.temp.read_temp()['temp_f'])
                else:
                    print("invalid unit. Try 'F' or 'C'")
            except Exception as e:
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

    def sensOutOfRange(self) -> list:
        '''Gives list of strings to pass to event handler. Checks for
        High pH, low pH, and low EC as there is no behavior for High EC currently'''
        solutions = [None, None, None]
        pH_val = self.grab_pH()
        if (pH_val >= self.pH_High) and (self.on_timer.time_remaining() is not None):
            solutions[0] = 'HIGH PH'
        elif (pH_val <= self.ph_Low) and (self.on_timer.time_remaining() is not None):
            solutions[1] = 'LOW PH'
        solutions[2] = 'LOW EC' if (self.grab_EC() <= self.EC_Low) \
            and (self.on_timer.time_remaining() is not None) else None
        return solutions
