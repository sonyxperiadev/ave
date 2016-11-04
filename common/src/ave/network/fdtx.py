# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import sys
import errno
import socket
import random

from ctypes   import *
from datetime import datetime, timedelta

from ave.network.exceptions import *

def rand_string():
    result = []
    for i in range(16):
        result.append(random.randint(0,9))
    return ''.join(['%d' % i for i in result])

class Errno(Exception):
    errno = 0

    def __init__(self, errno):
        self.errno = errno

    def __str__(self):
        return 'errno=%d' % self.errno

class FdTx(object):
    '''
    Implements file descriptor transfer between processes using a special
    feature of UNIX domain sockets. This feature is not wrapped by Python 2's
    standard library, so the implementation resides in a separate C library
    which is interfaced with the ``ctypes`` module.

    :arg so_path: *None* or a file system path to the underlying C library that
        implements file descriptor transfer.
    '''
    socket      = None # UNIX domain socket
    socket_path = None
    c_library   = None

    def __init__(self, so_path):
        if not so_path:
            so_path = 'libfdtx.so'
        self.c_library = self.load_so(so_path)

    def __del__(self):
        self.close()

    def load_so(self, so_path):
        c_library = CDLL(so_path, use_errno=True)

        self.send             = c_library.fdtx_send
        self.send.restype     = c_int
        self.send.argtypes    = [c_int, POINTER(c_int), c_uint, c_char_p, c_int]

        self.recv             = c_library.fdtx_recv
        self.recv.restype     = c_int
        self.recv.argtypes    = [c_int, POINTER(c_int), c_uint]

        self.max_fds          = c_library.fdtx_max_fds
        self.max_fds.restype  = c_int
        self.max_fds.argtypes = None

        return c_library

    def listen(self, dirname, filename=None):
        '''
        Create a UNIX domain socket in the file system and start listening on
        it for connections.

        :arg dirname: The file system directory where the socket file will be
            created.
        :arg filename: The file name of the created socket. Will be randomized
            if not set.
        :returns: The full socket path.
        :raises: *Exception* if the file already exists.
        '''
        if type(dirname) not in [str, unicode]:
            raise Exception('dirname must be a string: %s' % dirname)
        if filename:
            if type(filename) not in [str, unicode]:
                raise Exception('filename must be a string')
        else:
            filename = rand_string()
        if os.path.exists(os.path.join(dirname, filename)):
            raise Exception('file already exists')
        try:
            os.makedirs(dirname)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
        self.socket_path = os.path.join(dirname, filename)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(1)
        return self.socket_path

    def accept(self, timeout=None):
        '''
        Accept a connection. The caller must have called ``listen()`` first.

        ``FdTx`` only keeps track of one open socket internally. Calling this
        function more than once has undefined behavior.

        :arg timeout: The maximum amount of time to wait, in seconds, for a
            connection attempt.
        :raises: A *Timeout* exception if the timeout expires.
        '''
        if timeout:
            if type(timeout) not in [int, float]:
                raise Exception('timeout must be an integer or float')
            self.socket.settimeout(timeout)
        try:
            self.socket = self.socket.accept()[0]
        except socket.timeout:
            raise Timeout('timed out')

    def connect(self, path, timeout):
        '''
        Connect to an accepting peer. The attempt will be retried until it is
        successful or *timeout* expires.

        :arg path: File system path to a UNIX domain socket that is accepting
            connections.
        :arg timeout: The maximum amount of time to wait, in seconds, for the
            connection attempt to be successful.
        :raises: A *Timeout* exception if the timeout expires.
        '''
        limit = datetime.now() + timedelta(seconds=timeout)
        while True:
            if datetime.now() > limit:
                raise Timeout('no such socket file: %s' % path)
            if os.path.exists(path):
                break
            time.sleep(0.1)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(path)

    def close(self):
        '''
        Close the underlying domain socket.
        '''
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        if self.socket_path:
            try:
                os.unlink(self.socket_path)
            except OSError, e:
                print e
            self.socket_path = None

    def put(self, message, *fds):
        '''
        Send a message containing a free form text message and an array of file
        descriptors.

        .. Note:: The receiver must have been told beforehand, in a separate
            message or by convention, how many file descriptors it will receive.
        '''
        Cls = c_int * len(fds)
        buf = Cls(*fds)
        err = self.send(self.socket.fileno(), buf, len(fds), message, len(message))
        if err < 0:
            raise Errno(get_errno())

    def get(self, max_msg_len, max_fds):
        '''
        Receive a message containing a free form text message and an array of
        file descriptors.

        :returns: A tuple containing the message and a list of file descriptors.
        '''
        msg = (c_char * max_msg_len)()
        fds = (c_int * max_fds)()
        err = self.recv(self.socket.fileno(), fds, max_fds, msg, max_msg_len)
        if err == -1:
            raise Errno(get_errno())
        if err == -2:
            raise ConnectionClosed()
        return msg.value, [fd for fd in fds]
