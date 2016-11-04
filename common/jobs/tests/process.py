import os
import time
import psutil
import signal
import traceback

from ave.network.connection import find_free_port
from ave.network.process    import Process, get_proc_name, get_children
from ave.network.pipe       import Pipe
from ave.network.exceptions import Unstarted, Unwaitable, Unjoinable, Unknown
from ave.relay.lister       import RelayLister
from ave.relay.reporter     import Reporter
from ave.relay.server       import RelayServer

import setup

class P(Process):

    def run(self):
        while True:
            time.sleep(1)

class Stubborn(Process):

    def perform_prctl(self, death_signal=0):
        return # do not set PDEATHSIG

    def run(self):
        time.sleep(3)

class P2(P):

    def __init__(self, pipe, death_to_the_child=True):
        P.__init__(self)
        self.pipe               = pipe
        self.death_to_the_child = death_to_the_child

    def close_fds(self, exclude):
        exclude.append(self.pipe.w)
        Process.close_fds(self, exclude)

    def run(self):
        if self.death_to_the_child:
            p = P()
        else:
            p = Stubborn()
        p.start(synchronize=True)
        self.pipe.put(p.pid)
        while True:
            time.sleep(1)

class P3(Process):

    def run(self):
        time.sleep(2)

class Dummy(Process):

    def __init__(self, pid):
        self._pid = pid

# start/stop child
@setup.factory()
def t1(pretty, factory):
    try:
        p = P()
    except Exception, e:
        print('FAIL %s: could not create process: %s' % (pretty, e))
        return False

    try:
        p.start()
    except Exception, e:
        print('FAIL %s: could not start process: %s' % (pretty, e))
        return False

    try:
        pid = p.pid
    except Exception, e:
        print('FAIL %s: process has unknown pid: %s' % (pretty, e))
        return False

    try:
        p.terminate()
        p.join()
    except Exception, e:
        print('FAIL %s: could not terminate/join child: %s' % (pretty, e))
        return False

    return True

# start/stop daemon
@setup.factory()
def t2(pretty, factory):
    p = P()

    try:
        p.start(daemonize=True, synchronize=True)
    except Exception, e:
        print('FAIL %s: could not start process: %s' % (pretty, e))
        return False

    try:
        pid = p.pid
    except Exception, e:
        print('FAIL %s: could not get pid: %s' % (pretty, e))
        return False

    try:
        p.terminate()
    except Exception, e:
        print('FAIL %s: could not terminate: %s' % (pretty, e))
        return False

    try:
        p.join()
        print('FAIL %s: could join daemonized process' % pretty)
        return False
    except Unwaitable:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    return True

# child has correct process name?
@setup.factory()
def t3(pretty, factory):
    p = P(proc_name='proc_t3')
    p.start()
    factory.processes.append(p)

    time.sleep(1) # the actual set operation in the OS is asynchronous
    name = get_proc_name(p.pid)

    if name != 'proc_t3':
        print('FAIL %s: wrong name: %s' % (pretty, name))
        return False

    return True

# daemon has correct process name?
@setup.factory()
def t4(pretty, factory):
    p = P(proc_name='proc_t4')
    p.start(daemonize=True, synchronize=True)
    factory.processes.append(p)

    time.sleep(1) # the actual set operation in the OS is asynchronous
    name = get_proc_name(p.pid)

    if name != 'proc_t4':
        print('FAIL %s: wrong name: %s' % (pretty, name))
        return False

    return True

# grandchild dies when child dies if PDEATHSIG is set (default)?
@setup.factory()
def t5(pretty, factory):
    pipe = Pipe()
    p = P2(pipe)
    p.start()
    factory.processes.append(p)

    gc_pid = pipe.get()

    try:
        proc = psutil.Process(gc_pid)
    except Exception, e:
        print('FAIL %s: could not query grandchild: %s' % (pretty, e))
        return False

    os.kill(p.pid, signal.SIGKILL)

    ok = False
    for i in range(3):
        try:
            proc = psutil.Process(gc_pid)
        except psutil.NoSuchProcess:
            ok = True
            break
        time.sleep(0.5)

    if not ok:
        print('FAIL %s: could query grandchild: %s' % (pretty, proc))
        return False

    return True

# grandchild does not die when child dies if PDEATHSIG is unset?
@setup.factory()
def t6(pretty, factory):
    pipe = Pipe()
    p = P2(pipe, False)
    p.start()
    factory.processes.append(p)

    gc_pid = pipe.get()
    factory.processes.append(Dummy(gc_pid)) # so that setup kills it

    try:
        proc = psutil.Process(gc_pid)
    except Exception, e:
        print('FAIL %s: could not query grandchild: %s' % (pretty, e))
        return False

    os.kill(p.pid, signal.SIGTERM)

    ok = True
    for i in range(3):
        try:
            proc = psutil.Process(gc_pid)
        except psutil.error.NoSuchProcess:
            ok = False
            break
        time.sleep(0.5)

    if not ok:
        print('FAIL %s: grandchild died: %s' % pretty)
        return False

    return True

# can check liveness of child?
@setup.factory()
def t7(pretty, factory):
    p = P()
    p.start()
    factory.processes.append(p)

    try:
        alive = p.is_alive()
    except Exception, e:
        print('FAIL %s: could not check liveness: %s' % (pretty, e))
        return False

    if not alive:
        print('FAIL %s: wrong liveness' % pretty)
        return False

    p.terminate()

    for i in range(3):
        try:
            alive = p.is_alive()
            if not alive:
                break
        except Exception, e:
            print('FAIL %s: could not check deadness: %s' % (pretty, e))
            return False
        time.sleep(0.5)

    if alive:
        print('FAIL %s: wrong deadness' % pretty)
        return False

    return True    

# can not check liveness of grandchild?
@setup.factory()
def t8(pretty, factory):
    pipe = Pipe()
    p = P2(pipe)
    p.start()
    factory.processes.append(p)
    gc_pid = pipe.get()
    d = Dummy(gc_pid)
    factory.processes.append(d)

    try:
        alive = d.is_alive()
        print('FAIL %s: could check liveness of grandchild' % pretty)
        return False
    except Unwaitable:
        pass
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    return True

# can get pid of daemon?
@setup.factory()
def t9(pretty, factory):
    p = P3()
    p.start(daemonize=True, synchronize=True)
    try:
        pid = p.pid
    except Exception, e:
        print('FAIL %s: could not get pid of grandchild: %s' % (pretty, e))
        return False

    os.kill(pid, signal.SIGKILL) # the process will die anyway, but whatever
    return True
