# Copyright (C) 2013-2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import signal
import traceback

from ave.network.process import Process

class Daemon(Process):
    pid_path = None # string
    log_file = None # file object
    stdin    = None # file object, defaults to /dev/null
    stdout   = None # file object, defaults to /dev/null
    stderr   = None # file object, defaults to /dev/null

    def __init__(self, pid_path, log_file, stdin=None,stdout=None,stderr=None):
        if not stdin:
            stdin = open('/dev/null', 'r')
        if not stdout:
            stdout = open('/dev/null', 'a+')
        if not stderr:
            stderr = open('/dev/null', 'a+', 0)

        if type(pid_path) not in [str, unicode]:
            raise Exception(
                'pid_path is not a string: %s' % type(pid_path).__name__
            )
        if type(log_file) != file:
            raise Exception(
                'log_file is not a file: %s' % type(log_file).__name__
            )
        if type(stdin) != file:
            raise Exception('stdin is not a file: %s' % type(stdin).__name__)
        if type(stdout) != file:
            raise Exception('stdout is not a file: %s' % type(stdout).__name__)
        if type(stderr) != file:
            raise Exception('stderr is not a file: %s' % type(stderr).__name__)

        self.pid_path = pid_path
        self.log_file = log_file
        self.stdin    = stdin
        self.stdout   = stdout
        self.stderr   = stderr

        Process.__init__(self, target=self.run, args=None, logging=True)

    def close_fds(self, exclude):
        exclude.append(self.stdin.fileno())
        exclude.append(self.stdout.fileno())
        exclude.append(self.stderr.fileno())
        exclude.append(self.log_file.fileno())
        Process.close_fds(self, exclude)

    def redirect(self):
        sys.stdout.flush()
        sys.stderr.flush()

        os.dup2(self.stdin.fileno(),  sys.stdin.fileno())
        os.dup2(self.stdout.fileno(), sys.stdout.fileno())
        os.dup2(self.stderr.fileno(), sys.stderr.fileno())

    # private only
    def set_pid(self, pid):
        with open(self.pid_path,'w+') as f:
            os.fchmod(f.fileno(), 0666)
            f.write(str(pid))
            f.flush()

    # both contexts
    def get_pid(self):
        try:
            with open(self.pid_path,'r') as f:
                pid = f.read().strip()
                if pid:
                    return int(pid)
        except IOError:
            pass
        except ValueError:
            pass
        return 0

    def start(self):
        if self.get_pid():
            raise Exception('pid file %s exist' % self.pid_path)

        Process.start(self, daemonize=True, synchronize=True)
        self.set_pid(self.pid)
        return self.get_pid()

    def restart(self):
        if not self.get_pid():
            raise Exception('pid file %s does not exist' % self.pid_path)

        old_pid = self.get_pid()
        self.target = self.rerun # override the default target=self.run
        Process.start(self, daemonize=True, synchronize=True)
        self.set_pid(self.pid)
        return self.get_pid()

    def stop(self):
        pid = self.get_pid()
        if not pid:
            raise Exception('pid file %s does not exist' % self.pid_path)

        try: # can't call waitpid() on non-child. instead retry until exception
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
        except OSError, e:
            if 'No such process' in str(e):
                if os.path.exists(self.pid_path):
                    os.remove(self.pid_path)
            else:
                raise e

    def exit(self, code):
        # remove the pid file unless an overlapped restart is ongoing. this is
        # visible as a change of the contents of the pid file
        if self.get_pid() == os.getpid():
            try:
                os.remove(self.pid_path)
            except Exception, e:
                self.log('could not delete pid file: %s' % e)
        Process.exit(self, code)

    def run(self):
        raise Exception('subclass must implement Daemon.run()')

    def rerun(self):
        raise Exception('subclass must implement Daemon.rerun()')
