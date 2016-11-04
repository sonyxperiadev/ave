# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import hmac
import time
import json
import errno
import socket
import select
import struct
import random
import traceback

from datetime import datetime, timedelta

from ave.network.exceptions import *

### FUNCTIONS NEEDED TO PERFORM DIGEST BASED HANDSHAKE #########################

CHALLENGE = b'#CHALLENGE#'

def make_salt():
    return os.urandom(20)

def make_digest(message, authkey=''):
    if type(authkey) != str:
        raise Exception('authkey is not a non-unicode string')
    if not message[:len(CHALLENGE)] == CHALLENGE:
        raise Exception('wrong challenge: %r' % message)
    salt   = message[len(CHALLENGE):]
    #print 'salt 1: %s' % ''.join(['%d' % ord(c) for c in salt])
    digest = hmac.new(authkey, salt).digest()
    return digest

def validate_digest(salt, digest, authkeys):
    #print 'salt 2: %s' % ''.join(['%d' % ord(c) for c in salt])
    #print 'digest: %s' % ''.join(['%d' % c for c in bytearray(digest)])
    for key in authkeys:
        if type(key) != str:
            raise Exception('authkey is not a non-unicode string')
    digests = {}
    for key in authkeys:
        accept = hmac.new(key, salt).digest()
        #print 'accepts: %s' % ''.join(['%d' % c for c in bytearray(accept)])
        if digest == accept:
            return key
    return None

def finish_challenge(response):
    response = json.loads(response)
    if 'authenticated' not in response:
        raise Exception('not an authentication result: %s' % response)
    if response != { 'authenticated': True }:
        raise AuthError('authentication failed')

### OTHER CONVENIENCE FUNCTIONS ################################################

def find_free_port(start=49152, stop=65536, listen=True):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for i in range(20000):
        try:
            port = random.randint(start, stop)
            s.bind(('', port))
            if listen:
                s.listen(socket.SOMAXCONN)
            return (s, port)
        except Exception, e:
            pass
    raise Exception('no free port available')

### THE CONNECTION CLASS #######################################################

