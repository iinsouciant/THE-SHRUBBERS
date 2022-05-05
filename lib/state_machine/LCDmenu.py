# state_machine/LCDmenu.py - ME 195 Shrubbers Project Code
# Raspberry Pi 4B/3B
#
# Implement the menu state machine to handle user input events and change the pump state machines
#
# Written by Gustavo Garay, Summer Selness, Ryan Sands (sandsryanj@gmail.com)
#   v0.60 06-Nov-2021 Migration of skeleton from main file
#   v0.65 17-Feb-2022 Drafting menu state machine to interact with hydro
#   v0.90 23-Mar-2022 Working LCD integration and menu for 8 operations. CSV file functionality complete
#   v1.00 27-Mar-2022 Moving pump state machines to separate file for organization
#   v1.15 13-Apr-2022 Add functionality to have menu to send settings to other state machines.
#                     Timer functionality increased to handle None exceptions and other use cases.

# TODO import only stuff we need from library
from time import sleep, monotonic
import csv
import warnings
from lib.lcd.lcd import CursorMode

class timer():
    '''Creates a nonblocking timer to trigger a timer event when checked. Use timer_set to start the timer.
    Changing TIMER_INTERVAL does not update the new end time of the timer. '''
    timer_time = None

    def __init__(self, interval):
        try:
            self.TIMER_INTERVAL = float(interval)
        except ValueError as e:
            warnings.warn(f'Invalid timer input: {e}\nSetting interval to None')
            self.TIMER_INTERVAL = None

    def timer_event(self):
        '''Checks to see if the time has passed. If it has, turns off timer and returns True. If the timer was not set,
        returns None'''
        if (self.timer_time is not None) and monotonic() >= self.timer_time:
            self.timer_time = None
            return True
        elif self.timer_time is None:
            return None
        else:
            return False

    def event_no_reset(self):
        '''Checks to see if the time has passed. If it has, returns True. Must be manually stopped/reset'''
        if (self.timer_time is not None) and monotonic() >= self.timer_time:
            # self.timer_time = None
            return True
        elif self.timer_time is None:
            return None
        else:
            return False

    def timer_set(self, new=None):
        '''Restarts timer from time of method call'''
        if (type(new) is int) or (type(new) is float):
            self.TIMER_INTERVAL = new
        try:
            self.timer_time = monotonic() + self.TIMER_INTERVAL
        except TypeError as e:
            if self.TIMER_INTERVAL is None:
                print("Timer interval set to None")
                self.timer_time = None
            else:
                pass

    def time_remaining(self):
        '''Checks to see if the time has passed. If it not, returns float of difference. No reset if time has passed'''
        if (self.timer_time is not None) and monotonic() >= self.timer_time:
            return None
        else:
            return self.timer_time - monotonic()
    
    def new_interval_timer(self, new_interval):
        '''Adjusts the remaining time of the timer to fit new interval'''
        if (new_interval is not None) and (self.TIMER_INTERVAL is not None):
            if self.timer_time is None:
                self.TIMER_INTERVAL = new_interval
                self.timer_set()
            else:
                self.timer_time += new_interval - self.TIMER_INTERVAL
        else: 
            self.timer_time = None
        self.TIMER_INTERVAL = new_interval


