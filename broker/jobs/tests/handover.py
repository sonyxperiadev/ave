# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import json
import time
import traceback

from ave.network.process    import Process
from ave.network.exceptions import *
from ave.broker._broker     import validate_serialized, RemoteBroker, Broker
from ave.broker.session     import RemoteSession
from ave.broker.exceptions  import *

import setup

# check that a broker with trivial allocations can have its state serialized
@setup.brokers([],'master',[],False,False)
def t1(HOME, master):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        s = master.serialize()
    except Exception, e:
        print('FAIL %s: trivial serialization failed: %s' % (pretty, str(e)))
        return False

    try:
        validate_serialized(s)
    except Exception, e:
        print('FAIL %s: could not validate adoption: %s' % (pretty, str(e)))
        return False

    return True

# like t1 but with some allocations
@setup.brokers([],'master',[],False,False)
def t2(HOME, master):
    pretty = '%s t2' % __file__
    print(pretty)

    c1 = RemoteBroker(master.address, authkey=master.authkey, home=HOME.path)
    c1.get_resources({'type':'handset'}, {'type':'workspace'})

    c2 = RemoteBroker(master.address, authkey=master.authkey, home=HOME.path)
    c2.get_resources({'type':'handset'}, {'type':'relay'})

    try:
        s = master.serialize()
    except Exception, e:
        print('FAIL %s: trivial serialization failed: %s' % (pretty, str(e)))
        return False

    try:
        validate_serialized(s)
    except Exception, e:
        print('FAIL %s: could not validate adoption: %s' % (pretty, str(e)))
        return False

    return True

# trivial handover between two brokers: no allocations. more or less just check
# that the takeover can be started on the same port as the handover and that
# configuration data is the same
@setup.factory()
def t3(factory):
    pretty = '%s t3' % __file__
    print(pretty)

    handover = factory.make_master('master')
    adoption,config,fdtx_path = handover.begin_handover() # stops listening
    try:
        takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    except Exception, e:
        print('FAIL %s: could not start takeover: %s' % (pretty, str(e)))
        return False
    try:
        handover.end_handover(1)
    except ConnectionClosed:
        pass
    except Exception, e:
        print('FAIL %s: unexpected error: %s' % (pretty, str(e)))
        return False

    # compare the config and serialization of the two
    c = takeover.get_config()
    if c != config:
        print('FAIL %s: configuration mismatch: %s != %s' % (pretty, c, config))
        return False

    return True

# make a few allocations, then handover. check that both brokers show the same
# availability of equipment
@setup.factory()
def t4(factory):
    pretty = '%s t4' % __file__
    print(pretty)

    handover = factory.make_master('master')
    avail_1  = handover.list_available()

    # make some allocations
    c1      = RemoteBroker(handover.address, home=factory.HOME.path)
    h1,w1   = c1.get_resources({'type':'handset'}, {'type':'workspace'})
    avail_2 = handover.list_available()
    c2      = RemoteBroker(handover.address, home=factory.HOME.path)
    h2,r2   = c2.get_resources({'type':'handset'}, {'type':'relay'})
    avail_3 = handover.list_available()

    # hand over
    adoption,config,fdtx_path = handover.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    # check that availability is correct. stop the sessions started against the
    # handover and check that the resources become availabe in the takeover
    result = takeover.list_available()
    if len(result) != len(avail_3):
        print('FAIL %s: wrong avail 3: %s != %s' % (pretty, result, avail_3))
        return False

    ok = False
    del(c2)
    for i in range(10): # allow some time for brokers to detect session death
        result = takeover.list_available()
        if len(result) == len(avail_2):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: wrong avail 2: %s != %s' % (pretty, result, avail_2))
        return False

    ok = False
    del(c1)
    for i in range(10): # allow some time for brokers to detect session death
        result = takeover.list_available()
        if len(result) == len(avail_1):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: wrong avail 1: %s != %s' % (pretty, result, avail_2))
        return False

    return True

# kill off one of the original sessions during the handover and check that the
# associated resources become available in the takeover
@setup.factory()
def t5(factory):
    pretty = '%s t5' % __file__
    print(pretty)

    handover = factory.make_master('master')
    avail_1  = handover.list_available()

    # make some allocations
    c1      = RemoteBroker(handover.address, home=factory.HOME.path)
    h1,w1   = c1.get_resources({'type':'handset'}, {'type':'workspace'})
    avail_2 = handover.list_available()
    c2      = RemoteBroker(handover.address, home=factory.HOME.path)
    h2,r2   = c2.get_resources({'type':'handset'}, {'type':'relay'})
    avail_3 = handover.list_available()

    adoption,config,fdtx_path = handover.begin_handover()
    session = RemoteSession(h2.address, h2.authkey)
    try:
        session.crash() # kill the second session during the handover
    except ConnectionClosed:
        pass
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    result = takeover.list_available()
    if len(result) != len(avail_2):
        print('FAIL %s: wrong avail: %s != %s' % (pretty, result, avail_2))
        return False

    return True

