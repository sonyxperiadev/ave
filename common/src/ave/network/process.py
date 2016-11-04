# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import gc
import os
import sys
import time
import errno
import signal
import ctypes
import traceback

import json

import ave.cmd

from ave.network.pipe       import Pipe
from ave.network.exceptions import *

# the recommended method to implement get_children() and get_proc_name() is to
# use the psutil module but unfortunately the version in Ubuntu 10 is too old
# to support the needed functions.

def get_children(pid):
    cmd = ['/usr/bin/pgrep', '-P', str(pid)]
    pids = ave.cmd.run(cmd)[1]
    return [int(pid) for pid in pids.splitlines()]

def get_proc_name(pid):
    try:
        with open(os.path.join('/proc', str(pid), 'comm')) as f:
            return f.read().strip()
    except Exception, e:
        raise Exception('could not get process name for PID %d: %s' % (pid, e))

class Process(object):
    _pid    = -1
    target  = None
    args    = None
    logging = False

    def __init__(self, target=None, args=None, logging=False, proc_name=None):
        if target != None and not callable(target):
            raise Exception('target is not a callable: %s' % target)
        if type(logging) != bool:
            raise Exception('logging is not a boolean: %s' % logging)
        if not proc_name:
            proc_name = 'ave-%s' % type(self).__name__
        if type(proc_name) not in [str, unicode]:
            raise Exception('proc_name is not a string: %s' % proc_name)
        self.target    = target or self.run
        self.args      = args or ()
        self.logging   = logging
        self.proc_name = proc_name

    @property
    def pid(self):
        if self._pid < 0:
            raise Exception('process PID is not known')
        if self._pid == 0:
            return os.getpid()
        return self._pid

    def dump_fds(self):
        out = ave.cmd.run('ls -l /proc/%d/fd' % self.pid)[1]
        out = out.splitlines()
        out = [o.split() for o in out]
        out = [o for o in out if len(o) > 2]
        fds = {}
        for o in out:
            fds[int(o[8])] = o[10]
        return fds

    def list_fds(self):
        # unfortunately there is no portable way of listing file descriptors.
        # on linux: list the contents of /proc/<os.getpid()>/fd/.
        path = '/proc/%d/fd' % self.pid
        fds  = {}
        for f in os.listdir(path):
            target = os.path.realpath(os.path.join(path, f))
            fds[int(f)] = target
        return fds

    def close_fds(self, exclude):
        if type(exclude) != list:
            raise Exception('exclude is not a list: %s' % exclude)
        for i in exclude:
            if type(i) != int:
                raise Exception('exclude is not a list of int: %s' % exclude)
        # close all file descriptors except 0,1,2, whatever file descriptor is
        # connected to /dev/ptmx, and whatever the subclass wants to keep open.
        exclude.extend([0,1,2])
        for fd in self.list_fds().keys():
            if fd in exclude:
                continue
            try:
                os.close(fd)
            except OSError, e:
                if e.errno == errno.EBADF:
                    continue
                raise

    def redirect(self):
        pass

    def start(self, daemonize=False, synchronize=False):
        if synchronize:
            # pass a pipe down to the (grand) child so it can pass its pid back
            # when the child has been fully initialized. this synchronizes the
            # setup of signal handlers, which is otherwise hard to do for the
            # caller. it also lets the caller see the pid of daemon processes
            # as a property on the Process instance.
            # synchronization has a significant performance cost. disable it
            # for short lived daemons that need to be created quickly and will
            # not be interacted with by the caller. e.g. panotti shouters.
            pipe = Pipe()
            exclude = [pipe.w]
        else:
            pipe = None
            exclude = []
        if daemonize:
            if not self._daemonize():
                if synchronize:
                    self._pid = pipe.get() # now guaranteed to be reparented
                    del pipe
                return # parent returns to caller
            else:
                pass # continue below, at self.redirect()
        else:
            self._pid = os.fork()
            if self._pid != 0: # parent process
                if synchronize:
                    pipe.get() # now guaranteed to be fully initialized
                    del pipe
                return
        self.close_fds(exclude)
        self.redirect()
        gc.collect()
        self.log('start PID=%d' % self.pid)
        self.initialize()

        if synchronize:
            pipe.put(self.pid)
            del pipe

        exit_code = 0

        try:
            self.target(*self.args)
        except Exception, e:
            self.log('Exception in target():\n%s' % traceback.format_exc())
            exit_code = 1
        try:
            self.exit(exit_code)
        except Exception, e:
            self.log('Exception in exit():\n%s' % traceback.format_exc())
            exit_code = 2
        os._exit(exit_code) # make sure we *do* exit even if subclass is broken

    def exit(self, code):
        self.log('exit PID=%d code=%d' % (self.pid, code))
        os._exit(code) # do *not* return to caller

    def _daemonize(self):
        # double-fork. refer to "Advanced Programming in the UNIX Environment"
        try: # first fork
            pid = os.fork()
            if pid > 0: # first parent
                os.waitpid(pid, 0) # wait for second child to start
                return False # return to caller of daemonize()
        except OSError, e:
            self.log('fork #1 failed: %s' % e)
            return # return caller of daemonize()

        # decouple first parent
        os.setsid()
        os.chdir("/")
        os.umask(0)

        ppid = os.getpid() # yes, getpid(). it will be the child's ppid

        try: # second fork
            self._pid = os.fork()
            if self._pid > 0: # second parent. just exit
                os._exit(0) # this is the wait() above
        except OSError, e:
            self.log('fork #2 failed: %s' % e)
            os._exit(1)

        # wait until ppid changes
        while os.getppid() == ppid:
            time.sleep(0.1)

        return True

    def set_process_name(self, proc_name):
        # set a process name that is identifiable in top and ps
        libc = ctypes.CDLL('libc.so.6')
        PR_SET_NAME = 15
        libc.prctl(PR_SET_NAME, proc_name, 0, 0, 0)

    def perform_prctl(self, death_signal=0, __proc_name__=None):
        libc = ctypes.CDLL('libc.so.6')
        PR_SET_PDEATHSIG = 1
        libc.prctl(PR_SET_PDEATHSIG, death_signal) # 0 disables death signalling

        if __proc_name__: # backward comp for DUST. please don't use this param
            self.set_process_name(__proc_name__)

    def handle_SIGTERM(self, signum, frame):
        self.log('SIGTERM exit PID=%d' % self.pid)
        os._exit(signum)

    def handle_SIGUSR1(self, signum, frame):
        trace = ''.join(traceback.format_stack(frame))
        self.log('SIGUSR1 trace PID=%d:\n%s' % (self.pid, trace))

    def set_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.handle_SIGTERM)
        signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)
        # ensures that SIGTERM is sent to this process when its parent dies:
        self.perform_prctl(signal.SIGTERM)

    def initialize(self):
        self.set_signal_handlers()
        self.set_process_name(self.proc_name)

    def kill(self, sig):
        if self._pid == -1:
            raise Exception('cannot terminate unstarted process')
        try:
            os.kill(self.pid, sig)
        except os.error, e:
            if e.errno == errno.ESRCH: # no such process
                self.log('no process to kill with PID=%d\n' % self.pid)
                return
            raise

    def terminate(self):
        self.log('terminate by PID=%d' % os.getpid())
        self.kill(signal.SIGTERM)

    def join_nohang(self):
        if self._pid == -1:
            raise Unstarted('cannot join unstarted process')
        if self._pid == 0:
            raise Unjoinable('a process cannot join itself')
        try:
            return os.waitpid(self._pid, os.WNOHANG)
        except os.error, e:
            if e.errno == errno.ECHILD:
                raise Unwaitable('target process is not a child')
            if e.errno == errno.ESRCH:
                raise Unknown('cannot join unknown process')
            else:
                raise

    def join(self, timeout=None):
        if timeout:
            limit = time.time() + timeout
        else:
            limit = None
        while (limit == None) or (time.time() < limit):
            (pid,exit) = self.join_nohang()
            if (pid,exit) == (0,0):
                time.sleep(0.1)
                continue
            self.log('join by PID=%d' % os.getpid())
            return exit
        raise Timeout('timed out')

    def is_alive(self):
        try:
            (pid,exit) = os.waitpid(self.pid, os.WNOHANG)
            return (pid,exit) == (0,0)
        except os.error, e:
            if e.errno == errno.ECHILD:
                raise Unwaitable('target process is not a child')
            if e.errno == errno.ESRCH:
                raise Unknown('cannot wait for unknown process')
            raise
        return False

    def log(self, message):
        if self.logging:
            sys.stderr.write('%s %s %d -- %s\n' % (
                time.ctime(), self.proc_name, os.getpid(), message
            ))
            sys.stderr.flush()
