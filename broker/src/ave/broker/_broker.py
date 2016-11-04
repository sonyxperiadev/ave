# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import json
import stat
import errno
import random
import socket
import signal
import traceback

from types import NoneType

import ave.config
import ave.broker.profile

from ave.broker.session       import Session, RemoteSession, AdoptedSession
from ave.broker.resource      import *
from ave.broker.profile       import *
from ave.handset.lister       import HandsetLister
from ave.network.exceptions   import *
from ave.network.connection   import find_free_port
from ave.network.control      import Control, RemoteControl
from ave.network.fdtx         import FdTx, Errno
from ave.workspace            import Workspace


from constants         import *
from exceptions        import *
from allocator         import LocalAllocator, ShareAllocator
from notifier          import Notifier, RemoteNotifier

AUTHKEY_LENGTH = 16

def rand_authkey():
    result = []
    for i in range(AUTHKEY_LENGTH):
        result.append(random.randint(0,9))
    return ''.join(['%d' % i for i in result])

def get_configuration_path(home):
    return os.path.join(home, '.ave', 'config', 'broker.json')

def load_configuration(path):
    if not os.path.exists(path):
        raise Exception('no such configuration file: %s' % path)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception, e:
        raise Exception(
            'could not load broker configuration file: %s' % str(e)
        )

def validate_configuration(config):
    '''
    Check if the dictionary 'config' is a valid Broker configuration.
    '''
    # helper function to get uniform problem reports
    def complain_format(attribute, format, current):
        raise Exception(
            'broker attribute "%s" must be on the form %s. '
            'current value=%s (type=%s)'
            % (attribute, format, current, str(type(current)))
        )
    # there are no mandatory fields in the configuration, but if "host", "port"
    # or "stacks" are set, then they override the default values
    if not 'logging' in config:
        config['logging'] = True
    if not 'host' in config:
        config['host'] = socket.gethostbyaddr(socket.gethostname())[0]
    if not 'port' in config:
        config['port'] = 4000
    if not 'stacks' in config:
        config['stacks'] = []
    if not 'remote' in config:
        config['remote'] = None # TODO: default to broker.sonyericsson.net

    if not type(config['host']) in [str, unicode]:
        complain_format('host', '{"host":<string>}', config['host'])
    if not type(config['port']) == int:
        complain_format('port', '{"port":<integer>}', config['port'])

    stack_complaint = (
        '{"stacks":[<stack>, ...]}, where <stack> is a list that contains '
        'one or more profiles that uniquely identify equipment. e.g. '
        '[{"type":"handset", "serial":"1"}, {"type":"relay", "uid":"2"}]'
    )
    if not type(config['stacks']) == list:
        complain_format('stacks', stack_complaint, config['stacks'])
    for stack in config['stacks']:
        if type(stack) != list:
            complain_format('stacks', stack_complaint, config['stacks'])
        for profile in stack:
            if type(profile) != dict:
                complain_format('stacks', stack_complaint, config['stacks'])
            if 'type' not in profile:
                raise Exception(
                    'the stacked profile "%s" does not contain the "type" '
                    'attribute'
                    % profile
                )
            if ('serial' not in profile
            and 'imei' not in profile
            and 'uid' not in profile):
                raise Exception(
                    'the stacked profile "%s" does not contain at least one '
                    'attribute that uniquely identifies any equipment. '
                    '(use "serial" or "imei" for handsets, "uid" for other '
                    'equipment)'
                    % profile
                )

    if config['remote']:
        if (type(config['remote']) != dict
        or  'host'   not in config['remote']
        or  'port'   not in config['remote']
        or  'policy' not in config['remote']
        or  type(config['remote']['host'])   not in [str, unicode]
        or  type(config['remote']['port'])   != int
        or  type(config['remote']['policy']) not in [str, unicode]):
            complain_format(
                'remote', '{"remote":{"host":<string>, "port":<integer>, '
                '"policy":<string>}', config['remote']
            )
        if config['remote']['policy'] not in ['share', 'forward']:
            raise Exception(
                'broker conguration: remote policy must be "share" or "forward"'
            )
        if config['remote']['policy'] == 'share':
            if 'authkey' not in config['remote']:
                raise Exception(
                    'broker configuration: remote sharing authkey not set. '
                    'example:\n'
                    '"remote":{\n'
                    '    "host":"hostname", "port":4000,\n'
                    '    "policy":"share", "authkey":"admin_key"\n'
                    '}'
                )
            if type(config['remote']['authkey']) == unicode:
                config['remote']['authkey'] = str(config['remote']['authkey'])
            if type(config['remote']['authkey']) != str:
                raise Exception(
                    'broker configuration: remote sharing authkey must be a '
                    'string'
                )