# make sure one of the sessions is super busy during the handover so that it
# cannot engage in communication with the takeover during session adoption
@setup.factory()
def t6(factory):
    pretty = '%s t6' % __file__
    print(pretty)

    handover = factory.make_master('master')
    avail    = handover.list_available()

    def oob_client(address):
        r = RemoteBroker(address, home=factory.HOME.path)
        h,w = r.get_resources({'type':'handset'}, {'type':'workspace'})
        w.run('sleep 3') # right, extremely busy, but it prevents other action
        while True:
            time.sleep(1) # don't let client die and loose all resources

    p = Process(target=oob_client, args=(handover.address,))
    p.start()

    # make sure the oob client has gotten its resources
    ok = False
    for i in range(10):
        if len(handover.list_available()) != len(avail):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: catastrophic' % pretty)

    adoption,config,fdtx_path = handover.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    result = True
    if len(takeover.list_available()) == len(avail):
        print('FAIL %s: wrong avail: %s' % (pretty, avail))
        result = False

    p.terminate()
    p.join()

    return result

# check that resources of super busy sessions are reclaimed when the session
# finally dies
@setup.factory()
def t7(factory):
    pretty = '%s t7' % __file__
    print(pretty)

    handover = factory.make_master('master')
    avail    = handover.list_available()

    def oob_client(address):
        r = RemoteBroker(address, home=factory.HOME.path)
        h,w = r.get_resources({'type':'handset'}, {'type':'workspace'})
        w.run('sleep 2') # right, extremely busy, but it prevents other action

    p = Process(target=oob_client, args=(handover.address,))
    p.start()

    # make sure the oob client has gotten its resources
    ok = False
    for i in range(10):
        if len(handover.list_available()) != len(avail):
            ok = True
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: catastrophic' % pretty)
        p.terminate()
        p.join()
        return False

    adoption,config,fdtx_path = handover.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    # now wait for the client to die, so that its session dies, so that
    # the takeover detects this, so that the associated resouces can be reclaimed,
    # so that the takeover's availability is the same as when we started
    ok = False
    for i in range(10):
        if len(takeover.list_available()) == len(avail):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: super busy session not tracked correctly' % pretty)

    p.terminate()
    p.join()

    return ok

# check that sessions survive multiple broker restarts
@setup.factory()
def t8(factory):
    pretty = '%s t8' % __file__
    print(pretty)

    original = factory.make_master('master')
    avail    = original.list_available()

    def oob_client(address):
        r = RemoteBroker(address, home=factory.HOME.path)
        h,w = r.get_resources({'type':'handset'}, {'type':'workspace'})
        while True:
            time.sleep(1)

    p = Process(target=oob_client, args=(original.address,))
    p.start()

    # make sure the oob client has gotten its resources
    ok = False
    for i in range(10):
        if len(original.list_available()) != len(avail):
            ok = True
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: catastrophic' % pretty)
        p.terminate()
        p.join()
        return False

    # do two handovers in a row
    adoption,config,fdtx_path = original.begin_handover()
    interim = factory.make_takeover('master', adoption, config, fdtx_path)
    original.end_handover(1)

    adoption,config,fdtx_path = interim.begin_handover()
    final = factory.make_takeover('master', adoption, config, fdtx_path)
    interim.end_handover(1)

    # check that all brokers have the same availability
    a1 = original.list_available()
    a2 = interim.list_available()
    a3 = final.list_available()
    if len(a1) != len(a2) != len(a3):
        print(
            'FAIL %s: a handover failed somewhere: %s != %s != %s'
            % (pretty, a1, a2, a3)
        )
        p.terminate()
        p.join()
        return False

    # kill the client so that the brokers reclaim the equipment
    p.terminate()
    p.join()

    ok = False
    for i in range(10):
        a3 = final.list_available()
        if len(a3) == len(avail):
            ok = True
            break
    if not ok:
        print(
            'FAIL %s: wrong availability: %d %d %d %d'
            % (pretty, len(a1), len(a2), len(a3), len(avail))
        )
        return False

    # check that the original and interim brokers have terminated now that they
    # don't have any sessions with allocations
    try:
        original.ping() # ping
    except Exit, e:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False
    try:
        interim.ping() # ping
    except Exit, e:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

