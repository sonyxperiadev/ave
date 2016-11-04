# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import time
import socket
import traceback

from ave.network.control    import Control
from ave.broker._broker     import *
from ave.network.connection import *
from ave.broker.session     import Exit, RemoteSession
from ave.broker.allocator   import LocalAllocator
from ave.broker.profile     import *

import setup

# check that basic remote allocation works
@setup.brokers(['forwarder'], 'master', [], True, False)
def t1(HOME, master, forwarder):
    pretty = '%s t1' % __file__
    print(pretty)

    # try to get pretty:mary twice from the local broker. the first should be
    # locally allocated, the second should be remotely allocated.
    h1 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})
    h2 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})

    p1 = h1.get_profile()
    if p1['serial'] != 'forwarder-1':
        print('FAIL %s: wrong local serial: %s' % (pretty, p1))
        return False

    p2 = h2.get_profile()
    if p2['serial'] != 'master-1':
        print('FAIL %s: wrong remote serial: %s' % (pretty, p2))
        return False

    return True

# check that the local session is killed off if a remote allocation fails
@setup.brokers(['forwarder'], 'master', [], True, False)
def t2(HOME, master, forwarder):
    pretty = '%s t2' % __file__
    print(pretty)

    h1 = forwarder.get_resources({'type':'handset', 'serial': 'forwarder-2'})
    try:
        h2 = forwarder.get_resources({'type':'handset', 'serial':'no-such'})
        print('FAIL %s: second allocation succeeded' % pretty)
    except Exception, e:
        if not str(e).startswith('no such resource'):
            print('FAIL %s: wrong error message 1: %s' % (pretty, str(e)))
            return False

    # check that the local session is now inaccessible
    try:
        h1.get_profile()
        print('FAIL %s: local session still accessible' % pretty)
        return False
    except Exception, e:
        if str(e) not in ['connection refused', 'connection closed']:
            print('FAIL %s: wrong error message 2: %s' % (pretty, str(e)))
            return False

    return True

# check that local session is killed off if the remote session dies
@setup.brokers(['forwarder'], 'master', [], True, False)
def t3(HOME, master, forwarder):
    pretty = '%s t3' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})
    h2 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})

    # crash the remote session
    r2 = RemoteSession(h2.address, h2.authkey, timeout=h2.timeout)
    try:
        r2.crash()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    time.sleep(1) # session death is asynchronous. allow for time to die

    try:
        h1.get_profile()
        print('FAIL %s: local session still accessible' % pretty)
    except ConnectionRefused:
        pass # good
    except socket.error:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return False

    return True

# like t3 but connection has already been established to local session when the
# remote session gets killed.
@setup.brokers(['forwarder'], 'master', [], True, False)
def t4(HOME, master, forwarder):
    pretty = '%s t4' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})
    h2 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})

    msg = h1.get_profile() # establishes connection

    # crash the remote session
    r2 = RemoteSession(h2.address, h2.authkey, timeout=h2.timeout)
    try:
        r2.crash()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    time.sleep(1) # session death is asynchronous. allow for time to die

    try:
        h1.get_profile()
        print('FAIL %s: local session still accessible' % pretty)
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return False

    return True

# check that remote session is killed off if the local session dies
@setup.brokers(['forwarder'], 'master', [], True, False)
def t5(HOME, master, forwarder):
    pretty = '%s t5' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})
    h2 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})

    # crash the local session
    r1 = RemoteSession(h1.address, h1.authkey, timeout=h1.timeout)
    try:
        r1.crash()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    time.sleep(1) # session death is asynchronous. allow for time to die
    try:
        h2.get_profile()
        print('FAIL %s: remote session still accessible' % pretty)
    except ConnectionRefused:
        pass # good
    except socket.error:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
        return False

    return True

# like t5 but connection has already been established to remote session when
# the local session gets killed
@setup.brokers(['forwarder'], 'master', [], True, False)
def t6(HOME, master, forwarder):
    pretty = '%s t6' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})
    h2 = forwarder.get_resources({'type':'handset', 'pretty':'mary'})

    msg = h2.get_profile()

    # crash the local session
    r1 = RemoteSession(h1.address, h1.authkey, timeout=h1.timeout)
    try:
        r1.crash()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    time.sleep(1) # session death is asynchronous. allow for time to die

    try:
        h2.get_profile()
        print('FAIL %s: remote session still accessible' % pretty)
    except ConnectionClosed:
        pass # good
    except socket.error:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, (e)))
        return False

    return True

