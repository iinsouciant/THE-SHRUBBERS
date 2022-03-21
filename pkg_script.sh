#!/bin/sh

# install the packages
APT_PKGS="python3-gpiozero"
PIP3_PKGS="Adafruit-Blinka adafruit-circuitpython-ads1x15 scipy"

apt-get update
apt-get upgrade -y
apt remove python3-numpy -y
pip install numpy
apt-get install $APT_PKGS -y
pip3 install $PIP3_PKGS 
apt autoremove

# ensure 1024x768 res
CONFIG="/boot/config.txt"
if grep -Fq "hdmi_force_hotplug" $CONFIG
then
    sed -i "hdmi_force_hotplug/c\hdmi_force_hotplug=1"
else
    echo "hdmi_force_hotplug=1" >> $CONFIG
fi

if grep -Fq "hdmi_ignore_edid" $CONFIG
then
    sed -i "hdmi_ignore_edid/c\hdmi_ignore_edid=0xa5000080"
else
    echo "hdmi_ignore_edid=0xa5000080" >> $CONFIG
fi

if grep -Fq "hdmi_group" $CONFIG
then
    sed -i "hdmi_group/c\hdmi_group=2"
else
    echo "hdmi_group=2" >> $CONFIG
fi

if grep -Fq "hdmi_mode" $CONFIG
then
    sed -i "hdmi_mode/c\hdmi_mode=16"
else
    echo "hdmi_mode=16" >> $CONFIG
fi

pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
python3 raspi-blinka.py