# check that clients still attached to the handover get Restarting exceptions
# when they try to allocate after the handover has been done. this *can* be
# fixed so that clients migrate automatically, but it is difficult and I would
# prefer to not implement it unless there a strong case can be made for it
@setup.factory()
def t9(factory):
    pretty = '%s t9' % __file__
    print(pretty)

    handover = factory.make_master('master')
    client   = RemoteBroker(handover.address, home=factory.HOME.path)

    # make first allocation
    h,w = client.get_resources({'type':'handset'}, {'type':'workspace'})

    # hand over
    adoption,config,fdtx_path = handover.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    # make seconc allocation
    try:
        client.get({'type':'handset'})
        print('FAIL %s: second allocation did not fail' % pretty)
        return False
    except Restarting:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

# check that a restarted share shows up again in its master
@setup.factory()
def t10(factory):
    pretty = '%s t10' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share')
    share.start_sharing()
    time.sleep(1)

    client = RemoteBroker(address=master.address, home=factory.HOME.path)
    h = client.get_resources({'type':'handset', 'serial':'share-1'})
    a1 = master.list_available()

    # restart the share
    adoption,config,fdtx_path = share.begin_handover()
    takeover = factory.make_takeover('share', adoption, config, fdtx_path)

    a2 = master.list_available()
    if len(a1) == len(a2):
        print('FAIL %s: shared resources still visible: %s' % (pretty, a2))
        return False

    # finish the handover so that takeover can start accepting RPC's. then
    # check that the master sees all equipment except the one allocated
    share.end_handover(1)
    ok = False
    for i in range(10):
        a3 = master.list_available()
        if len(a3) == len(a1):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: wrong availability: %s' % (pretty, a3))
        return False
    for profile in a3:
        if 'serial' in profile and profile['serial'] == 'share-1':
            print('FAIL %s: busy equipment shared' % pretty)
            return False

    # finally check that the resource can still be manipulated
    try:
        p = h.get_profile()
        if p['serial'] != 'share-1':
            print('FAIL %s: wrong profile: %s' % (pretty, p))
            return False
    except Exception, e:
        print('FAIL %s: unexpected error: %s' % (pretty, e))
        return False

    return True

# check that shares reconnect to a restarted master
@setup.factory()
def t11(factory):
    pretty = '%s t11' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share')
    share.start_sharing()
    time.sleep(1)

    client = RemoteBroker(address=master.address, home=factory.HOME.path)
    h1 = client.get_resources({'type':'handset', 'serial':'share-1'})
    h2 = client.get_resources({'type':'handset', 'serial':'master-1'})
    a1 = master.list_available()

    # restart the master
    adoption,config,fdtx_path = master.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    master.end_handover(1)

    # connect to the new master and check the availability again
    master = RemoteBroker(address=master.address, home=factory.HOME.path)
    ok = False
    for i in range(10):
        a2 = master.list_available()
        if len(a2) == len(a1):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: wrong availability: %s' % (pretty, a2))
        return False
    for profile in a2:
        if 'serial' in profile and profile['serial'] == 'share-1':
            print('FAIL %s: busy equipment shared' % pretty)
            return False

    return True

# check that .end_handover() doesn't time out even if the takeover did not get
# any sessions to adopt. regression test
@setup.factory()
def t12(factory):
    pretty = '%s t12' % __file__
    print(pretty)

    master = factory.make_master('master')
    adoption,config,fdtx_path = master.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)

    try:
        master.end_handover(1)
    except ConnectionClosed:
        pass
    except Exception, e:
        print('FAIL %s: unexpected error: %s' % (pretty, e))
        return False

    return True

# check that the handover exits when the last session terminates
@setup.factory()
def t13(factory):
    pretty = '%s t13' % __file__
    print(pretty)

    handover = factory.make_master('master')

    # make some sessions
    c1      = RemoteBroker(handover.address, home=factory.HOME.path)
    h1,w1   = c1.get_resources({'type':'handset'}, {'type':'workspace'})
    avail_2 = handover.list_available()
    c2      = RemoteBroker(handover.address, home=factory.HOME.path)
    h2,r2   = c2.get_resources({'type':'handset'}, {'type':'relay'})
    avail_3 = handover.list_available()

    adoption,config,fdtx_path = handover.begin_handover()
    takeover = factory.make_takeover('master', adoption, config, fdtx_path)
    handover.end_handover(1)

    # crash the sessions
    session = RemoteSession(h1.address, h1.authkey)
    try:
        session.crash()
    except ConnectionClosed:
        pass
    session = RemoteSession(h2.address, h2.authkey)
    try:
        session.crash()
    except ConnectionClosed:
        pass

    for i in range(10): # wait until only one session remains, then close it
        authkeys = handover.get_session_authkeys()
        if len(authkeys) == 1:
            break
        time.sleep(0.3)

    # check that the handover sends its exit message when the last session is
    # closed
    try:
        handover.close_session(authkeys[0])
    except Exit, e:
        if str(e) != 'broker restarted. please reconnect':
            print('FAIL %s: wrong exit message: %s' % (pretty, str(e)))
            return False
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    try:
        handover.ping() # ping
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True
