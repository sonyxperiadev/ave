#coding=utf8

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import time
import socket
import errno
import signal
import struct
import traceback

from datetime import datetime

import ave.cmd

from ave.network.control    import Control, RemoteControl, Exit
from ave.network.connection import *
from ave.network.exceptions import *
from ave.network.pipe       import Pipe
from ave.network.process    import Process

from decorators import smoke
from setup      import MockControl

class setup(object):
    Class = None # mocked Control subclass

    def __init__(self, Class):
        self.Class = Class

    def __call__(self, fn):
        def decorated_fn():
            sock, port = find_free_port()
            pipe    = Pipe()
            control = self.Class(port, 'password', sock, [], pipe)
            control.start()
            remote  = RemoteControl(('', port), 'password', 5)
            result  = fn(control, remote, pipe)
            try:
                time.sleep(0.1)
                control.terminate()
                control.join()
            except OSError, e:
                if e.errno == errno.ESRCH:
                    pass # the test already killed the process
                else:
                    raise e
            return result
        return decorated_fn


@setup(MockControl)
def t01(control, remote, pipe):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        response = remote.sync_ping()
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: synchronous call failed: %s' % (pretty, str(e)))
        return False

    if response != 'pong':
        print('FAIL %s: wrong response: %s' % (pretty, response))
        return False

    return True

@setup(MockControl)
def t02(control, remote, pipe):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        response = remote.async_ping()
    except Exception, e:
        print('FAIL %s: asynchronous call failed: %s' % (pretty, str(e)))
        return False

    if response != None:
        print('FAIL %s: wrong response: %s' % (pretty, response))
        return False

    try:
        oob = pipe.get(timeout=1)
    except Exception, e:
        print('FAIL %s: never got out of band response' % pretty)
        return False

    if oob != 'pong':
        print('FAIL %s: wrong oob response: %s' % (pretty, oob))
        return False

    return True

# check that a ready-made socket can be passed to new listener Control objects
@smoke
def t03():
    pretty = '%s t3' % __file__
    print(pretty)

    sock, port = find_free_port()
    try:
        pipe    = Pipe()
        control = MockControl(None, None, sock, [], pipe)
        control.start()
    except Exception, e:
        print('FAIL %s: could not create control: %s' % (pretty, str(e)))
        return False

    try:
        remote = RemoteControl(('',port), None, 1)
    except Exception, e:
        print('FAIL %s: could not create remote: %s' % (pretty, str(e)))
        return False

    try:
        remote.stop(__async__=True)
        control.join()
        oob = pipe.get(timeout=1)
    except Exception, e:
        print('FAIL %s: never got out of band response' % pretty)
        return False

    if oob != 'shutdown':
        print('FAIL %s: wrong oob response: %s' % (pretty, oob))
        return False

    return True

# check that two Control objects don't interfere with each other
@smoke
def t04():
    pretty = '%s t4' % __file__
    print(pretty)

    s1,p1 = find_free_port()
    s2,p2 = find_free_port()

    try:
        c1 = MockControl(p1, 'password', s1)
        c2 = MockControl(p2, 'drowssap', s2)
    except Exception, e:
        print('FAIL %s: could not create two controls: %s' % (pretty, str(e)))
        return False

    try:
        c1.start()
        c2.start()
    except Exception, e:
        print('FAIL %s: could not start both controls: %s' % (pretty, str(e)))
        return False

    try:
        r1 = RemoteControl(('',p1), 'password', 1)
        r2 = RemoteControl(('',p2), 'password', 1)
    except Exception, e:
        print('FAIL %s: could not create two remotes: %s' % (pretty, str(e)))
        return False

    try:
        pong1 = r1.sync_ping()
        pong2 = r2.sync_ping()
    except Exception, e:
        print('FAIL %s: could not ping both controls: %s' % (pretty, str(e)))
        return False

    if pong1 != pong2 != 'pong':
        print('FAIL %s: wrong pong: %s %s' % (pretty, pong1, pong2))
        return False

    c1.terminate()
    c2.terminate()
    c1.join()
    c2.join()

    return True

