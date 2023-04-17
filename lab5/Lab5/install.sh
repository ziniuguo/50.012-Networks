#!/bin/bash
# Installation script for 50.012 Networks Lab 5
# This must be run as root
# replace apt with other package manager where necessary
apt install mininet tmux curl libcgroup openvswitch-testcontroller python3-pip gnupg psmisc

# Install frrouting - see the project homepage for distro-specific instructions
# this is for debian
# add GPG key
curl -s https://deb.frrouting.org/frr/keys.asc | apt-key add -
# possible values for FRRVER: frr-6 frr-7 frr-8 frr-stable
# frr-stable will be the latest official stable release
FRRVER="frr-stable"
echo deb https://deb.frrouting.org/frr $(lsb_release -s -c) $FRRVER | tee -a /etc/apt/sources.list.d/frr.list
# update and install FRR
sudo apt update && sudo apt install frr frr-pythontools

# disable the openvswitch-testcontroller daemon
# replace systemd with whatever init system you are using
systemctl stop openvswitch-testcontroller
systemctl disable openvswitch-testcontroller
