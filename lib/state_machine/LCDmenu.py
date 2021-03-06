#! /bin/python
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

from time import time
from csv import reader, writer
from warnings import warn

from lib.lcd.lcd import CursorMode

class timer():
    '''Creates a nonblocking timer to trigger a timer event when checked. Use timer_set to start the timer.
    Changing TIMER_INTERVAL does not update the new end time of the timer. '''
    timer_time = None

    def __init__(self, interval):
        try:
            self.TIMER_INTERVAL = float(interval)
        except ValueError as e:
            warn(f'Invalid timer input: {e}\nSetting interval to None')
            self.TIMER_INTERVAL = None

    def timer_event(self) -> bool:
        '''Checks to see if the time has passed. If it has, turns off timer and returns True. If the timer was not set,
        returns None'''
        if (self.timer_time is not None) and time() >= self.timer_time:
            self.timer_time = None
            return True
        elif self.timer_time is None:
            return None
        else:
            return False

    def event_no_reset(self) -> bool:
        '''Checks to see if the time has passed. If it has, returns True. Must be manually stopped/reset'''
        if (self.timer_time is not None) and time() >= self.timer_time:
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
            self.timer_time = time() + self.TIMER_INTERVAL
        except TypeError as e:
            if self.TIMER_INTERVAL is None:
                print("Timer interval set to None")
                self.timer_time = None
            else:
                pass

    def time_remaining(self) -> float:
        '''Checks to see if the time has passed. If it not, returns float of difference. No reset if time has passed'''
        if self.timer_time is None:
            return None
        else:            
            if time() >= self.timer_time:
                return None
            else:
                return self.timer_time - time()

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
    ops = ("Flood timer", "Channel Pump timer", "Empty timer",
        "Max water level", "pH thresholds", "EC thresholds", 
        "Calibrate pH", "Calibrate EC", "Force off pump+UV+valve", 
        "Force off nutrient conditioners", "Test outputs",
        "Open/close valves")
    parent = start
    child = ops
    m1_hover = 0
    m2_hover = 0
    ft = 60*60*3  # flood timer
    ap = 60*15  # active pump timer to flood channels
    et = 60*60*3.5  # empty timer
    # Sensor threshold values
    pHH = 9  # high pH threshhold
    pHL = 4  # low pH threshhold
    ECH = 2  # high EC threshhold
    ECL = 0.01  # low EC threshhold
    sT = 65  # sonar threshold
    # to help track program cycle between power shutoff
    __cycleIndex = 0
    __cycleTime = ap
    # timer to put the menu to idle
    idle_timer = timer(3*60)
    idle_timer.timer_set()
    idle_printer = timer(5)
    _idle_n = 0

    def __init__(self, LCD, shrub, conditioner, test=False, output=None):
        self.state = self.start
        self.LCD = LCD
        self.shrub = shrub
        self.conditioner = conditioner

        self.test = test
        self.output_file = output

        # check to see if state machine settings exist. if not create w/ default settings
        try:
            with open('Settings.csv', 'r') as f:
                settings = reader(f)
                rows = [row for row in settings if True]
                self.ft = int(rows[0][1])
                self.ap = int(rows[1][1])
                self.et = float(rows[2][1])
                self.sT = int(rows[3][1])
                self.pHH = float(rows[4][1])
                self.pHL = float(rows[5][1])
                self.ECH = float(rows[6][1])
                self.ECL = float(rows[7][1])
                self.__cycleIndex = int(rows[8][1])
                self.__cycleTime = float(rows[9][1])
                self.printf("Settings loaded")

        except (IOError, IndexError) as e:
            if (e is IOError) or (e is IndexError):
                self.printf("Settings.csv does not exist. Creating file with default settings.")
            with open(r"Settings.csv", 'w') as f:
                rows = [[self.ops[0], self.ft], 
                    [self.ops[1], self.ap], 
                    [self.ops[2], self.et], 
                    [self.ops[3], self.sT],
                    ['pH High Threshold', self.pHH], 
                    ['pH Low Threshold', self.pHL], 
                    ['EC High Threshold', self.ECH], 
                    ['EC Low Threshold', self.ECL],
                    ['Pump cycle stage', self.__cycleIndex],
                    ['Cycle time remaining', self.__cycleTime],
                ] 
                settings = writer(f)
                settings.writerows(rows)
        
        # list of operation settings
        self.settings = [self.ft, self.ap, self.et, self.sT, self.pHH, self.pHL,
            self.ECH, self.ECL, self.__cycleIndex, self.__cycleTime]
        self.shrub.update_settings([self.settings[0], self.settings[1], self.settings[2]], 
            self.settings[3], cycle=[self.settings[8], self.settings[9]])
        self.conditioner.update_settings(self.settings[4], self.settings[5], self.settings[6],
            self.settings[7])
        self.conditioner.pH_High = self.pHH
        self.conditioner.pH_Low = self.pHL
        self.conditioner.EC_High = self.ECH
        self.conditioner.EC_Low = self.ECL
        # calc time pump needs to be off to let plants be submerged and drained
        # save change to shrub state machine
        self.shrub.ptimes = [self.settings[0], self.settings[1], self.settings[2]]

    def printf(self, msgs, terminal=False):
        '''Save output to terminal to text file'''
        if self.output_file is not None:
            if type(msgs) is str:
                with open(self.output_file, 'a') as f:
                    print(msgs, file=f)
                if terminal:
                    print(msgs)
            else:
                for msg in msgs:
                    with open(self.output_file, 'a') as f:
                        print(msg, file=f)
                    if terminal:
                        print(msg)
        else:
            print(msgs)

    # TODO figure out more efficient way to save?
    def saveParamChange(self, cycle=False):
        '''Save the new user defined value to the settings file'''
        if not cycle:
            if type(self.parent) is int:
                if (self.parent <= 3) and (self.parent >= 0):
                    i = self.parent
                if (self.parent >= 8) or (self.parent < 0):
                    self.LCD.print("The parent variable does not correspond to a valid save location in the settings")
                    raise LookupError("The parent variable does not correspond to a valid save location in the settings")
            elif (self.parent == 'pH THRESH'):
                # assume child is ph LOW if not ph HIGH
                i = 4 if (self.child == 'pH HIGH') else 5
            elif (self.parent == 'EC THRESH'):
                # assume child is EC LOW if not EC HIGH
                i = 6 if (self.child == 'EC HIGH') else 7
            else:
                raise LookupError("Invalid parent setting to save")

            self.settings[i] = self.param2change
        # if cycle, check cycle state of shrub and save to file
        else:
            self.settings[8], self.settings[9] = self.getCycle()

        with open(r"Settings.csv", 'w') as f:
            rows = [['Flood Timer', self.settings[0]], 
                ['Active Pump Timer', self.settings[1]],
                ['Empty Timer', self.settings[2]],  
                ['Max water level', self.settings[3]],
                ['pH High Threshold', self.settings[4]], 
                ['pH Low Threshold', self.settings[5]], 
                ['EC High Threshold', self.settings[6]], 
                ['EC Low Threshold', self.settings[7]],
                ['Pump cycle stage', self.settings[8]],
                ['Cycle time remaining', self.settings[9]],
            ] 
            new_settings = writer(f)
            new_settings.writerows(rows)

        # save change to shrub state machine
        self.shrub.update_settings([self.settings[0], self.settings[1], self.settings[2]], self.settings[3])
        self.conditioner.update_settings(self.settings[4], self.settings[5], self.settings[6], self.settings[7])
        self.conditioner.pH_High = self.settings[4]
        self.conditioner.pH_Low = self.settings[5]
        self.conditioner.EC_High = self.settings[6]
        self.conditioner.EC_Low = self.settings[7]
        if not cycle:
            self.LCD.clear()
            self.LCD.set_cursor_mode(CursorMode.HIDE)
            self.LCD.print("Settings saved!")
            # show message until user input
            self.child = "WAIT"
            self.parent = None

    def getCycle(self) -> list:
        self.__cycleIndex = self.shrub.hydro_state
        self.__cycleTime = self.shrub.hydroTimer.time_remaining()
        return [self.__cycleIndex, self.__cycleTime]

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
        '''Print the next set of sensor values on the LCD screen
        when called by program. Lists up to 3 of the previously measured values'''
        # see if there are any prior printed values
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
        self._idle_n %= 5  # loop through each sensor
        n = self._idle_n
        # set timer to wait for next call to idle_print
        self.idle_printer.timer_set()
        if n == 0:
            # TODO get analog pressure sensor for water level
            temp = round(self.shrub.water_height(), 1)
            if temp == 63.9:
                self._a = "Need sonar replacement"
            else:
                self._a = f"Water level: {self.shrub.water_height():.1f} cm"
        elif n == 1:
            self._a = f"pH level: {self.conditioner.grab_pH():.1f}"
        elif n == 2:
            # TODO fix ec sensor
            self._a = "EC sensor is broken"
            #self._a = f"Conductivity level: {:.2f} mS"
        elif n == 3:
            self._a = f"Water temp: {self.conditioner.grab_temp(unit='F'):.2f} F"
        elif n == 4:
            [cycle_n, time_float] = self.getCycle()
            if cycle_n in [0,5]:
                cycle_string = "Flooding"
            if cycle_n in [1,6]:
                cycle_string = "Soaking"
            if cycle_n in [2,3,7,8]:
                cycle_string = "Draining"
            if cycle_n in [4,9]:
                cycle_string = "Oxygenating"
            time_int = int(time_float)
            self._a = f'System: {cycle_string}-{self.timeFormat(time_int)}'

        
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

    def timeFormat(self, sec) -> str:
        '''automatically convert seconds to HH:MM:SS format for user to read'''
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        h = int(h)
        m = int(m)
        s = int(s)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def A_at_m1(self):
        '''handle the menu change when the user selects an operation at first level. 
        To add more simple operations, add an elif at the end of the method'''
        self.parent = self.m1_hover
        self.LCD.clear()
        # for  flood timer, drain active pump timer, 
        if self.m1_hover <= 3:
            self.child = None

            # show setting being changed and current value
            self.LCD.print(self.ops[self.m1_hover])
            [row, col] = self.LCD.cursor_pos()
            # check if cursor wrapped around
            self.LCD.set_cursor_pos(int(row), 0) if col == 0 else self.LCD.set_cursor_pos(int(row)+1, 0)

            if self.m1_hover <= 2:
                self.LCD.print(f"{self.timeFormat(self.settings[self.m1_hover])}")
                self.m2_hover = 4  # HH:MM:SS format, default start at first min mark

                return self.settings[self.m1_hover]
            
            # get allowable max water height in reservoir setting and allow user to change it
            if self.m1_hover == 3:
                # 3 sigfigs, e.g. 123 choice of which digit to increase
                self.m2_hover = 2
                self.LCD.print(f"0{self.settings[self.m1_hover]} cm") if self.settings[self.m1_hover] < 100 else \
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

        # user toggle the main pump, uv, valves
        elif self.m1_hover == 8:
            self.shrub.evt_handler(evt="USER TOGGLE")
            if self.shrub.userToggle:
                self.LCD.print("Pump/UV/valve off")
            elif self.shrub.userToggle is False:
                self.LCD.print("Pump/UV/valve on")
            self.child = "WAIT"
            return None  # prevent rest from being run

        # user toggles conditioning pumps
        elif self.m1_hover == 9:
            self.conditioner.evt_handler(evt="USER TOGGLE")
            if self.conditioner.userToggle:
                self.LCD.print("Nutrient conditioners are off")
            elif self.conditioner.userToggle is False:
                self.LCD.print("Nutrient conditioners are on")
            self.child = "WAIT"
            return None  # prevent rest from being run

        elif self.m1_hover == 10:
            self.LCD.print("Turning on all outputs for a few seconds")
            self.child = "WAIT"
            self.conditioner.evt_handler(evt="TEST")
            self.shrub.evt_handler(evt="TEST")
            return None  # prevent rest from being run

        elif self.m1_hover == 11:
            self.LCD.print("Toggled valves")
            self.child = "WAIT"
            self.shrub.evt_handler(evt="VALVE TOGGLE")
            self.LCD.print(" Valves are open") if self.shrub.valveToggle else self.LCD.print(" Valves are closed")
               
            return None  # prevent rest from being run

    def evt_handler(self, evt=None, timer=False):
        '''Handles event passed to the menu'''
        if self.test:
            self.printf(f"child: {self.child}\nparent: {self.parent}")
            try:
                self.printf('event:', evt)
            except Exception as e:
                self.printf('event: None', e)

        # whenever there has been no user input for a while, go back to idle
        if timer: 
            self.idle()
            return None  # prevent rest of evt handler being run

        # should restart timer for setting the menu state to idle
        if evt is not None:
            self.idle_timer.timer_set()
            self.state = 'ACTIVE'
            if evt == 'TEST':
                self.shrub.evt_handler(evt='TEST')
                self.LCD.print("All outputs enabled for 6 seconds")
                self.child = 'WAIT'
                return None  # prevent rest of evt handler being run
 
        # the idle level of the menu
        if (self.child == self.ops) and (self.parent == self.start):
            # wait for user input to start menu
            if (evt == "U_B") or (evt == "D_B") or (evt == "L_B") or (evt == "R_B") \
                or (evt == "A_B") or (evt == "B_B"): self.startMenu()
        
        # showing message to be cleared and send user to start after user input
        elif self.child == 'WAIT':
            if (evt == 'A_B') or (evt == "R_B") or (evt == "D_B") \
                or (evt == "B_B") or (evt == "L_B") or (evt == "U_B"): self.startMenu()

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
                # show what the user toggle state is in menu
                if self.m1_hover == 8:
                    self.LCD.print("\nCurrently off") if self.shrub.userToggle else self.LCD.print('\n Currently normal')
                if self.m1_hover == 9:
                    self.LCD.print("\nCurrently off") if self.conditioner.userToggle else self.LCD.print('\n Currently normal')
                if self.m1_hover == 11:
                    self.LCD.print("\nCurrently open") if self.shrub.valveToggle else self.LCD.print('\n Currently closed')
                self.child = self.ops[self.m1_hover]
            elif (evt == "D_B"):
                self.m1_hover -= 1
                if self.m1_hover < 0:
                    self.m1_hover = len(self.ops) - 1
                
                self.LCD.clear()
                self.LCD.print(self.ops[self.m1_hover])
                # show what the user toggle state is in menu
                if self.m1_hover == 8:
                    self.LCD.print("\nCurrently off") if self.shrub.userToggle else self.LCD.print('\n Currently normal')
                if self.m1_hover == 9:
                    self.LCD.print("\nCurrently off") if self.conditioner.userToggle else self.LCD.print('\n Currently normal')
                if self.m1_hover == 11:
                    self.LCD.print("\nCurrently open") if self.shrub.valveToggle else self.LCD.print('\n Currently closed')
                self.child = self.ops[self.m1_hover]
        
        # if not in first level of menus
        elif self.child not in self.ops:
            # need to make sure once it goes to first submenu, it doesn't raise error
            if type(self.parent) is int:
                # TODO implement logic to handle if empty time is less than drain time
                # need to be wary of how we determine how long to open valves to drain. 
                # maybe as a function of fill timer
                # TODO see if logic needed for 0 timers
                # submenus to change timings
                if (self.parent <= 1) and (self.child is None):
                    if (evt == "A_B"):
                        # save changes to file
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.startMenu(hover=self.parent)
                    elif (evt == "U_B"):
                        # increase HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 10*60*60
                        elif self.m2_hover == 1:
                            self.param2change += 1*60*60
                        elif self.m2_hover == 3:
                            self.param2change += 10*60
                        elif self.m2_hover == 4:
                            self.param2change += 1*60
                        elif self.m2_hover == 6:
                            self.param2change += 10
                        elif self.m2_hover == 7:
                            self.param2change += 1
                        # max timer
                        if self.param2change > 20*60*60:
                            self.param2change = 20*60*60
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    elif (evt == "D_B"):
                        # decrease HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 10*60*60
                        elif self.m2_hover == 1:
                            self.param2change -= 1*60*60
                        elif self.m2_hover == 3:
                            self.param2change -= 10*60
                        elif self.m2_hover == 4:
                            self.param2change -= 1*60
                        elif self.m2_hover == 6:
                            self.param2change -= 10
                        elif self.m2_hover == 7:
                            self.param2change -= 1
                        # prevent timer going below 1 min
                        if self.param2change < 3.5*60:
                            self.param2change = 3.5*60
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    elif (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 8
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (8 - 1) if self.m2_hover < 0 else self.m2_hover
                
                # active pump timer
                if (self.parent == 2) and (self.child is None):
                    if (evt == "A_B"):
                        # save changes to file
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.startMenu(hover=self.parent)
                    elif (evt == "U_B"):
                        # increase HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 10*60*60
                        elif self.m2_hover == 1:
                            self.param2change += 1*60*60
                        elif self.m2_hover == 3:
                            self.param2change += 10*60
                        elif self.m2_hover == 4:
                            self.param2change += 1*60
                        elif self.m2_hover == 6:
                            self.param2change += 10
                        elif self.m2_hover == 7:
                            self.param2change += 1
                        # max timer
                        if self.param2change > 20*60*60:
                            self.param2change = 20*60*60
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    elif (evt == "D_B"):
                        # decrease HH:MM:SS timer based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 10*60*60
                        elif self.m2_hover == 1:
                            self.param2change -= 1*60*60
                        elif self.m2_hover == 3:
                            self.param2change -= 10*60
                        elif self.m2_hover == 4:
                            self.param2change -= 1*60
                        elif self.m2_hover == 6:
                            self.param2change -= 10
                        elif self.m2_hover == 7:
                            self.param2change -= 1
                        # prevent timer going below 1 min
                        if self.param2change < 60:
                            self.param2change = 60
                        self.LCD.clear()
                        self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.timeFormat(self.param2change)}")
                    elif (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 8
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (8 - 1) if self.m2_hover < 0 else self.m2_hover
                            
                # save max water height
                elif (self.parent == 3) and (self.child is None): 
                    if (evt == "A_B"):
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.startMenu(hover=self.parent)
                    elif (evt == "U_B"):
                        # increase the gap based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 100
                        elif self.m2_hover == 1:
                            self.param2change += 10
                        elif self.m2_hover == 2:
                            self.param2change += 1
                        # max height
                        if self.param2change > self.shrub.hole_depth:
                            self.param2change = self.shrub.hole_depth
                        self.LCD.clear()
                        # ensure always 3 digits shown
                        if self.param2change < 100:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n0{self.param2change} cm")
                        else:
                            self.LCD.print(f"{self.ops[self.m1_hover]}:\n{self.param2change} cm")
                    elif (evt == "D_B"):
                        # decrease the gap based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 100
                        elif self.m2_hover == 1:
                            self.param2change -= 10
                        elif self.m2_hover == 2:
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
                    elif (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    elif (evt == "L_B"):
                        self.m2_hover -= 1
                        self.m2_hover = (3 - 1) if self.m2_hover < 0 else self.m2_hover       

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
                        elif (evt == "D_B"):
                            self.parent = self.child
                            self.child = "pH LOW"
                            self.param2change = self.settings[5]
                            self.LCD.clear()
                            self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                        elif (evt == "B_B"):
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
                        elif (evt == "D_B"):
                            self.parent = self.child
                            self.child = "EC LOW"
                            self.param2change = self.settings[7]
                            self.LCD.clear()
                            self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                        elif (evt == "B_B"):
                            self.startMenu(self.m1_hover)

            # second level to change pH threshold values
            elif (self.parent == 'pH THRESH'):
                if (self.child == 'pH HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.parent = 4
                        self.child = 'pH THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('pH High Threshold\npH Low Threshold')
                    elif (evt == "U_B"):
                        # increase the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 1
                        elif self.m2_hover == 2:
                            self.param2change += .1
                        # max pH
                        if self.param2change > 9.9:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH High Threshold:\n{self.param2change:.1f}")
                    elif (evt == "D_B"):
                        # decrease the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        elif self.m2_hover == 2:
                            self.param2change -= .1
                        # min gap
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        self.LCD.print(f"pH High Threshold:\n{self.param2change:.1f}")
                    elif (evt == 'R_B'):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (3 - 1) if self.m2_hover < 0 else self.m2_hover
                            
                elif (self.child == 'pH LOW'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.parent = 4
                        self.child = 'pH THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('pH High Threshold\npH Low Threshold')
                    elif (evt == "U_B"):
                        # increase the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change += 1
                        elif self.m2_hover == 2:
                            self.param2change += .1
                        # max pH
                        if self.param2change > 9.9:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                    elif (evt == "D_B"):
                        # decrease the pH based on hover position
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        elif self.m2_hover == 2:
                            self.param2change -= .1
                        # min pH
                        elif self.param2change < 0:
                            self.param2change = 9.9
                        self.LCD.clear()
                        self.LCD.print(f"pH Low Threshold:\n{self.param2change:.1f}")
                    elif (evt == 'R_B'):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 3
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (3 - 1) if self.m2_hover < 0 else self.m2_hover

            # second level to change pH threshold values
            elif (self.parent == 'EC THRESH'):
                if (self.child == 'EC HIGH'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.parent = 5
                        self.child = 'EC THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('^ EC High Threshold\nv EC Low Threshold')
                    # increase the EC based on hover position. want it to be to two decimal places X.XX
                    elif (evt == "U_B"):
                        if self.m2_hover == 0:
                            self.param2change += 1
                        elif self.m2_hover == 2:
                            self.param2change += .1
                        elif self.m2_hover == 3:
                            self.param2change += .01
                        # max EC
                        if self.param2change > 10.0:
                            self.param2change = 10.0
                        self.LCD.clear()
                        self.LCD.print(f"EC High Threshold:\n{self.param2change:.2f}")
                    elif (evt == "D_B"):
                        # decrease the EC based on hover position. want it to be to two decimal places X.XX
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        elif self.m2_hover == 2:
                            self.param2change -= .1
                        elif self.m2_hover == 3:
                            self.param2change -= .01
                        # min EC
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        self.printf(f"unformatted:{self.param2change}\n{self.param2change:.2f}")
                        self.LCD.print(f"EC High Threshold:\n{self.param2change:.2f}")
                    elif (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 4
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (4 - 1) if self.m2_hover < 0 else self.m2_hover
                            
                elif (self.child == 'EC LOW'):
                    if (evt == "A_B"):
                        self.saveParamChange()
                    elif (evt == "B_B"):
                        # send to level above
                        self.parent = 5
                        self.child = 'EC THRESH'
                        self.LCD.clear()
                        self.LCD.set_cursor_mode(CursorMode.HIDE)
                        self.LCD.print('^ EC High Threshold\nv EC Low Threshold')
                    elif (evt == "U_B"):
                        if self.m2_hover == 0:
                            self.param2change += 1
                        elif self.m2_hover == 2:
                            self.param2change += .1
                        elif self.m2_hover == 3:
                            self.param2change += .01
                        # max EC
                        if self.param2change > 10.0:
                            self.param2change = 10.0
                        self.LCD.clear()
                        self.printf(f"{self.param2change:.2f}")
                        self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                    elif (evt == "D_B"):
                        # decrease the EC based on hover position. want it to be to two decimal places X.XX
                        if self.m2_hover == 0:
                            self.param2change -= 1
                        elif self.m2_hover == 2:
                            self.param2change -= .1
                        elif self.m2_hover == 3:
                            self.param2change -= .01
                        # min EC
                        if self.param2change < 0:
                            self.param2change = 0
                        self.LCD.clear()
                        self.printf(f"{self.param2change:.2f}")
                        self.LCD.print(f"EC Low Threshold:\n{self.param2change:.2f}")
                    elif (evt == "R_B"):
                        # change hover position. loop if too far right
                        self.m2_hover += 1
                        self.m2_hover %= 4
                    elif (evt == "L_B"):
                        # change hover position. loop if too far left
                        self.m2_hover -= 1
                        self.m2_hover = (4 - 1) if self.m2_hover < 0 else self.m2_hover

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
    def __init__(self, output=None):
        print("LCD test instance created.")
    
    def print(self, stuff):
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
    
    def clear(self):
        print('Simulated lcd screen clear\n\n\n\n')
    
    def set_cursor_pos(self, row, column):
        print("\n")
        pass

    def set_cursor_mode(self, cursor_mode):
        pass

    def cursor_pos(self):
        return [0, 0]

    def idle(self):
        print("Idle Mode: Want to user timer and cache system to continually show new sensor data")
    
if __name__ == "__main__":
    print("Incorrect file run. Run shrubber_main.py to initialize sensors, actuators, etc.")