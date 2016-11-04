# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import json
import signal
import ctypes
import traceback

import ave.config

from ave.network.process    import Process
from ave.network.exceptions import ConnectionClosed, AveException

class Reporter(Process):

    def __init__(self, home, logging, profiles, timeout):
        self.home     = home
        self.profiles = profiles
        self.timeout  = timeout
        Process.__init__(self, None, None, logging, 'ave-relay-reporter')

    def set_signal_handlers(self):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)

    def run(self):
        try:
            from ave.broker import Broker
            authkeys = ave.config.load_authkeys(self.home)
            broker = Broker(None, self.timeout, authkeys['share'], self.home)
        except Exception, e:
            self.log('ERROR: could not create broker client: %s' % e)
            return # early return
        try:
            self.log(
                'report virtual equipment list to broker:\n%s'
                % json.dumps(self.profiles, indent=4)
            )
            broker.add_equipment('local', self.profiles)
        except ConnectionClosed:
            self.log('broker closed the connection')
        except AveException, e:
            self.log('ERROR: broker exception:\n%s\n%s' % (e.format_trace(), e))
        except Exception, e:
            self.log('WARNING: could not report: %s' % str(e))