# check that connctions to a terminated controller is refused
@smoke
def t06():
    pretty = '%s t6' % __file__
    print(pretty)

    s,p  = find_free_port()
    ctrl = MockControl(p, 'password', s)
    ctrl.start()
    con1 = RemoteControl(('',p), 'password', 1)
    try:
        con1.raise_exit()
    except Exit:
        pass # good
    ctrl.join(2)

    con2 = BlockingConnection(('',p), 'password')
    try:
        con2.connect()
    except ConnectionRefused, e:
        pass # good
    except ConnectionTimeout:
        print('FAIL %s: connection timeout instead of refusal' % pretty)
        return False
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))

    return True

# like t6 but with a timeout on the failing connection attempt
def t07():
    pretty = '%s t7' % __file__
    print(pretty)

    s,p  = find_free_port()
    ctrl = MockControl(p, 'password', s)
    ctrl.start()
    con1 = RemoteControl(('',p), 'password', 1)
    try:
        con1.raise_exit()
    except Exit:
        pass # good
    ctrl.join(2)

    con2 = BlockingConnection(('',p), 'password')
    try:
        con2.connect(timeout=1)
    except ConnectionRefused, e:
        pass # good
    except ConnectionTimeout:
        print('FAIL %s: connection timeout instead of refusal' % pretty)
        return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))

    return True

def list_fds():
    # unfortunately there is no portable way of listing file descriptors.
    # on linux: list the contents of /proc/<os.getpid()>/fd/.
    path = '/proc/%d/fd/' % os.getpid()
    fds  = {}
    for f in os.listdir(path):
        target = os.path.realpath(os.path.join(path, f))
        fds[int(f)] = target
    return fds

# check that add_connection() causes lost_connection() upcalls
@smoke
def t08():
    pretty = '%s t8' % __file__
    print(pretty)

    s,p1 = find_free_port()
    q    = Pipe()
    ctr1 = MockControl(p1, 'password', s, [], q)
    ctr1.start()

    s,p2 = find_free_port()
    ctr2 = MockControl(p2, None, s)
    ctr2.start()

    rem1 = RemoteControl(('',p1), 'password', timeout=5)
    rem1.connect_remote(('',p2), None)

    result = True
    ctr2.kill()
    try:
        msg = q.get(timeout=1)
    except Exception, e:
        print('FAIL %s: connection not lost: %s' % (pretty, str(e)))
        result = False

    if msg != ['',p2]:
        print('FAIL %s: wrong connection lost: %s' % (pretty, msg))
        result = False

    ctr1.terminate()
    ctr1.join()
    ctr2.join()
    return result

# same as t8 but second controller is stopped instead of killed
def t09():
    pretty = '%s t9' % __file__
    print(pretty)

    s,p1 = find_free_port()
    q1   = Pipe()
    ctr1 = MockControl(p1, 'password', s, [], q1)
    ctr1.start()

    s,p2 = find_free_port()
    q2   = Pipe()
    ctr2 = MockControl(p2, None, s, [], q2)
    ctr2.start()

    rem1 = RemoteControl(('',p1), 'password', timeout=5)
    rem1.connect_remote(('',p2), None)

    rem2 = RemoteControl(('',p2), None, timeout=5)
    rem2.stop(__async__=True)

    result = True
    try:
        msg = q1.get(timeout=1)
        if msg != ['',p2]:
            print('FAIL %s: wrong connection lost: %s' % (pretty, msg))
            result = False
    except Exception, e:
        print('FAIL %s: connection not lost: %s' % (pretty, str(e)))
        result = False
        ctr2.terminate()

    ctr1.terminate()
    ctr1.join()
    ctr2.join()
    return result