def validate_serialized(serialized):
    '''
    expects input like this: (a dict of sessions indexed by their authkeys)
    {
        <authkey>: {
            'pid': <integer>,
            'address': [<string>,<integer>],
            'allocations': [
                { 'profile': <profile>, 'collateral': [<profile>, ...] },
                ...
            ]
        }
    }
    '''
    if type(serialized) != dict:
        raise Exception('serialized data must be a dictionary')
    validated = {}

    for authkey in serialized:
        if type(authkey) not in [str, unicode]:
            raise Exception('serialized data must be a mapping from strings')
        authkey = str(authkey) # type demoting needed -> string

        details = serialized[authkey]
        if 'pid' not in details:
            raise Exception('details do not include pid: %s' % details)
        if type(details['pid']) != int:
            raise Exception('"pid" detail is not an integer: %s' % details)
        pid = details['pid']

        if 'address' not in details:
            raise Exception('details do not include address: %s' % details)
        if type(details['address']) != list:
            raise Exception('"address" detail is not a list: %s' % details)
        address = tuple(details['address']) # type conversion needed -> tuple
        if (len(address) != 2
        or  type(address[0]) not in [str, unicode]
        or  type(address[1]) != int):
            raise Exception(
                '"address" detail is not a (string,int) tuple: %s' % details
            )

        if 'allocations' not in details:
            raise Exception('details do not include allocations: %s' % details)
        if type(details['allocations']) != list:
            raise Exception('"allocations" detail is not a list: %s' % details)
        allocations = details['allocations']
        for i in range(len(allocations)):
            alloc = allocations[i]
            if 'profile' not in alloc:
                raise Exception('allocation detail has no profile: %s' % alloc)
            if 'collateral' not in alloc:
                raise Exception('allocation detail has no collateral: %s'%alloc)
            checked = []
            for j in range(len(alloc['collateral'])):
                checked.append(profile_factory(alloc['collateral'][j]))
            allocations[i] = {
                'profile': profile_factory(alloc['profile']),
                'collateral': checked
            }

        validated[authkey] = {
            'pid': pid,
            'address': address,
            'allocations': allocations
        }

    return validated