class Connection(object):
    address             = None # (string, integer)
    socket              = None
    partial_get_header  = None # build with network input until len = 4
    partial_get_payload = None # build with network input until len = header
    partial_put_header  = None # reduce with network output until len = 0
    partial_put_payload = None # reduce with network output until len = 0

    def __init__(self, address, socket=None):
        if ((not socket)
        and (not isinstance(address, tuple)
        or   type(address[0]) not in [str, unicode]
        or   type(address[1]) != int
        or   address[1] < 1)):
            raise Exception('address must be a (string, integer > 0) tuple')
        self.address = address
        self.socket  = socket

    def __del__(self):
        self.close()

    def __repr__(self):
        return '%s(address=%s)' % (type(self).__name__, self.address)

    def __eq__(self, other):
        return id(self) == id(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def fileno(self):
        return self.socket.fileno()

    @property
    def port(self):
        return self.address[1]

    def set_keepalive(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

    def set_buf_sizes(self, recv_size, send_size):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, recv_size)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, send_size)
        return self.get_buf_sizes()

    def get_buf_sizes(self):
        recv = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        send = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        return recv,send

    def listen(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.set_keepalive()
        self.socket.bind(('', self.address[1]))
        self.socket.listen(socket.SOMAXCONN)
        self.socket.setblocking(0)
        return self

    def accept(self, Class=None):
        self.socket.setblocking(0)
        try:
            sock, addr = self.socket.accept()
        except socket.error, e:
            if e.errno == errno.EAGAIN:
                raise ConnectionAgain()
            raise
        sock.setblocking(0)
        if Class:
            return Class(addr, sock)
        return Connection(addr, sock)

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.set_keepalive()
        try:
            self.socket.connect(self.address)
        except socket.error, e:
            if e.errno == errno.EINPROGRESS:
                raise ConnectionInProgress()
            raise

    def close(self, hard=True):
        if not self.socket:
            return
        if hard:
            try: # fails if the connection was never established
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception, e:
                pass
        self.socket.close()

    def write(self, obj):
        try:
            size = self.socket.send(obj)
            if size == 0:
                raise ConnectionClosed()
            return size
        except socket.error, e:
            if e.errno == errno.EAGAIN:
                raise ConnectionAgain(str(e))
            if e.errno == errno.EPIPE:
                raise ConnectionClosed(str(e))
            if e.errno == errno.ECONNRESET:
                raise ConnectionClosed(str(e))
            raise

    def read(self, size):
        try:
            tmp = self.socket.recv(size)
            if not tmp:
                raise ConnectionClosed()
            return tmp
        except socket.error, e:
            if e.errno == errno.EAGAIN:
                raise ConnectionAgain(str(e))
            if e.errno == errno.EBADF:
                raise ConnectionClosed(str(e))
            if e.errno == errno.ECONNRESET:
                raise ConnectionClosed(str(e))
            raise

    def read_header(self):
        partial = self.partial_get_header or ''
        if len(partial) == 4:
            return partial
        header = self.read(4 - len(partial))
        self.partial_get_header = partial + header
        if len(partial) + len(header) != 4:
            return None
        return partial + header

    def read_payload(self, size):
        partial = self.partial_get_payload or ''
        if len(partial) == size:
            return partial
        payload = self.read(size - len(partial))
        self.partial_get_payload = partial + payload
        if len(partial) + len(payload) != size:
            return None
        return partial + payload

    @classmethod
    def make_header(cls, payload):
        if type(payload) != str:
            raise Exception('payload is not a string: %s' % type(payload))
        return struct.pack('>L', len(payload)) # network order, 4 bytes

    @classmethod
    def validate_message(cls, message):
        if len(message) < 4: # smallest message is 4 header bytes + 0 body
            raise Exception('header too short: %d' % len(message))
        size = struct.unpack('>L', message[:4])[0]
        if len(message[4:]) != size:
            raise Exception(
                'payload has wrong size: %d != %d' % (len(message[4:]), size)
            )
        return size, message[4:]

    def put(self, payload):
        '''
        Write a payload to the network, prefixed by a 32 bit network order
        integer that carries the byte size of *payload*.
        '''
        if self.partial_put_header != None:
            header = self.partial_put_header
        else:
            header = Connection.make_header(payload)
        if header: # may be empty string if already sent
            done = self.write(header)
            self.partial_put_header = header[done:]
            if done != 4:
                return None

        if self.partial_put_payload: # override parameter value
            payload = self.partial_put_payload
        done = self.write(payload)
        if done != len(payload):
            self.partial_put_payload = payload[done:]
            return None

        self.partial_put_header  = None
        self.partial_put_payload = None
        return payload

    def get(self):
        '''
        Read a message from the network. The message must be composed of a 32
        bit network order integer header followed by a payload whose size is
        encoded in the header.
        '''
        try:
            header = self.read_header()
            if not header:
                return None
            size = struct.unpack('>L', header)[0]
            payload = self.read_payload(size)
            if not payload:
                return None
        except ConnectionAgain:
            return None
        self.partial_get_header  = None
        self.partial_get_payload = None
        return payload

errmask = select.POLLERR | select.POLLHUP | select.POLLNVAL

class BlockingConnection(Connection):

    def poll(self, mask, timeout):
        poller = select.poll()
        poller.register(self.socket.fileno(), mask)
        return poller.poll(int(timeout*1000))

    def connect(self, timeout=None, optimist=False):
        if timeout != None:
            limit = time.time() + timeout
        while True:
            if timeout != None and time.time() > limit:
                raise ConnectionTimeout('connection attempt timed out')
            try:
                Connection.connect(self)
            except ConnectionInProgress:
                if timeout == None:
                    events = self.poll(select.POLLOUT, -1)
                else:
                    events = self.poll(select.POLLOUT, timeout)
                if not events:
                    raise ConnectionTimeout('connection attempt timed out')
                if events[0][1] & (select.POLLERR | select.POLLHUP):
                    if optimist:
                        time.sleep(0.1)
                        continue
                    raise ConnectionRefused()
                if events[0][1] & select.POLLOUT:
                    e = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if e == errno.ECONNREFUSED:
                        raise ConnectionRefused()
                    return
            return # good

    def accept(self, timeout=None):
        if timeout == None:
            timeout = -1
        events = self.poll(select.POLLIN | errmask, timeout)
        if not events:
            raise ConnectionTimeout('nothing to accept')
        if events[0][1] & (select.POLLHUP | select.POLLERR):
            raise ConnectionClosed('error condition on socket')
        return Connection.accept(self, Class=BlockingConnection)

    def read(self, size, timeout=None):
        payload = ''
        if timeout != None:
            limit = time.time() + timeout
        while len(payload) < size:
            if timeout != None and time.time() > limit:
                raise ConnectionTimeout()
            try:
                payload += Connection.read(self, size - len(payload))
            except ConnectionAgain:
                if timeout != None:
                    self.poll(select.POLLIN, limit-time.time()) # TODO: check events
                else:
                    self.poll(select.POLLIN, -1)
        return payload

    def write(self, payload, timeout=None):
        size  = len(payload)
        done  = 0
        limit = None
        if timeout != None: # first and last test of 'timeout'
            limit = time.time() + timeout
        while done < size:
            try:
                done += Connection.write(self, payload[done:])
            except ConnectionAgain:
                if limit:
                    timeout == limit - time.time()
                else:
                    timeout = -1
                events = self.poll(select.POLLOUT, timeout)
                if not events:
                    raise ConnectionTimeout('write attempt timed out')
                if events[0][1] & (select.POLLHUP | select.POLLERR):
                    raise ConnectionClosed(
                        'write attempt failed with %d at %d %f'
                        % (events[0][1], done, timeout)
                    )
                if events[0][1] & select.POLLOUT:
                    continue
                raise Exception('unknown events: %s' % events)

    def get(self, timeout=None):
        if timeout != None:
            limit = time.time() + timeout
        header = self.read(4, timeout)
        size   = struct.unpack('>L', header)[0]
        if timeout != None:
            timeout = limit - time.time()
        return self.read(size, timeout)

    def put(self, payload, timeout=None):
        if type(payload) != str:
            raise Exception('payload is not a string: %s' % type(payload))
        try:
            header = Connection.make_header(payload)
        except Exception, e:
            raise Exception('could not create message header: %s' % str(e))
        self.write(header + payload, timeout)