# check that signal handlers are active by checking that a subclass' shutdown()
# gets called.
@smoke
def t10():
    pretty = '%s t10' % __file__
    print(pretty)

    s,p = find_free_port()
    q = Pipe()
    c = MockControl(p, None, s, [], q)
    c.start()
    r = RemoteControl(('',p), None, timeout=5)
    r.sync_ping()

    c.terminate()
    try:
        q.get(timeout=1)
    except Exception, e:
        print('FAIL %s: never got oob message: %s' % (pretty, str(e)))
        c.kill()
        return False
    c.join(2)

    return True

# check that two contollers with connections to each other discover when the
# other one shuts down
def t11():
    pretty = '%s t11' % __file__
    print(pretty)

    s,p1 = find_free_port()
    q1   = Pipe()
    ctr1 = MockControl(p1, 'password', s, [], q1)
    ctr1.start()

    s,p2 = find_free_port()
    q2   = Pipe()
    ctr2 = MockControl(p2, None, s, [], q2)
    ctr2.start()

    # ask ctr1 to create a connection to ctr2
    rem1 = RemoteControl(('',p1), 'password', timeout=5)
    msg = rem1.connect_remote(('',p2), None)
    if msg != 'pong':
        print('FAIL %s: bad connection established: %s' % (pretty, msg))
        ctr1.terminate()
        ctr2.terminate()
        ctr1.join()
        ctr2.join()
        return False

    # tell ctr1 to shut down and wait for out of band ack
    rem1.stop(__async__=True)
    try:
        msg = q1.get(1)
    except Exception, e:
        print('FAIL %s: first oob not received: %s' % (pretty, str(e)))
        ctr1.terminate()
        ctr2.terminate()
        return False
    if msg != 'shutdown':
        print('FAIL %s: wrong fist oob receieved: %s' % (pretty, msg))
        ctr1.terminate()
        ctr2.terminate()
        return False

    # check if ctr2 discovered the connection loss from ctr1
    result = True
    try:
        msg = q2.get(1)
        if type(msg) != list: # no way of knowing the exact content beforehand
            print('FAIL %s: wrong second oob received: %s' % (pretty, msg))
            result = False
    except Exception, e:
        print('FAIL %s: second oob not received: %s' % (pretty, str(e)))
        result = False

    ctr2.terminate()
    ctr1.join()
    ctr2.join()
    return result

# check that two contollers with connections to each other discover when the
# other one is killed
@smoke
def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    s,p1 = find_free_port()
    ctr1 = MockControl(p1, 'password', s)
    ctr1.start()

    s,p2 = find_free_port()
    q    = Pipe()
    ctr2 = MockControl(p2, None, s, [], q)
    ctr2.start()

    # ask ctr1 to create a connection to ctr2
    rem1 = RemoteControl(('',p1), 'password', timeout=5)
    msg = rem1.connect_remote(('',p2), None)
    if msg != 'pong':
        print('FAIL %s: bad connection established: %s' % (pretty, msg))
        ctr1.terminate()
        ctr2.terminate()
        ctr1.join()
        ctr2.join()
        return False

    # kill ctr1
    ctr1.kill()

    # check if ctr2 discovered the connection loss from ctr1
    result = True
    try:
        msg = q.get(1)
        if type(msg) != list: # no way of knowing the exact content beforehand
            print('FAIL %s: wrong oob received: %s' % (pretty, msg))
            result = False
    except Exception, e:
        print('FAIL %s: oob not received: %s' % (pretty, str(e)))
        result = False

    ctr2.terminate()
    ctr1.join()
    ctr2.join()
    return result

