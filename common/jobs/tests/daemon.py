# Copyright (C) 2013-2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import errno
import signal
import traceback

from psutil import Process, NoSuchProcess

from ave.network.daemon     import Daemon
from ave.network.control    import Control
from ave.network.connection import find_free_port
from ave.workspace          import Workspace
from ave.exceptions         import Timeout

class MockDaemon(Daemon):

    def run(self):
        self.log('run')
        for i in range(10):
            time.sleep(1)

    def rerun(self):
        self.log('rerun')
        for i in range(10):
            time.sleep(1)

def join(pid, timeout):
    if pid == 0:
        return
    start = time.time()
    while time.time() - start < timeout:
        try:
            proc = Process(pid)
        except NoSuchProcess:
            return
        except IOError, e:
            if e.errno == errno.ESRCH:
                return
            else:
                raise e
        time.sleep(0.5)
    raise Timeout('timeout')

def setup(fn):
    def decorated():
        w = Workspace()
        result = fn(w)
        w.delete()
        return result
    return decorated

# daemon can be started/stopped?
@setup
def t01(w):
    pretty = '%s t1' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = MockDaemon(pid_path, log_file)

    d.start()

    pid = d.get_pid()

    d.stop()

    ok = False
    for i in range(6):
        try:
            proc = Process(pid)
        except NoSuchProcess:
            ok = True
            break # good
        time.sleep(0.5)

    if not ok:
        print('FAIL %s: could not stop daemon' % pretty)
        os.kill(pid, signal.SIGTERM)

    return ok

# look for the pid file. check that it is deleted when the deamon stops
@setup
def t02(w):
    pretty = '%s t2' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = MockDaemon(pid_path, log_file)

    d.start()

    if not os.path.exists(pid_path):
        print('FAIL %s: no pid file after start' % pretty)
        d.stop()
        return False

    d.stop()

    if os.path.exists(pid_path):
        print('FAIL %s: pid file remains after stop: %s' % (pretty, pid_path))
        return False

    return True

# check that the daemon is reparented to init (pid 1)
@setup
def t03(w):
    pretty = '%s t3' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = MockDaemon(pid_path, log_file)

    d.start()
    pid = d.get_pid()

    ok = False
    for i in range(10):
        proc = Process(pid)
        if isinstance(type(proc).ppid, property):
            ppid = proc.ppid
        else:
            ppid = proc.ppid()
        if ppid == 1:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: daemon not reparented: ppid=%s' % (pretty, ppid))

    d.stop()

    return ok

# check that the daemon can be restarted
@setup
def t04(w):
    pretty = '%s t4' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = MockDaemon(pid_path, log_file)

    d.start()
    pid1 = d.get_pid()
    d.restart()
    pid2 = d.get_pid()

    if pid1 == pid2:
        print('FAIL %s: pid did not change after restart' % pretty)
        d.stop()
        return False

    ok = False
    for i in range(10):
        proc = Process(pid2)
        if isinstance(type(proc).ppid, property):
            ppid = proc.ppid
        else:
            ppid = proc.ppid()
        if ppid == 1:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: daemon not reparented: ppid=%d' % (pretty, ppid))

    d.stop()

    return ok

# check that test helper join() works
@setup
def t05(w):
    pretty = '%s t5' % __file__
    print(pretty)

    class SuicideDaemon(Daemon):
        def run(self):
            self.log('goodbye cruel world!')

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = SuicideDaemon(pid_path, log_file)

    d.start()
    try:
        join(d.get_pid(), 5)
    except Exception, e:
        print('FAIL %s: daemon did not die: %s' % (pretty, e))
        return False

    return True

# check that the same file can be used as explicit log file, stdout and stderr
@setup
def t06(w):
    pretty = '%s t6' % __file__
    print(pretty)

    class PrintDaemon(Daemon):
        def run(self):
            self.log('print to log file')
            print('print to stdout')
            sys.stderr.write('print to stderr\n')
            sys.stderr.flush()

    log_path = w.make_tempfile()
    pid_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = PrintDaemon(pid_path, log_file, stdout=log_file, stderr=log_file)

    d.start()
    join(d.get_pid(), 5)

    with open(log_path) as f:
        log_seen = stdout_seen = stderr_seen = False
        contents = f.readlines()
        for line in contents:
            if 'print to log file' in line:
                log_seen = True
            if 'print to stdout' in line:
                stdout_seen = True
            if 'print to stderr' in line:
                stderr_seen = True

        if not log_seen:
            print('FAIL %s: no writes to log file' % pretty)
            return False
        if not stdout_seen:
            print('FAIL %s: no writes to stdout' % pretty)
            return False
        if not stderr_seen:
            print('FAIL %s: no writes to stderr' % pretty)
            return False

