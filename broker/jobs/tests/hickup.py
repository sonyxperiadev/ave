#coding=utf8

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import glob
import json
import signal

from ave.network.exceptions import *
from ave.network.control    import RemoteControl
from ave.network.connection import *

import setup

def wait_hickup_dir(path, timeout):
    limit = time.time() + timeout
    while True:
        if time.time() > limit:
            return False
        if os.path.isdir(path):
            return True
        time.sleep(0.5)

# check that signalling a control process does not kill it
@setup.factory()
def t01(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    ctrl = factory.make_master('master')
    pid  = ctrl.get_pid()
    os.kill(pid, signal.SIGUSR1)

    try:
        pid = ctrl.get_pid()
    except ConnectionClosed, e:
        print('FAIL %s: SIGUSR1 killed the process: %s' % (pretty, e))
        return False
    except Exception, e:
        print('FAIL %s: unknown error: %s' % (pretty, e))
        return False

    return True

# check that trace files are written to <home>/.ave/hickup with predictable
# file names
@setup.factory()
def t02(factory):
    pretty = '%s t2' % __file__
    print(pretty)

    ctrl = factory.make_master('master')
    pid  = ctrl.get_pid()
    os.kill(pid, signal.SIGUSR1)

    hickup_dir = os.path.join(factory.HOME.path, '.ave', 'hickup')
    # signal handler runs asynchronously. allow for time to pass before failing
    if not wait_hickup_dir(hickup_dir, 3):
        print('FAIL %s: hickup dir not created' % pretty)
        return False

    # expect to find a file whose name includes todays date, the name of the
    # signalled process and the process' pid. don't bother with high clock
    # resolution in the date check. do note that the test *can* fail if run
    # run very close to midnight
    files = glob.glob(os.path.join(hickup_dir, '*'))
    date  = time.strftime('%Y%m%d')

    if len(files) != 2: # for the broker and one session
        print('FAIL %s: wrong number of files: %s' % (pretty, files))
        return False

    if date not in files[0]:
        print('FAIL %s: date not in file name: %s' % (pretty, files[0]))
        return False

    if 'broker' not in files[0]:
        print('FAIL %s: process name not in file name: %s' % (pretty, files[0]))
        return False

    if str(pid) not in files[0] and str(pid) not in files[1]:
        print('FAIL %s: pid not in file name: %s' % (pretty, files[0]))
        return False

    return True

# check that the signal does not interfere with equipment listers
@setup.factory()
def t03(factory):
    pretty = '%s t3' % __file__
    print(pretty)

    ctrl  = factory.make_master('master')
    bpid  = ctrl.get_pid()
    lpids = ctrl.get_lister_pids()

    if [pid for pid in lpids if pid < 2] != []:
        print('FAIL %s: impossible lister PIDs: %d' % (pretty, lpids))
        return False

    # signal the broker and wait for the hickup directory to appear. the signal
    # should be propagated to the equipment lister long before the directory is
    # created.
    os.kill(bpid, signal.SIGUSR1)
    path = os.path.join(factory.HOME.path, '.ave', 'hickup')
    wait_hickup_dir(path, 3)

    lpids2 = ctrl.get_lister_pids()
    if lpids2 != lpids:
        print('FAIL %s: listers affected: %s != %s' % (pretty, lpids2, lpids))
        return False

    return True

# check that the signal does not interfere with sessions
@setup.factory()
def t04(factory):
    pretty = '%s t4' % __file__
    print(pretty)

    ctrl  = factory.make_master('master')
    bpid  = ctrl.get_pid()
    spids = ctrl.get_session_pids()

    if [pid for pid in spids if pid < 2] != []:
        print('FAIL %s: impossible session PIDs: %d' % (pretty, spids))
        return False

    # signal the broker and wait for the hickup directory to appear. the signal
    # should be propagated to the equipment lister long before the directory is
    # created.
    os.kill(bpid, signal.SIGUSR1)
    path = os.path.join(factory.HOME.path, '.ave', 'hickup')
    wait_hickup_dir(path, 3)

    spids2 = ctrl.get_session_pids()
    if spids2 != spids:
        print('FAIL %s: sessions affected: %s != %s' % (pretty, spids2, spids))
        return False

    return True