# set up a longer forwarding chain and check that this works like one with only
# two links
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t7(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t7' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    # crash the last session in the chain
    r3 = RemoteSession(h3.address, h3.authkey, timeout=h3.timeout)
    try:
        r3.crash()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    time.sleep(3) # session death is asynchronous. allow for time to die

    try:
        h1.get_profile()
        print('FAIL %s: local session still accessible' % pretty)
    except (ConnectionClosed, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 1: %s' % (pretty, (e)))
        return False

    try:
        h2.get_profile()
        print('FAIL %s: remote session still accessible' % pretty)
    except (ConnectionClosed, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 2: %s' % (pretty, (e)))
        return False

    return True

# check that resources from different brokers have different session addresses
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t8(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t8' % __file__
    print(pretty)

    # get local and remote resources
    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    # check that the resources are held by different sessions
    if (h1.address == h2.address
    or  h1.address == h3.address
    or  h2.address == h3.address):
        print(
            'FAIL %s: session addresses are the same: %s'
            % (pretty, h1.address, h2.address, h3.address)
        )
        return False

    return True

# check that resources from the same remote broker have the same session address
@setup.brokers(['forwarder'], 'master', [], True, False)
def t9(HOME, master, forwarder):
    pretty = '%s t9' % __file__
    print(pretty)

    # get remote resources
    h1 = forwarder.get_resources({'type':'handset', 'serial':'master-1'})
    h2 = forwarder.get_resources({'type':'handset', 'serial':'master-2'})
    h3 = forwarder.get_resources({'type':'handset', 'serial':'master-3'})

    # check that the resources are held by the same session
    if (h1.address != h2.address
    or  h1.address != h3.address
    or  h2.address != h3.address):
        print(
            'FAIL %s: session addresses are not the same: %s'
            % (pretty, h1.address, h2.address, h3.address)
        )
        return False

    return True

# check that interleaved allocations to different clients work
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t10(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t10' % __file__
    print(pretty)

    # get 'jane' directly from the middle broker so that it's taken when the
    # last broker forwards its second request
    h2 = forwarder_a.get_resources({'type':'handset', 'pretty':'jane'})

    # get the first and last 'jane' through the last broker
    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    # check that the resources are held by different sessions
    if (h1.address == h2.address
    or  h1.address == h3.address
    or  h2.address == h3.address):
        print(
            'FAIL %s: session addresses are the same: %s'
            % (pretty, h1.address, h2.address, h3.address)
        )
        return False

    return True

# like t10 but also yield h2 after forwarder_b allocated h1 and h3, then let
# forwarder_b allocate h2
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t11(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t11' % __file__
    print(pretty)

    # get 'jane' directly from the middle broker so that it's taken when the
    # last broker forwards its second request
    h2 = forwarder_a.get_resources({'type':'handset', 'pretty':'jane'})

    # get the first and last 'jane' through the last broker
    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    # yield h2
    forwarder_a.yield_resources(h2)

    # check that the second 'jane' is now available through the last broker
    try:
        h2 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    except Exception, e:
        print('FAIL %s: could not allocate after yield: %s' % (pretty, str(e)))
        return False

    return True

# check that all sessions on all brokers are terminated if one of the brokers
# terminate
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t12(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t12' % __file__
    print(pretty)

    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    try:
        forwarder_a = RemoteBroker(
            forwarder_a.address, authkey='admin_key', home=HOME.path
        )
        forwarder_a.interrupt()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 1: %s' % (pretty, str(e)))
        return False

    time.sleep(2) # give session death some time to spread among brokers

    try:
        print h1.get_profile()
    except (ConnectionClosed, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 2: %s' % (pretty, str(e)))
        return False
    try:
        print h2.get_profile()
    except (ConnectionClosed, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 3: %s' % (pretty, str(e)))
        return False
    try:
        print h3.get_profile()
    except (ConnectionClosed, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception 4: %s' % (pretty, str(e)))
        return False

    return True

# check that the error message is correct when trying to allocate equipment
# that doesn't exist *and* the referenced remote broker is unavailable. i.e.
# the broker's configuration file says there is a remote master but there
# is actually not one up and running.
@setup.brokers(['forwarder'], 'master', [], True, False)
def t13(HOME, master, forwarder):
    pretty = '%s t13' % __file__
    print(pretty)

    # stop the second broker to get the situation described above
    try:
        master.stop()
    except ConnectionClosed:
        pass # good

    try:
        h = forwarder.get({'type':'handset', 'pretty':'betty boop'})
        print('FAIL %s: allocation did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('Broker connection failed'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# yield forwarded allocations
@setup.brokers(['forwarder-a', 'forwarder-b'], 'master', [], True, False)
def t14(HOME, master, forwarder_a, forwarder_b):
    pretty = '%s t14' % __file__
    print(pretty)

    # get all 'jane' resources through the last forwarder
    h1 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = forwarder_b.get_resources({'type':'handset', 'pretty':'jane'})

    # yield and re-allocate each resource through the last forwarder
    for resource in [h1, h2, h3]:
        profile = resource.get_profile()
        try:
            forwarder_b.yield_resources(resource)
        except Exception, e:
            print('FAIL %s: yielding %s failed: %s' % (pretty, profile, str(e)))
            return False
        try:
            h1 = forwarder_b.get_resources(profile)
        except Exception, e:
            print('FAIL %s: allocating %s failed: %s' % (pretty,profile,str(e)))
            return False

    return True


# check that making new connections to the brokers works

# allocate remote stacks

# should a broker's death affect sessions it created?
