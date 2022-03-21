#!/bin/sh

# install the packages
APT_PKGS="python3-gpiozero"
PIP3_PKGS="Adafruit-Blinka adafruit-circuitpython-ads1x15 scipy"

apt-get update
apt-get upgrade -y
apt-get install $APT_PKGS -y
pip3 install $PIP3_PKGS -y

pip install numpy -y

# enable i2c 
CONFIG="/boot/config.txt"
if grep -Fq "dtparam=i2c_arm" $CONFIG
then
    sed -i "s/dtparam=i2c_arm/c\dtparam=i2c_arm=on"
else
    echo "dtparam=i2c_arm=on" >> $CONFIG
fi