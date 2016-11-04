# Copyright (C) 2013-2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import traceback
import inspect

import os
import sys
import json
import time
import types
import errno
import select
import signal
import ctypes
import psutil

from socket   import error as SocketError
from datetime import datetime, timedelta

import ave.config
import ave.cmd

from ave.network.process    import Process
from ave.network.connection import *
from ave.network.exceptions import *

INMASK  = select.POLLIN | select.POLLPRI
OUTMASK = select.POLLOUT
ERRMASK = select.POLLERR | select.POLLHUP | select.POLLNVAL

# the recommended method to implement get_children() and get_proc_name() is to
# use the psutil module but unfortunately the version in Ubuntu 10 is too old
# to support the needed functions.

def get_children(pid):
    cmd = ['/usr/bin/pgrep', '-P', str(pid)]
    pids = ave.cmd.run(cmd)[1]
    return [int(pid) for pid in pids.splitlines()]

def get_proc_name(pid):
    try:
        with open(os.path.join('/proc', str(pid), 'comm')) as f:
            return f.read().strip()
    except Exception, e:
        raise Exception('could not get process name for PID %d: %S' % (pid, e))

def event_str(event):
    r = []
    if event & select.POLLIN:
        r.append('IN')
    if event & select.POLLOUT:
        r.append('OUT')
    if event & select.POLLPRI:
        r.append('PRI')
    if event & select.POLLERR:
        r.append('ERR')
    if event & select.POLLHUP:
        r.append('HUP')
    if event & select.POLLNVAL:
        r.append('NVAL')
    return ' '.join(r)

def to_milliseconds(interval):
    if interval < 0:
        return -1
    if type(interval) in [float, int]:
        return int(interval * 1000)
    return -1

# used to make sure a control never tries to dump objects that cannot be JSON
# serialized
def enforce_unicode(obj):
    if (not obj) or type(obj) in [int, long, float, unicode, bool]:
        return obj
    if type(obj) == str:
        return unicode(obj, errors='replace')
    if type(obj) in (list, tuple):
        return [enforce_unicode(o) for o in obj]
    if isinstance(obj, dict):
        result = {}
        for key in obj:
            result[enforce_unicode(key)] = enforce_unicode(obj[key])
        return result
    raise Exception('INTERNAL ERROR: OBJECT IS NOT JSON COMPATIBLE: %s' % obj)

class Partial(Exception):
    header  = None
    payload = None

    def __init__(self, header, payload):
        self.header  = header
        self.payload = payload