# like t12 but the controllers are merely stopped and the client keeps an open
# connection
@smoke
def t13():
    pretty = '%s t13' % __file__
    print(pretty)

    s,p1 = find_free_port()
    q1   = Pipe()
    ctr1 = MockControl(p1, 'pass', s, [], q1)
    ctr1.start()

    s,p2 = find_free_port()
    q2   = Pipe()
    ctr2 = MockControl(p2, 'secret', s, [], q2)
    ctr2.start()

    # ask ctr1 to create a connection to ctr2
    rem1 = RemoteControl(('',p1), 'pass', timeout=5)
    msg = rem1.connect_remote(('',p2), 'secret')
    if msg != 'pong':
        print('FAIL %s: bad connection established: %s' % (pretty, msg))
        ctr1.terminate()
        ctr2.terminate()
        ctr1.join()
        ctr2.join()
        return False

    # stop ctr1 but don't drop the connection to it (rem1 is still in scope and
    # doesn't get garbage collected or expressely closed)
    rem1.stop(__async__=True)
    ctr1.join()

    # check if ctr2 discovered the connection loss from ctr1
    result = True
    try:
        msg = q2.get(1)
        if type(msg) != list: # no way of knowing the exact content beforehand
            print('FAIL %s: wrong oob received: %s' % (pretty, msg))
            result = False
    except Exception, e:
        print('FAIL %s: oob not received: %s' % (pretty, str(e)))
        result = False

    ctr2.terminate()
    ctr2.join()
    return result

# check the error message when calling a function that doesn't exist
def t14():
    pretty = '%s t14' % __file__
    print(pretty)

    s,p = find_free_port()
    c = MockControl(p, 'pass', s)
    c.start()
    r = RemoteControl(('',p), 'pass', timeout=5)

    # any call to a non-function will do
    result = True
    try:
        r.bla_bla_bla()
        print('FAIL %s: call did not fail' % pretty)
        result = False
    except Exception, e:
        if str(e) != 'no such RPC: bla_bla_bla':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            result = False

    c.terminate()
    c.join()
    return result

# check that Control function that SIGKILL self.pid returns on the client side
@smoke
def t15():
    pretty = '%s t15' % __file__
    print(pretty)

    class Ping(Process):

        def close_fds(self, exclude):
            exclude.append(self.args[1].w)
            Process.close_fds(self, exclude)

        def run(self, port, pipe):
            r = RemoteControl(('',port), 'pass', timeout=5)
            try:
                r.mock_death()
            except ConnectionClosed, e:
                pass # good
            except Exception, e:
                print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
                pipe.put(False)
            pipe.put(True)

    sock,port = find_free_port()
    q1 = Pipe()
    c = MockControl(port, 'pass', sock, [], q1)
    c.start()
    q2 = Pipe()
    p = Ping(args=(port,q2))
    p.start()

    result = True
    try:
        result = q2.get(timeout=5)
    except Exception, e:
        print('FAIL %s: death was mocked: %s' % (pretty, str(e)))
        result = False
        c.terminate()

    c.join()
    return result

# check that extra authkeys can be used to authenticate when the primary key is
# not set
def t16():
    pretty = '%s t16' % __file__
    print(pretty)

    sock, port = find_free_port()
    c = MockControl(port, None, sock, {'alt':'key'})
    c.start()

    r = RemoteControl(('',port), 'key', timeout=5)
    who = r.whoami()

    result = True
    if who != 'key':
        print('FAIL %s: wrong who: %s' % (pretty, who))
        result = False

    c.terminate()
    c.join()
    return result

# check that extra authkeys can be used to authenticate when the primary key is
# also set
def t17():
    pretty = '%s t17' % __file__
    print(pretty)

    sock, port = find_free_port()
    c = MockControl(port, 'key1', sock, {'alt':'key'})
    c.start()

    r = RemoteControl(('',port), 'key', timeout=5)
    who = r.whoami()

    result = True
    if who != 'key':
        print('FAIL %s: wrong who: %s' % (pretty, who))
        result = False

    c.terminate()
    c.join()
    return result

# check that multiple extra keys are accepted
@smoke
def t18():
    pretty = '%s t18' % __file__
    print(pretty)

    sock, port = find_free_port()
    c = MockControl(port, 'key1', sock, {'alt2':'key2', 'alt3':'key3'})
    c.start()

    result = True
    for key in ['key1', 'key2', 'key3']:
        r = RemoteControl(('',port), key, timeout=5)
        who = r.whoami()
        if who != key:
            print('FAIL %s: wrong who: %s' % (pretty, who))
            result = False
            break

    c.terminate()
    c.join()
    return result

