#!/bin/sh

APT_PKGS="python3-gpiozero libatlas-bas-dev"
PIP3_PKGS="adafruit-circuitpython-ads1x15 scipy GitPython libcblas-dev pygame argparse"

apt-get update
apt-get upgrade -y
apt remove python3-numpy -y
pip3 install $PIP3_PKGS
# for some reason this order of installing numpy works w/ RPi
pip install numpy==1.20
pip3 install --upgrade numpy
apt-get install $APT_PKGS -y
apt autoremove
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
python3 raspi-blinka.py