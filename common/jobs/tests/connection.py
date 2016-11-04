# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import time
import json
import socket
import pickle

from ave.network.process    import Process
from ave.network.connection import *

from decorators import smoke

### TESTS FOR BLOCKING CONNECTIONS ONLY ########################################
# non-blocking connections are tested in the control tests, especially the     #
# sync-stepped ones.                                                           #
################################################################################

# check that connection attempts fail if no one is listening
def t01():
    pretty = '%s t1' % __file__
    print(pretty)

    # bind socket to port but don't start listening
    sock,port = find_free_port(listen=False)

    c = BlockingConnection(('',port), None)
    try:
        c.connect()
        print('FAIL %s: connect() did not fail' % pretty)
        return False
    except ConnectionRefused:
        pass # good
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return False

    return True

# check that optimistic connection attempts time out rather than fail if no one
# is listening
def t02():
    pretty = '%s t2' % __file__
    print(pretty)

    # bind socket to port but don't start listening
    sock,port = find_free_port(listen=False)

    c = BlockingConnection(('',port), None)
    try:
        c.connect(timeout=1, optimist=True)
        print('FAIL %s: connect() did not fail' % pretty)
        return False
    except ConnectionTimeout:
        pass # good
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return False

    return True

# check that connection attempts succeed immediately if the peer is already
# accepting on its end
def t03():
    pretty = '%s t3' % __file__
    print(pretty)

    def ping(port, sock):
        listener = BlockingConnection(('',port), socket=sock)
        listener.listen()
        c = listener.accept(timeout=2)
        c.put('test the connection', timeout=1)
        c.close() # should not affect success of connect()

    def test(port):
        time.sleep(1)
        c = BlockingConnection(('',port), None)
        try:
            c.connect()
        except Exception, e:
            traceback.print_exc()
            print('FAIL %s: could not connect: %s' % (pretty, str(e)))
            return False

        try:
            msg = c.get(timeout=1)
            if msg != 'test the connection':
                print('FAIL %s: wrong message: %s' % (pretty, msg))
                return False
        except Exception, e:
            traceback.print_exc()
            print('FAIL %s: get() failed: %s' % (pretty, e))
            return False

    # bind socket to port but don't start listening
    sock,port = find_free_port(listen=False)
    pinger = Process(target=ping, args=(port,sock))
    pinger.start()

    result = test(port)

    pinger.terminate()
    pinger.join()

    return result

# check that connection attempts succeed if someone accepts soon enough
def t04():
    pretty = '%s t4' % __file__
    print(pretty)

    def ping(port, sock):
        listener = BlockingConnection(('',port), socket=sock)
        time.sleep(2)
        listener.listen()
        c = listener.accept(timeout=1)
        c.put('test the connection', timeout=1)
        c.close() # should not affect success of connect()

    def test(port):
        try:
            c = BlockingConnection(('',port), None)
            c.connect(timeout=3, optimist=True)
        except Exception, e:
            print('FAIL %s: connect failed: %s' % (pretty, str(e)))
            return False

        try:
            msg = c.get(timeout=1)
            if msg != 'test the connection':
                print('FAIL %s: wrong message: %s' % (pretty, msg))
                return False
        except Exception, e:
            print('FAIL %s: get() failed: %s' % (pretty, e))
            return False

    # bind socket to port but don't start listening
    sock,port = find_free_port(listen=False)
    pinger = Process(target=ping, args=(port, sock))
    pinger.start()

    result = test(port)

    pinger.terminate()
    pinger.join()

    return result

# check that accept() times out if no one is connecting
def t05():
    pretty = '%s t5' % __file__
    print(pretty)

    sock,port = find_free_port(listen=False)
    listener = BlockingConnection(('',port), sock)
    listener.listen()

    try:
        listener.accept(timeout=0.5)
        print('FAIL %s: accept did not time out' % pretty)
        return False
    except ConnectionTimeout:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    return True

