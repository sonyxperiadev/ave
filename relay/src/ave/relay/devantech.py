# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import copy
import traceback

from serial import Serial

import ave.config
import ave.relay.config

from ave.relay.profile      import RelayProfile, BoardProfile
from ave.relay.exceptions   import *
from ave.network.control    import RemoteControl
from ave.network.exceptions import *

class DevantechBoard(object):
    home    = None
    profile = None
    config  = None
    device  = None

    def __init__(self, profile, home=None, config=None):
        if type(profile) != BoardProfile:
            raise Exception('profile type != BoardProfile: %s' % type(profile))
        if not home:
            home = ave.config.load_etc()['home']
        if not config:
            config = DevantechBoard.load_config(home)
        self.profile = DevantechBoard.validate_profile(profile)
        self.config  = ave.relay.config.validate_board_config(config,profile,8)
        if self.device_node != None:
            self.device = Serial(self.device_node)

    @property
    def uid(self):
        return self.profile['serial']

    @property
    def device_node(self):
        return self.profile['device_node']

    @classmethod
    def validate_profile(cls, profile):
        if 'type' not in profile:
            raise Exception('profile without "type" field: %s' % profile)
        if 'vendor' not in profile or profile['vendor'] != 'devantech':
            raise Exception('profile with wrong vendor: %s' % profile)
        if 'serial' not in profile:
            raise Exception('profile without "serial" field: %s' % profile)
        if 'device_node' not in profile:
            raise Exception('profile without "device_node" field: %s' % profile)
        return profile

    @classmethod
    def load_config(cls, home):
        path = os.path.join(home, '.ave','config','devantech.json')
        if not os.path.exists(path):
            raise Exception('no such config file: %s' % path)
        try:
            with open(path) as f:
                return json.load(f)
        except Exception, e:
            raise Exception('could not load config file: %s' % e)

    def close(self):
        pass # not needed for this device. done by garbage collect

    def list_groups(self):
        return self.config['groups']

    def get_profile(self):
        return copy.deepcopy(self.profile)

    def set_state(self, state):
        pass # board can be trusted to keep correct state information

    def get_state(self):
        if not self.device:
            raise DeviceOffline()
        return [int(self.get_port(i)) for i in range(1,9)]

    def set_port(self, port, high):
        if not self.device:
            raise DeviceOffline()
        if type(port) != int or port < 1 or port > 8:
            raise Exception('port not an integer [1..8]: %s' % port)
        if type(high) != bool:
            raise Exception('high is not a boolean: %s' % high)
        if high:
            self.device.write(chr(0x64 + port))
        else:
            self.device.write(chr(0x6e + port))

    def get_port(self, port):
        if not self.device:
            raise DeviceOffline()
        # getting the state value may be unreliable. use with caution
        self.device.write(chr(0x5b))
        high = ord(self.device.read(1))
        return (high & (0x01 << (port-1))) != 0

    def set_group_circuit(self, group, circuit, high):
        if group not in self.config['groups']:
            raise Exception('no such group of circuits: %s' % group)
        if circuit not in self.config['groups'][group]:
            raise Exception('no such circuit: %s' % circuit)
        port = self.config['groups'][group][circuit]
        self.set_port(port, high)

    def get_group_circuit(self, group, circuit):
        if group not in self.config['groups']:
            raise Exception('no such group of circuits: %s' % group)
        if circuit not in self.config['groups'][group]:
            raise Exception('no such circuit: %s' % circuit)
        port = self.config['groups'][group][circuit]
        return self.get_port(port)

    def reset_group(self, group):
        if group not in self.config['groups']:
            raise Exception('no such group: %s' % group)
        ports = []
        for circuit in self.config['groups'][group]:
            ports.append(self.config['groups'][group][circuit])
        # set the default value for each port
        for p in ports:
            self.set_port(p, self.config['defaults'][p-1] == 1)

    def reset_board(self):
        # set the default value for each port
        for p in [1,2,3,4,5,6,7,8]:
            self.set_port(p, self.config['defaults'][p-1] == 1)
