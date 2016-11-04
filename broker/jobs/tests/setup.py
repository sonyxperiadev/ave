# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import errno
import signal
import traceback

from ave.network.connection import *
from ave.network.control    import Control
from ave.network.exceptions import *
from ave.broker.session     import Session, RemoteSession
from ave.broker._broker     import Broker, RemoteBroker, LOCAL
from ave.broker.allocator   import LocalAllocator
from ave.broker.profile     import *
from ave.workspace          import Workspace
from ave.handset.lister     import HandsetLister

FLOCKER = {
            "ftp": {
                "password": "ftpuser",
                "store": "/srv/www/flocker",
                "port": 21,
                "timeout": 30,
                "user": "ftpuser"
            },
            "host": "cnbjlx20050",
            "enable" : True,
            "http": {
                "doc-root": "/srv/www",
                "port": 80
            }
        }

class MockSession(Session):

    @Control.rpc
    def raise_exception(self, msg):
        raise Exception(msg)

    @Control.rpc
    def raise_ave_exception(self, msg):
        raise AveException({'message':msg})

    @Control.rpc
    def raise_exit(self, msg='passed to client'):
        raise Exit(msg)

class session(object):

    def __init__(self, uid=None):
        pass

    def __call__(self, fn):
        def decorated_fn():
            sock,port = find_free_port()
            s = MockSession(port, 'password', ('',1), sock, logging=False)
            s.start()
            # spin until session is fully up and accepting connections
            for i in range(10):
                try:
                    BlockingConnection(('',port), 'password').connect(timeout=5)
                    break
                except ConnectionRefused:
                    time.sleep(0.1)
                    continue
            result = fn(s, RemoteSession(('', port), 'password'))
            try:
                s.terminate()
                s.join()
            except:
                pass
            return result
        return decorated_fn


def make_handsets(prefix):
    return [
        HandsetProfile({
            'type':'handset', 'vendor':'foo', 'product':'bar',
            'serial':'%s-1' % prefix,'pretty':'mary',
            'sysfs_path': '/', 'power_state': 'boot_completed',
            'platform':'android', 'product.model':'d1123',
            'workstation'  : 'slave-%s.corpusers.net' % prefix
        }),
        HandsetProfile({
            'type':'handset', 'vendor':'foo', 'product':'bar',
            'serial':'%s-2' % prefix,'pretty':'jane',
            'sysfs_path': '/', 'power_state': 'boot_completed',
            'platform':'android', 'product.model':'d1124',
            'workstation'  : 'slave-%s.corpusers.net' % prefix
        }),
        HandsetProfile({
            'type':'handset', 'vendor':'foo', 'product':'bar',
            'serial':'%s-3' % prefix,'pretty':'doe',
            'sysfs_path': '/', 'power_state': 'boot_completed',
            'platform':'android', 'product.model':'d1125',
            'workstation'  : 'slave-%s.corpusers.net' % prefix
        })
    ]

def make_relays(prefix):
    return [
        RelayProfile({
            'type'       : 'relay',
            'uid'        : '%s-a' % prefix,
            'pretty'     : 'gustav',
            'circuits'   : {'usb.pc.vcc':1},
            'power_state': 'online'
        }),
        RelayProfile({
            'type'       : 'relay',
            'uid'        : '%s-b' % prefix,
            'pretty'     : 'vasa',
            'circuits'   : {'handset.battery':2, 'usb.pc.vcc':3},
            'power_state': 'online'
        })
    ]

def make_stacks(prefix, style):
    if style == 'messy':
        return [
            [{'type':'relay', 'uid':'%s-a' % prefix},
             {'type':'handset','serial':'%s-1' % prefix}],
            [{'type':'relay', 'uid':'%s-a' % prefix},
             {'type':'handset','serial':'%s-2' % prefix}],
            [{'type':'relay', 'uid':'%s-b' % prefix},
             {'type':'handset','serial':'%s-2' % prefix}],
            [{'type':'relay', 'uid':'%s-b' % prefix},
             {'type':'handset','serial':'%s-3' % prefix}]
        ]
    elif style == 'clean':
        return [
            [{'type':'relay', 'uid':'%s-a' % prefix},
             {'type':'handset','serial':'%s-1' % prefix}],
            [{'type':'relay', 'uid':'%s-b' % prefix},
             {'type':'handset','serial':'%s-2' % prefix}]
        ]
    elif style == 'multi-messy':
        return [
            [{'type':'handset','serial':'%s-1' % prefix},
             {'type':'relay', 'uid':'%s-b' % prefix},
             {'type':'handset','serial':'%s-2' % prefix}]
        ]