class Broker(Control):

    def __init__(
            self, address=None, socket=None, remote=None, authkeys=None,
            stacks=None, ws_cfg=None, adoption=None, fdtx_path=None,
            hsl_paths=None, home=None, logging=None
        ):
        if not home:
            home = ave.config.load_etc()['home']

        # load and validate the configuration file
        config = load_configuration(get_configuration_path(home))
        # the 'address' and 'socket' parameters are only there to support tests
        # and now we just brutally inject 'address' in the configuration if it
        # was passed. there is an otherwise silent assumption that the socket
        # is listening on the port that is passed in 'address'. stuff will stop
        # working otherwise for sure.
        if address:
            config['host'] = address[0]
            config['port'] = address[1]
        # same thing with the 'remote' parameter. drop in replacement of the
        # values read from a real config file.
        if remote != None:
            config['remote'] = remote
        if authkeys == None: # more test case configuration support
            authkeys = ave.config.load_authkeys(home)
        if stacks != None: # more test case configuration support
            config['stacks'] = stacks
        if not logging is None:  # priority in order: parameter, config, default
            config['logging'] = logging
        validate_configuration(config)
        # no self. assignment before this point:
        Control.__init__(
            self, config['port'], None, socket, authkeys, interval=1, home=home,
            proc_name='ave-broker', logging=config['logging']
        )
        self.config     = config
        self.sessions   = {} # authkey -> (Session, RemoteSession)
        # support mockable workspace configurations:
        if not ws_cfg:
            ws_cfg_path = Workspace.default_cfg_path(home)
            ws_cfg      = Workspace.load_config(ws_cfg_path, home)
        self.ws_cfg     = ws_cfg
        self.shares     = {} # Connection -> address
        self.notifier   = None
        self.hsl        = None
        self.brl        = None # Beryllium Rig Lister
        self.wlan_lister= None
        self.pm_lister  = None
        self.allocating = True
        if adoption:
            if not fdtx_path:
                raise Exception('adoption data must come with an fdtx path')
            adoption = validate_serialized(adoption)
        self.adoption   = adoption
        self.fdtx_path  = fdtx_path
        self.hsl_paths  = hsl_paths
        self.make_tempdir()

    def make_tempdir(self):
        try:
            os.makedirs('/tmp/ave')
            os.chmod('/tmp/ave', 0777)
        except OSError, e:
            if e.errno == errno.EEXIST:
                return
            raise Exception('could not make /tmp/ave: %s' % str(e))
        except Exception, e:
            raise Exception('could not make /tmp/ave: %s' % str(e))

    @Control.rpc
    def get_profile(self):
        return BrokerProfile(self.config)

    @property
    def address(self):
        return (self.config['host'], self.config['port'])

    @property
    def remote_address(self):
        try:
            return (self.config['remote']['host'],self.config['remote']['port'])
        except:
            return None

    @property
    def forward(self):
        try:
            return self.config['remote']['policy'] == 'forward'
        except:
            return False

    def make_allocators(self):
        self.allocators = {}
        self.allocators['local'] = LocalAllocator(self.home, self.ws_cfg)
        self.allocators['local'].set_stacks(self.config['stacks'])
        ws_profile = WorkspaceProfile(self.ws_cfg)
        self.allocators['local'].set_ws_profile(ws_profile)

    # a handset lister that tracks handsets in a separate process
    def make_handset_lister(self):
        try:
            auth = self.keys['share']
        except Exception:
            auth = None
        self.hsl = HandsetLister(
            self.address[1], auth, self.hsl_paths, self.config['logging']
        )
        self.hsl.start()
        self.join_later(self.hsl)

    def make_pm_lister(self):
        try:
            auth = self.keys['share']
        except Exception:
            self.log(
                'WARNING: there is no "share" authentication key. check your '
                '.ave/config/authkeys.json file.'
            )
            auth = None
        try:
            from ave.powermeter.lister import PowermeterLister
            self.pm_lister = PowermeterLister(self.address[1], auth, self.home)
            self.pm_lister.start()
            self.join_later(self.pm_lister)
        except:
            pass

    # a handset lister that tracks handsets in a separate process
    def make_beryllium_lister(self):
        try:
            from ave.beryllium.lister import BerylliumLister
            try:
                auth = self.keys['share']
            except Exception:
                auth = None
            self.brl = BerylliumLister(self.address[1], auth)
            self.brl.start()
            self.join_later(self.brl)
        except:
            pass

    # a wlan lister that tracks wlans in a separate process
    def make_wlan_lister(self):
        try:
            from ave.wlan.lister import WlanLister
            try:
                auth = self.keys['share']
            except Exception:
                auth = None
            self.wlan_lister = WlanLister(self.address[1], auth)
            self.wlan_lister.start()
            self.join_later(self.wlan_lister)
        except:
            pass

    def adopt_sessions(self):
        if not self.fdtx_path:
            return
        fdtx = FdTx(None)
        fdtx.connect(self.fdtx_path, 5)
        # receive open file descriptors together with their associated authkeys
        while True:
            try: # future safety: double the needed message length, two fd's
                authkey, fd = fdtx.get(AUTHKEY_LENGTH*2, 2)
            except ConnectionClosed:
                break # other end sent all it had
            if authkey not in self.adoption:
                continue # session died during handover
            self.adoption[authkey]['fd'] = fd[0] # just one fd per message
        for authkey in self.adoption:
            if 'fd' not in self.adoption[authkey]:
                continue # session died during handover
            # reconnect the session
            fd      = self.adoption[authkey]['fd']
            pid     = self.adoption[authkey]['pid']
            address = tuple(self.adoption[authkey]['address'])
            # represent the adopted session by an AdoptedSession instance that
            # only implements .pid and .terminate()
            local   = AdoptedSession(pid)
            sock    = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            remote  = RemoteSession(address, authkey, timeout=1, sock=sock)
            self.add_connection(remote._connection, authkey)
            self.sessions[authkey] = (local, remote)

            # recreate the allocation records
            alloc   = self.adoption[authkey]['allocations']
            for a in alloc:
                resource   = a['profile']
                collateral = a['collateral']
                self.allocators['local'].allocate(resource, remote, collateral)

    def initialize(self):
        Control.initialize(self)
        self.make_handset_lister()
        self.make_beryllium_lister()
        self.make_wlan_lister()
        self.make_pm_lister()
        self.make_allocators()
        self.adopt_sessions()
        if self.is_sharing():
            self.start_sharing()

    def stop_listers(self):
        if self.hsl:
            try:
                self.hsl.terminate()
                self.hsl = None
            except Exception, e:
                self.log('WARNING: could not stop handset lister: %s' % e)
        if self.brl:
            try:
                self.brl.terminate()
                self.brl = None
            except Exception, e:
                self.log('WARNING: could not stop beryllium lister: %s' % e)
        if self.wlan_lister:
            try:
                self.wlan_lister.terminate()
                self.wlan_lister = None
            except Exception, e:
                self.log('WARNING: could not stop wlan lister: %s' % e)
        if self.pm_lister:
            try:
                self.pm_lister.terminate()
                self.pm_lister = None
            except Exception, e:
                self.log('WARNING: could not stop power meter lister: %s' % e)

    def shutdown(self, details=None):
        # terminate all processes started by the broker
        if self.hsl:
            self.hsl.terminate()
        if self.brl:
            self.brl.terminate()
        if self.wlan_lister:
            self.wlan_lister.terminate()
        if self.pm_lister:
            self.pm_lister.terminate()
        self.stop_sharing()
        for session in self.sessions.values():
            try:
                # send SIGTERM, not SIGKILL, so that Session.shutdown() runs
                session[LOCAL].terminate()
            except OSError, e:
                if e.errno not in [errno.ECHILD, errno.ESRCH]:
                    raise Exception('unhandled errno: %d' % e.errno)
        Control.shutdown(self, details) # does not return. always do last

    def get_current_session(self):
        authkey = self.get_connection_authkey(self.current_connection)
        if authkey not in self.sessions:
            raise Exception('session closed')
        return self.sessions[authkey][REMOTE]

    def new_session(self, authkey):
        if authkey in self.sessions:
            raise Exception('INTERNAL ERROR: session already added for authkey')
        sock, port = find_free_port()
        session    = Session(
            port, authkey, self.address, sock, self.ws_cfg, self.home,
            self.config['logging']
        )
        session.start() # new process!
        self.join_later(session)
        remote     = RemoteSession((self.address[0], port), authkey)
        # connect to the new session and add the connection to event tracking
        try:
            self.add_connection(remote.connect(5), authkey)
        except Exception, e:
            print('ERROR: could not connect to new session: %s' % str(e))
            session.kill(signal.SIGKILL) # not much else to do
            return
        self.sessions[authkey] = (session, remote)

    # override callback defined by Control class
    def new_connection(self, connection, authkey):
        # set a randomly generated authkey on the new connection if the client
        # didn't already authenticate with some other authkey
        if not authkey:
            authkey = rand_authkey()
            self.set_connection_authkey(connection, authkey)
            self.new_session(authkey)

    # override callback defined by Control class
    def lost_connection(self, connection, authkey):
        if connection in self.shares:
            del self.allocators[self.shares[connection]]
            del self.shares[connection]
            return

        # if the connection's .authkey is found in the session list, then kill
        # off the entire session and reclaim all associated resources.
        if not authkey:
            raise Exception('lost a connection without authkey')
        if authkey in self.sessions:
            self.close_session(authkey)

    def joined_process(self, pid, exit):
        if self.notifier and pid == self.notifier[LOCAL].pid:
            # notifier died, possibly because the remote master dropped all
            # shares. what to do? just start a new one and hope the master
            # accepts it.
            self.notifier = None
            self.start_sharing()

    ### SHARE HANDLING BEGIN ###################################################

    def has_shares(self):
        return len(self.allocators) > 1

    def share_handler(fn):
        def decorated_fn(self, address, *vargs, **kwargs):
            if address != 'local':
                address = tuple(address) # lists are not hashable
                if address not in self.allocators:
                    self.allocators[address] = ShareAllocator(address)
                    if self.current_connection not in self.shares:
                        self.shares[self.current_connection] = address
            return fn(self, address, *vargs, **kwargs)
        return decorated_fn

    def is_sharing(self):
        return (self.config['remote']
           and  self.config['remote']['policy'] == 'share')

    @Control.rpc
    @Control.preauth('admin')
    def start_sharing(self):
        if self.notifier:
            self.stop_sharing()
        self.log('start sharing: %s' % self.config['remote'])
        authkey    = self.config['remote']['authkey']
        sock, port = find_free_port()
        notifier   = Notifier(
            port, sock, self.remote_address, authkey, self.address,
            self.config['logging']
        )
        notifier.start()
        self.join_later(notifier)
        remote = RemoteNotifier(('',port))
        self.notifier = (notifier, remote)
        try:
            remote.connect(1)
        except Exception, e:
            self.log('ERROR: could not connect to new notifier: %s' % e)
            self.log(traceback.format_exc())
            self.restart_sharing()
            return None

        ws_profile = WorkspaceProfile(self.ws_cfg)

        try:
            self.notifier[REMOTE].set_ws_profile(
                ws_profile, False, __async__=True
            )
            self.notifier[REMOTE].set_stacks(
                self.list_stacks(), True, __async__=True
            )
        except Exception, e:
            self.log('ERROR: could not interact with notifier: %s' % e)
            self.log(''.join(traceback.format_stack()))
            if type(e) == AveException and e.has_trace():
                self.log('server side trace:')
                self.log(e.format_trace())
            self.restart_sharing()
            return None
        self.update_sharing()
        return ('', port) # mostly useful to have in test cases

    @Control.rpc
    @Control.preauth('admin')
    def list_shares(self):
        return [list(s) for s in self.shares.values()]

    @Control.rpc
    @Control.preauth('admin')
    def drop_share(self, address):
        address = tuple(address) # lists are not hashable
        if address in self.allocators:
            del self.allocators[address]
        for connection in self.shares:
            if self.shares[connection] == address:
                self.remove_connection(connection) # to avoid POLLNVAL events
                connection.close()
                del self.shares[connection]
                break

    @Control.rpc
    @Control.preauth('admin')
    def drop_all_shares(self):
        # extract the full list of connections (shares.keys()) before looping
        # through the shares. otherwise an exception will be raised when the
        # shares entry is deleted
        for connection in self.shares.keys():
            self.remove_connection(connection)
            connection.close()
            address = self.shares[connection]
            self.log('drop share: %s' % str(address))
            del self.allocators[address]
            del self.shares[connection]

    @Control.rpc
    @Control.preauth('admin')
    def restart_sharing(self):
        if not self.notifier:
            return
        self.log('restart sharing')
        # kill the process without cleaning away the notfier objects. the dead
        # notifier process will be picked up in joined_process() and a new one
        # started.
        self.notifier[LOCAL].kill(signal.SIGKILL) # make sure it's really dead

    @Control.rpc
    @Control.preauth('admin')
    def stop_sharing(self):
        if not self.notifier:
            return
        self.log('stop sharing')
        # avoid terminating twice by setting self.notifier=None before killing
        # the process. can only happen during teardown after a test case but bad
        # anyway
        proc = self.notifier
        self.notifier = None
        proc[LOCAL].kill(signal.SIGKILL) # make sure it's really dead ...
        del proc

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    def set_ws_profile(self, address, profile):
        self.log(
            'got workspace profile from %s:\n%s'
            % (str(address), json.dumps(profile, indent=4))
        )
        self.allocators[address].set_ws_profile(profile)

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    def add_workspaces(self, address, profiles):
        raise Exception('add_workspaces() is obsolete. upgrade to AVE 28')

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    def remove_workspaces(self, address, profiles):
        raise Exception('remove_workspaces() is obsolete. upgrade to AVE 28')

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    def set_stacks(self, address, stacks):
        self.log(
            'got stacks from %s:\n%s'
            % (str(address), json.dumps(stacks, indent=4))
        )
        self.allocators[address].set_stacks(stacks)

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    #@trace
    def add_equipment(self, address, profiles):
        # no longer used between brokers. only accept local equipment
        if address != 'local':
            raise Exception(
                'cannot used add_equipment() with non-local equipment. please '
                'use set_equipment() instead (introduced in AVE 27).'
            )
        self.log('lister added:\n%s' % json.dumps(profiles, indent=4))
        self.allocators[address].add_equipment(profiles)
        # if sharing - update master as well
        if self.is_sharing():
            self.update_sharing()

    @Control.rpc
    @Control.preauth('share')
    @share_handler
    def set_equipment(self, address, equipment, allocations):
        self.log(
            'got equipment from %s:\n%s'
            % (str(address), json.dumps(equipment, indent=4))
        )
        self.allocators[address].set_equipment(equipment, allocations)
        # if sharing - update master as well
        if self.is_sharing():
            self.update_sharing()

    def update_sharing(self):
        if self.notifier == None:
            return
        total_equipment = []
        total_allocations = {}
        allocator_index = 0
        for a in self.allocators:
            equipment, allocations = \
                self.allocators[a].get_full_equipment_status()
            total_equipment.extend(equipment)
            for al in allocations:
                total_allocations[allocator_index] = allocations[al]
                allocator_index += 1
        try:
            self.notifier[REMOTE].set_equipment(
                total_equipment,
                total_allocations,
                __async__=True
            )
        except Exception, e:
            self.log('ERROR: could not interact with notifier: %s' % e)
            self.log(''.join(traceback.format_stack()))
            if type(e) == AveException and e.has_trace():
                self.log('server side trace:')
                self.log(e.format_trace())
            self.restart_sharing()

    ### RESOURCE ALLOCATION ####################################################

    @Control.rpc
    @Control.auth
    def get_resource(self, *profiles): # backwards compatibility
        return self.get(*profiles)

    @Control.rpc
    @Control.auth
    def get_resources(self, *profiles): # backwards compatibility
        return self.get(*profiles)


    @Control.rpc
    @Control.auth
    #@trace
    #@prof(immediate=True, entries=20)
    def get_multi_resources(self, *profiles):
        if not self.allocating:
            raise Restarting('broker is restarting')
        session = self.get_current_session()
        result = []
        tmp = []
        for profile in profiles:
            tmp = []
            if type(profile) is list:
                for p in profile:
                    if 'type' not in p:
                        raise Exception('profile "type" field is missing: %s' % p)
                    if p['type'] not in [
                        'workspace', 'handset', 'relay', 'testdrive', 'beryllium',
                        'wlan', 'powermeter'
                    ]:
                        raise Exception('unknown profile type "%s"' % p['type'])
                    # default the requested power state of handsets to boot_complete
                    # to avoid silly mistakes where a job gets an offline handset or
                    # something like that
                    if p['type'] == 'handset' and 'power_state' not in p:
                        p['power_state'] = 'boot_completed'
                    # default the requested power state of relays to online to avoid
                    # silly mistakes where a job gets a relay from an offline board
                    if p['type'] == 'relay' and 'power_state' not in p:
                        p['power_state'] = 'online'
                    tmp +=[ave.broker.profile.factory(p),]

                result.append(tmp)
            else:
                if 'type' not in profile:
                    raise Exception('profile "type" field is missing: %s' % profile)

                if profile['type'] not in [
                    'workspace', 'handset', 'relay', 'testdrive', 'beryllium',
                    'wlan', 'powermeter'
                ]:
                    raise Exception('unknown profile type "%s"' % profile['type'])
                if profile['type'] == 'handset' and 'power_state' not in profile:
                    profile['power_state'] = 'boot_completed'
                if profile['type'] == 'relay' and 'power_state' not in profile:
                    profile['power_state'] = 'online'

                result.append([ave.broker.profile.factory(profile)])

        profiles = result
        profiles_map = {}
        responses_map = {}
        for i in range(len(profiles)):
            profiles_map[i] = profiles[i]

        # make a distinction between simple and complex allocations. simple ones
        # include at most one piece of physical equipment.
        responses = []
        for a in sorted(self.allocators):
            if len(profiles_map.keys()) == 0:
                break
            allocator = self.allocators[a]
            for key in profiles_map.keys():
                best_error = None
                try:
                    resources = allocator.get_resources(profiles_map[key], session)
                    if self.is_sharing():
                        self.update_sharing()
                    responses_map[key] = resources
                    profiles_map.pop(key)
                except Busy, e:
                    best_error = e
                except NoSuch, e:
                    if not best_error:
                        best_error =e
                except Shared:
                    address = allocator.remote_address
                    result = self.multi_defer_allocation(session, address, *profiles_map[key])
                    responses_map[key] = result
                    profiles_map.pop(key)

        if len(profiles_map.keys()) == 0:
            for key in sorted(responses_map.keys()):
                responses.append(responses_map[key])
            return responses
        elif self.forward:
            # like with sharing remote broker, but the forwarding case
            address = list(self.remote_address)
            for key in profiles_map.keys():
                result = self.multi_defer_allocation(session, address, *profiles_map[key])
                responses_map[key]= result
                profiles_map.pop(key)
        elif len(profiles_map.keys()) != 0:
            self.close_session(session.authkey)
            raise best_error

        for key in sorted(responses_map.keys()):
            responses.append(responses_map[key])

        return responses

    @Control.rpc
    @Control.auth
    #@trace
    #@prof(immediate=True, entries=20)
    def get(self, *profiles):
        if not self.allocating:
            raise Restarting('broker is restarting')
        session = self.get_current_session()
        # do some sanity checks first: all profiles must have the "type" field
        # and there must not be more than one profile of a particular type in
        # the request.
        tmp = []
        for p in profiles:
            if 'type' not in p:
                raise Exception('profile "type" field is missing: %s' % p)
            if p['type'] not in [
                'workspace', 'handset', 'relay', 'testdrive', 'beryllium',
                'wlan', 'powermeter'
            ]:
                raise Exception('unknown profile type "%s"' % p['type'])
            # default the requested power state of handsets to boot_complete
            # to avoid silly mistakes where a job gets an offline handset or
            # something like that
            if p['type'] == 'handset' and 'power_state' not in p:
                p['power_state'] = 'boot_completed'
            # default the requested power state of relays to online to avoid
            # silly mistakes where a job gets a relay from an offline board
            if p['type'] == 'relay' and 'power_state' not in p:
                p['power_state'] = 'online'
            tmp.append(ave.broker.profile.factory(p))
        profiles = tmp

        # make a distinction between simple and complex allocations. simple ones
        # include at most one piece of physical equipment.
        best_error = None
        for a in sorted(self.allocators): # 'local' sorts before tuple
            allocator = self.allocators[a]
            try:
                resources = allocator.get_resources(profiles, session)
                if self.is_sharing():
                    self.update_sharing()
                return resources # success and early return
            except Busy, e:
                best_error = e
            except NoSuch, e:
                if not best_error:
                    best_error = e
            except Shared: # success and early return
                # matching resources found in a sharing remote broker. add the
                # profiles to the session and let it use the remote to attempt
                # the allocation against that broker.
                address = allocator.remote_address
                return self.defer_allocation(session, address, *profiles)

        if self.forward:
            # like with sharing remote broker, but the forwarding case
            address = list(self.remote_address)
            return self.defer_allocation(session, address, *profiles)
        else:
            self.close_session(session.authkey)
            raise best_error

    def defer_allocation(self, session, remote_address, *profiles):
        session.async_add_resources(remote_address, *profiles)
        result = {
            'address'  : session.address,
            'authkey'  : session.authkey,
            'resources': profiles
        }
        return result

    def multi_defer_allocation(self, session, remote_address, *profiles):
        session.multi_async_add_resources(remote_address, *profiles)
        result = {
            'address'  : session.address,
            'authkey'  : session.authkey,
            'resources': profiles
        }
        return result

    @Control.rpc
    @Control.auth
    def yield_resources(self, *resources):
        resources = list(resources)
        for i in range(len(resources)): # cast plain dict objects to Profiles
            r = resources[i]
            resources[i] = ave.broker.profile.factory(r)
        session = self.get_current_session()
        if not session:
            raise Exception('no resources to yield')

        # three cases to consider:
        # 1 - resources are allocated locally
        # 2 - resources are allocated by a remote share
        # 3 - resources are allocated by a forward broker
        deferred = []
        released = []
        for r in resources:
            for a in self.allocators.values():
                try:
                    released.extend(a.yield_resource(session, r))
                    break
                except NoSuch: # may be case 2 or 3
                    pass
                # do not catch NotOwner or NotAllocated --> throw back to client
            # always let client finish the yield. this covers both case 3 and
            # a twisted version of case 2: if a share has disconnected since
            # the client allocated one of its resources. then the resources
            # cannot be found in any allocator.
            deferred.append(r)
        if released:
            self.update_sharing()
        return deferred # let client talk directly to the involved sessions

    ### HANDOVER TO REPLACEMENT BROKER #########################################

    @Control.rpc
    def serialize(self):
        allocations = self.allocators['local'].serialize()
        state = {}
        for authkey in self.sessions:
            if authkey not in allocations:
                continue # skip sessions that do not have allocations
            session = self.sessions[authkey]
            state[authkey] = {
                'pid'        : session[LOCAL].pid,
                'address'    : list(session[REMOTE].address)
            }
            state[authkey]['allocations'] = allocations[authkey]
        return state

    @Control.rpc
    @Control.preauth('admin')
    def begin_handover(self, fdtx_dir='/tmp/ave'):
        # call this function on the broker that is going to be replaced.
        # steps:
        # stop listening for new connections from clients, stop the notifier,
        # disconnect all shares, disable further allocation (a session will
        # receive a Restarting exception if it manages to allocate at precisely
        # this moment and is expected to try again once or twice), create a
        # UNIX domain socket to transfer file descriptors (in a separate step),
        # serialize the state of the local allocator and all live sessions
        # (PIDs and RPC keys). finally return serialized data and the path to
        # UNIX domain socket.
        # first of all check that fdtx_dir is writable. otherwise the socket
        # will not be created in it and everything fails
        if os.path.exists(fdtx_dir) and os.path.isdir(fdtx_dir):
            if not os.access(fdtx_dir, os.R_OK | os.X_OK | os.W_OK):
                raise Exception('directory not writable: %s' % fdtx_dir)
        self.stop_listening()
        self.stop_sharing()
        self.drop_all_shares()
        self.stop_listers()
        self.allocating = False
        self.fdtx = FdTx(None)
        uds_path = self.fdtx.listen(fdtx_dir, 'handover-%s' % rand_authkey())
        # make sure the caller will be able to interact with the new socket by
        # making it world readable and world writable
        mode = (stat.S_IRUSR  # owner has read permission
             |  stat.S_IWUSR  # owner has write permission
             |  stat.S_IRGRP  # group has read permission
             |  stat.S_IWGRP  # group has write permission
             |  stat.S_IROTH  # others have read permission
             |  stat.S_IWOTH) # others have write permission
        os.chmod(uds_path, mode)
        return self.serialize(), self.config, uds_path

    @Control.rpc
    @Control.preauth('admin')
    def end_handover(self, timeout):
        self.fdtx.accept(timeout)
        # make sure all sockets used by RemoteSession instances are in blocking
        # mode, then use the FdTX instance to hand over the file descriptors
        for authkey in self.sessions:
            try:
                fd = self.sessions[authkey][REMOTE]._connection.fileno()
            except Exception, e:
                print(
                    'WARNING: cannot hand over session %s: %s'
                    % (authkey, str(e))
                )
            self.fdtx.put(authkey, fd)
        self.fdtx.close()

        # shut down if no sessions are left to take care of
        if not self.sessions:
            self.shutdown()

    #### THE FOLLOWING FUNCTIONS ARE DECLARED AS RPC FOR TESTING PURPOSES ONLY.
    #### REGULAR CLIENTS ARE NOT SUPPOSED TO USE THEM BUT THEY MAY BE USEFUL
    #### IN LAB SUPERVISION TOOLING. FORWARDING TO REMOTE BROKERS IS NOT DONE
    #### FOR ALL FUNCTIONS, SO E.G. list_allocations() ONLY RETURNS THE LOCAL
    #### ALLOCATIONS.

    @Control.rpc
    @Control.preauth('admin')
    def list_allocators(self):
        return self.allocators.keys()

    @Control.rpc
    @Control.preauth('admin')
    def list_handsets(self, profile=None):
        return self.allocators['local'].list_handsets(profile)

    @Control.rpc
    @Control.preauth('admin')
    def list_relays(self, profile=None):
        return self.allocators['local'].list_relays(profile)

    @Control.rpc
    @Control.preauth('admin')
    def list_equipment(self, profile=None, allocator=None):
        result = []
        # allocators indexed by address tuples but list_allocators give lists
        if type(allocator) == list:
            allocator = tuple(allocator)
        for a in self.allocators:
            if not allocator or a == allocator:
                result.extend(self.allocators[a].list_equipment(profile))
        return result

    @Control.rpc
    @Control.preauth('admin')
    def list_available(self, profile=None):
        result = []
        for a in self.allocators:
            result.extend(self.allocators[a].list_available(profile))
        return result

    @Control.rpc
    @Control.preauth('admin')
    def list_stacks(self):
        result = []
        for a in self.allocators:
            result.extend(self.allocators[a].list_stacks())
        return result

    @Control.rpc
    @Control.preauth('admin')
    def close_session(self, authkey):
        session  = self.sessions[authkey] # (Session, RemoteSession) tuple
        released = []

        # loop through share allocators
        for a in self.allocators:
            allocator = self.allocators[a]
            released.extend(self.allocators[a].close_session(session))

        try:
            session[LOCAL].terminate() # don't bother being nice.
        except OSError, e:
            if e.errno not in [errno.ECHILD, errno.ESRCH]:
                raise Exception('unhandled errno: %d' % e.errno)
        del self.sessions[authkey]
        # re-add released resources to the remote master broker if this broker
        # is configured to share
        if released and self.is_sharing():
            self.update_sharing()
        if not self.allocating:
            # handover in progress. shut down when no sessions with allocations
            # remain
            if not self.sessions:
                self.shutdown(Exit('broker restarted. please reconnect'))

    @Control.rpc
    @Control.auth
    def list_allocations(self):
        session = self.get_current_session()
        result = []
        if not session:
            return []
        for a in self.allocators:
            result.extend(self.allocators[a].list_allocations(session))
        return result

    @Control.rpc
    def list_allocations_all(self):
        result = []
        for a in self.allocators:
            result.extend(self.allocators[a].list_allocations(None))
        return result


    @Control.rpc
    @Control.auth
    def list_collateral(self):
        session = self.get_current_session()
        if not session:
            return []
        return self.allocators['local'].list_collateral(session)

    @Control.rpc
    def list_collateral_all(self):
        return self.allocators['local'].list_collateral(None)

    @Control.rpc
    @Control.preauth('admin')
    def stop(self):
        Control.stop(self)
        return True

