#!/bin/bash

echo "Installing Spop Dependencies"
apt-get update
apt-get -y install libao-dev libglib2.0-dev libjson-glib-1.0-0 libjson-glib-dev libao-common libasound2-dev libreadline-dev libsox-dev libsoup2.4-dev libsoup2.4-1

echo "Installing Spop and libspotify"
cd / 
wget http://repo.volumio.org/Packages/Spop/spop.tar.gz
tar xf /spop.tar.gz
rm /spop.tar.gz

echo "Done"
