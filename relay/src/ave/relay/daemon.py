import os
import sys
import time
import errno
import signal
import traceback

import ave.config

from ave.network.exceptions import *
from ave.relay.server       import RelayServer, RemoteRelayServer

PID_PATH = '/var/tmp/ave-relay.pid'
LOG_PATH = '/var/tmp/ave-relay.log'

class RelayServerDaemon(RelayServer):

    def __init__(self, inherited=None):
        RelayServer.__init__(self, inherited=inherited)
        self.input  = open('/dev/null', 'r')
        self.output = open(LOG_PATH, mode='a+', buffering=0)

    def close_fds(self, exclude):
        exclude.append(self.input.fileno())
        exclude.append(self.output.fileno())
        RelayServer.close_fds(self, exclude)

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
        RelayServer.initialize(self)

    def start(self):
        RelayServer.start(self, daemonize=True)

    def restart(self, authkey):
        # find the already running server. the port number mustn't have changed
        handover = RemoteRelayServer(authkey=authkey, timeout=3)
        try:
            state = handover.begin_handover()
        except AveException, e:
            trace = e.format_trace()
            self.log('ERROR: handover failed:\n%s\n%s' % (trace, e))
            return
        except Exception, e:
            trace = traceback.format_exc()
            self.log('ERROR: handover failed:\n%s\n%s' % (trace, e))
            return

        takeover = RelayServerDaemon(inherited=state['boards'])
        takeover.start()
        try:
            handover.end_handover() # raises ConnectionClosed if it shuts down
        except ConnectionClosed:
            pass
        except AveException, e:
            trace = e.format_trace()
            self.log('ERROR: handover failed:\n%s\n%s' % (trace, e))
            return
        except Exception, e:
            trace = traceback.format_exc()
            self.log('ERROR: handover failed:\n%s\n%s' % (trace, e))
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