class RemoteBroker(RemoteControl):

    def __init__(self, address=None, timeout=5, authkey=None, home=None):
        if not home:
            home = ave.config.load_etc()['home']
        # load and validate the configuration file
        config = load_configuration(get_configuration_path(home))
        validate_configuration(config)
        if not address:
            address = (config['host'], config['port'])
        RemoteControl.__init__(self, address, authkey, timeout)
        self.config  = config
        self.session = None

    def __del__(self):
        if self.session:
            del self.session
        RemoteControl.__del__(self)

    def get_resources(self, *profiles):
        return self.get(*profiles)
    def get_resource(self, *profiles):
        return self.get(*profiles)

    def get_resources_raw(self, *profiles):
        fn = RemoteControl.__getattr__(self, 'get')
        try:
            response = fn(*profiles)
        except AveException, e:
            # cast into a broker specific class. the factory will return the
            # original exception if it isn't a broker specific one
            raise exception_factory(e)
        if not self.session:
            address = tuple(response['address'])
            # authkey is used in hmac computation, which doesn't grok unicode:
            authkey = str(response['authkey'])
            self.session = RemoteSession(address, authkey)
        # we now have the session RPC keys and the profiles the broker added to
        # the session. ask the session for the RPC keys for those resources.
        return self.session.get_resources(*response['resources'])

    def get_multi_resources_raw(self, *profiles):
        fn = RemoteControl.__getattr__(self, 'get_multi_resources')
        try:
            responses = fn(*profiles)
        except AveException, e:
            raise exception_factory(e)
        if not self.session:
            address = tuple(responses[0]['address'])
            authkey = str(responses[0]['authkey'])
            self.session = RemoteSession(address, authkey)

        profiles = ()
        for response in responses:
            profiles += (response['resources'],)
        # we now have the session RPC keys and the profiles the broker added to
        # the session. ask the session for the RPC keys for those resources.
        return self.session.get_multi_resource(*profiles)


    def get(self, *profiles):
        # two stage approached: first let the broker return session RPC keys.
        # then use those to ask the session for the resource RPC keys. both
        # steps may raise BUSY exceptions, etc.
        # the rationale for using two stages is that it avoids long stalls in
        # the broker's main loop during resource allocation, whose latencies
        # are unknowable in a networked setup.
        multi = False
        seen_type = []
        for p in profiles:
            if type(p) is tuple:
                multi = True
                break
            elif 'type' in p and p['type'] in seen_type:
                multi = False
                break
            elif 'type' not in p:
                raise Exception('profile "type" field is missing: %s' % p)
            else:
                seen_type.append(p['type'])

        if multi:
            response = self.get_multi_resources_raw(*profiles)
        else:
            response = self.get_resources_raw(*profiles)

        result = ()
        for resource in response:
            profile = resource['profile']
            address = tuple(resource['address'])
            authkey = str(resource['authkey']) # hmac computation must have str
            if profile['type'] == 'workspace':
                result += (RemoteWorkspace(address, authkey, profile),)
            elif profile['type'] == 'handset':
                result += (RemoteHandset(address, authkey, profile),)
            elif profile['type'] == 'beryllium':
                result += (RemoteBeryllium(address, authkey, profile),)
            elif profile['type'] == 'relay':
                result += (RemoteRelay(address, authkey, profile),)
            elif profile['type'] == 'testdrive':
                result += (RemoteTestDrive(address, authkey, profile),)
            elif profile['type'] == 'wlan':
                result += (RemoteWlan(address, authkey, profile),)
            elif profile['type'] == 'powermeter':
                result += (RemotePowermeter(address, authkey, profile),)
            else:
                raise Exception('unknown resource type: %s' % profile)
        if len(result) == 1:
            return result[0]
        return tuple(result)

    def yield_resources(self, *resources):
        if not self.session:
            raise Exception('no resources to yield')
        fn = RemoteControl.__getattr__(self, 'yield_resources')
        profiles = []
        for r in resources:
            if isinstance(r, RemoteSession):
                profiles.append(r.profile)
            elif isinstance(r, Profile):
                profiles.append(r)
            elif type(r) == dict:
                profiles.append(r)
            else:
                raise Exception('do not know how to yield this: %s' % str(r))
        deferred = fn(*profiles)
        if deferred:
            self.session.yield_resources(deferred)
