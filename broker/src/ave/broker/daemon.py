# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import json
import time
import errno
import signal
import traceback

from ave.network.exceptions import *
from ave.broker._broker     import Broker, RemoteBroker

PID_PATH = '/var/tmp/ave-broker.pid'
LOG_PATH = '/var/tmp/ave-broker.log'

class BrokerDaemon(Broker):

    def __init__(self, adoption=None, fdtx_path=None):
        Broker.__init__(self, adoption=adoption, fdtx_path=fdtx_path)
        self.input  = open('/dev/null', 'r')
        self.output = open(LOG_PATH, mode='a+', buffering=0)

    def close_fds(self, exclude):
        exclude.append(self.input.fileno())
        exclude.append(self.output.fileno())
        Broker.close_fds(self, exclude)

    def redirect(self):
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self.input.fileno(),  sys.stdin.fileno())
        os.dup2(self.output.fileno(), sys.stdout.fileno())
        os.dup2(self.output.fileno(), sys.stderr.fileno())

    def set_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.handle_SIGTERM)
        signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

    def write_pid_file(self):
        with open(PID_PATH,'w+') as f:
            os.fchmod(f.fileno(), 0666)
            f.write(str(self.pid))
            f.flush()

    def read_pid_file(self):
        try:
            with open(PID_PATH,'r') as f:
                pid = f.read().strip()
                if pid:
                    return int(pid)
        except (IOError, ValueError):
            pass
        # got error or file has invalid content:
        raise Exception('pid file %s does not exist' % PID_PATH)

    def initialize(self):
        self.write_pid_file()
        Broker.initialize(self)

    def start(self):
        Broker.start(self, daemonize=True)

    def restart(self, authkey):
        # find the already running broker. the port number mustn't have changed
        handover = RemoteBroker(timeout=3, authkey=authkey)
        try:
            adoption,config,fdtx_path = handover.begin_handover()
        except Exception, e:
            self.log('ERROR: handover failed: %s' % str(e))
            return

        # create the new broker
        takeover = BrokerDaemon(adoption=adoption, fdtx_path=fdtx_path)
        takeover.start()
        try:
            handover.end_handover(3) # raises ConnectionClosed if it shuts down
        except ConnectionClosed:
            pass
        except Exception, e:
            self.log('ERROR: handover failed: %s' % str(e))
            return

        pid = takeover.read_pid_file()
        self.log('restarted pid = %d' % pid)

    def stop(self):
        pid = self.read_pid_file()
        try: # can't call waitpid() on non-child. instead retry until exception
            for i in range(3):
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            # still not dead? kill harder
            os.kill(pid, signal.SIGKILL)
        except OSError, e:
            if e.errno == errno.ESRCH:
                pass
            else:
                raise e
        if os.path.exists(PID_PATH):
             os.remove(PID_PATH)

    def hickup(self):
        pid = self.read_pid_file()
        os.kill(pid, signal.SIGUSR1)
