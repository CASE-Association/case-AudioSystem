# RPI_Audio
Resources for the local CASE Audio system.
### Installation
```
sudo apt-get update
#sudo apt-get install -y python-dev python-pip libfreetype6-dev libjpeg-dev build-essential python-rpi.gpio
sudo pip install --upgrade setuptools pip wheel
sudo pip install --upgrade socketIO-client-2
sudo apt-get install rpi.gpio -y
git clone https://github.com/Stefanlarsson95/RPI_Audio
chmod +x ~/CASE_DSP/AudioSupervisor.py
sudo cp ~/CASE_DSP/AudioSupervisor.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable AudioSupervisor.service
sudo dpkg-reconfigure tzdata
reboot
```


Creator: Stefan Larsson 2019