class MockLocalAllocator(LocalAllocator):

    def __init__(self, handsets, relays, home, ws_cfg):
        LocalAllocator.__init__(self, home, ws_cfg)
        self._handsets = handsets
        self._relays = relays
        self.equipment.extend(handsets)
        self.equipment.extend(relays)

    def deallocate_relay(self, resource):
        pass # superclass tries to tell a relay server to close the relay on
             # deallocation, but that is just pointless in this mocked setup.

class MockBroker(Broker):
    handsets  = None
    relays    = None
    autoshare = False

    def __init__(
            self, address, socket, remote, handsets, relays, stacks, authkeys,
            ws_cfg, adoption, fdtx_path, hsl_paths=None, alloc=True,
            autoshare=False, home=None, slow_down=0
        ):
        Broker.__init__(
            self, address, socket, remote, authkeys, stacks, ws_cfg, adoption,
            fdtx_path, hsl_paths, home, logging=False
        )
        self.handsets  = handsets
        self.relays    = relays
        self.alloc     = alloc
        self.autoshare = autoshare
        self.slow_down = slow_down

    def make_pm_lister(self):
        # do not want this lister to interfere with fast paced broker tests.
        # the powermeter lister can hang for quite while when the toto box
        # behaves odd and doesn't accept connection attempts, etc. in real
        # installations, this should not be a problem because the life cycle
        # of a broker is much longer.
        pass

    @Control.rpc
    def get_config(self):
        return self.config

    @Control.rpc
    def set_handset_power_state(self, serial, power_state):
        serial_found = False
        for e in self.allocators['local'].equipment:
            if 'serial' in e:
                if e['serial'] == serial:
                    serial_found = True
                    e['power_state'] = power_state
                    self.update_sharing()
                    break
        return serial_found

    def make_allocators(self):
        self.allocators = {}
        if self.alloc: # if alloc: override local allocator
            self.allocators['local'] = MockLocalAllocator(
                self.handsets, self.relays, self.home, self.ws_cfg
            )
        else:
            self.allocators['local'] = LocalAllocator(self.home, self.ws_cfg)
        self.allocators['local'].set_stacks(self.config['stacks'])
        ws_profile = WorkspaceProfile(self.ws_cfg)
        self.allocators['local'].set_ws_profile(ws_profile)

    @Control.rpc
    def get_session_authkeys(self):
        result = []
        for k in self.sessions.keys():
            result.append(k)
        return result

    @Control.rpc
    def close_session(self, authkey):
        Broker.close_session(self, authkey)

    @Control.rpc
    def set_rejecting(self, value):
        self.rejecting = value

    @Control.rpc
    def ping(self):
        return 'pong'

    @Control.rpc
    def get_pid(self):
        return os.getpid()

    @Control.rpc
    def get_lister_pids(self):
        result = []
        if self.hsl and os.waitpid(self.hsl.pid, os.WNOHANG) == (0,0):
            result.append(self.hsl.pid)
        if self.brl and os.waitpid(self.brl.pid, os.WNOHANG) == (0,0):
            result.append(self.brl.pid)
        return result

    @Control.rpc
    def get_session_pids(self):
        result = []
        for session in self.sessions.values():
            if os.waitpid(session[LOCAL].pid, os.WNOHANG) == (0,0):
                result.append(session[LOCAL].pid)
        return result

    def update_sharing(self):
        if self.slow_down:
            time.sleep(self.slow_down)
        Broker.update_sharing(self)

    @Control.rpc
    def interrupt(self):
        os.kill(self.pid, signal.SIGTERM)

    @Control.rpc
    def list_workspaces(self, profile=None, allocators=['local']):
        result = []
        for a in allocators:
            if type(a) == list:
                a = tuple(a) # allocators indexed by address tuples
            result.extend(self.allocators[a].list_workspaces(profile))
        return result

class RemoteSlaveBroker(RemoteBroker):
    pass