# check that a failed authentication can be retried by creating new remote
# control objects
@smoke
def t19():
    pretty = '%s t19' % __file__
    print(pretty)

    sock, port = find_free_port()
    c = MockControl(port, 'key1', sock, {'alt2':'key2', 'alt3':'key3'})
    c.start()

    r = RemoteControl(('',port), 'no such key', timeout=5)
    who = r.whoami()
    if who != None:
        print('FAIL %s: wrong who 1: %s' % (pretty, who))
        c.terminate()
        c.join()
        return False

    r = RemoteControl(('',port), 'key3', timeout=5)
    who = r.whoami()
    if who != 'key3':
        print('FAIL %s: wrong who 2: %s' % (pretty, who))
        c.terminate()
        c.join()
        return False

    c.terminate()
    c.join()
    return True

# check that the preauth decorator accepts users with valid keys
def t20():
    pretty = '%s t20' % __file__
    print(pretty)

    sock, port = find_free_port()
    accounts = {'admin':'key2', 'root':'key3', 'nobody':'key4'}
    c = MockControl(port, 'key1', sock, accounts)
    c.start()

    r = RemoteControl(('',port), 'key2', timeout=5)
    who = r.whoami_preauth()
    if who != 'key2':
        print('FAIL %s: wrong who: %s' % (pretty, who))
        c.terminate()
        c.join()
        return False

    c.terminate()
    c.join()
    return True

# check that the preauth decorator rejects users who authenticate but do not
# have valid preauth keys
def t21():
    pretty = '%s t21' % __file__
    print(pretty)

    sock, port = find_free_port()
    accounts = {'admin':'key2', 'root':'key3', 'nobody':'key4'}
    c = MockControl(port, 'key1', sock, accounts)
    c.start()

    r = RemoteControl(('',port), 'key4', timeout=5)
    who = r.whoami()
    if who != 'key4':
        print('FAIL %s: wrong who: %s' % (pretty, who))
        c.terminate()
        c.join()
        return False

    r = RemoteControl(('',port), 'key4', timeout=5)
    try:
        r.whoami_preauth()
    except Exception, e:
        if str(e) != 'not authorized to make this call':
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
            c.terminate()
            c.join()
            return False

    c.terminate()
    c.join()
    return True

# t22
# check that control cannot be fooled into waiting indefinitely on a client
# that sends a poorly formatted response to an authentication challenge.
# test moved to stepped control tests. the behavior of control is also slightly
# different than before: rather than timing out and disconnecting a misbehaved
# client, it simply ignores it.

# check that the preauth decorator accepts users without valid keys if the named
# accounts are all explicitly configured to use the None key
@smoke
def t23():
    pretty = '%s t23' % __file__
    print(pretty)

    sock, port = find_free_port()
    c = MockControl(port, None, sock, {'admin':None, 'root':None})
    c.start()

    r = RemoteControl(('',port), 'foo bar', timeout=5)
    who = r.whoami_preauth()
    if who != None:
        print('FAIL %s: wrong who: %s' % (pretty, who))
        c.terminate()
        c.join()
        return False

    c.terminate()
    c.join()
    return True

# check that Control.idle() is called with the specified interval
def t24():
    pretty = '%s t24' % __file__
    print(pretty)

    sock, port = find_free_port()
    q = Pipe()
    c = MockControl(port, None, sock, pipe=q, interval=1)
    c.start()

    start = datetime.now()
    ok = True
    for i in range(3):
        try:
            msg = q.get(timeout=2)
        except Exception, e:
            print('FAIL %s: did not receive message: %s' % (pretty, str(e)))
            ok = False
            break
        if msg != 'idle':
            print('FAIL %s: wrong message: %s' % (pretty, str(msg)))
            ok = False
            break
    stop = datetime.now()
    c.terminate()
    c.join()

    if not ok:
        return

    def to_milliseconds(delta):
        return (delta.seconds * 1000) + (delta.microseconds / 1000)

    mean = to_milliseconds((stop - start) / 3)
    if mean < 900 or mean > 1100:
        print('FAIL %s: mean is deviant: %d' % (pretty, mean))
        return False

    return True