class menu():
    ''' Implement a menu state machine x levels deep to allow the user to
    configure the shrubber state machine without blocking operations elsewhere
    and simultaneously output information to the LCD screen.'''
    start = "IDLE"
    # TODO incorporate operation to turn on all outputs
    ops = ("Flood timer", "Channel Pump timer", "Empty timer",
        "Gap from top", "pH thresholds", "EC thresholds", 
        "Calibrate pH", "Calibrate EC", "Shut off pump+UV+valve", 
        "Shut off nutrient conditioners", "Test outputs")
    parent = start
    child = ops
    m1_hover = 0
    m2_hover = 0
    ft = 19*60  # flood timer
    et = 6*60  # empty timer
    ap = 120  # active pump timer to flood channels
    # Sensor threshold values
    pHH = 9
    pHL = 4
    ECH = 2
    ECL = 0.01
    sT = 16  # sonar threshold
    # independent timer event
    idle_timer = timer(3*60)
    idle_timer.timer_set()
    idle_printer = timer(8)
    _idle_n = 0

    def __init__(self, LCD, shrub, conditioner):
        self.state = self.start
        self.LCD = LCD
        self.shrub = shrub
        self.conditioner = conditioner

        # TODO add row to remember what hydro state we were last on so that it doesn't start pumping on reboot
        # periodically add what time is remaining on pump timer as well due to long duration
        # on boot, check to see if state machine settings exist. if not create w/ default settings
        try:
            with open('Settings.csv', 'r') as f:
                settings = csv.reader(f)
                rows = [row for row in settings if True]
                self.ft = int(rows[0][1])
                self.ap = int(rows[1][1])
                self.et = int(rows[2][1])
                self.sT = int(rows[3][1])
                self.pHH = float(rows[4][1])
                self.pHL = float(rows[5][1])
                self.ECH = float(rows[6][1])
                self.ECL = float(rows[7][1])
                print("Settings loaded")

        except (IOError) as e:
            if e is IOError:
                print("Settings.csv does not exist. Creating file with default settings.")
            with open(r"Settings.csv", 'w') as f:
                rows = [[self.ops[0], self.ft], 
                    [self.ops[1], self.ap], 
                    [self.ops[2], self.et], 
                    [self.ops[3], self.sT],
                    ['pH High Threshold', self.pHH], 
                    ['pH Low Threshold', self.pHL], 
                    ['EC High Threshold', self.ECH], 
                    ['EC Low Threshold', self.ECL],
                ] 
                settings = csv.writer(f)
                settings.writerows(rows)
        
        # list of operation settings
        self.settings = [self.ft, self.ap, self.et, self.sT, self.pHH, self.pHL, self.ECH, self.ECL, ]
        self.shrub.update_settings([self.settings[0], self.settings[1], self.settings[2]], self.settings[3])
        self.conditioner.update_settings(self.settings[4], self.settings[5], self.settings[6], self.settings[7])
        self.conditioner.pH_High = self.pHH
        self.conditioner.pH_Low = self.pHL
        self.conditioner.EC_High = self.ECH
        self.conditioner.EC_Low = self.ECL
        # calc time pump needs to be off to let plants be submerged and drained
        # save change to shrub state machine
        self.shrub.ptimes = [self.settings[0], self.settings[1], self.settings[2]]

    # TODO figure out more efficient way to save?
    def saveParamChange(self):
        '''Save the new user defined value to the settings file'''
        if type(self.parent) is int:
            if (self.parent <= 3) and (self.parent >= 0):
                i = self.parent
            if (self.parent >= 8) or (self.parent < 0):
                self.LCD.print("The parent variable does not correspond to a valid save location in the settings")
                raise LookupError("The parent variable does not correspond to a valid save location in the settings")
        elif (self.parent == 'pH THRESH'):
            if (self.child == 'pH HIGH'):
                i = 4
            if (self.child == 'pH LOW'):
                i = 5
        elif (self.parent == 'EC THRESH'):
            if (self.child == 'EC HIGH'):
                i = 6
            if (self.child == 'EC LOW'):
                i = 7
        else:
            raise LookupError("Invalid parent setting to save")

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
            new_settings = csv.writer(f)
            new_settings.writerows(rows)

        # save change to shrub state machine
        self.shrub.update_settings([self.settings[0], self.settings[1], self.settings[2]], self.settings[3])
        self.conditioner.update_settings(self.settings[4], self.settings[5], self.settings[6], self.settings[7])
        self.conditioner.pH_High = self.settings[4]
        self.conditioner.pH_Low = self.settings[5]
        self.conditioner.EC_High = self.settings[6]
        self.conditioner.EC_Low = self.settings[7]
        self.LCD.clear()
        self.LCD.set_cursor_mode(CursorMode.HIDE)
        self.LCD.print("Settings saved!")
        # show message until user input
        self.child = "WAIT"
        self.parent = None

    def startMenu(self, hover=0):
        '''Send the menu back to the first level menu'''
        self.idle_timer.timer_set()
        self.parent = self.start
        self.m1_hover = hover
        self.m2_hover = 0
        self.param2change = 0
        self.child = self.ops[hover]
        self.state = "START MENU"
        self.LCD.clear()
        self.LCD.print(self.ops[hover]) 

    def idle(self):
        '''Send the state machine to the idle state showing sensor values'''
        self.parent = self.start
        self.child = self.ops
        self.state = "IDLE"
        self.idle_printer.timer_set()
        self.LCD.clear()
        self.LCD.print("Menu is now idle.")
    
    def idle_print(self):
        # save old strings printed for scrolling effect
        try:
            c = self._b
        except Exception as e:
            c = ""
        try:
            self._b = self._a
        except Exception as e:
            self._b = ""
        
        self.LCD.clear()
        self._idle_n += 1
        self._idle_n %= 4  # loop through each sensor
        n = self._idle_n
        # set timer to wait for next call to idle_print
        self.idle_printer.timer_set()
        if n == 0:
            self._a = f"Water level: {self.shrub.water_height():.1f} cm"
        if n == 1:
            self._a = f"pH level: {self.conditioner.grab_pH():.1f}"
        if n == 2:
            self._a = f"Conductivity level: {self.conditioner.grab_EC():.2f} mS"
        if n == 3:
            self._a = f"Water temp: {self.conditioner.grab_temp(unit='F'):.2f} F"
        
        # to create scrolling effect
        self.LCD.print(self._a)
        [row, col] = self.LCD.cursor_pos()
        # check if cursor wrapped around
        if col == 0:
            self.LCD.set_cursor_pos(int(row), 0)
        else:
            self.LCD.set_cursor_pos(int(row)+1, 0)
        self.LCD.print(self._b)
        [row, col] = self.LCD.cursor_pos()
        row = int(row)
        col = int(col)
        # check if cursor wrapped around
        if col != 0:
            row += 1
        if row <= 3:
            self.LCD.set_cursor_pos(row, 0)
            self.LCD.print(c)

    def timeFormat(self, sec):
        '''automatically convert seconds to HH:MM:SS format for user to read'''
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def A_at_m1(self):
        '''handle the menu change when the user selects an operation'''
        self.parent = self.m1_hover
        self.LCD.clear()
        # for  flood timer, drain active pump timer, 
        if self.m1_hover <= 3:
            self.child = None

            # show setting being changed and current value
            self.LCD.print(self.ops[self.m1_hover])
            [row, col] = self.LCD.cursor_pos()
            # check if cursor wrapped around
            if col == 0:
                self.LCD.set_cursor_pos(int(row), 0)
            else:
                self.LCD.set_cursor_pos(int(row)+1, 0)

            if self.m1_hover <= 2:
                self.LCD.print(f"{self.timeFormat(self.settings[self.m1_hover])}")
                self.m2_hover = 4  # HH:MM:SS format, default start at first min mark

                return self.settings[self.m1_hover]
            
            # get allowable water height in reservoir setting and allow user to change it
            if self.m1_hover == 3:
                # 3 sigfigs, e.g. 123 choice of which digit to increase
                self.m2_hover = 2
                if self.settings[self.m1_hover] < 100:
                    self.LCD.print(f"0{self.settings[self.m1_hover]} cm")
                else:
                    self.LCD.print(f"{self.settings[self.m1_hover]} cm")
                return self.settings[self.m1_hover]
        
        # show sublevel to pick low/high pH threshold values
        elif self.m1_hover == 4:
            self.child = 'pH THRESH'
            self.LCD.print('^ pH High Threshold\nv pH Low Threshold')
            return None
        
        # show sublevel to pick low/high EC threshold values
        elif self.m1_hover == 5:
            self.child = 'EC THRESH'
            self.LCD.print('^ EC High Threshold\nv EC Low Threshold')
            return None
        
        # operation to run EC calibration
        elif self.m1_hover == 7:
            # sets logic to handle A or B input on next loop
            self.child = "EC CONFIRM"
            self.LCD.print("Press A once the EC sensor is fully submerged in solution")
            return None

        elif self.m1_hover == 6:
            self.child = "pH CONFIRM"
            self.LCD.print("Press A once the pH sensor is fully submerged in solution")
            return None

        # TODO test
        elif self.m1_hover == 8:
            self.shrub.evt_handler(evt="USER TOGGLE")
            if self.shrub.userToggle:
                self.LCD.print("Pump/UV/valve off")
            elif self.shrub.userToggle is False:
                self.LCD.print("Pump/UV/valve on")
            self.child = "WAIT"

        # TODO test toggle works
        elif self.m1_hover == 9:
            self.conditioner.evt_handler(evt="USER TOGGLE")
            if self.conditioner.userToggle:
                self.LCD.print("Pump/UV/valve off")
            elif self.conditioner.userToggle is False:
                self.LCD.print("Pump/UV/valve on")
            self.child = "WAIT"

        elif self.m1_hover == 10:
            self.LCD.print("Turning on all outputs for a few seconds")
            self.child = "WAIT"
            self.conditioner.evt_handler(evt="TEST")
            self.shrub.evt_handler(evt="TEST")
            
    # TODO see if i can segment this to reduce loop time?
    def evt_handler(self, evt=None, timer=False, test=True):
        if test:
            print(f"child: {self.child}")
            print(f'parent: {self.parent}')
            try:
                print('event:', evt)
            except Exception as e:
                print('event: None', e)
        # should restart timer for setting the menu state to idle
        if evt is not None:
            self.idle_timer.timer_set()
            self.state = 'ACTIVE'
            if evt == 'TEST':
                self.shrub.evt_handler(evt='TEST')
                self.conditioner.evt_handler(evt='TEST')
                self.LCD.print("All outputs enabled for 6 seconds")
                self.child = 'WAIT'

        # whenever there has been no user input for a while, go back to idle
        if timer:
            self.idle()
        
        # the idle level of the menu
        if (self.child == self.ops) and (self.parent == self.start):
            # wait for user input to start menu
            if (evt == "U_B") or (evt == "D_B") or (evt == "L_B") or (evt == "R_B") \
                    or (evt == "A_B") or (evt == "B_B"):
                self.startMenu()
        
        # showing message to be cleared and send user to start after user input
        elif self.child == 'WAIT':
            if (evt == 'A_B') or (evt == "R_B"):
                self.startMenu()

        # first level of menu showing configuration options
        elif self.child in self.ops:
            if (evt == "B_B") or (evt == "L_B"):
                # send to level above
                self.idle()
            elif (evt == "A_B") or (evt == "R_B"):
                self.param2change = self.A_at_m1()
            elif (evt == "U_B"):
                self.m1_hover += 1
                # resets the selected option back to 0 if it goes too high
                self.m1_hover %= len(self.ops)

                self.LCD.clear()
                self.LCD.print(self.ops[self.m1_hover])
                '''# show next operation beneath it. commented out cause confusing rn
                [row, col] = self.LCD.cursor_pos()
                # check if cursor wrapped around
                if col == 0:
                    self.LCD.set_cursor_pos(int(row), 0)
                else:
                    self.LCD.set_cursor_pos(int(row)+1, 0)
                self.LCD.print(self.ops[self.m1_hover-1])'''
                self.child = self.ops[self.m1_hover]
            elif (evt == "D_B"):
                self.m1_hover -= 1
                if self.m1_hover < 0:
                    self.m1_hover = len(self.ops) - 1
                
                self.LCD.clear()
                self.LCD.print(self.ops[self.m1_hover])
                '''[row, col] = self.LCD.cursor_pos()
                # check if cursor wrapped around
                if col == 0:
                    self.LCD.set_cursor_pos(int(row), 0)
                else:
                    self.LCD.set_cursor_pos(int(row)+1, 0)
                # in case it's the last operation hovered over
                try:
                    self.LCD.print(self.ops[self.m1_hover-1])
                except IndexError:
                    self.LCD.print(self.ops[0])'''
                self.child = self.ops[self.m1_hover]
        
        elif self.child not in self.ops:
            # need to make sure once it goes to first submenu, it doesn't raise error
            if type(self.parent) is int:
                # submenus to change timings
                if (self.parent <= 2) and (self.child is None):
                    if (evt == "A_B"):
                        # save changes to file
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.startMenu(hover=self.parent)
                    if (evt == "U_B"):
                        # increase HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 10*60*60
                        if self.m2_hover == 1:
                            self.param2change += 1*60*60
                        if self.m2_hover == 3:
                            self.param2change += 10*60
                        if self.m2_hover == 4:
                            self.param2change += 1*60
                        if self.m2_hover == 6:
                            self.param2change += 10
                        if self.m2_hover == 7:
                            self.param2change += 1
                        # max timer
                        if self.param2change > 20*60*60:
                            self.param2change = 20*60*60
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    if (evt == "D_B"):
                        # decrease HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 10*60*60
                        if self.m2_hover == 1:
                            self.param2change -= 1*60*60
                        if self.m2_hover == 3:
                            self.param2change -= 10*60
                        if self.m2_hover == 4:
                            self.param2change -= 1*60
                        if self.m2_hover == 6:
                            self.param2change -= 10
                        if self.m2_hover == 7:
                            self.param2change -= 1
                        # prevent timer going negative
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 8
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 8 - 1
                    
                # save water gap
                elif (self.parent == 3) and (self.child is None): 
                    if (evt == "A_B"):
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.startMenu(hover=self.parent)
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
                        self.LCD.clear()
                        # ensure always 3 digits shown
                        if self.param2change < 100:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n0{self.param2change} cm")
                        else:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.param2change} cm")
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
                        self.LCD.clear()
                        # ensure always 3 digits shown
                        if self.param2change < 100:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n0{self.param2change} cm")
                        else:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.param2change} cm")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    if (evt == "L_B"):
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 3 - 1

                # sublevel to choose pH thresholds
                elif (self.parent == 4):
                    if (self.child == 'pH THRESH'):
                        self.m2_hover = 0
                        # should show two rows for low and high threshold
                        # pressing up button should choose top option
                        if (evt == "U_B") or (evt == 'A_B'):
                            self.parent = self.child
                            self.child = "pH HIGH"
                            self.param2change = self.settings[4]
                            self.LCD.clear()
                            self.LCD.print(f"pH High Threshold:\n{self.param2change:.1f}")
                            #self.LCD.print(f"pH High Threshold:\n{self.settings[4]}")
                        # pressing down should choose bottom option
                        if (evt == "D_B"):
                            self.parent = self.child
                            self.child = "pH LOW"
                            self.param2change = self.settings[5]
                            self.LCD.clear()
                            self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                        if (evt == "B_B"):
                            self.startMenu(self.m1_hover)

                # sublevel to choose EC thresholds
                elif (self.parent == 5):
                    if (self.child == 'EC THRESH'):
                        self.m2_hover = 0
                        # should show two rows for low and high threshold
                        # pressing up button should choose top option
                        if (evt == "U_B"):
                            self.parent = self.child
                            self.child = "EC HIGH"
                            self.param2change = self.settings[6]
                            self.LCD.clear()
                            self.LCD.print(f"EC High Threshold:\n{self.param2change:.2f}")
                        # pressing down should choose bottom option
                        if (evt == "D_B"):
                            self.parent = self.child
                            self.child = "EC LOW"
                            self.param2change = self.settings[7]
                            self.LCD.clear()
                            self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                        if (evt == "B_B"):
                            self.startMenu(self.m1_hover)

            # second level to change pH threshold values
            elif (self.parent == 'pH THRESH'):
                if (self.child == 'pH HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 4
                        self.child = 'pH THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('pH High Threshold\npH Low Threshold')
                    if (evt == "U_B"):
                        # increase the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 1
                        if self.m2_hover == 2:
                            self.param2change += .1
                        # max pH
                        if self.param2change > 9.9:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH High Threshold:\n{self.param2change:.1f}")
                    if (evt == "D_B"):
                        # decrease the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        if self.m2_hover == 2:
                            self.param2change -= .1
                        # min gap
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        self.LCD.print(f"pH High Threshold:\n{self.param2change:.1f}")
                    if (evt == 'R_B'):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 3 - 1
                if (self.child == 'pH LOW'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 4
                        self.child = 'pH THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('pH High Threshold\npH Low Threshold')
                    if (evt == "U_B"):
                        # increase the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 1
                        if self.m2_hover == 2:
                            self.param2change += .1
                        # max pH
                        if self.param2change > 9.9:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                    if (evt == "D_B"):
                        # decrease the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        if self.m2_hover == 2:
                            self.param2change -= .1
                        # min pH
                        if self.param2change < 0:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                    if (evt == 'R_B'):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 3 - 1

            # second level to change pH threshold values
            elif (self.parent == 'EC THRESH'):
                if (self.child == 'EC HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 5
                        self.child = 'EC THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('EC High Threshold\nEC Low Threshold')
                    # increase the EC based on hover position. want it to be to two decimal places X.XX
                    if (evt == "U_B"):
                        if self.m2_hover == 0:
                            self.param2change += 1
                        if self.m2_hover == 2:
                            self.param2change += .1
                        if self.m2_hover == 3:
                            self.param2change += .01
                        # max EC
                        if self.param2change > 10.0:
                            self.param2change = 10.0
                        self.LCD.clear()
                        self.LCD.print(f"EC High Threshold:\n{self.param2change:.2f}")
                    if (evt == "D_B"):
                        # decrease the EC based on hover position. want it to be to two decimal places X.XX
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        if self.m2_hover == 2:
                            self.param2change -= .1
                        if self.m2_hover == 3:
                            self.param2change -= .01
                        # min EC
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        print(f"unformatted:{self.param2change}\n{self.param2change:.2f}")
                        self.LCD.print(f"EC High Threshold:\n{self.param2change:.2f}")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 4
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 4 - 1
                if (self.child == 'EC LOW'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    if (evt == "B_B"):
                        # send to level above
                        self.parent = 5
                        self.child = 'EC THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('EC High Threshold\nEC Low Threshold')
                    if (evt == "U_B"):
                        if self.m2_hover == 0:
                            self.param2change += 1
                        if self.m2_hover == 2:
                            self.param2change += .1
                        if self.m2_hover == 3:
                            self.param2change += .01
                        # max EC
                        if self.param2change > 10.0:
                            self.param2change = 10.0
                        self.LCD.clear()
                        print(f"{self.param2change:.2f}")
                        self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                    if (evt == "D_B"):
                        # decrease the EC based on hover position. want it to be to two decimal places X.XX
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        if self.m2_hover == 2:
                            self.param2change -= .1
                        if self.m2_hover == 3:
                            self.param2change -= .01
                        # min EC
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        print(f"{self.param2change:.2f}")
                        self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                    if (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 4
                    if (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        if self.m2_hover < 0:
                            self.m2_hover = 4 - 1

            # second level submenus to confirm calibration of sensors
            elif self.child == "EC CONFIRM":
                # TODO run in debugger. seems to get stuck here
                if (evt == "A_B") or (evt == "R_B"):
                    self.LCD.clear()
                    self.LCD.print(self.conditioner.EC_calibration())
                    self.child = "WAIT"
                    self.parent = None
                elif (evt == "B_B") or (evt == "L_B"):
                    self.startMenu(self.m1_hover)

            elif self.child == "pH CONFIRM":
                if (evt == "A_B") or (evt == "R_B"):
                    self.LCD.clear()
                    self.LCD.print(self.conditioner.pH_calibration())
                    self.child = "WAIT"
                    self.parent = None
                elif (evt == "B_B") or (evt == "L_B"):
                    self.startMenu(self.m1_hover)
            

class LCDdummy():
    '''Dummy LCD class to handle methods before incorporating real LCD library. Use for testing/troubleshooting only.'''
    def __init__(self):
        print("LCD test instance created.")
    
    def display(self, stuff):
        '''Handle string, list, tuple, int, and float inputs to put them on LCD'''
        if (type(stuff) is list) or (type(stuff) is tuple):
            for ele in stuff:
                print(ele)
        elif type(stuff) is str:
            print(stuff)
        elif (type(stuff) is int) or (type(stuff) is float):
            stuff = str(stuff)
            print(stuff)
        else:
            raise Exception("Not a valid input to display")
    
    def idle(self):
        print("Idle Mode: Want to user timer and cache system to continually show new sensor data")
    
if __name__ == "__main__":
    print("Incorrect file run. Run shrubber_main.py to initialize sensors, actuators, etc.")