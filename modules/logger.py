
'''
Multicollor logger by Stefan Larsson
'''

import datetime


class LOGLEVEL:
    def __init__(self):
        pass
    FATAL = -1
    ERROR = 0
    WARN = 1
    INFO = 2
    DEBUG = 3


class Log:
    def __init__(self, level=LOGLEVEL.WARN):
        self._lvl = level

    def fatal(self, text):  # Red
        if self._lvl == LOGLEVEL.FATAL:
            print("{}--:\033[91m FATAL\033[0m :--- {}".format(datetime.datetime.now().strftime("t:%S.%f"), text))

    def err(self, text, err = ''):    # Red
        if self._lvl <= LOGLEVEL.ERROR:
            print("{}--:\033[91m DERROR\033[0m :--- {}: {}".format(datetime.datetime.now().strftime("t:%S.%f"), text, err))

    def warn(self, text):   # Magenta
        if self._lvl <= LOGLEVEL.WARN:
            print("{}--:\033[95m Warning\033[0m :--- {}".format(datetime.datetime.now().strftime("t:%S.%f"), text))

    def info(self, text):   # Green
        if self._lvl <= LOGLEVEL.INFO:
            print("{}--:\033[92m Info\033[0m :--- {}".format(datetime.datetime.now().strftime("t:%S.%f"), text))

    def debug(self, text):  # Yellow
        if self._lvl <= LOGLEVEL.DEBUG:
            print("{}--:\033[93m Debug\033[0m :--- {}".format(datetime.datetime.now().strftime("t:%S.%f"), text))

    def blue(self, text):    # Blue
        if self._lvl <= LOGLEVEL.DEBUG:
            print("{}--:\033[94m Debug\033[0m :--- {}".format(datetime.datetime.now().strftime("t:%S.%f"), text))

    def set_level(self, level):
        if level in range(-1, 3):
            self._lvl = level
        else:
            self.warn("Unable to set Log level: " + str(level))

    def get_level(self):
        return self._lvl

