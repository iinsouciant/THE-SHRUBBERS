# state_machine/shrubber.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement state machines to handle events passed to it
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.60 06-Nov-2021 Migration of skeleton from main file
#   v0.65 17-Feb-2022 Drafting menu state machine to interact with hydro

# not sure what this is
from xml.etree.ElementPath import ops
# Butterowrth lowpass filter
from lib.butterworth import b_filter as BF
from lib.DFR import DFRobot_EC as EC
from lib.DFR import DFRobot_PH as PH
# TODO import only stuff we need from library
import time
import csv
import warnings

class timer():
    '''Creates a nonblocking timer to trigger a timer event when checked'''
    timer_time = None

    def __init__(self, interval):
        self.TIMER_INTERVAL = interval

    def timer_event(self):
        if (self.timer_time is not None) and time.monotonic() >= self.timer_time:
            self.timer_time = None
            return True
        else:
            return False

    def timer_set(self):
        self.timer_time = time.monotonic() + self.TIMER_INTERVAL
    
    # TODO for ebb and flow may want to make an alternate version for hours/min?

# TODO split hydro for main pump and conditioning
# TODO make alternating valve method for draining
class hydro():
    '''Part of the Shrubber state machine that handles
    events passed to it, and defines and run the states as needed.'''
    go = None  # indicates direction for turning
    start = "IDLE"
    test = False  # for printing state change and events
    test_q = "Y"
    # pump active and inactive times
    ptimes = [15, 45]
    pt = 0
    # independent timer event for pump/UV. start on
    ptimer = timer(ptimes[pt])
    ptimer.timer_set()
    # valve open time
    vtime = 60*3
    vt1 = 0
    vt2 = 0

    def __init__(self, pump, pHsens, ECsens, buttons, sonar, LCD, valves, filters=[7, 5, 5]):
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
        self.fs = BF.LowPassFilter(filters[0])
        self.fpH = BF.LowPassFilter(filters[1])
        self.fEC = BF.LowPassFilter(filters[2])
        self.pHsens = pHsens
        self.pH = PH.DFRobot_PH()
        self.ECsens = ECsens
        self.EC = EC.DFRobot_EC()
        self.topValve = valves[0]
        self.botValve = valves[1]

    def __repr__(self):
        return "state_machine({}, {}, {}, {}, {}, {})".format(self.pump, self.pHsens,
        self.ECsens, self.bs, self.sonar, self.LCD)
    
    def __str__(self):  # TODO check if we need to update this
        '''Provides formatted sensor values connected to state machine'''
        return "State: {}\nWater level: {} cm\npH: {}\nEC: {} mS".format(
            self.state, self.water_height(), self.grab_pH(), self.grab_EC()
        )  # dummy function names

    def __error(err_string):
        raise Exception(err_string)

    # TODO update this: pass in pause button toggle + event and it chooses next state depending on current state. 
    def evt_handler(self, evt=None, ptime=False, vtime=False, pause=False):
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

        # TODO test
        if ptime:
            self.pt += 1
            self.pt %= 2
            if self.pt == 0:
                print("Pump/UV is on. WIP")
                self.active()
            if self.pt == 1:
                print("Pump/UV is idle. WIP")
                self.pump.value = 0
            self.ptimer = timer(self.ptimes[self.pt])
            self.ptimer.timer_set()

        # TODO valve events/timing so they alternate
        if vtime:
            print('Open one valve. set timer to then open other valve. change which goes first next time')
            # have it called once to open first valve, second time to open second valve, third time to close both
            if self.vt1 == 0:
                if self.vt2 == 0:
                    self.topValve.on
                if self.vt2 == 1:
                    self.botValve.on
            if self.vt1 == 1:
                if self.vt2 == 0:
                    self.botValve.on
                if self.vt2 == 1:
                    self.topValve.on
            # TODO finish
            pass

    def active(self, pwr=30):
        self.pump.value(pwr/100)  # TODO set default value to match 1 GPM 

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
    def test_print(self):
        warnings.warn("This mehod is deprocated, use print(shrub) instead", DeprecationWarning)
        print("State: {}\nWater level: {} cm\npH: {}\nEC: {} mS".format(
            self.state, self.grab_sonar(), self.grab_pH(), self.grab_EC()
        )
        )  # dummy function names

    def pump_pwm(level, pump):
        """This method is deprecated, use GZ.PWMLED value method instead."""
        warnings.warn("use GZ.PWMLED value method and pass in float instead", DeprecationWarning)
        pump.value(level)

    def pump_test(self, drive_time, mag=60):  # for testing each direction of the pumps
        self.pump.value = mag/100
        time.sleep(drive_time)
        self.pump.value = 0
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
    ft = 19*60
    dt = 6*60
    ap = 120
    # Sensor threshold values
    pHH = 9
    pHL = 4
    ECH = 2
    ECL = 0
    sT = 10
    # independent timer event
    idle_timer = timer(5*60)
    idle_timer.timer_set()

    def __init__(self, LCD, shrub):
        self.state = self.start
        self.LCD = LCD
        self.shrub = shrub

        # on boot, check to see if state machine settings exist. if not create w/ default settings
        try:
            with open('Settings.csv', 'r') as f:
                settings = csv.reader(f)
                rows = [row for row in settings if True]
                self.ft = int(rows[0][1])
                self.dt = int(rows[1][1])
                self.ap = int(rows[2][1])
                self.sT = int(rows[3][1])
                self.pHH = int(rows[4][1])
                self.pHL = int(rows[5][1])
                self.ECH = int(rows[6][1])
                self.ECL = int(rows[7][1])
                print("Settings loaded")
        except (IOError) as e:
            if e is IOError:
                print("Settings.txt does not exist. Creating file with default settings.")
            with open(r"Settings.csv", 'w') as f:
                rows = [['Flood Timer', self.ft], 
                    ['Drain Timer', self.dt], 
                    ['Active Pump Timer', self.ap], 
                    ['Gap from top', self.sT],
                    ['pH High Threshold', self.pHH], 
                    ['pH Low Threshold', self.pHL], 
                    ['EC High Threshold', self.ECH], 
                    ['EC Low Threshold', self.ECL],
                ] 
                settings = csv.writer(f)
                settings.writerows(rows)
        
        # list of operation settings
        self.settings = [self.ft, self.dt, self.ap, self.sT, self.pHH, self.pHL, self.ECH, self.ECL, ]

    # TODO figure out more efficient way to save?
    def saveParamChange(self):
        '''Save the new user defined value to the settings file'''
        if (self.parent <= 3) and (self.parent >= 0):
            i = self.parent
        if (self.parent == 'pH THRESH'):
            if (self.child == 'pH HIGH'):
                i = 4
            if (self.child == 'pH LOW'):
                i = 5
        if (self.parent == 'EC THRESH'):
            if (self.child == 'EC HIGH'):
                i = 6
            if (self.child == 'EC LOW'):
                i = 7
        if (self.parent >= 8) or (self.parent < 0):
            raise LookupError("The parent variable does not correspond to a valid save location in the settings")

        self.settings[i] = self.param2change
        with open(r"Settings.csv", 'w') as f:
            rows = [['Flood Timer', self.settings[0]], 
                ['Drain Timer', self.settings[1]], 
                ['Active Pump Timer', self.settings[2]], 
                ['Gap from top', self.settings[3]],
                ['pH High Threshold', self.settings[4]], 
                ['pH Low Threshold', self.settings[5]], 
                ['EC High Threshold', self.settings[6]], 
                ['EC Low Threshold', self.settings[7]],
            ] 
            settings = csv.writer(f)
            settings.writerows(rows)

        # calc time pump needs to be off to let plants be submerged and drained
        inactive_timer = self.settings[0]+self.settings[1]
        # save change to shrub state machine
        self.shrub.times[self.settings[2], inactive_timer]

    def startMenu(self, hover=0):
        '''send the menu back to the first level menu'''
        self.idle_timer.timer_set()
        self.parent = self.start
        self.m1_hover = hover
        self.m2_hover = 0
        self.param2change = 0
        self.child = self.ops[hover]
        self.state = "START MENU"
        # potentially blocking depending on how we implement LCD, maybe threading library to help
        self.LCD.display(self.ops[0]) 

    def idle(self):
        '''send the state machine to the idle state showing sensor values'''
        self.parent = self.start
        self.child = self.ops
        self.state = "IDLE"
        # special lcd state to scroll sensor data while non blocking. maybe multiprocessing? maybe just send on timer
        self.LCD.idle()  

    def timeFormat(sec):
        '''automatically convert seconds to HH:MM:SS format for user to read'''
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}"

    def A_at_m1(self):
        '''handle the menu change when the user selects an operation'''
        self.parent = self.m1_hover
        # for  flood timer, drain active pump timer, 
        if self.m1_hover <= 3:
            self.child = None
            # show setting being changed and current value
            self.LCD.display(f"{self.ops[self.m1_hover]}: {self.settings[self.m1_hover]}")
            if self.m1_hover <= 2:
                self.m2_hover = 3  # HH:MM:SS format, default start at first min mark
                return self.settings[self.m1_hover]
            
            # get allowable water height in reservoir setting and allow user to change it
            if self.m1_hover == 3:
                # 3 sigfigs, e.g. 123 choice of which digit to increase
                self.m2_hover = 2
                return self.settings[self.m1_hover]
        
        # show sublevel to pick low/high threshold values
        if self.m1_hover == 4:
            self.child = 'pH THRESH'
            self.LCD.display(['pH High Threshold', 'pH Low Threshold'])
            return None
        
        # show sublevel to pick low/high threshold values
        if self.m1_hover == 5:
            self.child = 'EC THRESH'
            self.LCD.display(['EC High Threshold', 'EC Low Threshold'])
            return None
        
        # TODO test calibration menus
        if self.m1_hover == 7:
            # sets logic to handle A or B input on next loop
            self.child = "EC CONFIRM"
            self.LCD.display("Press A once EC is fully submerged in solution")
            return None

        if self.m1_hover == 6:
            self.child = "pH CONFIRM"
            self.LCD.display("Press A once EC is fully submerged in solution")
            return None

        # TODO finish menu logic for toggle pump/uv
        if self.m1_hover == 8:
            raise Exception("TODO toggle pump/UV")

        # TODO finish menu logic for toggle peristaltic
        if self.m1_hover == 9:
            raise Exception("TODO toggle conditioning pumps")

    def evt_handler(self, evt=None, timer=False, test=True):  # TODO test menu. see if i can segment this to reduce loop time?
        if test:
            print(f"child: {self.child}")
            print(f'parent: {self.parent}')
            print('event: '+evt)
        # should restart timer for setting the menu state to idle
        if evt is not None:
            self.idle_timer.timer_set()

        # whenever there has been no user input for a while, go back to idle
        if timer:
            self.idle()
        
        # the idle level of the menu
        if (self.child == self.ops) and (self.parent == self.start):
            # wait for user input to start menu
            if (evt == "U_B") or (evt == "D_B") or (evt == "L_B") or (evt == "R_B") \
                or (evt == "A_B") or (evt == "B_B"):
                self.startMenu()
        
        # first level of menu showing configuration options
        elif self.child in self.ops:
            if (evt == "B_B") or (evt == "L_B"):
                # send to level above
                self.idle()
            if (evt == "A_B") or (evt == "R_B"):
                self.param2change = self.A_at_m1()
            if (evt == "U_B"):
                self.m1_hover += 1
                # resets the selected option back to 0 if it goes too high
                self.m1_hover %= len(self.ops)
            if (evt == "D_B"):
                self.m1_hover -= 1
                if self.m1_hover < 0:
                    self.m1_hover = len(self.ops) - 1
        
        # submenu to change timings
        elif self.child not in self.ops:
            # need to make sure once it goes to first submenu, it doesn't raise error here
            if type(self.parent) is int:
                if (self.parent <= 2) and (self.child is None):
                    if (evt == "A_B"):
                        # save changes to file
                        self.saveParamChange(self.param2change)
                        # send back to first level menu
                        self.startMenu()
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = self.ops[self.m1_hover]
                        self.child = None
                    if (evt == "U_B"):
                        # increase HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 10*60*60
                        if self.m2_hover == 1:
                            self.param2change += 1*60*60
                        if self.m2_hover == 2:
                            self.param2change += 10*60
                        if self.m2_hover == 3:
                            self.param2change += 1*60
                        if self.m2_hover == 4:
                            self.param2change += 10
                        if self.m2_hover == 5:
                            self.param2change += 1
                        # max timer
                        if self.param2change > 20*60*60:
                            self.param2change = 20*60*60
                        # TODO want some way to blink the number being hovered over
                        self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                    if (evt == "D_B"):
                        # decrease HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 10*60*60
                        if self.m2_hover == 1:
                            self.param2change -= 1*60*60
                        if self.m2_hover == 2:
                            self.param2change -= 10*60
                        if self.m2_hover == 3:
                            self.param2change -= 1*60
                        if self.m2_hover == 4:
                            self.param2change -= 10
                        if self.m2_hover == 5:
                            self.param2change -= 1
                        # prevent timer going negative
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 6
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 6 - 1
                    
                # save water gap
                if (self.parent == 3) and (self.child is None): 
                    if (evt == "A_B"):
                        self.saveParamChange(self.param2change)
                        # send back to first level menu
                        self.startMenu() 
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = self.ops[self.m1_hover]
                        self.child = None
                    if (evt == "U_B"):
                        # increase the gap based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 100
                        if self.m2_hover == 1:
                            self.param2change += 10
                        if self.m2_hover == 2:
                            self.param2change += 1
                        # max gap
                        if self.param2change > 999:
                            self.param2change = 999
                        self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                    if (evt == "D_B"):
                        # decrease the gap based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 100
                        if self.m2_hover == 1:
                            self.param2change -= 10
                        if self.m2_hover == 2:
                            self.param2change -= 1
                        # min gap
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    if (evt == "L_B"):
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 3 - 1

                # sublevel to choose pH thresholds
                if (self.parent == 4):
                    if (self.child == 'pH THRESH'):
                        self.m2_hover = 0
                        # should show two rows for low and high threshold
                        # pressing up button should choose top option
                        if (evt == "U_B") or (evt == 'A_B'):
                            self.parent = self.child
                            self.child = "pH HIGH"
                            self.param2change = self.settings[4]
                            self.LCD.display(f"pH High Threshold: {self.timeFormat(self.param2change)}")
                        # pressing down should choose bottom option
                        if (evt == "D_B"):
                            self.parent = self.child
                            self.child = "pH LOW"
                            self.param2change = self.settings[5]
                            self.LCD.display(f"pH Low Threshold: {self.timeFormat(self.param2change)}")
                        if (evt == "B_B"):
                            self.startMenu(self.m1_hover)

                # sublevel to choose EC thresholds
                if (self.parent == 5):
                    if (self.child == 'EC THRESH'):
                        self.m2_hover = 0
                        # should show two rows for low and high threshold
                        # pressing up button should choose top option
                        if (evt == "U_B"):
                            self.parent = self.child
                            self.child = "EC HIGH"
                            self.param2change = self.settings[6]
                            self.LCD.display(f"EC High Threshold: {self.timeFormat(self.param2change)}")
                        # pressing down should choose bottom option
                        if (evt == "D_B"):
                            self.parent = self.child
                            self.child = "pH LOW"
                            self.param2change = self.settings[7]
                            self.LCD.display(f"EC Low Threshold: {self.timeFormat(self.param2change)}")
                        if (evt == "B_B"):
                            self.startMenu(self.m1_hover)

            # second level to change pH threshold values
            if (self.parent == 'pH THRESH'):
                if (self.child == 'pH HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange(self.param2change)
                        # send back to first level menu
                        self.startMenu() 
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 4
                        self.child = 'pH THRESH'
                        self.LCD.display(['pH High Threshold', 'pH Low Threshold'])
                    if (evt == "U_B"):
                        # increase the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 1
                        # max pH
                        if self.param2change > 14:
                            self.param2change = 14
                        self.LCD.display(f"pH High Threshold: {self.timeFormat(self.param2change)}")
                    if (evt == "D_B"):
                        # decrease the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        # min gap
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")

            # second level to change pH threshold values
            if (self.parent == 'EC THRESH'):
                if (self.child == 'EC HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange(self.param2change)
                        # send back to first level menu
                        self.startMenu() 
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 5
                        self.child = 'EC THRESH'
                        self.LCD.display(['EC High Threshold', 'EC Low Threshold'])
                    # increase the EC based on hover position. want it to be to two decimal places X.XX
                    if self.m2_hover == 0:
                        self.param2change += 1
                    if self.m2_hover == 1:
                        self.param2change += .1
                    if self.m2_hover == 2:
                        self.param2change += .01
                    # max EC
                    if self.param2change > 10.0:
                        self.param2change = 10.0
                    self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                if (evt == "D_B"):
                    # decrease the EC based on hover position. want it to be to two decimal places X.XX
                    if self.m2_hover == 0:
                        self.param2change -= 1
                    if self.m2_hover == 1:
                        self.param2change -= .1
                    if self.m2_hover == 2:
                        self.param2change -= .01
                    # min EC
                    if self.param2change < 0:
                        self.param2change = 0
                    self.LCD.display(f"{self.ops[self.m1_hover]}: {self.timeFormat(self.param2change)}")
                if (evt == "R_B"):
                    # change hover position. loop if too far right
                    self.m2_hover += 1
                    self.m2_hover %= 3
                if (evt == "L_B"):
                    # change hover position. loop if too far left
                    self.m2_hover -= 1
                    if self.m2_hover < 0:
                        self.m2_hover = 3 - 1

            # second level submenus to confirm calibration of sensors
            if self.child == "EC_CONFIRM":
                if (evt == "A_B") or (evt == "R_B"):
                    # TODO test
                    self.LCD.display(self.shrub.EC_calibration())
                    self.startMenu()
                if (evt == "B_B") or (evt == "L_B"):
                    self.startMenu(self.m1_hover)

            if self.child == "PH_CONFIRM":
                if (evt == "A_B") or (evt == "R_B"):
                    # TODO test
                    self.LCD.display(self.shrub.pH_calibration())
                    self.startMenu()
                if (evt == "B_B") or (evt == "L_B"):
                    self.startMenu(self.m1_hover)