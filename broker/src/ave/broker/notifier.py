# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import json
import traceback

from ave.network.control import Control, RemoteControl
from ave.broker.profile  import profile_factory


def validate_address(addr):
    if (type(addr) != tuple
    or  len(addr) != 2
    or  type(addr[0]) not in [str, unicode]
    or  type(addr[1]) != int):
        raise Exception('address must be a (<string>,<integer>) tuple')

class Notifier(Control):
    remote_addr   = None
    remote_auth   = None
    local_addr    = None
    ws_profile    = None
    stacks        = None
    equipment     = None
    remote        = None
    allocations   = None
    collateral    = None

    def __init__(self, port, sock, remote_addr, remote_auth,local_addr,logging):
        Control.__init__(
            self, port, None, sock, interval=1, proc_name='ave-broker-notifier',
            logging=False
        )
        validate_address(remote_addr)
        validate_address(local_addr)
        self.remote_addr = remote_addr
        self.remote_auth = remote_auth
        self.remote      = None
        self.local_addr  = local_addr
        self.equipment   = None
        self.allocations = {}
        self.collateral  = {}

    def shutdown(self):
        if self.remote:
            self.remote = None
        Control.shutdown(self)

    def lost_connection(self, connection, authkey):
        self.log('lost connection: %s' % str(connection.address))
        if self.remote and connection == self.remote._connection:
            self.shutdown()

    def run(self):
        try:
            Control.run(self)
        except KeyboardInterrupt:
            self.shutdown()
        except Exception, e:
            traceback.print_exc()
            self.shutdown()

    def idle(self):
        self.execute()

    @Control.rpc
    def ping(self): # for testing purposes
        return 'pong'

    @Control.rpc
    def execute(self):
        # strategy: add everything on the todo-list until successful. sleep for
        # successively longer periods between retries.
        try:
            if not self.remote:
                self.remote = RemoteControl(
                    self.remote_addr, self.remote_auth, 5, False
                )
                self.add_keepwatching(self.remote.connect(5), self.remote_auth)
                self.log('connected to %s' % str(self.remote_addr))
        except Exception, e:
            self.log('WARNING: could not connect to master: %s' % e)
            self.remote = None
            self.retry_later()
            return
        try:
            if self.ws_profile:
                self.remote.set_ws_profile(self.local_addr, self.ws_profile)
            if self.stacks:
                self.remote.set_stacks(self.local_addr, self.stacks)
            if self.equipment != None:
                self.remote.set_equipment(
                    self.local_addr,
                    self.equipment,
                    self.allocations
                )
                dump = json.dumps(self.equipment,indent=4)
                addr = str(self.remote_addr)
                self.log('shared equipment with %s:\n%s' % (addr,dump))
        except Exception, e:
            self.log('WARNING: could not notify master: %s' % str(e))
            self.retry_later()
            return

        # clear the todo-list
        self.ws_profile     = None
        self.stacks         = None
        self.equipment      = None
        self.collateral     = {}
        self.allocations    = {}
        self.interval       = 1000 # do not sleep indefinitely in kernel space

    def retry_later(self):
        if self.interval < 16000:
            self.interval *= 2 # avoid hammering the remote broker

    @Control.rpc
    def set_ws_profile(self, profile, execute):
        self.ws_profile = profile
        if execute:
            self.execute()

    @Control.rpc
    def set_stacks(self, stacks, execute):
        self.stacks = stacks
        if execute:
            self.execute()

    @Control.rpc
    def set_equipment(self, profiles, allocations):
        self.equipment   = [profile_factory(p) for p in profiles]
        self.allocations = allocations
        self.execute()

class RemoteNotifier(RemoteControl):

    def __init__(self, address, timeout=1):
        RemoteControl.__init__(self, address, None, timeout)
