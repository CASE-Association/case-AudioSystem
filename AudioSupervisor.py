#!/usr/bin/python

from __future__ import unicode_literals
import json, sys
from socketIO_client import SocketIO
import time
import datetime as dt
import pytz
from time import sleep
from threading import Thread
from hardware import *
from modules.logger import *
import RPi.GPIO as GPIO
import os

GPIO.setmode(GPIO.BCM)


# Configs:
t_open = datetime.time(07, 00)  # 07:00
t_case = datetime.time(18, 49)  # 17:00
t_clean = datetime.time(23, 30)  # Time to lower music and clean
t_closing = datetime.time(20, 59)  # 00:00
maxvol_cleaning = 75
maxvol_lab = 80
maxvol_case = 100

# Setup control button inputs.
btn_prew = None
btn_pp = None
btn_nxt = None
# GPIO.setup(btn_prew, GPIO.IN, pull_up_down=GPIO.PUD_UP)   # Prew
# GPIO.setup(btn_pp, GPIO.IN, pull_up_down=GPIO.PUD_UP)   # Play/Pause
# GPIO.setup(btn_nxt, GPIO.IN, pull_up_down=GPIO.PUD_UP)   # Next

log = Log(LOGLEVEL.INFO)

volumio_host = 'localhost'
volumio_port = 3000
VOLUME_DT = 5  # volume adjustment step

volumioIO = SocketIO(volumio_host, volumio_port)


class DigitalSoundProcessor:
    def __init__(self):
        pass


DSP = DigitalSoundProcessor

DSP.activeSong = 'AMPI'
DSP.activeArtist = 'VOLUMIO'
DSP.playState = 'unknown'
DSP.playPosition = 0
DSP.ptime = 0
DSP.duration = 0
DSP.modal = False
DSP.playlistoptions = []
DSP.queue = []
DSP.libraryFull = []
DSP.libraryNames = []
DSP.volume = 0
DSP.source = None
DSP.closed = False

emit_volume = False
emit_track = False


def onPushState(data):
    newStatus = None
    if 'trackType' in data:
        s = data['trackType']
        if s != DSP.source:
            log.info("New source: " + str(s))
            DSP.source = s

    if 'title' in data:
        newSong = data['title']
    else:
        newSong = ''
    if newSong is None:
        newSong = ''

    if 'artist' in data:
        newArtist = data['artist']
    else:
        newArtist = ''
    if newArtist is None:  # volumio can push NoneType
        newArtist = ''

    if 'position' in data:  # current position in queue
        DSP.playPosition = data['position']  # didn't work well with volumio ver. < 2.5

    if 'status' in data:
        newStatus = data['status']

    if 'seek' in data:
        DSP.ptime = data['seek']

    if 'duration' in data:
        DSP.duration = data['duration']

    if 'volume' in data:
        DSP.volume = data['volume']

    if 'disableVolumeControl' in data:
        DSP.volumeControlDisabled = data['disableVolumeControl']

    if (newSong != DSP.activeSong):  # new song
        log.info("New Song: " + "\033[94m" + newSong.encode('ascii', 'ignore') + "\033[0m")
        DSP.activeSong = newSong
        DSP.activeArtist = newArtist

    if newStatus != DSP.playState:
        DSP.playState = newStatus


def onPushQueue(data):
    DSP.queue = [track['name'] if 'name' in track else 'no track' for track in data]
    log.info('Queue length is ' + str(len(DSP.queue)))


def onPushBrowseSources(data):
    log.info('Browse sources:')
    for item in data:
        log.blue(item['uri'])


def onPushListPlaylist(data):
    global DSP
    if len(data) > 0:
        DSP.playlistoptions = data


def onNextBtnEvent():
    volumioIO.emit('next', '')


def onPPBtnEvent(state='toggle'):
    volumioIO.emit(state, '')


def onPrewBtnEveny():
    volumioIO.emit('prev', '')


