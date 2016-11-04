import os
import time
import json
import errno
import struct
import select

from ave.network.exceptions import *

ERRMASK = select.POLLERR | select.POLLHUP | select.POLLNVAL

class Pipe(object):

    def __init__(self):
        self.r, self.w = os.pipe()

    def __del__(self):
        self.close()

    def make_header(self, payload):
        return struct.pack('>L', len(payload)) # network order, 4 bytes

    def poll(self, mask, timeout):
        poller = select.poll()
        poller.register(self.r, mask)
        return poller.poll(int(timeout*1000))

    def empty(self):
        return self.poll(select.POLLIN, 0) == []

    def read(self, size, timeout=None):
        if timeout != None:
            limit = time.time() + timeout
        payload = ''
        while len(payload) < size:
            if timeout != None:
                events = self.poll(select.POLLIN, max(0, limit - time.time()))
            else:
                events = self.poll(select.POLLIN, -1)
            if not events:
                raise ConnectionTimeout()
            if events[0][1] & ERRMASK:
                raise ConnectionReset()
            tmp = os.read(self.r, size)
            if not tmp:
                raise ConnectionClosed()
            payload += tmp
        return tmp

    def get(self, timeout=None):
        if timeout != None:
            limit = time.time() + timeout
        header = ''
        while len(header) != 4:
            header += self.read(4, timeout)
        size = struct.unpack('>L', header)[0]
        if timeout != None:
            timeout = limit - time.time()
        obj = self.read(size, timeout)
        return json.loads(obj)

    def put(self, payload):
        payload = json.dumps(payload)
        try:
            header = self.make_header(payload)
        except Exception, e:
            raise Exception('could not create message header: %s' % str(e))
        os.write(self.w, header + payload)

    def close(self):
        try:
            os.close(self.r)
        except OSError, e:
            if e.errno != errno.EBADF:
                raise
        try:
            os.close(self.w)
        except OSError, e:
            if e.errno != errno.EBADF:
                raise