# check that the daemon reparents to init even if the subclass' run() crashes.
# also check that the pid file is gone afterwards
@setup
def t07(w):
    pretty = '%s t7' % __file__
    print(pretty)

    class CrashDaemon(Daemon):
        def run(self):
            time.sleep(1)
            raise Exception('good news everyone!')

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')
    d        = CrashDaemon(pid_path, log_file, stderr=log_file)

    d.start()

    proc = Process(d.get_pid())
    ok   = True
    if isinstance(type(proc).ppid, property):
        ppid = proc.ppid
    else:
        ppid = proc.ppid()
    if ppid != 1:
        print('FAIL %s: daemon not reparented: ppid=%d' % (pretty, ppid))
        ok = False

    join(d.get_pid(), 5)

    if os.path.exists(pid_path):
        print('FAIL %s: crashed daemon did not remove its pid file' % pretty)
        return False

    with open(log_path) as f:
        contents = f.read()
        if 'good news everyone!' not in contents:
            print('FAIL %s: stack trace not logged:\n%s' % (pretty, contents))
            return False

    return True

# check that restarting in an overlapping fashion does not result in a chomped
# pid file. the original daemon may exit after the replacement has started and
# will want to delete its pid file
@setup
def t08(w):
    pretty = '%s t8' % __file__
    print(pretty)

    class SlowDeath(Daemon):

        def __init__(self, pid_path, log_file):
            Daemon.__init__(self, pid_path, log_file)

        def handle_SIGTERM(self, signum, frame):
            self.log('SIGTERM')
            self.stop = True

        def run(self):
            self.stop = False
            self.log('none done')
            signal.signal(signal.SIGTERM, self.handle_SIGTERM)
            while not self.stop:
                time.sleep(1)
            self.log('half done')

        def rerun(self):
            self.stop = False
            while not self.stop:
                time.sleep(1)
            self.log('all done')

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()
    log_file = open(log_path, 'w')

    d1 = SlowDeath(pid_path, log_file)
    d1.start()
    pid1 = d1.get_pid()

    d2 = SlowDeath(pid_path, log_file)
    d2.restart()
    pid2 = d2.get_pid()

    os.kill(pid1, signal.SIGTERM)
    join(pid1, 5)

    if not os.path.exists(pid_path):
        print('FAIL %s: pid file got chomped' % pretty)
        os.kill(pid2, signal.SIGTERM)
        return False

    try:
        d2.stop()
    except Exception, e:
        print('FAIL %s: could not stop replacement: %s' % (pretty, e))
        return False

    return True

class Duster(Control):

    def __init__(self):
        sock,port = find_free_port()
        Control.__init__(self, port, None, sock, logging=True, interval=1)

    def idle(self):
        raise Exception('idle')

class DusterDaemon(Daemon):

    def __init__(self, pid_path, log_path):
        log = open(log_path, 'a+', 0)
        Daemon.__init__(self, pid_path, log, stdout=log, stderr=log)

    def run(self):
        try:
            j = Duster()
            j.start()
        except Exception, e:
            self.log('failed to start duster: %s' % str(e))
            return 1
        print 'started'
        pid = j.pid
        self.log('started duster pid = %d' % pid)
        j.join() # wait until the duster dies
        self.log('joined duster pid = %d' % pid)

    def rerun(self):
        # normally stop() would be executed here, but to get desired behaviour
        # that's done in main (to be able to provide error message to the user
        # instead of silent failure and only print to log...)
        try:
            j = Duster()
            j.start()
        except Exception, e:
            self.log('failed to restart duster: %s' % str(e))
            return 1
        pid = j.pid
        self.log('restarted duster pid = %d' % pid)
        j.join()
        self.log('joined duster pid = %d' % pid)

# start a daemon after the same pattern found in many DUST executables
@setup
def t09(w):
    pretty = '%s t9' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()

    pid = 0

    d1 = DusterDaemon(pid_path, log_path)
    d1.start()

    try:
        pid = d1.get_pid()
    except Exception, e:
        print('FAIL %s: could not read d1 PID file: %s' % (pretty, e))
        return False

    d2 = DusterDaemon(pid_path, log_path)
    d2.restart()

    try:
        pid = d2.get_pid()
    except Exception, e:
        print('FAIL %s: could not read d2 PID file: %s' % (pretty, e))
        return False

    d3 = DusterDaemon(pid_path, log_path)
    d3.stop()

    if d3.get_pid():
        print('FAIL %s: PID file not deleted' % pretty)
        return False

    return True

# does exception catching in Process.start() result in a log entry for the
# daemon?
@setup
def t10(w):
    pretty = '%s t10' % __file__
    print(pretty)

    pid_path = w.make_tempfile()
    log_path = w.make_tempfile()

    d1 = DusterDaemon(pid_path, log_path)
    d1.start()
    time.sleep(2)

    with open(log_path) as f:
        content = f.read()
        if 'Exception in target():' not in content:
            print('FAIL %s: wrong logs: %s' % (pretty, content))
            return False

    try:
        d1.stop()
        print('FAIL %s: could stop daemon without PID file' % pretty)
        return False
    except Exception, e:
        if 'pid file %s does not exist' % pid_path not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True