"""
Startup initializer
"""
print('\033[92m \n'
         '   _________________________________________________________________________________________________\n'
         ' /\033[95m      ____    _    ____  _____ \033[94m     _             _ _       \033[91m  ____            _                    \033[92m\ \n'
         '|\033[95m      / ___|  / \  / ___|| ____|\033[94m    / \  _   _  __| (_) ___  \033[91m / ___| _   _ ___| |_ ___ _ __ ___      \033[92m|\n'
         '|\033[95m     | |     / _ \ \___ \|  _|  \033[94m   / _ \| | | |/ _` | |/ _ \ \033[91m \___ \| | | / __| __/ _ \  _ ` _ \     \033[92m|\n'
         '|\033[95m     | |___ / ___ \ ___) | |___ \033[94m  / ___ \ |_| | (_| | | (_) |\033[91m  ___) | |_| \__ \ |_  __/ | | | | |    \033[92m|\n'
         '|\033[95m      \____/_/   \_\____/|_____|\033[94m /_/   \_\__,_|\__,_|_|\___/ \033[91m |____/ \__, |___/\__\___|_| |_| |_|    \033[92m|\n'
         '|                                                                    \033[91m |___/\033[90m By Stefan Larsson 2019    \033[92m|\n'
         ' \__________________________________________________________________________________________________ /\033[0m \n')


def _receive_thread():
    volumioIO.wait()


# GPIO.add_event_callback(btn_nxt, GPIO.FALLING, callback=onNextBtnEvent(), bouncetime=300)
# GPIO.add_event_callback(btn_pp, GPIO.FALLING, callback=onPPBtnEvent(), bouncetime=300)
# GPIO.add_event_callback(btn_prew, GPIO.FALLING, callback=onPrewBtnEveny(), bouncetime=300)

receive_thread = Thread(target=_receive_thread, name="Receiver")
receive_thread.daemon = True

volumioIO.on('pushState', onPushState)
volumioIO.on('pushQueue', onPushQueue)
volumioIO.on('pushListPlaylist', onPushListPlaylist)
volumioIO.on('pushBrowseSources', onPushBrowseSources)

# get list of Playlists and initial state
volumioIO.emit('listPlaylist')
volumioIO.emit('getState')
#volumioIO.emit('getQueue')
sleep(0.1)
try:
    with open('DSPconfig.json', 'r') as f:  # load last playing track number
        config = json.load(f)
except IOError:
    pass
else:
    DSP.playPosition = config['track']

receive_thread.start()

# todo Implement: if longpress on p/p -> disconnect current user(restart client)



def t_in_range(start, end):  # Check if current time is in given range
    now_time = datetime.datetime.now().time()
    return start <= now_time <= end


def volume_guard(limit, start, stop):  # Check if volume state is ok
    global emit_volume
    # Check if volume is not over limit if time is in timespan.
    if t_in_range(start, stop) and DSP.volume > limit:
        log.warn('Music over limit! ({}%), New volume level: {}%'.format(DSP.volume, limit))
        DSP.volume = maxvol_cleaning
        emit_volume = True
        return False
    return True


def reset_Spotify_connect():
    try:
        #os.system("systemctl restart volspotconnect2")  # Restart Spotify Connect client.
        log.warn("Spotify Connect was reset!")
    except Exception as err:
        log.err("Spotify reset error, ", err)

def main():
    global emit_volume, emit_track

    while True:
        if emit_volume:
            emit_volume = False
            log.info("Volume: " + str(DSP.volume))
            volumioIO.emit('volume', DSP.volume)

        if emit_track:
            emit_track = False
            try:
                log.info('Track selected: ' + str(DSP.playPosition + 1) + '/' + str(len(DSP.queue)) + ' ' + DSP.queue[
                    DSP.playPosition].encode('ascii', 'ignore'))
            except IndexError:
                pass
            volumioIO.emit('play', {'value': DSP.playPosition})

        if t_in_range(t_open, t_closing):  # If lab is open
            DSP.closed = False
            # Check if music state is ok
            if not volume_guard(maxvol_case, t_case, t_clean) and \
                    not volume_guard(maxvol_lab, t_open, t_case) and \
                    not volume_guard(maxvol_cleaning, t_clean, t_closing):
                # State not ok
                pass

            else:
                # State ok
                log.info("Everything is ok.")
                time.sleep(1)
        else:   # If Lab is closed
            # Stop music
            if not DSP.closed:
                DSP.closed = True
                DSP.volume = 0     # Turn down volume
                #emit_volume = True
                #volumioIO.emit('stop')  # Stop playing music request
                time.sleep(1)
                reset_Spotify_connect()  # Disconnect Spotify Connection
            log.info("Lab is close until: {}".format(t_open.strftime('%H:%M')))
            time.sleep(10)



def defer():
    try:
        GPIO.cleanup()
        receive_thread.join(1)
        DSP.cleanup()
        log.info("System exit ok")

    except Exception as err:
        log.err("Defer Error: " + str(err))


if __name__ == '__main__':
    try:
        main()
    except(KeyboardInterrupt, SystemExit):
        defer()  # todo make work!
