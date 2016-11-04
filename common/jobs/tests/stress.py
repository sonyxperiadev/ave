import os
import sys
import time
import string
import signal
import random

from ave.exceptions      import AveException, Exit
from ave.network.control import RemoteControl

import setup

def client_01(port, prefix):
    c = RemoteControl(('',port), None, timeout=10)
    while True:
        if random.random() > 0.9:
            c = RemoteControl(('',port), None, timeout=10)
        try:
            c.sync_ping()
        except Exit:
            os._exit(0)
        except Exception, e:
            print('client PID=%d got exception: %s' % (os.getpid(), e))
            os._exit(1)

def client_02(port, prefix):
    c = RemoteControl(('',port), None, timeout=10)
    while True:
        if random.random() > 0.8:
            c = RemoteControl(('',port), None, timeout=10)
        try:
            c.upper('x'*1000*1000)
        except Exit:
            os._exit(0)
        except Exception, e:
            print('client PID=%d got exception: %s' % (os.getpid(), e))
            os._exit(1)

def client_03(port, prefix):
    c = RemoteControl(('',port), None, timeout=10)
    while True:
        if random.random() > 0.7:
            c = RemoteControl(('',port), None, timeout=10)
        try:
            c.raise_ave_exception({'message':'hello', 'recognize':'me'})
        except Exit:
            os._exit(0)
        except AveException, e:
            if 'recognize' in e.details:
                continue
            print('client PID=%d got exception: %s' % (os.getpid(), e))
            os._exit(2)
        except Exception, e:
            print('client PID=%d got exception: %s' % (os.getpid(), e))
            os._exit(1)

# load test for control. send hickup if the control freezes up
@setup.factory()
def t1(pretty, factory):
    ctrl = factory.make_control(home=factory.HOME.path, max_tx=100000)
    pid  = ctrl.get_pid()
    port = ctrl.port

    children = []
    for c in range(30):
        children.append(factory.make_client(client_01, port, c))
    for c in range(30, 60):
        children.append(factory.make_client(client_02, port, c))
    for c in range(60, 90):
        children.append(factory.make_client(client_03, port, c))

    exit = 1
    cpid = 0
    emsg = ''

    while [proc for proc in children if proc.is_alive()] != []:
        time.sleep(1)

    for proc in children:
        # we're happy if any client returns zero as that means the control
        # finished correctly. other clients may then report error codes as
        # they may experience broken connections, etc, but those can then
        # be ignored.
        # there is a problem if *no* client returns zero.
        exit = min(exit, proc.exitcode)
        cpid = proc.pid

    if exit != 0:
        print('FAIL %s: PID %d detected an error' % (pretty, cpid))
        return False

    return True