class Control(Process):
    '''
    This is the base class for all RPC capable AVE services. It accepts new
    connections on a listening TCP socket and polls the resulting sockets for
    traffic. Incoming JSON encoded messages are treated as remote procedure
    calls.

    ``Control`` implements a very limited cookie based authentication mechanism
    to secure that clients and their sessions are not accidentally mixed up,
    and a similar system based on persistent cookies to limit and/or expand
    client capabilities.

    :arg port: The port number to listen on.
    :arg authkey: If set, clients who do not provide the same key will not be
        allowed to connect.
    :arg socket: Must be a socket object that is listening on the same port as
        was specified with the *port* parameter.
    :arg alt_keys: A dictionary of alternative authentication keys that may be
        used to implement persistent cookies. Keys that appear in this dict may
        be used with the ``@Control.preauth()`` decorator. Functions that are
        marked this way can only be called by clients that authenticated with
        the right key when connecting.
    :arg interval: The interval in seconds at which the ``Control.idle()``
        method is called.

    .. Note:: None of the ``Control`` methods are directly accessible by RPC.
        Subclasses are expected to expose functions that should be accessible
        over RPC.

    .. Warning:: The use of persistent cookies to limit or expand a client's
        access rights does *not* constitute a security system. It is intended
        to prevent accidental use of features from contexts where they do not
        make sense to use and could potentially affect system performance
        severely.
    '''
    def __init__(self, port,authkey=None,socket=None,alt_keys={},interval=None,
        home=None, proc_name=None, logging=False):
        if (not socket) and (type(port) != int or port < 1):
            raise Exception('client port must be integer >= 1')
        # authkey is used in hmac computation, which doesn't understand unicode
        if authkey and type (authkey) != str:
            raise Exception('authkey must be a regular string')
        Process.__init__(self, self.run, (), logging, proc_name)
        self.socket  = socket
        self.port    = port        # listening port for all connections
        self.fds     = {}
        if type(authkey) not in [str, types.NoneType]:
            raise Exception('authkey must be a regular string or None')
        self.keys = {0: authkey}   # primary authentication key (may be None)
        if alt_keys:
            if type(alt_keys) != dict:
                raise Exception('alt_keys must be a dictionary')
            for k in alt_keys:
                if type(alt_keys[k]) not in [str, types.NoneType]:
                    raise Exception('alt keys must be regular strings or None')
                self.keys[k] = alt_keys[k]
        if type(interval) not in [int, float, types.NoneType]:
            raise Exception(
                'the interval (seconds) must be expressed as in integer, a '
                'float, or None'
            )
        if not home:
            home = ave.config.load_etc()['home']
        self.home           = home
        self.interval       = to_milliseconds(interval)
        self.unpend         = []    # fd's to ignore in pending events handling
        self.rejecting      = False
        self.accepting      = []    # connections
        self.authenticating = {}    # connection -> salt
        self.established    = {}    # connection -> authkey or None
        self.keepwatching   = {}
        self.listener       = None
        self.outgoing       = {}    # connection -> message
        self.buf_sizes      = (1024*16, 1024*16) # setsockopt() parameters
        self.deferred_joins = None

    def close_fds(self, exclude):
        if self.socket:
            exclude.append(self.socket.fileno())
        Process.close_fds(self, exclude)

    def initialize(self):
        Process.initialize(self)
        self.deferred_joins = []
        self.listener = Connection(('',self.port), self.socket)
        if not self.listener.socket: # do not replace caller provided socket
            self.listener.listen()
        self.poller = select.poll()
        self.pollable(self.listener.fileno(), self.listener, INMASK | ERRMASK)

    ### PROCESS MANAGEMENT #####################################################

    def start(self, daemonize=False, synchronize=False):
        Process.start(self, daemonize, synchronize)
        if self.socket:
            self.socket.close() # do not leave open in parent process

    def run(self):
        self.main_loop()
        self.shutdown()

    def stop(self):
        self.alive = False

    def shutdown(self, details=None):
        '''
        Exit the main loop and write a last exit message on all connections
        before closing them. The exit message will be serialized as an ``Exit``
        exception.
        '''
        # close all open connections
        for connection in self.accepting:
            connection.close()
        for connection in self.authenticating:
            if details:
                self.write_exit_message(connection, details)
            connection.close()
        for connection in self.established:
            if details:
                self.write_exit_message(connection, details)
            connection.close()
        if self.listener:
            self.listener.close()
        self.join_deferred()
        os._exit(1) # causes queued messages on outbound sockets to be flushed
                    # in the background. Man page: socket(7) SO_LINGER

    def get_children(self):
        return get_children(os.getpid())

    def handle_SIGTERM(self, signum, frame):
        self.shutdown()

    def handle_SIGUSR1(self, signum, frame):
        # propagate the signal to children, but only if they are AVE processes
        for pid in self.get_children():
            name = get_proc_name(pid)
            if name.startswith('ave-'):
                os.kill(pid, signal.SIGUSR1)
        # make the dump directory if it doesn't exist
        hickup_dir = os.path.join(self.home, '.ave', 'hickup')
        try:
            os.makedirs(hickup_dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                self.log('ERROR: could not create %s: %s' % (hickup_dir, e))
                return
        # create the trace file
        date = time.strftime('%Y%m%d-%H%M%S')
        name = '%s-%s-%d' % (date, self.proc_name, os.getpid())
        path = os.path.join(hickup_dir, name)
        with open(path, 'w') as f:
            f.write('stack:\n%s' % ''.join(traceback.format_stack(frame)))
            f.write('locals:\n%s\n' % frame.f_locals)
            f.write('globals:\n%s' % frame.f_globals)

    def join_later(self, proc):
        '''
        Defer joining of the process to the control process' main loop. When
        the process is joined, ``Control.joined_process()`` will be called.
        Deferred joins are made non-blocking. Any object whose class inherits
        from ``ave.network.process.Process`` may be joined in this way. Errors
        encountered in the actual attempt to join the process will be printed
        with ``Process.log()``.
        '''
        if not isinstance(proc, Process):
            raise Exception('not a Process or subclass: %s' % proc)
        if proc == self:
            raise Exception('cannot defer join of self')
        self.deferred_joins.append(proc)

    def join_deferred(self):
        again = []
        for proc in self.deferred_joins:
            try:
                (pid,exit) = proc.join_nohang()
                if (pid,exit) == (0,0):
                    again.append(proc)
                else:
                    self.joined_process(pid, exit)
            except Exception, e:
                name = type(e).__name__
                self.log('ERROR: %s(%s) when joining %d' % (name, e, proc._pid))
        self.deferred_joins = again

    def joined_process(self, pid, exit):
        '''
        May be implemented by classes that inherit from Control. The function
        will be called whenever a process terminates with a deferred join. See
        ``Control.join_later()`` for more information.
        '''
        pass

    ### HANDSHAKE & AUTHENTICATION STUFF #######################################

    def accept(self, connection):
        try:
            new = connection.accept()
            new.set_buf_sizes(*self.buf_sizes)
        except (ConnectionAgain, SocketError): # e.g. if the other end hangs up
            return None
        if self.rejecting:
            new.close()
            return None
        return new

    def get_authkeys(self):
        return [v for v in self.keys.values() if v != None]

    ### ADD/REMOVE CONNECTIONS TO THE MAIN LOOP HANDLING #######################

    def pollable(self, fd, connection, mask):
        assert fd > 0
        self.poller.register(fd, mask)
        self.fds[fd] = connection

    def unpollable(self, fd):
        self.poller.unregister(fd)
        del self.fds[fd]
        self.unpend.append(fd) # file descriptors may appear more than once in
        # the same batch of polling events. if the first such event causes the
        # removal of a connection, the handling of the next pending event will
        # fail as its file descriptor cannot be found. self.unpend is cleared
        # on each iteration of the main loop.

    def set_connection_authkey(self, connection, authkey):
        if connection not in self.established:
            raise Exception('not established: %s' % connection)
        if self.established[connection] != None:
            raise Exception('connection already has authkey')
        self.established[connection] = authkey

    def get_connection_authkey(self, connection):
        if connection not in self.established:
            raise Exception('not established: %s' % connection)
        return self.established[connection]

    def add_connection(self, connection, authkey):
        '''
        May be used by a subclass to add new open ``Connection`` objects to the
        main event loop.
        '''
        assert(connection != None)
        assert(connection.socket != None)
        self.established[connection] = authkey
        self.pollable(connection.fileno(), connection, INMASK | OUTMASK)

    def add_keepwatching(self, connection, authkey):
        assert(connection != None)
        assert(connection.socket != None)
        self.keepwatching[connection] = authkey
        self.pollable(connection.fileno(), connection, INMASK | OUTMASK)

    def remove_connection(self, connection):
        '''
        May be used by a subclass to remove a ``Connection`` objects from the
        main event loop.
        '''
        if connection in self.established:
            self.established.pop(connection)
        elif connection in self.authenticating:
            self.authenticating.pop(connection)
        elif connection in self.accepting:
            self.accepting.remove(connection)
        try:
            self.unpollable(connection.fileno())
        except:
            traceback.print_exc()
            pass

    def new_connection(self, connection, authkey):
        '''
        May be implemented by classes that inherit directly from ``Control``.
        The function will be called whenever a new connection is accepted by
        the ``Control`` object.
        '''
        pass

    def lost_connection(self, connection, authkey):
        '''
        May be implemented by classes that inherit directly from ``Control``.
        The function will be called whenever a previously accepted connection,
        or one added with ``add_connection()``, is lost. The function is called
        regardless of which peer caused the connection to be lost.
        '''
        pass

    def idle(self):
        '''
        Called periodically as long as there is no other activity in the main
        loop.
        '''
        pass # subclasses are not forced to implement this function

    def get_connection(self, fd):
        if fd not in self.fds:
            raise Exception('no connection with that file descriptor: %d' % fd)
        return self.fds[fd]

    def set_partial(self, fd, partial):
        if partial:
            self.partials[fd] = partial
        else:
            del self.partials[fd]

    def get_partial(self, fd):
        if fd not in self.partials:
            return None
        return self.partials[fd]

    def stop_listening(self):
        '''
        Stop accepting new clients. Close the listening socket.
        '''
        self.unpollable(self.listener.fileno())
        self.listener.close()

    def disable_death_signalling(self):
        self.perform_prctl(death_signal=0)

    def write_exit_message(self, connection, details):
        if isinstance(details, AveException):
            blob = { 'exception': details.details }
        else:
            blob = { 'exception': { 'type': 'Exit', 'message': str(details) } }
        try:
            connection.put(json.dumps(blob))
        except:
            pass # don't try to recover

    def main_loop(self):
        self.alive = True
        while self.alive:
            self.step_main()
            self.join_deferred()

    def step_listener(self, connection, event, fd):
        #print('%s(%s, %s)' %
        #   (inspect.currentframe().f_code.co_name,connection,event_str(event)))

        if event & ERRMASK:
            raise Exception('INTERNAL ERROR. LISTENER NEVER DIES')

        elif event & INMASK:
            new = self.accept(connection)
            if not new:
                # happens if peer hangs up during accept or the control is
                # rejecting new connections
                return
            self.pollable(new.fileno(), new, OUTMASK)
            self.accepting.append(new)
            # ignore all events for the same file descriptor in the current step
            # of the main loop. the OS may reuse descriptors aggressively and so
            # the events list may include POLLNVAL for the same descriptor. we
            # don't need to handle such a POLLNVAL event because that connection
            # is replaced (and GCed) by the call to self.pollable() above.
            self.unpend.append(new.fileno())

    def step_accepting(self, connection, event, fd):
        #print('%s(%s, %s)' %
        #   (inspect.currentframe().f_code.co_name,connection,event_str(event)))

        if event & ERRMASK:
            #print('%s %d close accepting %d %d %s' % (
            #   self.proc_name,os.getpid(),fd,connection.port,event_str(event)))
            self.accepting.remove(connection)
            connection.close()
            self.unpollable(fd)

        elif event & OUTMASK:
            self.accepting.remove(connection)
            salt = make_salt()
            try:
                connection.put(CHALLENGE + salt)
                self.authenticating[connection] = salt
                self.pollable(fd, connection, INMASK)
            except ConnectionClosed:
                #print('%s %d peer closed accepting %d %d OUT' % (
                #    self.proc_name, os.getpid(), fd, connection.port))
                connection.close()
                self.unpollable(fd)

    def step_authenticating(self, connection, event, fd):
        #print('%s(%s, %s)' %
        #   (inspect.currentframe().f_code.co_name,connection,event_str(event)))

        if event & ERRMASK:
            #print('%s %d close authenticating %d %d %s' % (
            #   self.proc_name,os.getpid(),fd,connection.port,event_str(event)))
            self.authenticating.pop(connection)
            connection.close()
            self.unpollable(fd)

        elif event & INMASK:
            try:
                digest = connection.get()
                if digest == None: # incomplete message read, try again later
                    self.pollable(fd, connection, INMASK)
                    return
            except ConnectionClosed:
                salt = self.authenticating[connection]
                self.authenticating.pop(connection)
                connection.close()
                self.unpollable(fd)
                #print('%s %d peer closed authenticating %d %d IN' % (
                #    self.proc_name, os.getpid(), fd, connection.port))
                return
            except Exception, e:
                msg = 'got invalid RPC from client, %s. disconnect' % unicode(e)
                response = {
                    'exception': { 'type':type(e).__name__, 'message': msg }
                }
                # hopefully the message reaches the client but we will not wait
                # for POLLOUT before writing it, because we should disconnect
                # the client immediately. this probably means the message could
                # get lost if the network is congested enough.
                connection.put(json.dumps(response))
                if self.established.has_key(connection):
                    authkey = self.established[connection]
                    self.lost_connection(connection, authkey)
                    self.established.pop(connection)
                connection.close()
                self.unpollable(fd)
                return


            salt    = self.authenticating[connection]
            keys    = self.get_authkeys()
            authkey = validate_digest(salt, digest, keys) # may return None
            # replace the digest salt with the accepted authkey and inform the
            # main loop that we need to send it to the client.
            self.authenticating[connection] = authkey
            self.pollable(fd, connection, OUTMASK)

        elif event & OUTMASK:
            authkey = self.authenticating[connection] # may be None
            self.authenticating.pop(connection)
            try:
                connection.put(json.dumps({ 'authenticated':authkey != None }))
                self.established[connection] = authkey # remember client's key
                self.new_connection(connection, authkey)
                self.pollable(fd, connection, INMASK)
            except ConnectionClosed:
                #print('%s %d peer closed authenticating %d %d OUT' % (
                #    self.proc_name, os.getpid(), fd, connection.port))
                connection.close()
                self.unpollable(fd)

    def step_established(self, connection, event, fd):
        #print('%s(%s, %s)' %
        #   (inspect.currentframe().f_code.co_name,connection,event_str(event)))

        if event & ERRMASK:
            #print('%s %d close established %d %d %s' % (
            #    self.proc_name,os.getpid(),fd,connection.port,event_str(event)))
            authkey = self.established[connection]
            self.lost_connection(connection, authkey)
            self.established.pop(connection)
            connection.close()
            self.unpollable(fd)

        elif event & INMASK:
            try:
                rpc = connection.get()
            except ConnectionClosed:
                authkey = self.established[connection]
                self.lost_connection(connection, authkey)
                self.established.pop(connection)
                connection.close()
                self.unpollable(fd)
                #print('%s %d peer closed established %d %d IN' % (
                #    self.proc_name, os.getpid(), fd, connection.port))
                return
            except Exception, e:
                msg = 'got invalid RPC from client, %s. disconnect' % unicode(e)
                response = {
                    'exception': { 'type':type(e).__name__, 'message': msg }
                }
                # hopefully the message reaches the client but we will not wait
                # for POLLOUT before writing it, because we should disconnect
                # the client immediately. this probably means the message could
                # get lost if the network is congested enough.
                connection.put(json.dumps(response))
                authkey = self.established[connection]
                self.lost_connection(connection, authkey)
                self.established.pop(connection)
                connection.close()
                self.unpollable(fd)
                return

            if rpc == None: # incomplete message read, try again later
                self.pollable(fd, connection, INMASK)
                return
            key = self.established[connection] # authkey presented by client
            try:
                method,resource,vargs,kwargs,async = self.validate_rpc(rpc, key)
            except Exception, e:
                response = json.dumps({'exception': enforce_unicode(str(e))})
                self.outgoing[connection] = response # pending to be sent
                self.pollable(fd, connection, OUTMASK)
                return # as done as it gets

            try:
                response = self.perform_rpc(method, resource, vargs, kwargs)
                if not async:
                    self.outgoing[connection] = response # pending to be sent
                    self.pollable(fd, connection, OUTMASK)
                return # all done
            except Exit, e:
                response = { 'exception': e.details }
                # TODO: try/except around put()
                connection.put(json.dumps(response)) # TODO: wait for OUTMASK?
                self.shutdown()
            except Exception:
                # disconnect the client and continue. TODO: log the exception
                authkey = self.established[connection]
                self.lost_connection(connection, authkey)
                self.established.pop(connection)
                connection.close()
                self.unpollable(fd)

        elif event & OUTMASK:
            try:
                response = self.outgoing[connection]
            except KeyError:
                # the deferred response must *not* be None, but may happen
                # anyway if a connection was added explicitly by the subclass
                self.pollable(fd, connection, INMASK)
                return
            try:
                if not connection.put(response): # could not send whole message
                    self.pollable(fd, connection, OUTMASK) # retry later
                    return
            except ConnectionClosed:
                #print('%s %d peer closed established %d %d OUT' % (
                #    self.proc_name, os.getpid(), fd, connection.port))
                connection.close()
                self.unpollable(fd)
                return
            self.outgoing[connection] = None
            self.pollable(fd, connection, INMASK)

    def step_keepwatching(self, connection, event, fd):
        if event & INMASK:
            try:
                connection.get()
            except ConnectionClosed:
                authkey = self.keepwatching[connection]
                self.lost_connection(connection, authkey)
                self.keepwatching.pop(connection)
                connection.close()
                self.unpollable(fd)
                return

    # run one step in the main loop
    def step_main(self):
        self.unpend = [] # TODO: reduce scope from class to function
        try:
            events = self.poller.poll(self.interval)
        except select.error, e: # (errno, string) tuple
            if e[0] == errno.EINTR:
                return # let caller decide how to proceed
        if not events:
            self.idle()
            return
        for (fd, event) in events:
            if fd in self.unpend: # file descriptor was removed from event
                continue          # handling as a result of the handling of
                                  # another event in the same poller batch.
            connection = self.get_connection(fd)
            self.current_connection = connection

            if connection == self.listener:
                self.step_listener(self.listener, event, fd)

            elif connection in self.accepting:
                self.step_accepting(connection, event, fd)

            elif connection in self.authenticating:
                self.step_authenticating(connection, event, fd)

            elif connection in self.established:
                self.step_established(connection, event, fd)

            elif connection in self.keepwatching:
                self.step_keepwatching(connection, event, fd)

    def validate_rpc(self, rpc, authkey):
        try: # welformed json blob?
            rpc = json.loads(rpc)
        except Exception, e:
            raise Exception('malformed JSON: %s' % rpc)
        # mandatory fields present?
        if 'method' not in rpc:
            raise Exception('the "method" attribute is missing')
        if 'params' not in rpc:
            raise Exception('the "params" attribute is missing')
        async = False
        if 'async' in rpc:
            async = rpc['async']
            if type(async) != bool:
                raise Exception('RPC async flag is not a boolean: %s' % rpc)
        # called method actually exists?
        try:
            method = getattr(self, rpc['method'])
        except:
            raise Exception('no such RPC: %s' % rpc['method'])
        # caller has access rights?
        if not hasattr(method, 'ave.control.rpc'):
            raise Exception('not an RPC: %s' % rpc)
        if hasattr(method, 'ave.control.auth'):
            if not authkey:
                raise Exception('not authenticated to make this call')
        if hasattr(method, 'ave.control.preauth'):
            # get the permissible account names attached to the function. then
            # check if the presented authkey matches any of the accounts.
            ok = False
            anonymous = True # if no account has a password, then this will be
                             # used to let anyone in
            for account in getattr(method, 'ave.control.preauth'):
                if account in self.keys:
                    if self.keys[account] != None:
                        anonymous = False
                    if self.keys[account] == authkey:
                        ok = True
            if anonymous:
                ok = True
            if not ok:
                raise Exception('not authorized to make this call')
        # welformed arguments?
        try:
            vargs  = rpc['params']['vargs']
            kwargs = rpc['params']['kwargs']
        except:
            raise Exception('malformed arguments: %s' % rpc['params'])

        return method, None, vargs, kwargs, async

    def perform_rpc(self, method, resource, vargs, kwargs):
        try: # make the method call
            result = method(*vargs, **kwargs)
            response = {'result': enforce_unicode(result)}
        except Exit:
            raise
        except AveException, e:
            response = { 'exception': e.details }
            if 'trace' not in e.details:
                response['exception']['trace'] = []
                (cls,exc,trace) = sys.exc_info()
                trace = traceback.extract_tb(trace)[1:]
                for entry in trace: # can't serialize tuples
                    response['exception']['trace'].append(list(entry))
        except Exception, e:
            response = {
                'exception': {
                    'message': unicode(e),
                    'type'   : type(e).__name__,
                    'trace'  : []
                }
            }
            (cls,exc,trace) = sys.exc_info()
            trace = traceback.extract_tb(trace)[1:] # don't include handle_rpc()
            for entry in trace: # can't serialize tuples
                response['exception']['trace'].append(list(entry))
        return json.dumps(response)

    @staticmethod
    def rpc(fn):
        setattr(fn, 'ave.control.rpc', True)
        return fn

    @staticmethod
    def auth(fn):
        setattr(fn, 'ave.control.auth', True)
        return fn

    class PreAuthDecorator:
        def __init__(self, *accounts):
            self.accounts = accounts
        def __call__(self, fn):
            setattr(fn, 'ave.control.preauth', self.accounts)
            return fn

    preauth = PreAuthDecorator

class RemoteControl(object):
    profile = None
    '''
    Class used to connect to ``Control`` objects. Creates a ``Connection``
    object internally to handle socket traffic with the peer.

    :arg address: A (port, host) tuple. The host may be the empty string ''
        which is interpreted as ``localhost``.
    :arg authkey: The authentication key, if any, to use.
    :arg timeout: Maximum amount of time in seconds to try connecting to a
        ``Control`` instance.
    :arg optimist: Set to ``True`` to keep retrying a connection attempt until
        it succeeds or the timeout expires.
    :arg sock: An open socket object that has already been connected to the
        port and host given in the *address* parameter.
    '''
    def __init__(self, address, authkey, timeout, optimist=True, sock=None,
        profile=None, home=None):
        self._connection = None
        self.address     = address
        self.authkey     = authkey
        self.timeout     = timeout or None
        self.optimist    = optimist
        self.profile     = profile
        self.home        = home
        if sock:
            self._connection = BlockingConnection(self.address, sock)
        try:
            import vcsjob
            self.job_guid = vcsjob.get_guid()
        except: # guid not set or vcsjob not even installed. how to log then?
            self.job_guid = None
        # don't import ave.panotti every time it is used. can't import it at
        # the module scope because ave.panotti also imports ave.network.control
        # which leads to an import error. assign the module to self instead.
        import ave.panotti as panotti
        setattr(self, 'panotti', panotti)

    def __del__(self):
        if self._connection:
            self._connection.close()

    @classmethod
    def make_rpc_blob(cls, method, resource, *vargs, **kwargs):
        async = False
        if '__async__' in kwargs:
            async = not not kwargs['__async__'] # cast to boolean
            del kwargs['__async__']
        blob = {
            'method'  : method,
            'resource': resource,
            'params'  : { 'vargs': list(vargs), 'kwargs': kwargs },
            'async'   : async
        }
        return json.dumps(blob)

    @property
    def port(self):
        return self.address[1]

    def connect(self, timeout):
        self._connection = self.make_connection(timeout)
        return self._connection

    def make_connection(self, timeout):
        limit = None
        if timeout != None:
            limit = time.time() + timeout
        c = BlockingConnection(self.address)
        c.connect(timeout, self.optimist)
        # expect first message to be an authentication request
        if timeout:
            timeout = max(limit - time.time(), 0)
        challenge = c.get(timeout)
        if timeout:
            timeout = max(limit - time.time(), 0)
        c.put(make_digest(challenge, self.authkey or ''), timeout)
        # expect second message to finalize the authentication
        if timeout:
            timeout = max(limit - time.time(), 0)
        try:
            finish_challenge(c.get(timeout))
        except AuthError, e:
            pass # do nothing. peer tracks authentication status
        return c

    def __getattr__(self, attribute):
        def make_rpc(*vargs, **kwargs):
            async   = ('__async__' in kwargs) and (not not kwargs['__async__'])
            timeout = self.timeout
            if async:
                timeout = 1 # better to fail quickly than to block on __async__
            blob = RemoteControl.make_rpc_blob(
                attribute, self.profile, *vargs, **kwargs
            )
            if not self._connection:
                self._connection = self.make_connection(timeout)
            self._connection.put(blob, timeout)
            if async:
                return None
            response = json.loads(self._connection.get(self.timeout))
            if 'exception' in response:
                self.panotti.shout(self.job_guid, response, self.home, False)
                raise exception_factory(response['exception'])
            return response['result']
        return make_rpc
