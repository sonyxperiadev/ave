#! /usr/bin/python2

import os
import signal

print('SIGTERM suicide')
os.kill(os.getpid(), signal.SIGTERM)
