# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import json
import select
import signal
import errno
import traceback

import ave.broker.profile

from ave.network.exceptions   import *
from ave.network.control      import Control, RemoteControl, Exit
from ave.broker.profile       import *
from ave.broker.exceptions    import *

from ave.relay.resource       import Relay
try:
    from ave.positioning.resource import TestDrive
except:# use stub if positioning support is not installed
    from positioning import TestDrive

from ave.handset.handset      import Handset
from ave.workspace            import Workspace

try: # prefer profile from full installation, if available
    from ave.powermeter.profile  import PowermeterProfile
except: # use stub if powermeter support is not installed
    from powermeter import PowermeterProfile

try: # prefer equipment class from full installation, if available
    from ave.beryllium.beryllium import Beryllium
except: # use stub if beryllium support is not installed
    from beryllium import Beryllium

try: # prefer equipment class from full installation, if available
    from ave.wlan.wlan import Wlan
except: # use stub if wlan support is not installed
    from wlan import Wlan

# this class is only used during broker restart when sessions are adopted by a
# newly started broker. the process of the original session cannot be reparented
# to the new broker, but at least it should be able to kill the originals. fix
# this by using dummy representations that only implement .pid and .terminate()
class AdoptedSession(object):

    def __init__(self, pid):
        if type(pid) != int:
            raise Exception('pid is not an integer: %s' % type(pid).__name__)
        self.pid = pid

    def join(self):
        pass # can't join/wait for this session process, don't own it.

    def terminate(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError, e:
            if e.errno == errno.ESRCH:
                return # process already killed by someone else
            if e.errno == errno.EPERM:
                # this can only happen if the original session was started as
                # a different user. e.g. if the broker has been restarted with
                # --demote=<some other user>. but don't worry too much about it
                # as sessions are eventually terminated anyway.
                print(
                    'WARNING: session with PID=%d not terminated because it '
                    'is owned by a different user. did you restart a broker '
                    'as a different user?' % self.pid
                )
                return
            raise e

class Session(Control):

    def __init__(self, port, authkey, broker_addr, socket=None, ws_cfg=None,
                 home=None, logging=True):
        if (not isinstance(broker_addr, tuple)
        or  type(broker_addr[0]) not in [str, unicode]
        or  type(broker_addr[1]) != int
        or  broker_addr[1] < 1):
            raise Exception('address must be a (string, integer > 0) tuple')
        Control.__init__(
            self, port, authkey, socket, {}, 1, home, 'ave-broker-session',
            logging
        )
        self.broker_addr = broker_addr # need to know how to "call home"
        self.resources   = {}          # resources owned by the session
        self.r_brokers   = {}          # (host,port) -> RemoteBroker
        self.r_sessions  = {}          # (host,port) -> RemoteSession
        self.r_resources = {}          # profile -> RemoteBroker
        self.deferred    = None        # use remote broker in next allocation
        self.mdeferred   = []
        self.ws_cfg      = ws_cfg      # configuration used for all workspaces

    @property
    def address(self):
        return (self.broker_addr[0], self.port)

    def trace(fn):
        def decorator(self, *vargs, **kwargs):
            try:
                return fn(self, *vargs, **kwargs)
            except Exception, e:
                traceback.print_exc()
                raise e
        return decorator

    def run(self):
        Control.run(self)

    def shutdown(self):
        for profile in self.resources.keys():
            del(self.resources[profile])
        Control.shutdown(self) # does not return. always do last

    # override callback defined by Control class:
    def lost_connection(self, connection, authkey):
        try:
            if self.get_remote_session(connection):
                self.shutdown()
        except:
            pass

    # need special handling of RPC to find the correct resource before calling
    # the wanted method on it
    def validate_rpc(self, rpc, authkey):
        try: # welformed json blob?
            rpc = json.loads(rpc)
        except Exception, e:
            raise Exception('malformed JSON: %s' % rpc)
        # mandatory fields present?
        if 'resource' not in rpc:
            raise Exception('the "resource" attribute is missing')
        if 'method' not in rpc:
            raise Exception('the "method" attribute is missing')
        if 'params' not in rpc:
            raise Exception('the "params" attribute is missing')
        async = False
        if 'async' in rpc:
            async = rpc['async']
            if type(async) != bool:
                raise Exception('RPC async flag is not a boolean: %s' % rpc)
        # figure out if the call is to the session itself or one of its held
        # resources. if it is to a resource, then don't bother checking for
        # rpc decorators, as the entire interfaces of such objects are exposed
        # as is.
        resource = None
        if rpc['resource']: # find the held resource and make the call on it
            try:
                profile = ave.broker.profile.factory(rpc['resource'])
                resource = self.resources[profile]
            except:
                raise Exception('no such resource: %s' % rpc['resource'])
            try:
                method = getattr(resource, rpc['method'])
            except:
                raise Exception('no such RPC: %s' % rpc['method'])
        else: # the call is to the session itself
            try:
                method = getattr(self, rpc['method'])
                if not hasattr(method, 'ave.control.rpc'):
                    raise Exception('not an RPC: %s' % rpc)
                if hasattr(method, 'ave.control.auth') and (not authkey):
                    raise Exception('not authenticated to make this call')
            except:
                raise Exception('no such RPC: %s' % rpc['method'])
        # welformed arguments?
        try:
            vargs  = rpc['params']['vargs']
            kwargs = rpc['params']['kwargs']
        except:
            raise Exception('malformed arguments: %s' % rpc['params'])
        return method, resource, vargs, kwargs, async

    @Control.rpc
    @Control.auth
    def stop(self):
        Control.stop(self)

    @Control.rpc
    @Control.auth
    def crash(self): # only used for testing purposes
        os.kill(os.getpid(), signal.SIGKILL)

    @Control.rpc
    def get_version(self):
        return 1

    def add_remote_session(self, session, authkey):
        # adds the remote session's connection to the main event loop to get
        # lost_connection() upcalls from Control.
        if not isinstance(session, RemoteSession):
            raise Exception('INTERNAL ERROR: not RemoteSession: %s' % session)
        if session._connection.address in self.r_sessions:
            raise Exception('INTERNAL ERROR: already added remote session')
        self.r_sessions[session._connection.address] = session
        self.add_connection(session._connection, authkey)

    def add_remote_broker(self, broker, authkey):
        # adds the remote broker's connection to the main event loop to get
        # lost_connection() upcalls from Control. tracks the broker based on
        # its address.
        if not isinstance(broker, RemoteControl):
            raise Exception('INTERNAL ERROR: not RemoteControl: %s' % broker)
        if broker._connection.address in self.r_brokers:
            raise Exception('INTERNAL ERROR: already added r_broker')
        self.r_brokers[broker._connection.address] = broker
        self.add_connection(broker._connection, authkey)
        self.add_remote_session(broker.session, authkey)

    def get_remote_broker(self, address):
        if address not in self.r_brokers:
            return None
        return self.r_brokers[address]

    def get_remote_session(self, connection):
        if connection.address not in self.r_sessions:
            return None
        return self.r_sessions[connection.address]

    @Control.rpc # TODO: change the broker to only use the asynchronous version
    def add_resource(self, profile):
        profile = ave.broker.profile.factory(profile)
        hash(profile)
        if isinstance(profile, BaseWorkspaceProfile):
            self.resources[profile] = Workspace(
                profile['uid'], None, self.ws_cfg, home=self.home
            )
        if type(profile) == HandsetProfile:
            self.resources[profile] = Handset(profile)
        if type(profile) == BerylliumProfile:
            self.resources[profile] = Beryllium(profile)
        if type(profile) == RelayProfile:
            self.resources[profile] = Relay(profile, home=self.home)
        if type(profile) == TestDriveProfile:
            self.resources[profile] = TestDrive(profile, home=self.home)
        if type(profile) == WlanProfile:
            self.resources[profile] = Wlan(profile, home=self.home)
        if type(profile) == PowermeterProfile:
            self.resources[profile] = Powermeter(profile, home=self.home)

    @Control.rpc
    # NOTE: this function is currently only used for adding remote resources
    # and works asynchronously, which probably would break local allocation in
    # the broker. should rework that so that add_resource() above can be taken
    # out. that would also speed up client-visible allocation. nice :)
    def async_add_resources(self, remote_address, *profiles):
        if type(remote_address) != list:
            raise Exception('remote_address must be a [host,port] list')
        if self.deferred:
            raise Exception('INTERNAL ERROR: self.deferred = %s'% self.deferred)
        self.deferred = (remote_address, profiles)

    @Control.rpc
    def multi_async_add_resources(self, remote_address, *profiles):
        if type(remote_address) != list:
            raise Exception('remote_address must be a [host,port] list')
        self.mdeferred.append((remote_address, profiles))

    @Control.rpc
    def yield_resources(self, resources):
        for profile in resources:
            profile = ave.broker.profile.factory(profile)
            if profile in self.resources:
                del self.resources[profile]
                continue
            if profile in self.r_resources:
                broker = self.r_resources[profile]
                try:
                    broker.yield_resources(profile)
                except:
                    # this is ok. may be due to disconnected broker
                    pass
                continue
            raise NoSuch('no such resource: %s' % profile)

    @Control.rpc
    @Control.auth
    def get_multi_resource(self, *profiles):
        profiles_map = {}
        responses_map = {}
        responses = []
        for i in range(len(profiles)):
            profiles_map[i] = profiles[i]

        for k, v in profiles_map.iteritems():
            found = False
            for deferred in self.mdeferred:
                if tuple(v) == deferred[1]:
                    found = True
                    remote_address = tuple(deferred[0])
                    remote_profile = deferred[1]
                    broker = self.get_remote_broker(remote_address)
                    if not broker:
                        add_broker = True
                        from ave.broker._broker import RemoteBroker # no circular import
                        broker = RemoteBroker(remote_address, home=self.home)
                    else:
                        add_broker = False

                    try:
                        response = broker.get_resources_raw(*remote_profile)
                        responses_map[k] = response
                    except (ConnectionTimeout, ConnectionClosed):
                        raise Exit('Broker connection failed')
                    except Exception, e:
                        # it doesn't matter what went wrong. kill off this session
                        raise Exit(str(e))
                    # keep separate books on remote resouces so they can't be mixed up
                    # with local ones. also keep track of the remote broker so that we
                    # can discover if it goes down.
                    for r in response:
                        profile = ave.broker.profile.factory(r['profile'])
                        self.r_resources[profile] = broker
                    if add_broker:
                        try:
                            self.add_remote_broker(broker, None)
                        except Exception, e:
                            print(
                                'WARNING: session could not connect remote broker: %s'
                                % str(e)
                            )
                            raise Exit(str(e))

                    self.mdeferred.remove(deferred)
                    break

            if not found:
                result = []
                for p in v:
                    pp = ave.broker.profile.factory(p)
                    if pp not in self.resources:
                        raise Exception('INTERNAL ERROR: no local resource %s' % p)

                    result.append({
                        'address': list(self.address),
                        'authkey': self.keys[0],
                        'profile': p
                    })
                responses_map[k] = result

        for k in sorted(responses_map.keys()):
            responses += responses_map[k]

        return responses


    @Control.rpc
    @Control.auth
    def get_resources(self, *profiles):
        if self.deferred:
            remote_address = tuple(self.deferred[0])
            broker = self.get_remote_broker(remote_address)
            if not broker:
                add_broker = True
                from ave.broker._broker import RemoteBroker # no circular import
                broker = RemoteBroker(remote_address, home=self.home)
            else:
                add_broker = False
            try:
                response = broker.get_resources_raw(*profiles)
            except (ConnectionTimeout, ConnectionClosed):
                raise Exit('Broker connection failed')
            except Exception, e:
                # it doesn't matter what went wrong. kill off this session.
                raise Exit(str(e))
            # keep separate books on remote resouces so they can't be mixed up
            # with local ones. also keep track of the remote broker so that we
            # can discover if it goes down.
            for r in response:
                profile = ave.broker.profile.factory(r['profile'])
                self.r_resources[profile] = broker
            if add_broker:
                try:
                    self.add_remote_broker(broker, None)
                except Exception, e:
                    print(
                        'WARNING: session could not connect remote broker: %s'
                        % str(e)
                    )
                    raise Exit(str(e))
            self.deferred = None
            return response
        else:
            result = []
            for p in profiles:
                pp = ave.broker.profile.factory(p)
                if pp not in self.resources:
                    raise Exception('INTERNAL ERROR: no local resource %s' % p)
                resource = self.resources[pp]
                result.append({
                    'address': list(self.address),
                    'authkey': self.keys[0],
                    'profile': p
                })
            return result

class RemoteSession(RemoteControl):

    def __init__(
            self, address, authkey, profile=None, timeout=None, optimist=False,
            sock=None
        ):
        RemoteControl.__init__(
            self, address, authkey, timeout, optimist, sock, profile
        )
