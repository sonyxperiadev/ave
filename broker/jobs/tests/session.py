#encoding=utf8

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import re
import json
import time
import socket
import traceback

from ave.workspace          import Workspace
from ave.broker._broker     import Broker, RemoteBroker
from ave.broker.session     import Session, RemoteSession
from ave.broker.resource    import RemoteWorkspace, RemoteHandset
from ave.network.connection import *
from ave.handset.profile    import HandsetProfile

import setup

# basic start/stop of session
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    sock,port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    try:
        s = Session(port, 'password', ('',1), None, logging=False)
        s.start()
    except Exception, e:
        print('FAIL %s: failed to create Session: %s' % (pretty, str(e)))
        return

    # connect to the session and tell it to stop itself
    r = RemoteSession(('',port), 'password', timeout=1, optimist=True)
    r.stop(__async__=True) # throw away the response
    try:
        s.join(1)
    except Exception, e:
        print('FAIL %s: session did not join' % pretty)
        s.terminate()
        return False
    return True

# start/stop sessions on the same listening port a couple of times to check that
# sockets get closed properly
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    sock,port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    for i in range(5):
        s = Session(port, 'password', ('',1), None, logging=False)
        s.start()
        r = RemoteSession(('',port), 'password', timeout=1, optimist=True)
        r.stop(__async__=True) # throw away the response
        try:
            s.join(1)
        except Exception, e:
            print('FAIL %s: session did not join' % pretty)
            s.terminate()
            return False
    return True

# check that many authentication challenges can be attempted simultaneously
@setup.session('test_session-t1')
def t3(s, r):
    pretty = '%s t3' % __file__
    print(pretty)

    # connect a supervisor
    try:
        c1 = BlockingConnection(('', r.port))
        c1.connect(timeout=5)
    except Exception, e:
        print('FAIL %s: could not connect supervisor 1: %s' % (pretty, str(e)))
        return False

    # do it again
    try:
        c2 = BlockingConnection(('', r.port))
        c2.connect(timeout=5)
    except Exception, e:
        print('FAIL %s: could not connect supervisor 2: %s' % (pretty, str(e)))
        return False

    # fail authentication on both to make them supervisor connections
    try:
        c1.put(make_digest(c1.get(), ''))
        finish_challenge(c1.get())
    except AuthError, e: # expected
        pass
    except Exception, e:
        print('FAIL %s: wrong exception 1: %s' % (pretty, str(e)))
        return False
    try:
        c2.put(make_digest(c2.get(), ''))
        finish_challenge(c2.get())
    except AuthError, e: # expected
        pass
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: wrong exception 2: %s' % (pretty, str(e)))
        return False

    c1.close()
    c2.close()

    r.stop(__async__=True)
    try:
        s.join(2)
    except Timeout:
        print('FAIL %s: session has not died' % pretty)
        s.kill(signal.SIGKILL)
        s.join()
        return False

    return True

# check that supervisor connections can be done by not specifying a password
@setup.session('test_session-t1')
def t4(s, r):
    pretty = '%s t4' % __file__
    print(pretty)

    # connect supervisor and fail authentication (no authkey given)
    try:
        r2 = RemoteSession(('', r.port), 'password')
    except Exception, e:
        print('FAIL %s: could not connect supervisor: %s' % (pretty, str(e)))
        return False

    # play ping pong with the session
    v = r2.get_version()
    if v != 1:
        print('FAIL %s: wrong version: %s' % (pretty, str(v)))
        return False

    return True

# check that workspace methods can be used through a session
@setup.session('test_session-t1')
def t5(s, r):
    pretty = '%s t5' % __file__
    print(pretty)

    workspace = Workspace('session-t5')

    # emulate resource handling done by broker
    r.add_resource({'type': 'workspace', 'uid':'session-t5'})
    w = RemoteWorkspace(
        r.address, r.authkey, {'type': 'workspace', 'uid':'session-t5'}
    )

    # check that there really is a workspace on the other end
    exc = None
    try:
        result = w.get_profile()
    except Exception, e:
        exc = e
    workspace.delete()

    if exc:
        print('FAIL %s: get_profile() failed: %s' % (pretty, str(exc)))
        return False

    if 'root' not in result:
        print('FAIL %s: not a workspace profile: %s' % (pretty, result))
        return False

    return True

# check that handset methods can be used through a session
@setup.session('test_session-t6')
def t6(s, rs):
    pretty = '%s t6' % __file__
    print(pretty)

    profile = HandsetProfile({
        'type':'handset', 'vendor':'foo', 'product':'bar',
        'serial':'1','pretty':'mary'
    })

    # emulate resource handling done by broker
    rs.add_resource(profile)
    rh = RemoteHandset(rs.address, rs.authkey, profile)

    # check that there really is a handset on the other end
    try:
        result = rh.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile() failed: %s' % (pretty, str(e)))
        return False

    if 'serial' not in result:
        print('FAIL %s: not a handset profile: %s' % (pretty, result))
        return False

    return True

# like t5 and t6, but through a broker's allocation
@setup.brokers([], 'master', [], True, False)
def t7(HOME, broker):
    pretty = '%s t7' % __file__
    print(pretty)

    w,h = broker.get_resource({'type':'workspace'}, {'type':'handset'})

    # check that there really is a workspace on the other end
    try:
        result = w.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile() 1 failed: %s' % (pretty, str(e)))
        return False
    if 'root' not in result or 'env' not in result:
        print('FAIL %s: not a workspace profile: %s' % (pretty, result))
        return False

    # check that there really is a handset on the other end
    try:
        result = h.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile() 2 failed: %s' % (pretty, str(e)))
        return False
    if 'serial' not in result:
        print('FAIL %s: not a handset profile: %s' % (pretty, result))
        return False

    return True