# check that accept() does not time out if a connection is made while it is
# waiting
def t06():
    pretty = '%s t6' % __file__
    print(pretty)

    def ping(port):
        time.sleep(1)
        c = BlockingConnection(('',port))
        c.connect(timeout=1)
        c.put('test the connection', timeout=1)
        c.close() # should not affect success of accept()

    def test():
        listener = BlockingConnection(('',port), sock)
        listener.listen()
        try:
            c = listener.accept(timeout=3)
        except Exception, e:
            print('FAIL %s: accept failed: %s' % (pretty, e))
            return False

        try:
            msg = c.get(timeout=1)
            if msg != 'test the connection':
                print('FAIL %s: wrong message: %s' % (pretty, msg))
                return False
        except Exception, e:
            print('FAIL %s: get() failed: %s' % (pretty, e))
            return False

    sock,port = find_free_port(listen=False)
    pinger = Process(target=ping, args=(port,))
    pinger.start()

    result = test()

    pinger.terminate()
    pinger.join()

    return result

# send very large messages to trigger timed out writes
def t07():
    pretty = '%s t7' % __file__
    print(pretty)

    class Ping(Process):

        def close_fds(self, exclude=[]):
            exclude.append(self.args[1].fileno())
            Process.close_fds(self, exclude)

        def run(self, port, sock):
            listener = BlockingConnection(('', port), socket=sock)
            c = listener.accept(timeout=3)
            msg = c.read(104, timeout=0.1) # don't read enough
            time.sleep(1)
            c.put(msg[4:], timeout=5) # skip header bytes

    def test(port):
        writer = BlockingConnection(('', port))
        writer.connect(timeout=3)

        try:
            writer.put('.'*10000000, timeout=0.05)
            print('FAIL %s: huge write did not time out' % pretty)
            return False
        except ConnectionTimeout:
            pass # good

        msg = writer.get(timeout=5)
        if len(msg) != 100:
            print('FAIL %s: got wrong answer: %s' % (pretty, msg))
            return False

        return True

    sock,port = find_free_port()
    pinger = Ping(args=(port,sock))
    pinger.start()

    result = test(port)

    pinger.terminate()
    pinger.join()

    return result

# check that sending to listening sockets that are not accepting do time out if
# the payload is large enough
def t08():
    pretty = '%s t8' % __file__
    print(pretty)

    sock, port = find_free_port()
    # don't accept on the socket

    c = BlockingConnection(('',port))
    c.connect() # always succeeds if remote is listening

    for i in range(100000):
        try:
            c.put('message is hello', timeout=1)
        except ConnectionTimeout:
            break # good
        except Exception, e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    return True

# check that receiving times out if not enough input is available
def t09():
    pretty = '%s t9' % __file__
    print(pretty)

    class Ping(Process):

        def close_fds(self, exclude=[]):
            exclude.append(self.args[1].fileno())
            Process.close_fds(self, exclude)

        def run(self, port, sock):
            listener = BlockingConnection(('', port), socket=sock)
            c = listener.accept(timeout=3)
            c.write('.'*100, timeout=1) # don't write enough
            while True:
                time.sleep(1)

    def test(port):
        c = BlockingConnection(('', port))
        c.connect(timeout=3)
        try:
            c.read(101, timeout=1) # read too much
            print('FAIL %s: read() not time out' % pretty)
            return False
        except ConnectionTimeout:
            pass # good
        return True

    sock,port = find_free_port()
    pinger = Ping(args=(port,sock))
    pinger.start()

    result = test(port)

    pinger.terminate()
    pinger.join()

    return result

# check that receiving fails if the connection is closed before enough data has
# become available
def t10():
    pretty = '%s t10' % __file__
    print(pretty)

    class Ping(Process):

        def close_fds(self, exclude=[]):
            exclude.append(self.args[1].fileno())
            Process.close_fds(self, exclude)

        def run(self, port, sock):
            listener = BlockingConnection(('', port), socket=sock)
            c = listener.accept(timeout=3)
            c.write('.'*100, timeout=1) # don't write enough
            c.close()

    def test(port):
        c = BlockingConnection(('', port))
        c.connect(timeout=3)
        try:
            c.read(101, timeout=1) # read too much
            print('FAIL %s: read did not fail' % pretty)
            return False
        except ConnectionClosed:
            pass # good
        return True

    sock,port = find_free_port()
    pinger = Ping(args=(port,sock))
    pinger.start()

    result = test(port)

    pinger.terminate()
    pinger.join()

    return result
