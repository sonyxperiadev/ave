# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import time
import traceback

from ave.network.connection import find_free_port
from ave.network.control    import Control
from ave.broker._broker     import Broker, RemoteBroker
from ave.broker.allocator   import LocalAllocator
from ave.broker.profile     import HandsetProfile, RelayProfile

import setup

# check that a shared stack becomes visible in the master broker
@setup.brokers([], 'master', ['slave'], False, True)
def t1(HOME, master, slave):
    pretty = '%s t1' % __file__
    print(pretty)

    stacks = master.list_stacks()
    if stacks != []:
        print('FAIL %s: master has stacks before sharing: %s' % (pretty,stacks))
        return False

    expected = slave.list_stacks()
    if len(expected) != 4:
        print('FAIL %s: slave has wrong number of stacks: %s'%(pretty,expected))

    slave.start_sharing()
    time.sleep(1)
    stacks = master.list_stacks()
    if stacks != expected:
        print('FAIL %s: master has wrong stacks: %s' % (pretty, stacks))
        return False

    return True

# allocate devices from the same stack
@setup.brokers([], 'master', ['slave'], True, True)
def t2(HOME, master, slave):
    pretty = '%s t2' % __file__
    print(pretty)

    time.sleep(1)
    try:
        h,r = master.get_resources({'type':'handset'}, {'type':'relay'})
    except Exception, e:
        print('FAIL %s: allocation failed: %s' % (pretty, str(e)))
        return False

    return True

# try to allocate two devices together, but from different stacks
@setup.brokers([], 'master', ['slave'], True, True)
def t3(HOME, master, slave):
    pretty = '%s t3' % __file__
    print(pretty)

    time.sleep(1)
    try:
        h,r = master.get_resources(
            {'type':'handset', 'serial':'3'},
            {'type':'relay',   'uid'   :'a'}
        )
        print('FAIL %s: allocation did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('cannot allocate all equipment together'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that unrequested devices in a stack are marked as collateral when other
# devices from the same stack have been requested
@setup.brokers([], 'master', ['slave'], True, True)
def t4(HOME, master, slave):
    pretty = '%s t4' % __file__
    print(pretty)

    time.sleep(1)
    h = master.get_resources({'type':'handset', 'serial':'slave-2'})

    # the slave's allocation should include two relays as collateral because
    # all stacks that contain the handset do so
    collateral = slave.list_collateral_all()
    if len(collateral) != 2:
        print('FAIL %s: wrong amount of collateral: %s' % (pretty, collateral))
        return False

    if {'type':'relay', 'uid':'slave-a'} not in collateral:
        print('FAIL %s: wrong collateral 1: %s' % (pretty, collateral))
        return False

    if {'type':'relay', 'uid':'slave-b'} not in collateral:
        print('FAIL %s: wrong collateral 2: %s' % (pretty, collateral))
        return False

    available = master.list_available()
    for c in collateral:
        if c in available:
            print('FAIL %s: %s still available: %s' % (pretty, c, available))
            return False

    return True

# check that all resources, including colllateral, are freed when the client
# disconnects
@setup.brokers([], 'master', ['slave'], True, True)
def t5(HOME, master, slave):
    pretty = '%s t5' % __file__
    print(pretty)

    time.sleep(1)
    expected = master.list_available()

    for i in range(3):
        b = RemoteBroker(master.address, home=HOME.path)
        try:
            h,r = b.get_resource({'type':'handset'}, {'type':'relay'})
        except Exception, e:
            print('FAIL %s: allocation %d failed: %s' % (pretty, i, str(e)))
            return False

        # disconnect from the master, causing the slave broker to free all
        # resources allocated to the client. then wait for the resources to
        # become available again.
        del b

        for j in range(10):
            found_all = True # let's be optimistic
            available = master.list_available()
            for e in expected:
                if e not in available:
                    found_all = False
            if found_all:
                break
            time.sleep(0.3)

        if not found_all:
            print('FAIL %s: some resources not re-added: %s'%(pretty,available))
            return False

    return True

# check that two allocations may share collateral.
# for instance, allocating relay a will cause handsets 1 and 2 to be marked as
# collateral. allocating relay b (which is not marked as collateral for any
# other allocation) will cause handset 2 and 3 to be marked as collateral. the
# common collateral (handset 2) will be used by none, which is why it is ok to
# share it.
#     stack 0  :  [ relay a, handset 1 ]
#     stack 1  :  [ relay a, handset 2 ]
#     stack 2  :  [ relay b, handset 2 ]
#     stack 3  :  [ relay b, handset 3 ]
@setup.brokers([], 'master', ['slave'], True, True)
def t6(HOME, master, slave):
    pretty = '%s t6' % __file__
    print(pretty)

    time.sleep(1)
    r0 = master.get_resource({'type':'relay', 'uid':'slave-a'})
    try:
        r1 = master.get_resource({'type':'relay', 'uid':'slave-b'})
    except Exception, e:
        print('FAIL %s: second allocation failed: %s' % (pretty, str(e)))
        return False

    return True

# check that stacked equipment can be matched against properties that are not
# visible in the stack, but are in the equipment's full profile
@setup.brokers([], 'master', ['slave'], True, True)
def t7(HOME, master, slave):
    pretty = '%s t7' % __file__
    print(pretty)

    time.sleep(1)
    try:
        r,h = master.get_resource(
            {'type':'relay', 'pretty':'gustav'},
            {'type':'handset', 'pretty':'mary'}
        )
    except Exception, e:
        print('FAIL %s: allocation failed: %s' % (pretty, str(e)))
        return False

    try:
        r,h = master.get_resource(
            {'type':'relay', 'pretty':'vasa'},
            {'type':'handset', 'pretty':'jane'} # collateral of first allocation
        )
        print('FAIL %s: impossible allocation succeeded' % pretty)
        return False
    except Exception, e:
        if e.message != 'cannot allocate all equipment together':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that the relay circuits can be matched while also requesting a handset
@setup.brokers([], 'master', ['slave'], True, True)
def t8(HOME, master, slave):
    pretty = '%s t8' % __file__
    print(pretty)

    time.sleep(1)
    r,h = master.get_resource(
        {'type':'relay', 'circuits':['handset.battery']},
        {'type':'handset'}
    )
    p = r.get_profile()
    e = {
        u'type'       : u'relay',
        u'uid'        : u'slave-b',
        u'circuits'   : { u'handset.battery':2 },
        u'power_state': u'online'
    }
    if p != e:
        print('FAIL %s: wrong relay profile: %s' % (pretty, p))
        return False

    return True