def make_workspace():
    HOME = Workspace() # created under default path for workspaces
    config_path = os.path.join(HOME.path, '.ave', 'config')
    os.makedirs(config_path)
    with open(os.path.join(config_path,'authkeys.json'), 'w') as f:
        f.write(json.dumps(
            {'admin':'admin_key', 'share':'share_key'}
        ))
    with open(os.path.join(config_path,'workspace.json'), 'w') as f:
        f.write(json.dumps(
            {
                'root':os.path.join(HOME.path,'workspaces'), 'env':[],
                'tools':{}, 'flocker': FLOCKER
            }
        ))
    with open(os.path.join(config_path,'broker.json'), 'w') as f:
        f.write(json.dumps({'logging':False}))

    return HOME

# one master and one slave
class brokers(object):

    def __init__(self, forwarders, master, slaves, share,pure,stacking='messy'):
        self.forwarders = forwarders
        self.master     = master
        self.slaves     = slaves
        self.share      = share
        self.pure       = pure # master has no equipment of its own
        self.stacking   = stacking

    def __call__(self, fn):
        def decorated_fn():
            HOME = make_workspace() # used for the test
            brokers, clients = self.make_brokers(HOME)
            for b in brokers:
                b.start()
            for b in clients:
                if type(b) == RemoteSlaveBroker and self.share:
                    b.start_sharing()
            result = fn(HOME, *clients)
            for b in brokers:
                b.terminate() # triggers signal handler and Broker.shutdown()
                b.join()
            HOME.delete()
            return result
        return decorated_fn

    def make_brokers(self, HOME):
        brokers = []
        clients = []
        b, c = self.make_master(HOME)
        brokers.append(b)
        clients.append(c)
        for prefix in self.forwarders:
            b, c = self.make_forwarder(brokers[-1], prefix, HOME)
            brokers.append(b)
            clients.append(c)
        for prefix in self.slaves:
            b, c = self.make_slave(brokers[0], prefix, HOME)
            brokers.append(b)
            clients.append(c)
        return brokers, clients

    def make_forwarder(self, master, prefix, HOME):
        sock, port = find_free_port()
        handsets   = make_handsets(prefix)
        config     = { 'host':'', 'port':master.address[1], 'policy':'forward' }
        ws_cfg     = {
            'root':os.path.join(HOME.path, prefix),
            'env':[], 'tools':{'ls':'/bin/ls'}, 'pretty':prefix
        }
        broker = MockBroker(
            ('',port), sock, config, handsets, [], None, None, ws_cfg, None,
            None, [], True, home=HOME.path
        )
        remote = RemoteBroker(address=('',port), home=HOME.path)
        return broker, remote

    def make_master(self, HOME):
        prefix = self.master
        sock, port = find_free_port()
        if self.pure:
            handsets = []
            relays   = []
            stacks   = []
        else:
            handsets = make_handsets(prefix)
            relays   = make_relays(prefix)
            stacks   = make_stacks(prefix, self.stacking)
        authkeys = {'admin':None, 'share':'share_key'}
        ws_cfg = {
            'root':os.path.join(HOME.path, prefix),
            'env':[], 'tools':{'sleep':'/bin/sleep'}, 'pretty':prefix,
            'flocker': FLOCKER,
            'wifi-capable': True,
            'wlan': {'ssid':'ssid', 'auth':'password'}
        }
        broker = MockBroker(
            ('',port), sock, None, handsets, relays, stacks, authkeys, ws_cfg,
            None, None, [], True, home=HOME.path
        )
        remote = RemoteBroker(address=('',port), authkey=None, home=HOME.path)
        return broker, remote

    def make_slave(self, master, prefix, HOME):
        sock, port = find_free_port()
        handsets   = make_handsets(prefix)
        relays     = make_relays(prefix)
        stacks     = make_stacks(prefix, self.stacking)
        config     = {
            'host':'', 'port':master.address[1],
            'policy':'share', 'authkey':u'share_key'
        }
        ws_cfg     = {
            'root':os.path.join(HOME.path, prefix),
            'env':[],'tools':{},'pretty':prefix,
            'flocker': FLOCKER
        }
        broker = MockBroker(
            ('',port), sock, config, handsets, relays, stacks, None, ws_cfg,
            None, None, [], True, home=HOME.path
        )
        remote = RemoteSlaveBroker(
            address=('',port), authkey='admin_key', home=HOME.path
        )
        return broker, remote