# check that the client sees same exception type, Exit, as raised on remote side
@smoke
@setup(MockControl)
def t25(control, remote, pipe):
    pretty = '%s t25' % __file__
    print(pretty)

    try:
        remote.raise_exit('passed to client')
    except Exit, e:
        if e.message != 'passed to client':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, e))
        return False

    return True

# check that the client sees same exception type, Timeout, as raised on remote
# side
@setup(MockControl)
def t26(control, remote, pipe):
    pretty = '%s t26' % __file__
    print(pretty)

    try:
        remote.raise_timeout()
    except Timeout, e:
        if e.message != 'command timed out':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, e))
        return False

    return True

# check that the client sees same exception type, RunError, as raised on remote
# side
@smoke
@setup(MockControl)
def t27(control, remote, pipe):
    pretty = '%s t27' % __file__
    print(pretty)

    try:
        remote.raise_run_error()
    except RunError, e:
        if 'No such file or directory' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, e))
        return False

    return True

# check that parent death signalling can be disabled
@setup(MockControl)
def t28(parent, parent_remote, pipe):
    pretty = '%s t28' % __file__
    print(pretty)

    # tell the parent to make a child
    try:
        port, pid = parent_remote.make_child()
    except Exception, e:
        print('FAIL %s: could not make child: %s' % (pretty, e))
        return False
    child_remote = RemoteControl(('',port), None, 5)

    # disable the child's death signalling
    try:
        child_remote.disable_death_signalling()
    except Exception, e:
        print('FAIL %s: could not disable signalling: %s' % (pretty, str(e)))
        os.kill(pid, signal.SIGTERM)
        return False

    # kill the parent and check that the child stays alive
    parent.terminate()
    parent.join()

    result = True
    for i in range(10):
        try:
            pong = child_remote.sync_ping()
        except Exception, e:
            print('FAIL %s: child did not pong: %s' % (pretty, str(e)))
            result = False
            break
        time.sleep(0.3)

    os.kill(pid, signal.SIGTERM)
    return result

# check that a control can be told to stop listening and that it doesn't affect
# already open connections
@smoke
@setup(MockControl)
def t29(control, remote, pipe):
    pretty = '%s t29' % __file__
    print(pretty)

    try:
        remote.stop_listening()
    except Exception, e:
        print('FAIL %s: could not stop listening: %s' % (pretty, str(e)))
        return False

    # existing connection is still alive?
    try:
        pong = remote.sync_ping()
    except Exception, e:
        print('FAIL %s: ping failed: %s' % (pretty, str(e)))
        return False

    # new connections cannot be made?
    try:
        r = RemoteControl(('',remote.address[1]), 'password', 1, False)
        pong = r.ping()
        print('FAIL %s: can talk to the deaf: %s' % (pretty, pong))
        return False
    except ConnectionRefused, e:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, str(e)))
        return False

    return True

# check that non-ASCII characters in implicitly typed AveException messages
# do not hang the control
@smoke
@setup(MockControl)
def t30(control, remote, pipe):
    pretty = '%s t30' % __file__
    print(pretty)

    try:
        remote.raise_plain_exception('åäö')
        print('FAIL %s: no exception raised' % pretty)
        return False
    except AveException, e:
        if e.message != u'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that non-ASCII characters in explicitly typed AveException messages
