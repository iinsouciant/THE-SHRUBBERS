#!/bin/sh

# install the packages
APT_PKGS="python3-gpiozero"
PIP3_PKGS="adafruit-circuitpython-ads1x15 scipy libcblas-dev"

apt-get update
apt-get upgrade -y
apt remove python3-numpy -y
apt-get install $APT_PKGS -y
pip3 install $PIP3_PKGS 
pip install numpy==1.20
pip install GitPython
apt-get install libatlas-base-dev -y
pip3 install --upgrade numpy
apt autoremove

pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
python3 raspi-blinka.py