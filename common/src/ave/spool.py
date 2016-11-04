# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import select
import errno

from StringIO import StringIO
from datetime import datetime, timedelta

class Spool(object):
    log  = None
    fds  = None

    def __init__(self, path):
        if path:
            if ' ' in path:
                raise Exception('path must not include spaces: %s' % path)
            if not os.path.isdir(path):
                raise Exception('not a directory: %s' % path)
        if path:
            self.log = open(os.path.join(path, 'log.0'), 'w')
            # TODO: rotate logs

    def __del__(self):
        if self.log:
            self.log.close()

    def register(self, fd):
        '''
        Register a file decriptor with the spool.
        '''
        if not self.fds:
            self.fds = select.poll()
        mask = (
            select.POLLERR | select.POLLHUP | select.POLLNVAL | select.POLLIN |
            select.POLLPRI
        )
        self.fds.register(fd, mask)

    def read(self, timeout=0):
        '''
        Read the contents of the spool. This may cause reads on the registered
        file descriptors.
        '''
        if not self.fds:
            raise Exception('no file descriptors registered')
        if timeout > 0:
            start = datetime.now()
        io = StringIO()
        stop = False
        while (not stop):
            stop = True
            if timeout > 0:
                limit = timeout - ((datetime.now() - start).microseconds / 1000)
                if limit < 0:
                    raise Exception('time out')
            else:
                limit = 0
            events = self.fds.poll(limit)
            if not events:
                raise Exception('time out')
            for e in events:
                if (e[1] & select.POLLIN
                or  e[1] & select.POLLPRI):
                    tmp = os.read(e[0], 4096)
                    if tmp:
                        io.write(tmp)
                        if self.log:
                            self.log.write(tmp)
                    continue
                if e[1] & select.POLLERR:
                    self.fds.unregister(e[0])
                    raise Exception('POLLERR')
                if e[1] & select.POLLHUP:
                    self.fds.unregister(e[0])
                    raise Exception('POLLHUP')
                if e[1] & select.POLLNVAL:
                    self.fds.unregister(e[0])
                    raise Exception('POLLNVAL')
        if self.log:
            self.log.flush()
        return io.getvalue()

def make_spool(path):
    path = os.path.normpath(path)
    try: # create the target directory
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (path, str(e))
            )
    return Spool(path)