# do not hang the control
@setup(MockControl)
def t31(control, remote, pipe):
    pretty = '%s t31' % __file__
    print(pretty)

    try:
        remote.raise_ave_exception({'message':'åäö'})
        print('FAIL %s: no exception raised' % pretty)
        return False
    except AveException, e:
        if e.message != u'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that non-ASCII characters in Exit messages do not hang the control
@setup(MockControl)
def t32(control, remote, pipe):
    pretty = '%s t32' % __file__
    print(pretty)

    try:
        remote.raise_exit('åäö')
        print('FAIL %s: no exception raised' % pretty)
        return False
    except Exit, e:
        if e.message != u'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that making invalid remote calls with non-ASCII characters in the call
# does not hang the control
@smoke
@setup(MockControl)
def t33(control, remote, pipe):
    pretty = '%s t33' % __file__
    print(pretty)

    # python does not permit non-ASCII characters in method names? get the name
    # of the called function through getattr() instead and "call" the attribute
    # without parameters (the function does not exist anyway)
    try:
        getattr(remote, 'åäö')()
        print('FAIL %s: no exception raised' % pretty)
        return False
    except AveException, e:
        if str(e) != 'no such RPC: åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that long running operations do not time out on RPC level if no timeout
# value has been set in the RemoteControl constructor. use numeric timeout 0.
@setup(MockControl)
def t34(control, remote, pipe):
    pretty = '%s t34' % __file__
    print(pretty)

    remote = RemoteControl(remote.address, remote.authkey, 0)
    try:
        remote.sleep(2)
    except ConnectionTimeout, e:
        print('FAIL %s: could not sleep for 2 seconds: %s' % (pretty, e))
        return False
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

# check that long running operations do not time out on RPC level if no timeout
# value has been set in the RemoteControl constructor. use None timeout.
@setup(MockControl)
def t35(control, remote, pipe):
    pretty = '%s t35' % __file__
    print(pretty)

    remote = RemoteControl(remote.address, remote.authkey, None)
    try:
        remote.sleep(2)
    except ConnectionTimeout, e:
        print('FAIL %s: could not sleep for 2 seconds: %s' % (pretty, e))
        return False
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

# check that long running operations do time out on RPC level if a too short
# timeout value has been set in the RemoteControl constructor.
@setup(MockControl)
def t36(control, remote, pipe):
    pretty = '%s t36' % __file__
    print(pretty)

    remote = RemoteControl(remote.address, remote.authkey, 0.5)
    try:
        remote.sleep(2)
        print('FAIL %s: could sleep for 2 seconds' % pretty)
        return False
    except ConnectionTimeout, e:
        pass
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

@setup(MockControl)
def t37(control, remote, pipe):
    pretty = '%s t37' % __file__
    print(pretty)

    remote = RemoteControl(remote.address, remote.authkey, 0.5)
    try:
        garbage = remote.make_garbage()
    except Exception, e:
        print('FAIL %s: could not handle garbage: %s' % (pretty, e))
        return False

    return True

# check that client receives OverflowError if size field of RPC message exceeds
# system limit for socket.recv().
@setup(MockControl)
def t38(control, remote, queue):
    pretty = '%s t38' % __file__
    print(pretty)

    # ping once to make sure connection is established, then write a corrupt
    # message on the connection and check the response
    remote.sync_ping()

    header  = struct.pack('>L', 0x7fffffff+1)
    payload = RemoteControl.make_rpc_blob('sync_ping', None, [], {})
    remote._connection.write(header + payload)

    try:
        response  = json.loads(remote._connection.get(timeout=3))
        exception = exception_factory(response['exception'])
        if type(exception) != OverflowError:
            print('FAIL %s: wrong exception: %s' % (pretty, exception))
            return False
    except Exception, e:
        print('FAIL %s: wrong response: %s' % (pretty, e))
        return False

    # check that connection is now closed
    try:
        remote.sync_ping()
        print('FAIL %s: connection not closed' % pretty)
        return False
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: not ConnectionClosed exception: %s' % (pretty, e))
        return False

    return True
