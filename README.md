# THE-SHRUBBERS

## Project Objectives

Design and fabricate a self sustaining hydroponic growing system for an urban environment. The system will be designed for rooftop, balcony, or greenhouse use.

## Project Scope

This system will will utilize pumps for water flow and aeration and use a pH, conductivity, and sonar sensor to monitor the system. It will fit in a 4x4x6ft space. It will operate at 0 ०C to 40 ०C and handle a corrosive or windy environment.

## I/O

### MCU(?)

Raspberry Pi 3B (1 GB RAM) utilizes the main file to monitor sensor data and interface with the user.
![imagename](./git-instructions/images/block%20diagram.png)

### Sensors

- [HC-SR04 Sonar sensor](https://www.adafruit.com/product/3942 "Sonar sensor")
- [DFR0300 Gravity EC sensor](https://www.dfrobot.com/product-1123.html "Analog Conductivity Sensor")
- [Gravity Analog pH sensor](https://atlas-scientific.com/kits/gravity-analog-ph-kit/ "pH kit")
- [Pressure sensors](https://www.mouser.com/ProductDetail/Seeed-Studio/114991178?qs=EU6FO9ffTwf0XRUPsDAe9g%3D%3D&mgh=1&gclid=Cj0KCQiAtJeNBhCVARIsANJUJ2HkixiQoLugfLpcpu6VXwtwWSyMwnQA3TV0bZjC7F1oVlWbF5goXOYaAmHCEALw_wcB)

All but the sonar sensor use analog signals, therefore we need to get an ADC for the RPi.

- [MCP3008](https://www.adafruit.com/product/856 "10-Bit ADC")

## User Input

- [6 tactile buttons](https://www.adafruit.com/product/1119 "Tactile button pack")

## Outputs

- 1 submerged pump (AC) to move water to the channels holding plants and through the filtration system.
- 3 peristaltic pumps (DC) to condition solution
- LCD display for UI

## Libraries

- [sonar](https://github.com/alaudet/hcsr04sensor "HC-SR04 Ultrasonic Sensor on Raspberry Pi")
- [GPIO Zero](https://gpiozero.readthedocs.io/en/stable/installing.html "Installing GPIO Zero")
- [spidev](https://pypi.org/project/spidev/ "pypi spidev page")
