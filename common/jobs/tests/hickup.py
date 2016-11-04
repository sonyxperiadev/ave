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
from ave.network.process    import Process

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
def t01(pretty, factory):
    ctrl = factory.make_control(home=factory.HOME.path)
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
def t02(pretty, factory):
    ctrl = factory.make_control(home=factory.HOME.path)
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

    if len(files) != 1:
        print('FAIL %s: wrong number of files: %s' % (pretty, files))
        return False

    if date not in files[0]:
        print('FAIL %s: date not in file name: %s' % (pretty, files[0]))
        return False

    if 'MockControl' not in files[0]:
        print('FAIL %s: process name not in file name: %s' % (pretty, files[0]))
        return False

    if str(pid) not in files[0]:
        print('FAIL %s: pid not in file name: %s' % (pretty, files[0]))
        return False

    return True

# check that the signal is propagated to children
@setup.factory()
def t03(pretty, factory):
    ctrl = factory.make_control(home=factory.HOME.path)
    pid  = ctrl.get_pid()
    ctrl.make_child()
    os.kill(pid, signal.SIGUSR1)

    path = os.path.join(factory.HOME.path, '.ave', 'hickup')
    wait_hickup_dir(path, 3)

    files = glob.glob(os.path.join(path, '*'))

    if len(files) != 2:
        print('FAIL %s: wrong number of files: %s' % (pretty, files))
        return False

    return True

# check that the signal is not propagated to non-ave processes such as external
# tools. these will otherwise terminate if they do not handle the signal.
@setup.factory()
def t04(pretty, factory):
    ctrl        = factory.make_control(home=factory.HOME.path)
    pid         = ctrl.get_pid()
    cport, cpid = ctrl.make_child()
    remote      = RemoteControl(('',cport), None, None)
    exe         = os.path.join(os.path.dirname(__file__),'hickup_catch_sigusr1')

    remote.run_external([exe, factory.HOME.path], __async__=True)
    time.sleep(1)
    os.kill(pid, signal.SIGUSR1)

    path = os.path.join(factory.HOME.path, '.ave', 'hickup')
    wait_hickup_dir(path, 3)
    time.sleep(1)

    files = glob.glob(os.path.join(path, '*'))

    for f in files:
        if f.endswith('hickup_catch_sigusr1'):
            print('FAIL %s: external child got SIGUSR1' % pretty)
            return False

    if len(files) != 2:
        print('FAIL %s: wrong number of files: %s' % (pretty, files))
        return False

    return True

# signal a process multiple times, count the trace files
@setup.factory()
def t05(pretty, factory):
    ctrl = factory.make_control(home=factory.HOME.path)

    for i in range(3):
        try:
            ctrl.kill(signal.SIGUSR1)
        except ConnectionClosed:
            print('FAIL %s: process died %d' % (pretty, i))
            return False
        except Exception, e:
            print('FAIL %s: unknown error %d: %s' % (pretty, i, e))
            return False
        time.sleep(1.1)

    path = os.path.join(factory.HOME.path, '.ave', 'hickup')
    wait_hickup_dir(path, 3)

    files = glob.glob(os.path.join(path, '*'))

    if len(files) != 3:
        print('FAIL %s: wrong number of files: %d' % (pretty, len(files)))
        return False

    return True

# check that signalling does not interfere with message passing
@setup.factory()
def t06(pretty, factory):
    def killer(pid):
        for i in range(150):
            os.kill(pid, signal.SIGUSR1)
            time.sleep(0.05)

    ctrl = factory.make_control(home=factory.HOME.path, authkey='')
    proc = Process(target=killer, args=(ctrl.get_pid(),))
    proc.start()

    # connect and authenticate
    conn = BlockingConnection(('',ctrl.port))
    conn.connect()
    conn.put(make_digest(conn.get(), ''))
    finish_challenge(conn.get())

    # feed messages slowly to the controller, check that it doesn't crash
    ok = True
    for i in range(15):
        blob = RemoteControl.make_rpc_blob('upper', None, 'a'*5000)
        conn.write(Connection.make_header(blob))
        #print '<',i
        for char in blob:
            conn.write(char)
            time.sleep(0.00002)
        #print '>',i
        try:
            msg = conn.get(timeout=1)
        except Exception, e:
            print('FAIL %s: control crashed in step %d: %s' % (pretty, i, e))
            ok = False
            break
        try:
            msg = json.loads(msg)
        except Exception, e:
            print('FAIL %s: could not decode response %d: %s' & (pretty, i, e))
            ok = False
            break
        if msg != { 'result': 'A'*5000 }:
            print('FAIL %s: wrong response in step %d: %s' % (pretty, i, msg))
            ok = False
            break

    proc.join()
    return ok
