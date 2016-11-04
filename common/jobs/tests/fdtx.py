# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import sys
import errno
import socket
import traceback

from ave.workspace          import Workspace
from ave.network.process    import Process
from ave.network.fdtx       import FdTx
from ave.network.exceptions import *

from decorators import smoke

def setup(fn):
    def decorated_fn(so_path):
        w = Workspace()
        r = fn(w, so_path)
        w.delete()
        return r
    return decorated_fn

def accepter(sock_path, file_paths, so_path=None):
    try:
        tx = FdTx(so_path)
        dirname, filename = os.path.split(sock_path)
        tx.listen(dirname, filename)
        tx.accept()
        files = []
        for p in file_paths:
            f = open(p, 'w')
            files.append(f)
        tx.put('foo bar', *[f.fileno() for f in files])
    except Exception, e:
        traceback.print_exc()
        print('FAIL: accepter failed')

def connecter(sock_path, message, num, so_path=None):
    try:
        tx = FdTx(so_path)
        tx.connect(sock_path, 2)
        msg, fds = tx.get(len('foo bar'), num)
        for fd in fds:
            os.write(fd, message)
            os.fsync(fd)
    except Exception, e:
        traceback.print_exc()
        print('FAIL: connecter failed')

# check that a single file descriptor can be sent
@setup
def t1(w, so_path):
    pretty = '%s t1' % __file__
    print(pretty)

    sock_path = os.path.join(w.path, 'fdtx.sock')
    file_path = os.path.join(w.path, 'file.txt')

    p1 = Process(target=accepter, args=(sock_path, [file_path], so_path))
    p2 = Process(target=connecter, args=(sock_path, 'star cream', 1, so_path))
    p1.start()
    time.sleep(0.1)
    p2.start()
    p1.join()
    p2.join()

    with open(file_path) as f:
        contents = f.read()
        if contents != 'star cream':
            print('FAIL %s: wrong reception: %s' % (pretty, contents))
            return False

    return True

# check that multiple file descriptors can be sent
@smoke
@setup
def t2(w, so_path):
    pretty = '%s t2' % __file__
    print(pretty)

    sock_path = os.path.join(w.path, 'fdtx.sock')
    file_paths = [
        os.path.join(w.path, 'file1.txt'),
        os.path.join(w.path, 'file2.txt'),
        os.path.join(w.path, 'file3.txt')
    ]

    p1 = Process(target=accepter, args=(sock_path, file_paths, so_path))
    p2 = Process(target=connecter, args=(sock_path, 'star cream', 3, so_path))
    p1.start()
    time.sleep(0.1)
    p2.start()
    p1.join()
    p2.join()

    for path in file_paths:
        with open(path) as f:
            contents = f.read()
            if contents != 'star cream':
                print('FAIL %s: wrong reception: %s' % (pretty, contents))
                return False

    return True

# check that connecting with a timeout works
@setup
def t3(w, so_path):
    pretty = '%s t3' % __file__
    print(pretty)

    def srv(sock_path, so_path=None):
        try:
            tx = FdTx(so_path)
            dirname, filename = os.path.split(sock_path)
            time.sleep(0.5) # make sure a bunch of early connects fail
            tx.listen(dirname, filename)
            tx.accept()
        except Exception, e:
            traceback.print_exc()
            print('FAIL: srv failed')

    sock_path = os.path.join(w.path, 'fdtx.sock')

    p = Process(target=srv, args=(sock_path, so_path))
    p.start()

    tx = FdTx(so_path)
    ok = True
    try:
        tx.connect(sock_path, 2)
    except Exception, e:
        print('FAIL %s: connect failed: %s' % (pretty, str(e)))
        ok = False
    p.terminate()
    p.join()

    return ok

# like t4 but with the delay after the call to .listen(). also send something
@smoke
@setup
def t4(w, so_path):
    pretty = '%s t4' % __file__
    print(pretty)

    def srv(sock_path, file_path, so_path=None):
        try:
            tx = FdTx(so_path)
            dirname, filename = os.path.split(sock_path)
            tx.listen(dirname, filename)
            time.sleep(0.5) # make sure a bunch of early connects fail
            tx.accept()
            f = open(file_path, 'w')
            tx.put('foo bar', f.fileno())

        except Exception, e:
            traceback.print_exc()
            print('FAIL: srv failed')

    file_path = os.path.join(w.path, 'test.txt')
    sock_path = os.path.join(w.path, 'fdtx.sock')

    p = Process(target=srv, args=(sock_path, file_path, so_path))
    p.start()

    tx = FdTx(so_path)
    ok = True
    try:
        tx.connect(sock_path, 2)
        tx.get(len('foo bar'), 1)
    except Exception, e:
        print('FAIL %s: connect/get failed: %s' % (pretty, str(e)))
        ok = False
    p.terminate()
    p.join()

    return ok

# does .get() detect that the other end has hung up?
@smoke
@setup
def t5(w, so_path):
    pretty = '%s t5' % __file__
    print(pretty)

    def srv(sock_path, file_path, so_path=None):
        try:
            tx = FdTx(so_path)
            dirname, filename = os.path.split(sock_path)
            tx.listen(dirname, filename)
            tx.accept()
            f = open(file_path, 'w')
            tx.put('foo bar', f.fileno())
            del(tx) # let's be explicit about closing down

        except Exception, e:
            traceback.print_exc()
            print('FAIL: srv failed')

    file_path = os.path.join(w.path, 'test.txt')
    sock_path = os.path.join(w.path, 'fdtx.sock')

    p = Process(target=srv, args=(sock_path, file_path, so_path))
    p.start()

    tx = FdTx(so_path)
    tx.connect(sock_path, 2)
    msg, fds = tx.get(len('foo bar'), 1)
    if msg != 'foo bar':
        print('FAIL %s: wrong first message: %s' % (pretty, msg))
        ok = False

    ok = True
    try:
        msg, fds = tx.get(len('foo bar'), 1)
        print('FAIL %s: second get() did not fail: %s' % (pretty, msg))
        ok = False
    except ConnectionClosed, e:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        ok = False

    p.terminate()
    p.join()

    return ok

# does the timeout on .accept() work?
@smoke
@setup
def t6(w, so_path):
    pretty = '%s t6' % __file__
    print(pretty)

    accepter = FdTx(so_path)
    accepter.listen(os.path.join(w.path, 'fdtx.sock'))

    try:
        accepter.accept(timeout=0.5)
        print('FAIL %s: accept did not time out' % pretty)
        return False
    except Timeout:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True
