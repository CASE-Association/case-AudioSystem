'''
Todo I2C guard to only read if ADAU1701 is confirmed confgured.
'''

from hardware import adau1701 as DSP
from modules import logger
import RPi.GPIO as GPIO
import time



GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
_VOL_READBACK_HIGH = 0x00
_VOL_READBACK_LOW = 0xB2
log = logger.Log()
#GPIO.setup([23, 15, 16], GPIO.OUT)
#GPIO.output([23, 15, 16], 0)


emit_volume = True
_update_hw_vol_freq = 3
_t_scan = time.time()
hw_volume = 0
sw_volume = 0
balance = 0
vol_err = 0
_VOL_ERR_HYSTERES = 2
rising_vol = True  # Defines the direction of volume knob rotation

def update_volume(f=None):
    if not f:
        f = _update_hw_vol_freq
    if time.time() - _t_scan >= 1/f:
        get_hw_vol()
        if emit_volume:
            return True
    return False


def hw_vol_up():
    GPIO.output(23, 1)
    GPIO.output([15, 16], (GPIO.HIGH, GPIO.LOW))


def hw_vol_dn():
    GPIO.output(23, 1)
    GPIO.output([15, 16], (GPIO.LOW, GPIO.HIGH))


def hw_vol_stop():
    GPIO.output([15, 16], 0)


def get_hw_vol():
    global _t_scan, _update_hw_vol_freq, hw_volume, sw_volume, vol_err, emit_volume, rising_vol
    _t_scan = time.time()
    vol = int(float(DSP.read_back(_VOL_READBACK_HIGH, _VOL_READBACK_LOW))*101)

    # Higher sensitively in turning direction and lower in opposite direction.
    if rising_vol and (vol > hw_volume or (vol + 1) < hw_volume) or\
            (vol < hw_volume or (vol - 1) > hw_volume):
        _update_hw_vol_freq = 10
        rising_vol = hw_volume < vol
        hw_volume = vol
        log.info("HW Volume: {}%".format(hw_volume))
        vol_err = abs(sw_volume - hw_volume)
        emit_volume = True
    else:
        _update_hw_vol_freq = 1.9
    return hw_volume


def set_hw_vol(vol=-1):
    global vol_err
    _TIMEOUT = 0.05
    if vol == -1:
        vol = sw_volume
    t_now = time.time()
    vol_now = get_hw_vol()

    # approx time to reach vol
    t_dif = abs(vol - vol_now)

    # while not timed out, try to set volume
    while t_now + _TIMEOUT * t_dif + 0.5 > time.time():
        v_now = get_hw_vol()
        new_vol_err = abs(vol - vol_now)
        if vol_err < _VOL_ERR_HYSTERES:
            hw_vol_stop()
            return True
        elif v_now < vol:
            hw_vol_up()
        else:
            hw_vol_dn()

        # Check if mechanical error
        if new_vol_err >= vol_err:
            time.sleep(0.75)
            if new_vol_err >= vol_err:
                hw_vol_stop()
                break
        vol_err = new_vol_err

        time.sleep(0.005*vol_err)
    hw_vol_stop()
    return False
