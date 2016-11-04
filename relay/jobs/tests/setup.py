# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import struct

from ave.relay.board        import RelayBoard
from ave.relay.lister       import RelayLister
from ave.relay.server       import RelayServer, RemoteRelayServer
from ave.workspace          import Workspace
from ave.network.control    import Control
from ave.network.connection import find_free_port, BlockingConnection
from ave.broker._broker     import Broker, RemoteBroker

AUTHKEYS = { 'admin':'admin', 'share':'share' }

BOARD_1 = {
    'vendor'     : 'mock',
    'product'    : 'mock',
    'serial'     : 'abc1',
    'sysfs_path' : None,
    'device_node': None,
    'power_state': 'online'
}

BOARD_2 = {
    'vendor'     : 'mock',
    'product'    : 'mock',
    'serial'     : 'abc2',
    'sysfs_path' : None,
    'device_node': None,
    'power_state': 'offline'
}

BOARD_3 = {
    'vendor'     : 'mock',
    'product'    : 'mock',
    'serial'     : 'abc3',
    'sysfs_path' : None,
    'device_node': None,
    'power_state': 'online'
}

RELAY_1 = {
    'type': 'relay',
    'uid' : 'abc1.a',
    'circuits': {'usb.pc.vcc':1},
    'power_state': 'online'
}

RELAY_2 = {
    'type': 'relay',
    'uid' : 'abc2.a',
    'circuits': {'usb.pc.vcc':1},
    'power_state': 'offline'
}

RELAY_3 = {
    'type': 'relay',
    'uid' : 'abc3.b',
    'circuits': {'usb.pc.vcc':1, 'handset.battery':2},
    'power_state': 'online'
}

DEVANTECH_CONFIG = {
    "*":{
        "groups": {
            "a": {"usb.pc.vcc":1, "handset.battery":2},
            "b": {"usb.pc.vcc":3, "handset.battery":4}
        },
        "defaults":[1,1,1,1,1,1,1,1]
    }
}

class MockBoard(object):
    profile = None
    state   = None
    config  = None

    def __init__(self, profile):
        self.profile = profile
        self.state   = [1,1,1]
        self.config  = {
            'groups': {
                'a': {'usb.pc.vcc':1, 'handset.battery':2},
                'b': {'usb.pc.vcc':3} } }

    @property
    def uid(self):
        return self.profile['serial']

    def close(self):
        pass

    def get_profile(self):
        return self.profile

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def reset_board(self):
        pass

    def list_groups(self):
        return self.config['groups']

    def set_group_circuit(self, group, circuit, value):
        if group not in self.config['groups']:
            raise Exception('no such group of circuits: %s' % group)
        if circuit not in self.config['groups'][group]:
            raise Exception('no such circuit: %s' % circuit)
        port = self.config['groups'][group][circuit]
        self.state[port-1] = int(value)

    def reset_group(self, group):
        if group not in self.config['groups']:
            raise Exception('no such group: %s' % group)
        ports = []
        for circuit in self.config['groups'][group]:
            ports.append(self.config['groups'][group][circuit])
        for p in ports:
            self.state[p-1] = 1

class MockServer(RelayServer):

    def __init__(self, home=None, config=None, inherited=None, socket=None,
        interval=0.5):
        RelayServer.__init__(self, home, config, inherited, socket, interval)

    def initialize(self):
        self.config['logging'] = False
        Control.initialize(self)

    def make_board(self, profile, home):
        return MockBoard(profile)

    def report_virtual(self, profiles, timeout=0.5):
        RelayServer.report_virtual(self, profiles, timeout)

class factory(object):
    HOME      = None
    processes = None

    def __init__(self):
        pass

    def __call__(self, fn):
        def decorated(*args, **kwargs):
            pretty = '%s %s' % (fn.func_code.co_filename, fn.func_name)
            print(pretty)
            self.HOME      = Workspace()
            self.processes = []
            os.makedirs(os.path.join(self.HOME.path, '.ave','config'))
            result = fn(pretty, self, *args, **kwargs)
            for p in self.processes:
                try:
                    p.terminate()
                    p.join()
                except Exception, e:
                    print e
            self.HOME.delete()
            return result
        return decorated

    def write_config(self, filename, config):
        path = os.path.join(self.HOME.path, '.ave','config',filename)
        with open(path, 'w') as f:
            json.dump(config, f)

    def make_lister(self, timeout, logging):
        sock,port = find_free_port(listen=False)
        c = BlockingConnection(('',port), sock)
        l = DevantechRelayLister(port, None, timeout, logging)
        l.start()
        self.processes.append(l)
        return c

    def make_server(self, inherited=None, make_socket=True):
        if make_socket:
            sock,port = find_free_port()
            config = {'port':port, 'logging':False}
            self.write_config('relay.json', config)
            server = MockServer(self.HOME.path, config, inherited, sock)
            remote = RemoteRelayServer(('',port), 'admin', home=self.HOME.path)
        else: # rely on configuration file in HOME
            server = MockServer(self.HOME.path, None, inherited)
            remote = RemoteRelayServer(None, 'admin', home=self.HOME.path)
        server.start()
        self.processes.append(server)
        return remote

    def _make_broker(self, sock, port):
        return Broker(
            address   = ('',port),
            socket    = sock,
            remote    = None,
            home      = self.HOME.path,
            ws_cfg    = {
                'root':self.HOME.path,
                'env':[], 'tools':{'sleep':'/bin/sleep'}, 'pretty':'broker',
                'flocker': { 'host':'any', 'port':40000003 }
            }
        )

    def make_broker(self):
        sock,port = find_free_port()
        self.write_config('broker.json', {'port':port, 'logging':False})
        broker = self._make_broker(sock, port)
        broker.start()
        remote = RemoteBroker(('',port), 5, 'admin', self.HOME.path)
        self.processes.append(broker)
        return remote

    def make_control(self):
        from ave.network.control import Control, RemoteControl

        class MockControl(Control):
            @Control.rpc
            def stop(self):
                Control.stop(self)

        sock,port = find_free_port()
        server = MockControl(port, 'admin', sock, {}, 1, self.HOME.path)
        remote = RemoteControl(('',port), 'admin', 2)
        server.start()
        self.processes.append(server)
        return remote

