# THE-SHRUBBERS

## Project Objectives

Design and fabricate a self sustaining hydroponic growing system for an urban environment. The system has been adapted for outdoor use.

## Project Specifications

| Dimensions (ft) | Weight Capacity (lbs)  | Plant Capacity | Reservoir Capacity (gal.) | Operating Conditions |
|-----------------|------------------------|----------------|---------------------------|----------------------|
| 8x4x7           | 300                    | 64             | 60                        | Outdoor Urban        |

## I/O

### MCU

Raspberry Pi 4B (2 GB RAM).
![image](https://user-images.githubusercontent.com/17360719/168444041-78178518-1072-4ef7-aa5b-608aa64ac3ce.png "Circuit Diagram")


### Sensors

- [HC-SR04 Sonar sensor](https://www.adafruit.com/product/3942 "Sonar sensor")
- [DFR0300 Gravity EC sensor](https://www.dfrobot.com/product-1123.html "Analog Conductivity Sensor")
- [Gravity Analog pH sensor](https://atlas-scientific.com/kits/gravity-analog-ph-kit/ "pH kit")
- [DS18B20 Temperature sensor](https://www.adafruit.com/product/381)

All but the sonar sensor use analog signals, therefore we need to get an ADC for the RPi.

- [ADS1015](https://www.adafruit.com/product/1083 "12-Bit ADC")

## User Input

- [6 tactile buttons](https://www.adafruit.com/product/1119 "Tactile button pack")

## Outputs

- 1 [by-pass pump](https://www.pentair.com/en-us/products/residential/water-supply-disposal/recreational-vehicle/shurflo-revolution-4008-series-by-pass-pump.html) (12 VDC) to move water to the channels holding plants and through the filtration system.
- 3 [peristaltic](https://www.adafruit.com/product/1150) pumps (12 VDC) to condition solution
- [LCD display](https://www.amazon.com/SunFounder-Backlight-Raspberry-Characters-Background/dp/B01GPUMP9C/) for UI

## Libraries

- [sonar](https://github.com/alaudet/hcsr04sensor "HC-SR04 Ultrasonic Sensor on Raspberry Pi")
- [GPIO Zero](https://gpiozero.readthedocs.io/en/stable/installing.html "Installing GPIO Zero")
- [Adafruit Blinka](https://github.com/adafruit/Adafruit_Blinka "Blinka GitHub page")
- [ADS 1X15](https://github.com/adafruit/Adafruit_CircuitPython_ADS1x15 "ADC Library page")
- [CircuitPython LCD](https://github.com/dhalbert/CircuitPython_LCD)

In console, navigate to the download location of the repository and run the package installer shell script for libraries not included in the repository itself. Note: the ones included in the repository are either created by us or modified versions of other libraries. Additionally, the `pkg.sh` file assumes you do not have CircuitPython installed on your Raspberry Pi prior to this and will attempt to install is after the other packages.
```
sudo sh pkg_script.sh
```
