#!/bin/sh

APT_PKGS="python3-gpiozero libatlas-bas-dev"
PIP3_PKGS="adafruit-circuitpython-ads1x15 scipy GitPython pygame argparse"

apt-get update
apt-get upgrade -y
apt remove python3-numpy -y
pip3 install $PIP3_PKGS
# for some reason this order of installing numpy works w/ RPi
pip install numpy
pip3 install opencv-python 
apt-get install libcblas-dev -y
apt-get install libhdf5-dev -y
apt-get install libhdf5-serial-dev -y
apt-get install libatlas-base-dev -y
apt-get install libjasper-dev -y
apt-get install libqtgui4 -y
apt-get install libqt4-test -y
apt-get install $APT_PKGS -y

modprobe wire
modprobe w1-gpio
modprobe w1-therm 

apt autoremove
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
python3 raspi-blinka.py