# check that the session rejects resource manipulation after the resource has
# been yielded.
@setup.factory()
def t8(factory):
    pretty = '%s t8' % __file__
    print(pretty)

    broker = factory.make_master('master')
    w,h = broker.get_resource({'type':'workspace'}, {'type':'handset'})

    # first manipulation should succeed. second manipulation should fail
    try:
        profile = h.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile() failed: %s' % (pretty, str(e)))
        return False
    # yield the resource and do the second manipulation
    try:
        broker.yield_resources(h, w)
    except Exception, e:
        print('FAIL %s: yield_resources() failed: %s' % (pretty, str(e)))
        return False
    try:
        w.get_profile()
        print('FAIL %s: workspace.get_profile() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('no such resource'):
            print('FAIL %s: wrong error message 1: %s' % (pretty, str(e)))
            return False
    try:
        h.get_profile()
        print('FAIL %s: handset.get_profile() did not fail' % pretty)
        return False
    except Exception, e:
        if not (str(e).startswith('no such resource')
        and     re.search(profile['serial'], str(e))):
            print('FAIL %s: wrong error message 2: %s' % (pretty, str(e)))
            return False

    return True

# like t7, but make multiple manipulations
@setup.brokers([], 'master', [], True, False)
def t9(HOME, broker):
    pretty = '%s t9' % __file__
    print(pretty)

    w,h = broker.get_resource({'type':'workspace'}, {'type':'handset'})

    # get the workspace's profile multiple times
    for i in range(5):
        try:
            w.get_profile()
        except Exception, e:
            print('FAIL %s: get workspace %d failed: %s' % (pretty, i, str(e)))
            return False

    # get the handset's profile multiple times
    for i in range(5):
        try:
            h.get_profile()
        except Exception, e:
            print('FAIL %s: get handset %d failed: %s' % (pretty, i, str(e)))
            return False

    return True

# check that the client can garbage collect resources without destroying the
# remote session.
# the original problem that motivated this test: the call to w.get_profile() (or
# any other resource method) causes a connection to be established between the
# client and the session object that the broker created. then, when the object
# 'w' is deleted, the connection gets closed automatically. the session sees
# this as a lost master connection and kills itself. the call to d.get_profile()
# then fails because the session is dead.
# a better behavior for the session is to simply remove lost connections and let
# the broker decide when to close the session. this can be depended on because
# the broker will be notified when a client closes its connection to the broker.
# the broker can then reclaim resources with impunity.
@setup.brokers([], 'master', [], True, False)
def t10(HOME, broker):
    pretty = '%s t10' % __file__
    print(pretty)

    w,d = broker.get_resource({'type':'workspace'}, {'type':'handset'})
    w.get_profile() # throw away response. the important part is to make sure
    # that the connection has been established.
    del(w) # causes the connection to the remote session to be torn down
    try:
        result = d.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile() failed: %s' % (pretty, str(e)))
        return False

    if result['type'] != 'handset':
        print('FAIL %s: result is wrong: %s' % (pretty, result))
        return False

    return True

# like t10 but doing it many times in a loop so that Python's built in garbage
# collector closes the session connections
@setup.brokers([], 'master', [], True, False)
def t11(HOME, broker):
    pretty = '%s t11' % __file__
    print(pretty)

    for i in range(5):
        w,d = broker.get_resource({'type':'workspace'}, {'type':'handset'})
        try:
            w.get_profile()
        except Exception, e:
            print('FAIL %s: first get_profile() failed: %s' % (pretty, str(e)))
            return False
        try:
            d.get_profile()
        except Exception, e:
            print('FAIL %s: second get_profile() failed: %s' % (pretty, str(e)))
            return False
        broker.yield_resources(w,d)

    return True

# check that non-ASCII characters in implicitly typed AveException messages
# do not hang the control
@setup.session()
def t12(session, remote):
    pretty = '%s t12' % __file__
    print(pretty)

    try:
        remote.raise_exception('åäö')
        print('FAIL %s: no exception raised' % pretty)
        return False
    except AveException, e:
        if e.message.encode('utf8') != 'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that non-ASCII characters in explicitly typed AveException messages
# do not hang the control
@setup.session()
def t13(session, remote):
    pretty = '%s t13' % __file__
    print(pretty)

    try:
        remote.raise_ave_exception('åäö')
        print('FAIL %s: no exception raised' % pretty)
        return False
    except AveException, e:
        if e.message.encode('utf8') != 'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that non-ASCII characters in Exit messages do not hang the control
@setup.session()
def t14(session, remote):
    pretty = '%s t14' % __file__
    print(pretty)

    try:
        remote.raise_exit('åäö')
        print('FAIL %s: no exception raised' % pretty)
        return False
    except Exit, e:
        if str(e) != 'åäö':
            print('FAIL %s: wrong error message: "%s"' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong error type: %s' % (pretty, type(e)))
        return False

    return True

# check that making invalid remote calls with non-ASCII characters in the call
# does not hang the control
@setup.session()
def t15(session, remote):
    pretty = '%s t15' % __file__
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
