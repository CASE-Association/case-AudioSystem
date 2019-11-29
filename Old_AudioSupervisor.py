#!/usr/bin/python

from __future__ import unicode_literals
import json, sys
from socketIO_client import SocketIO
from time import time, sleep
from threading import Thread
from hardware import *
from modules.logger import *
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

log = Log(LOGLEVEL.INFO)

volumio_host = 'localhost'
volumio_port = 3000
VOLUME_DT = 5  # volume adjustment step

volumioIO = SocketIO(volumio_host, volumio_port)

STATE_NONE = -1
STATE_PLAYER = 0
STATE_PLAYLIST_MENU = 1
STATE_QUEUE_MENU = 2
STATE_VOLUME = 3
STATE_SHOW_INFO = 4
STATE_LIBRARY_MENU = 5
STATE_CLOCK = 6

DSP.state = STATE_NONE
DSP.stateTimeout = 0
DSP.timeOutRunning = True
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

emit_volume = False
emit_track = False

def LoadPlaylist(playlistname):
    log.info("loading playlist: " + playlistname.encode('ascii', 'ignore'))
    DSP.playPosition = 0
    volumioIO.emit('playPlaylist', {'name': playlistname})
    DSP.state = STATE_PLAYER

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
        NowPlayingScreen.ptime = DSP.ptime

    if 'duration' in data:
        DSP.duration = data['duration']

    if DSP.state != STATE_VOLUME:  # get volume on startup and remote control
        try:  # it is either number or unicode text
            DSP.volume = int(data['volume'])
        except (KeyError, ValueError):
            pass

    if 'disableVolumeControl' in data:
        DSP.volumeControlDisabled = data['disableVolumeControl']

    if (newSong != DSP.activeSong):  # new song
        log.info("New Song: " + "\033[94m" + newSong.encode('ascii', 'ignore') + "\033[0m")
        DSP.activeSong = newSong
        DSP.activeArtist = newArtist
        if DSP.state == STATE_PLAYER and newStatus != 'stop':
            DSP.modal.UpdatePlayingInfo(newArtist, newSong)

    if newStatus != DSP.playState:
        DSP.playState = newStatus
        if DSP.state == STATE_PLAYER:
            if DSP.playState == 'play':
                iconTime = 35
            else:
                iconTime = 80
            DSP.modal.SetPlayingIcon(DSP.playState, iconTime)


def onPushQueue(data):
    DSP.queue = [track['name'] if 'name' in track else 'no track' for track in data]
    log.info('Queue length is ' + str(len(DSP.queue)))


def onPushBrowseSources(data):
    log.info('Browse sources:')
    for item in data:
        log.blue(item['uri'])


def onLibraryBrowse(data):
    DSP.libraryFull = data
    itemList = DSP.libraryFull['navigation']['lists'][0]['items']
    DSP.libraryNames = [item['title'] if 'title' in item else 'empty' for item in itemList]
    DSP.state = STATE_LIBRARY_MENU


def EnterLibraryItem(itemNo):
    selectedItem = DSP.libraryFull['navigation']['lists'][0]['items'][itemNo]
    log.info("Entering library item: " + DSP.libraryNames[itemNo].encode('ascii', 'ignore'))
    if selectedItem['type'][-8:] == 'category' or selectedItem['type'] == 'folder':
        volumioIO.emit('browseLibrary', {'uri': selectedItem['uri']})
    else:
        log.info("Sending new Queue")
        volumioIO.emit('clearQueue')  # clear queue and add whole list of items
        DSP.queue = []
        volumioIO.emit('addToQueue', DSP.libraryFull['navigation']['lists'][0]['items'])
        DSP.stateTimeout = 5.0  # maximum time to load new queue
        while len(DSP.queue) == 0 and DSP.stateTimeout > 0.1:
            sleep(0.1)
        DSP.stateTimeout = 0.2
        log.info("Play position = " + str(itemNo))
        volumioIO.emit('play', {'value': itemNo})


def LibraryReturn():  # go to parent category
    if not 'prev' in DSP.libraryFull['navigation']:
        DSP.state = STATE_PLAYER
    else:
        parentCategory = DSP.libraryFull['navigation']['prev']['uri']
        log.info("Navigating to parent category in library: " + parentCategory.encode('ascii', 'ignore'))
        if parentCategory != '' and parentCategory != '/':
            volumioIO.emit('browseLibrary', {'uri': parentCategory})
        else:
            DSP.state= STATE_PLAYER


def onPushListPlaylist(data):
    global DSP
    if len(data) > 0:
        DSP.playlistoptions = data


"""
Startup initializer
"""

def _receive_thread():
    volumioIO.wait()

receive_thread = Thread(target=_receive_thread, name="Receiver")
receive_thread.daemon = True

volumioIO.on('pushState', onPushState)
volumioIO.on('pushListPlaylist', onPushListPlaylist)
volumioIO.on('pushQueue', onPushQueue)
volumioIO.on('pushBrowseSources', onPushBrowseSources)
# volumioIO.on('pushBrowseLibrary', onLibraryBrowse)

# get list of Playlists and initial state
volumioIO.emit('listPlaylist')
volumioIO.emit('getState')
volumioIO.emit('getQueue')
#volumioIO.emit('getBrowseSources')
sleep(0.1)
try:
    with open('DSPconfig.json', 'r') as f:  # load last playing track number
        config = json.load(f)
except IOError:
    pass
else:
    DSP.playPosition = config['track']

receive_thread.start()


def main():
    global emit_volume, emit_track
    while True:
        if emit_volume:
            emit_volume = False
            log.info("Volume: " + str(DSP.volume))
            volumioIO.emit('volume', DSP.volume)
            DSP.state=STATE_VOLUME
            DSP.stateTimeout = 0.01

        if emit_track and DSP.stateTimeout < 4.5:
            emit_track = False
            try:
                log.info('Track selected: ' + str(DSP.playPosition + 1) + '/' + str(len(DSP.queue)) + ' ' + DSP.queue[
                    DSP.playPosition].encode('ascii', 'ignore'))
            except IndexError:
                pass
            volumioIO.emit('play', {'value': DSP.playPosition})


def defer():
    try:
        receive_thread.join(1)
        DSP.cleanup()
        log.info("System exit ok")

    except Exception as err:
        log.err("Defer Error: " + str(err))

if __name__ == '__main__':
    try:
        main()
    except(KeyboardInterrupt, SystemExit):
        defer() # todo make work!