class factory(object):
    HOME      = None # Workspace
    processes = None # brokers, actually

    def __call__(self, fn):
        def decorated_fn(*args, **kwargs):
            self.HOME = make_workspace()
            self.processes = []
            self.write_default_config()
            result = fn(self, *args, **kwargs)
            for p in self.processes:
                p.terminate()
                p.join()
            self.HOME.delete()
            return result
        return decorated_fn

    def write_config(self, name, content):
        path = os.path.join(self.HOME.path, '.ave', 'config', name)
        with open(path, 'w') as f:
            f.write(content)

    def write_default_config(self):
        pm_config = {
            'logging' : False,
            'log_path': os.path.join(self.HOME.path, 'pm.log'),
            'map_path': os.path.join(self.HOME.path, 'pm.json')
        }
        self.write_config('powermeter.json', json.dumps(pm_config))

    def make_master(self, prefix, hsl_paths=None):
        sock, port = find_free_port()

        if hsl_paths != None: # use real equipment
            handsets  = []
            relays    = []
            stacks    = []
            alloc     = False
        else: # use mocked equipment
            hsl_paths = []
            handsets  = make_handsets(prefix)
            relays    = make_relays(prefix)
            stacks    = make_stacks(prefix, 'messy')
            alloc     = True

        broker = MockBroker(
            address   = ('',port),
            socket    = sock,
            remote    = None,
            handsets  = handsets,
            relays    = relays,
            stacks    = stacks,
            authkeys  = {'admin':None, 'share':'share_key'},
            ws_cfg    = {
                'root':os.path.join(self.HOME.path, prefix),
                'env':[], 'tools':{'sleep':'/bin/sleep'}, 'pretty':prefix,
                'flocker': FLOCKER
            },
            adoption  = None,
            fdtx_path = None,
            hsl_paths = hsl_paths,
            alloc     = alloc,
            autoshare = False,
            home      = self.HOME.path
        )
        broker.start()
        remote = RemoteBroker(address=('',port), home=self.HOME.path)
        self.processes.append(broker)
        return remote

    def make_takeover(self, prefix,adoption,config,fdtx_path, hsl_paths=None):
        if hsl_paths != None: # use real equipment
            handsets  = []
            relays    = []
            stacks    = []
            alloc     = False
        else: # use mocked equipment
            hsl_paths = []
            handsets  = make_handsets(prefix)
            relays    = make_relays(prefix)
            stacks    = make_stacks(prefix, 'messy')
            alloc     = True

        broker = MockBroker(
            address   = (config['host'],config['port']),
            socket    = None,
            remote    = config['remote'],
            handsets  = handsets,
            relays    = relays,
            stacks    = stacks,
            authkeys  = {'admin':None, 'share':'share_key'},
            ws_cfg    = {
                'root'  : os.path.join(self.HOME.path, prefix),
                'tools' : {},
                'pretty': prefix,
                'flocker': FLOCKER
            },
            adoption  = adoption,
            fdtx_path = fdtx_path,
            hsl_paths = hsl_paths,
            alloc     = alloc,
            autoshare = True,
            home      = self.HOME.path
        )
        broker.start()
        self.processes.append(broker)
        remote = RemoteBroker(
            address=(config['host'],config['port']), home=self.HOME.path
        )
        return remote

    def make_share(self, master, prefix, autoshare=False, hsl_paths=None,
                   slow_down=0, stacking='messy'):
        sock, port = find_free_port()

        if hsl_paths != None: # use real equipment
            handsets  = []
            relays    = []
            stacks    = []
            alloc     = False
        else: # use mocked equipment
            hsl_paths = []
            handsets  = make_handsets(prefix)
            relays    = make_relays(prefix)
            stacks    = make_stacks(prefix, stacking)
            alloc     = True

        broker = MockBroker(
            address   = ('',port),
            socket    = sock,
            remote    = {
                'host':'', 'port':master.address[1],
                'policy':'share', 'authkey':u'share_key'
            },
            handsets  = handsets,
            relays    = relays,
            stacks    = stacks,
            authkeys  = {'admin':None},
            ws_cfg    = {
                'root':os.path.join(self.HOME.path, prefix),
                'env':[], 'tools':{}, 'pretty':prefix,
                'flocker': FLOCKER

            },
            adoption  = None,
            fdtx_path = None,
            hsl_paths = hsl_paths,
            alloc     = alloc,
            autoshare = autoshare,
            home      = self.HOME.path,
            slow_down = slow_down
        )
        remote = RemoteSlaveBroker(
            address=('',port), authkey=None, home=self.HOME.path
        )
        broker.start()
        self.processes.append(broker)
        return remote
