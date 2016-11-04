# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import json
import signal

from datetime import datetime

import ave.config

from ave.network.control  import Control, RemoteControl
from ave.relay.profile    import BoardProfile, RelayProfile
from ave.relay.board      import RelayBoard
from ave.relay.lister     import RelayLister
from ave.relay.reporter   import Reporter
from ave.relay.exceptions import *
from ave.exceptions       import Restarting

DEFAULT_PORT_NUMBER = 4006

class RelayServer(Control):
    home       = None
    config     = None
    lister     = None
    inherited  = None # [BoardProfile, ...]
    virtual    = None # {RelayProfile: Board}
    restarting = False

    def __init__(self, home=None, config=None, inherited=None, socket=None,
        interval=10):
        if not home:
            home       = ave.config.load_etc()['home']
        if not config:
            config     = RelayServer.load_config(home)
        self.home      = home
        self.config    = RelayServer.validate_config(config)
        self.virtual   = {}
        if inherited:
            self.inherited = [BoardProfile(i) for i in inherited]
        else:
            self.inherited = []
        # if inherited != None then any relays detected by the lister must not
        # be reset to default values if they appear in the states list. instead
        # the server trusts that the states correctly represent those relays.
        # this is used in restarts of the server.

        # get values needed for initialization of the superclass
        alt_keys = ave.config.load_authkeys(home)
        port     = self.config['port']
        Control.__init__(
            self, port, None, socket, alt_keys, interval, home, 'ave-relay',
            config['logging']
        )

    @classmethod
    def load_config(cls, home):
        path = os.path.join(home, '.ave','config','relay.json')
        if not os.path.exists(path):
            return {} # default to empty configuration
        try:
            with open(path) as f:
                return json.load(f)
        except Exception, e:
            raise Exception('could not load config file: %s' % e)

    @classmethod
    def validate_config(cls, config):
        # there are no mandatory fields in the configuration, but if "port" is
        # set, then it overrides the default value
        if type(config) != dict:
            raise Exception('config is not a dictionary: %s' % config)
        if not 'logging' in config:
            config['logging'] = True
        if not 'port' in config:
            config['port'] = DEFAULT_PORT_NUMBER
        if not type(config['port']) == int:
            raise Exception('attribute must be on the form {"port":<integer>}')
        return config

    def idle(self):
        self.report_virtual(self.virtual.keys())

    def initialize(self):
        Control.initialize(self)
        self.lister = RelayLister(self.port, self.keys['admin'], self.logging)
        self.lister.start()
        self.join_later(self.lister)

    def report_virtual(self, profiles, timeout=5):
        r = Reporter(self.home, self.logging, profiles, timeout)
        r.start(daemonize=True)

    def get_boards(self):
        seen   = []
        result = []
        for board in self.virtual.values():
            # the physical board occurs once per virtual circuit group in the
            # mapping. only count each board once.
            if board.uid in seen:
                continue
            seen.append(board.uid)
            result.append(board)
        return result

    ### GENERIC ADMIN FUNCTIONS ################################################

    @Control.rpc
    def ping(self):
        return 'ave-relay pong'

    @Control.rpc
    @Control.preauth('admin')
    def stop(self):
        Control.stop(self)

    ### HANDOVER TO REPLACEMENT SERVER #########################################

    @Control.rpc
    @Control.preauth('admin')
    def serialize(self):
        state = []
        for b in self.get_boards():
            p = b.get_profile()
            try:
                p['state'] = b.get_state()
            except DeviceOffline:
                continue
            state.append(p)
        return { 'boards': state }

    @Control.rpc
    @Control.preauth('admin')
    def begin_handover(self):
        self.stop_listening()
        self.restarting = True
        serialized = self.serialize()
        for b in self.get_boards():
            b.close()
        return serialized

    @Control.rpc
    @Control.preauth('admin')
    def end_handover(self):
        self.shutdown()

    ### SERVER SPECIFIC ADMIN FUNCTIONS ########################################

    # split this out of set_boards() to override it in tests
    def make_board(self, profile, home):
        return RelayBoard(profile, home=home)

    @Control.rpc
    @Control.preauth('admin')
    def set_boards(self, profiles): # must only be used by the lister
        boards  = [BoardProfile(p) for p in profiles] # may raise exception
        for profile in boards:
            try:
                b = self.make_board(profile, self.home)
            except Exception, e:
                self.log('ERROR: could not open board: %s' % e)
                continue
            if profile in self.inherited:
                index = self.inherited.index(profile)
                b.set_state(self.inherited[index]['state'])
                self.inherited.remove(profile)
            elif profile['power_state'] == 'online':
                b.reset_board()

            groups = b.list_groups()
            for name in groups:
                v = RelayProfile({
                    'type'       :'relay',
                    'uid'        : '%s.%s' % (b.uid, name),
                    'circuits'   : groups[name],
                    'power_state': profile['power_state']
                })
                if v in self.virtual:
                    del self.virtual[v] # fully replace old index with new.
                self.virtual[v] = b # serial is same. other fields may not be.
        self.report_virtual(self.virtual.keys()) # add the profiles to a broker

    @Control.rpc
    @Control.preauth('admin')
    def list_equipment(self):
        return [b.get_profile() for b in self.get_boards()]

    @Control.rpc
    @Control.preauth('admin')
    def list_virtual(self):
        return self.virtual.keys()

    def profile_to_board_group(self, profile):
        profile = RelayProfile(profile) # may raise exception
        board   = self.virtual[profile]
        # the virtual relay uid was constructed by contatenating the uid of the
        # board (the serial number, actually) with the id of a circuit group in
        # the board's configuration. now get the group id back by cutting out
        # the serial number part of the profile's uid.
        if not profile['uid'].startswith(board.uid+'.'):
            raise Exception('invalid profile does not match board uid')
        return board, profile['uid'][len(board.uid+'.'):]

    @Control.rpc
    @Control.preauth('admin')
    def set_board_circuit(self, profile, circuit, high):
        if self.restarting:
            raise Restarting('relay server is restarting')
        board, group = self.profile_to_board_group(profile)
        board.set_group_circuit(group, circuit, high)
        now   = datetime.utcnow()
        return [
            now.year, now.month, now.day,
            now.hour, now.minute, now.second,
            now.microsecond
        ]

    @Control.rpc
    @Control.preauth('admin')
    def reset_board_group(self, profile):
        if self.restarting:
            raise Restarting('relay server is restarting')
        board, group = self.profile_to_board_group(profile)
        board.reset_group(group)
        now   = datetime.utcnow()
        return [
            now.year, now.month, now.day,
            now.hour, now.minute, now.second,
            now.microsecond
        ]

class RemoteRelayServer(RemoteControl):

    def __init__(self, address=None, authkey=None, timeout=5, home=None):
        if not home:
            home = ave.config.load_etc()['home']
        # load and validate the configuration file
        config = RelayServer.load_config(home)
        config = RelayServer.validate_config(config)
        if not address:
            address = ('', config['port']) # local host only
        if authkey:
            authkey = str(authkey)
        RemoteControl.__init__(self, address, authkey, timeout)
