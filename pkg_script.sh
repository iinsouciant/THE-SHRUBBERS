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

# ensure 1024x768 res for vnc
CONFIG="/boot/config.txt"
if grep -Fq "hdmi_force_hotplug" $CONFIG
then
    sed -i "/hdmi_force_hotplug/c\hdmi_force_hotplug=1" $CONFIG
else
    echo "hdmi_force_hotplug=1" >> $CONFIG
fi

if grep -Fq "hdmi_ignore_edid" $CONFIG
then
    sed -i "/hdmi_ignore_edid/c\hdmi_ignore_edid=0xa5000080" $CONFIG
else
    echo "hdmi_ignore_edid=0xa5000080" >> $CONFIG
fi

if grep -Fq "hdmi_group" $CONFIG
then
    sed -i "/hdmi_group/c\hdmi_group=2" $CONFIG
else
    echo "hdmi_group=2" >> $CONFIG
fi

if grep -Fq "hdmi_mode" $CONFIG
then
    sed -i "/hdmi_mode/c\hdmi_mode=16" $CONFIG
else
    echo "hdmi_mode=16" >> $CONFIG
fi
# enable 1 wire interface for temp sensor
if grep -Fq "dtoverlay" $CONFIG
then
    sed -i "/dtoverlay/c\dtoverlay=w1-gpio" $CONFIG
else
    echo "dtoverlay=w1-gpio" >> $CONFIG
fi


pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
python3 raspi-blinka.py