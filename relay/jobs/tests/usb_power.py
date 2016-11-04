# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import errno
import shutil
import time
import traceback

from ave.exceptions    import *

import setup

# check that the relays can be manipulated
def t1(b,r,h):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        r.set_circuit('usb.pc.vcc', False)
    except Exception, e:
        print('FAIL %s: could not cut usb.pc.vcc: %s' % (pretty, str(e)))
        return
    try:
        state = h.wait_power_state('offline', timeout=5)
    except Exception, e:
        print('FAIL %s: waiting for offline failed: %s' % (pretty, str(e)))
        return
    if state != 'offline':
        print('FAIL %s: non-offline state: %s' % (pretty, state))
        return

    r.set_circuit('usb.pc.vcc', True)
    try:
        state = h.wait_power_state('boot_completed', timeout=5)
    except Exception, e:
        print('FAIL %s: waiting for android failed: %s' % (pretty, str(e)))
        return
    if state != 'boot_completed':
        print('FAIL %s: non-android mode: %s' % (pretty, state))
        return

# check that timeouts work on state waits
def t2(b,r,h):
    pretty = '%s t2' % __file__
    print(pretty)

    r.set_circuit('usb.pc.vcc', False)
    h.wait_power_state('offline', timeout=5)

    r.set_circuit('usb.pc.vcc', True)
    try:
        state = h.wait_power_state('boot_completed', timeout=0.0001)
        print('FAIL %s: waiting did not time out: %s' % (pretty, state))
        return
    except Timeout:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return

    # make sure we're back in android mode before ending the test
    try:
        h.wait_power_state('boot_completed', timeout=10)
    except Exception, e:
        print('FAIL %s: waiting for android mode failed: %s' % (pretty, str(e)))
        return

# check that relays are always closed when the broker reclaims them. otherwise
# equipment will most certainly disappear from time to time because jobs quit
# after opening a relay
def t3(b,r,h):
    pretty = '%s t3' % __file__
    print(pretty)

    # open the usb.pc.vcc relay to disconnect the handset. then yield the relay
    # back to the broker and wait for the handset to reappear as usb.pc.vcc gets
    # closed by the broker
    r.set_circuit('usb.pc.vcc', False)
    h.wait_power_state('offline', timeout=5)
    b.yield_resources(r)
    try:
        h.wait_power_state('boot_completed', timeout=5)
    except Exception, e:
        print('FAIL %s: handset did not reappear: %s' % (pretty, str(e)))
        return

