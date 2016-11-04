# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import json
import traceback

from ave.exceptions import AveException

from ave.network.connection import find_free_port
from ave.network.control    import Control
from ave.network.exceptions import ConnectionTimeout, ConnectionRefused
from ave.broker._broker     import Broker, RemoteBroker
from ave.broker.allocator   import LocalAllocator
from ave.broker.profile     import HandsetProfile
from ave.broker.notifier    import RemoteNotifier

import setup
# Convenience methods

def verify_allocators_on_broker(pretty, broker, expected_nr_of_allocators):
    for i in range(10): # wait for non-local allocator to appear
        allocators = broker.list_allocators()
        if len(allocators) >= expected_nr_of_allocators:
            break
        time.sleep(0.3)
    if len(allocators) < expected_nr_of_allocators:
        print('FAIL %s:Nr of allocators on broker: %d, expected %d' %
              (pretty, len(allocators), expected_nr_of_allocators))
        return False
    return True


# let a slave add resources to a master. then check that the shared resources
# show up in list_equipment() on the master.
#brokers([], 'master', ['slave'], False, False)
#def t1(HOME, master, slave):
@setup.factory()
def t1(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    master = factory.make_master('master')
    slave  = factory.make_share(master, 'slave', True)
    time.sleep(1)

    r1 = master.list_equipment()
    r2 = slave.list_equipment()

    result = master.list_equipment()

    # check that all items from r1 are in result
    for item in r1:
        if item not in result:
            print('FAIL %s: r1 item %s not in result: %s' %(pretty,item,result))
            return False
    # check that all items from r2 are in result
    for item in r2:
        if item not in result:
            print('FAIL %s: r2 item %s not in result: %s' %(pretty,item,result))
            return False

    return True

# add slave resources to a master, allocate one of them, and check that both
# brokers thinks it's unavailable
@setup.factory()
def t2(factory):
    pretty = '%s t2' % __file__
    print(pretty)

    master = factory.make_master('master')
    slave  = factory.make_share(master, 'slave', True)
    time.sleep(1)

    r1 = master.list_equipment()
    r2 = slave.list_equipment()
    wanted = r2.pop()
    slave.start_sharing()
    time.sleep(1)
    handset = master.get(wanted)

    # check that wanted is not available from either broker

    if wanted in master.list_available():
        print('FAIL %s: allocated resource still available from master' %
              pretty)
        return False

    if wanted in slave.list_available():
        print('FAIL %s: allocated resource still available from slave' % pretty)
        return False

    profile = handset.get_profile()
    if profile != wanted:
        print('FAIL %s: allocation has wrong profile: %s' % (pretty, profile))
        return False

    return True

# like t2 but also "crash" the job by disconnecting from the master. then check
# that both brokers list the resource as available again
@setup.factory()
def t3(factory):
    pretty = '%s t3' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True)
    time.sleep(1)

    r1 = master.list_equipment()
    r2 = slave.list_equipment()

    wanted  = r2.pop()
    client  = RemoteBroker(master.address, home=factory.HOME.path)
    handset = client.get_resources(wanted)

    del client # drop connection to "crash" client. note that this would not
    # work if we had made the allocation with the master because it would not
    # get garbage collected until t3() returns.

    # check that wanted is available again from the master
    found = False
    for i in range(10):
        if master.list_available(wanted):
            found = True
            break
        time.sleep(0.3)
    if not found:
        print('FAIL %s: resource not available after job crash' % pretty)
        return False

    if wanted not in slave.list_available():
        print('FAIL %s: resource not available from slave' % pretty)
        return False

    return True

# yield remotely allocated resources one at a time
@setup.factory()
def t4(factory):
    pretty = '%s t4' % __file__
    print(pretty)

    master  = factory.make_master('master')
    slave_a = factory.make_share(master, 'slave-a', True)
    slave_b = factory.make_share(master, 'slave-b', True)
    time.sleep(1)

    # get all 'jane' resources through the master
    h1 = master.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = master.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = master.get_resources({'type':'handset', 'pretty':'jane'})

    # yield and re-allocate each resource through the master
    for resource in [h1, h2, h3]:
        profile = resource.get_profile()
        try:
            master.yield_resources(resource)
        except Exception, e:
            print('FAIL %s: yielding %s failed: %s' % (pretty, profile, str(e)))
            return False
        for i in range(10): # give share some time to readd yielded equipment
            if master.list_available(profile):
                break
            time.sleep(0.3)
        try:
            resource = master.get_resources(profile)
        except Exception, e:
            print('FAIL %s: allocating %s failed: %s' % (pretty,profile,str(e)))
            return False
        result = resource.get_profile()
        if result != profile:
            print('FAIL %s: allocated wrong resource: %s' % (pretty, result))
            return False

    return True

# yield remotely allocated resources all at once
@setup.factory()
def t5(factory):
    pretty = '%s t5' % __file__
    print(pretty)

    master  = factory.make_master('master')
    slave_a = factory.make_share(master, 'slave-a', True)
    slave_b = factory.make_share(master, 'slave-b', True)
    time.sleep(1)
    num_available = len(master.list_available())

    # get all 'jane' resources through the master
    h1 = master.get_resources({'type':'handset', 'pretty':'jane'})
    h2 = master.get_resources({'type':'handset', 'pretty':'jane'})
    h3 = master.get_resources({'type':'handset', 'pretty':'jane'})

    profiles = []
    profiles.append(HandsetProfile(h1.get_profile()))
    profiles.append(HandsetProfile(h2.get_profile()))
    profiles.append(HandsetProfile(h3.get_profile()))

    # yield and re-allocate each resource through the master
    try:
        master.yield_resources(h1, h2, h3)
    except Exception, e:
        print('FAIL %s: could not yield: %s' % (pretty, str(e)))
        return False
    time.sleep(1)

    # check that all 'jane' handsets are available through the master again
    available = master.list_available()
    for p in profiles:
        if p not in available:
            print('FAIL %s: not re-added: %s' % (pretty, p))
            return False
    if len(available) != num_available:
        print('FAIL %s: wrong available: %s' % (pretty, available))
        return False

    return True

# does slave eventually re-add to a master that is temporarily unavailable at
# the time of resource reclamation?
@setup.factory()
def t6(factory):
    pretty = '%s t6' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', False)

    # slave is configured to not start sharing automatically. set master to
    # immediately close all new connections. then let the slave start sharing.
    master.set_rejecting(True)
    slave.start_sharing()

    # check that master doesn't see the equipment
    for i in range(5):
        available = master.list_available()
        if available:
            print('FAIL %s: master sees equipment: %s' % (pretty, available))
            return False
        time.sleep(0.5)

    # set master back to normal mode and check that it receives the slave's
    # equipment list
    master.set_rejecting(False)

    # check that master still doesn't see the equipment
    expected = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })
    ok = False
    for i in range(10):
        available = master.list_available()
        if expected in available:
            ok = True
            break
        time.sleep(0.5)
    if not ok:
        print('FAIL %s: master does not see equipment: %s' % (pretty,available))
        return False

    return True

# does master detect when slave goes offline, removing associated resources?
@setup.brokers([], 'master', ['slave-a', 'slave-b'], True, True)
def t7(HOME, master, slave_a, slave_b):
    pretty = '%s t7' % __file__
    print(pretty)

    # stuff to expect online/offline
    h1 = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-a-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })
    h2 = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-b-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })

    # check that the master has the equipment before disconnecting the slaves
    time.sleep(1)
    available = master.list_available()
    for expected in [h1, h2]:
        if expected not in available:
            print('FAIL %s: wrong available: %s' % (pretty, available))
            return False

    # disconnect slave a from the master and wait for the master to detect this
    ok = False
    slave_a.stop_sharing()
    for i in range(10):
        if h1 not in master.list_available():
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: h1 still available' % pretty)
        return False

    if h2 not in master.list_available():
        print('FAIL %s: master lost h2' % pretty)
        return False

    return True

# similar to t7, but instead check that equipment goes online when the sharing
# is restarted
@setup.factory()
def t8(factory):
    pretty = '%s t8' % __file__
    print(pretty)

    factory.write_config('broker.json', json.dumps({'logging':False}))
    master  = factory.make_master('master')
    slave_a = factory.make_share(master, 'slave-a', True)
    slave_b = factory.make_share(master, 'slave-b', True)

    h1 = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-a-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })
    h2 = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-b-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })

    # wait for shared equipment to show up in master
    ok = False
    for i in range(10):
        available = master.list_available({'type':'handset'})
        if h1 in available and h2 in available:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: shared equipment not available' % pretty)
        return False

    # disconnect both slaves
    ok = False
    slave_a.stop_sharing()
    slave_b.stop_sharing()
    for i in range(10):
        available = master.list_available({'type':'handset'})
        if h1 not in available and h2 not in available:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        available = json.dumps(available, indent=2)
        print('FAIL %s: equipment still available: %s' % (pretty, available))
        return False

    # reconnect slave a and check that h1 goes online
    ok = False
    slave_a.start_sharing()
    for i in range(10):
        if h1 in master.list_available():
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: h1 not online' % pretty)
        return False

    if h2 in master.list_available():
        print('FAIL %s: h2 is online' % pretty)
        return False

    return True

# does slave discover that master goes offline and restart sharing from scratch?
@setup.brokers([], 'master', ['slave'], True, True)
def t9(HOME, master, slave):
    pretty = '%s t9' % __file__
    print(pretty)

    # expected equipment
    h1 = HandsetProfile({
        u'type'   : u'handset',
        u'product': u'bar',
        u'vendor' : u'foo',
        u'serial' : u'slave-1',
        u'pretty' : u'mary',
        u'sysfs_path' : '/',
        u'power_state': 'boot_completed',
        u'platform'   : 'android'
    })

    time.sleep(1)
    share = master.list_shares()[0]
    master.drop_share(share)

    # wait for the slave to reconnect and reshare
    ok = False
    for i in range(10):
        if h1 in master.list_available():
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: h1 not available' % pretty)
        return False

    return True

# does the notifier add more than once?
@setup.brokers([], 'master', ['slave'], True, True, stacking='clean')
def t10(HOME, master, slave):
    pretty = '%s t10' % __file__
    print(pretty)

    # expected equipment. all come from the slave
    available = master.list_available({'type':'handset'})

    allocated = []
    for a in available:
        allocated.append(master.get_resource(a))

    # check that nothing is available (all other equipment is collateral)
    check = master.list_available()
    if check != []:
        print('FAIL %s: equipment still available: %s' % (pretty, check))
        return False

    for a in allocated:
        master.yield_resources(a)

    # wait for the equipment to get readded
    ok = False
    for i in range(10):
        count = 0
        for a in available:
            if a in master.list_available():
                count += 1
        if count == len(available):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print(
            'FAIL %s: some equipment not available: %s'
            % (pretty, master.list_available())
        )
        return False

    return True

# like t10 but the master drops the share here and there
@setup.factory()
def t11(factory):
    pretty = '%s t11' % __file__
    print(pretty)

    master = factory.make_master('master', []) # no equipment
    slave  = factory.make_share(master, 'slave', True, stacking='clean')

    ok = False
    for i in range(10):
        if master.list_available({'type':'handset'}):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: share did not register' % pretty)
        return False

    share = master.list_shares()[0]

    # expected equipment. all come from the slave
    available = master.list_available({'type':'handset'})
    if not available:
        print('FAIL %s: no handsets available' % pretty)
        return False

    allocated = []
    for a in available:
        master.drop_share(share)
        ok = False
        for i in range(10): # give share some time to reconnect between drops
            if master.list_available(a):
                allocated.append(master.get_resource(a))
                ok = True
                break
            else:
                time.sleep(0.3)
        if not ok:
            print('FAIL %s: could not allocate %s' % (pretty, a))
            return False

    # check that nothing is available (all other equipment is collateral)
    check = master.list_available()
    if check != []:
        print('FAIL %s: equipment still available: %s' % (pretty, check))
        return False

    for a in allocated:
        master.drop_share(share)
        ok = False
        for i in range(10): # give share some time to reconnect between drops
            try:
                master.yield_resources(a)
                ok = True
                break
            except Exception, e:
                time.sleep(0.3)
        if not ok:
            print('FAIL %s: could not yield %s' % (pretty, a))
            return False

    # wait for the equipment to get readded
    ok = False
    for i in range(10):
        count = 0
        for a in available:
            if a in master.list_available():
                count += 1
        if count == len(available):
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print(
            'FAIL %s: some equipment not available: %s'
            % (pretty, master.list_available())
        )
        return False

    return True

# check that starting share that cannot find master does not crash
def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    def make_slave(master_address, prefix, HOME):
        sock, port = find_free_port()
        handsets   = setup.make_handsets(prefix)
        config     = {
            'host':'', 'port':master_address[1],
            'policy':'share', 'authkey':u'share_key'
        }
        ws_cfg     = {
            'root':os.path.join(HOME.path, prefix),
            'env':[],'tools':{},'pretty':prefix
        }
        broker = setup.MockBroker(
            ('',port), sock, config, handsets, [], [], None, ws_cfg,
            None, None, [], True, home=HOME.path
        )
        remote = setup.RemoteSlaveBroker(
            address=('',port), authkey='admin_key', home=HOME.path
        )
        return broker, remote

    try:
        HOME = setup.make_workspace()
        master_address = ('bad_broker_address',111666)
        broker, remote = make_slave(master_address, 'slave', HOME)
        broker.start()
        try:
            # make the broker start sharing, should not crash even though there
            # is no master broker to share to.
            remote.start_sharing()
            return True
        except Exception as e:
            print(
                'FAIL %s: slave crashed when master was not found: %s'
                % (pretty, str(e))
            )
            return False
    finally:
        broker.terminate()
        broker.join()
        HOME.delete()

#Verifying sharing via one extra broker, slave_b->slave_a->master
@setup.factory()
def t13(factory):
    pretty = '%s t13' % __file__
    print(pretty)

    try:
        master = factory.make_master('master')
        slave_a = factory.make_share(master, 'slave_a', True)
        slave_b = factory.make_share(slave_a, 'slave_b', True)

        if not verify_allocators_on_broker(pretty, master, 2):
            return False

        # make a new slave connection so that we can close it by garbage
        # collecting it. the 'slave' parameter is held by the setup,
        # so del(slave) won't work
        master_client = RemoteBroker(master.address, home=factory.HOME.path)
        slave_a_client = RemoteBroker(slave_a.address, home=factory.HOME.path)
        slave_b_client = RemoteBroker(slave_b.address, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    # allocate directly from the slave
    expected_available_on_master = 15
    master_available = master_client.list_available()
    if(len(master_available)!=expected_available_on_master):
        print('FAIL %s:Nr of available on Master: %d, expected %d' %
              (pretty, len(master_available), expected_available_on_master))
        return False

    expected_available_on_slave_a = 10
    slave_a_available = slave_a_client.list_available()
    if(len(slave_a_available)!=expected_available_on_slave_a):
        print('FAIL %s:Nr of available on Slave_a: %d, expected %d' %
              (pretty, len(slave_a_available), expected_available_on_slave_a))
        return False

    expected_available_on_slave_b = 5
    slave_b_available = slave_b_client.list_available()
    if(len(slave_b_available)!=expected_available_on_slave_b):
        print('FAIL %s:Nr of available on Slave_b: %d, expected %d' %
              (pretty, len(slave_b_available), expected_available_on_slave_b))
        return False

    return True

# Verifying sharing via one extra broker, slave_b->slave_a->master,
# verifying allocation on master verifying allocation on slave a and b is
# redundant because the same functionality is used in master with aspect to
# local and share allocators.
@setup.factory()
def t14(factory):
    pretty = '%s t14' % __file__
    print(pretty)

    PROFILE = {'type':'handset'}
    MAX_ALLOWED_ITERATIONS = 10
    try:
        master = factory.make_master('master')
        slave_a = factory.make_share(master, 'slave_a', True)
        slave_b = factory.make_share(slave_a, 'slave_b', True)

        if not verify_allocators_on_broker(pretty, master, 2):
            return False

        # create clients for manipulation
        master_client = RemoteBroker(master.address, home=factory.HOME.path)
        slave_a_client = RemoteBroker(slave_a.address, home=factory.HOME.path)
        slave_b_client = RemoteBroker(slave_b.address, home=factory.HOME.path)

        handsets_master = []
        handsets_slave_a = []
        handsets_slave_b = []
    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    for i in range(1, 4, 1):
        expected_available_on_master = 9-i*3  # 6, 3, 0 the three times

        try:
            handsets_master.append(master_client.get(PROFILE))
            time.sleep(.1)
            handsets_slave_a.append(slave_a_client.get(PROFILE))
            time.sleep(.1)
            handsets_slave_b.append(slave_b_client.get(PROFILE))
            time.sleep(.1)
        except Exception, e:
            pass

        # Verifying allocation on Master
        for attempt in range(MAX_ALLOWED_ITERATIONS+1):
            master_available = master_client.list_available(PROFILE)
            if len(master_available) == expected_available_on_master:
                break
            if attempt < MAX_ALLOWED_ITERATIONS:
                time.sleep(0.5)
                continue
            else:
                print('FAIL %s:Nr of available on Master: %d, expected %d' %
                      (pretty, len(master_available),
                       expected_available_on_master))
                print('Iteration: %d' % i)
                print('master_available: %s\n' %
                      json.dumps(master_available, indent=4))
                return False
    return True


#Verifying sharing via one extra broker, slave_b->slave_a->master,
# verifying over allocation
@setup.factory()
def t15(factory):
    pretty = '%s t15' % __file__
    print(pretty)

    PROFILE = {'type':'handset'}
    MAX_ALLOWED_ITERATIONS = 10

    try:
        master = factory.make_master('master')
        slave_a  = factory.make_share(master, 'slave_a', True)
        slave_b  = factory.make_share(slave_a, 'slave_b', True)

        if not verify_allocators_on_broker(pretty, master, 2):
            return False

        # create clients for manipulation
        master_client = RemoteBroker(master.address, home=factory.HOME.path)
        slave_a_client = RemoteBroker(slave_a.address, home=factory.HOME.path)
        slave_b_client = RemoteBroker(slave_b.address, home=factory.HOME.path)

        handsets_master = []
        handsets_slave_a = []
        handsets_slave_b = []

        # Allocate all 9 handsets
        for i in range(3):
            handsets_master.append(master_client.get(PROFILE))
            time.sleep(.1)
            handsets_slave_a.append(slave_a_client.get(PROFILE))
            time.sleep(.1)
            handsets_slave_b.append(slave_b_client.get(PROFILE))
            time.sleep(.1)

    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    # Try to allocate on slave_b causing three handsets to be freed
    try:
        handsets_slave_b.append(slave_b_client.get(PROFILE))
        time.sleep(.1)
    except Exception, e:
        pass

    expected_available_on_master = 3

    for attempt in range(MAX_ALLOWED_ITERATIONS+1):
        master_available = master_client.list_available(PROFILE)
        if len(master_available) == expected_available_on_master:
            break
        if attempt < MAX_ALLOWED_ITERATIONS:
            time.sleep(0.5)
            continue
        else:
            print('FAIL %s:Nr of available on Master: %d, expected %d' %
                  (pretty, len(master_available),
                   expected_available_on_master))
            print('master_available: %s\n' %
                  json.dumps(master_available, indent=4))
        return False

    # Try to allocate non existing equipment on slave_a causing three
    # handsets to be freed
    try:
        handsets_slave_a.append(slave_a_client.get({'type': 'handset',
                                                    'pretty': 'mrX'}))
        time.sleep(.1)
    except Exception, e:
        pass

    expected_available_on_master = 6

    for attempt in range(MAX_ALLOWED_ITERATIONS+1):
        master_available = master_client.list_available(PROFILE)
        if len(master_available) == expected_available_on_master:
            break
        if attempt < MAX_ALLOWED_ITERATIONS:
            time.sleep(0.5)
            continue
        else:
            print('FAIL %s:Nr of available on Master: %d, expected %d' %
                  (pretty, len(master_available),
                   expected_available_on_master))
            print('master_available: %s\n' %
                  json.dumps(master_available, indent=4))
        return False

    # Try to allocate non existing equipment on master causing three
    # handsets to be freed
    try:
        handsets_master.append(master_client.get({'type': 'handset',
                                                  'pretty': 'mrX'}))
        time.sleep(.1)
    except Exception, e:
        pass

    expected_available_on_master = 9

    for attempt in range(MAX_ALLOWED_ITERATIONS+1):
        master_available = master_client.list_available(PROFILE)
        if len(master_available) == expected_available_on_master:
            break
        if attempt < MAX_ALLOWED_ITERATIONS:
            time.sleep(0.5)
            continue
        else:
            print('FAIL %s:Nr of available on Master: %d, expected %d' %
                  (pretty, len(master_available),
                   expected_available_on_master))
            print('master_available: %s\n' %
                  json.dumps(master_available, indent=4))
        return False

    return True

# Verifying sharing via one extra broker, slave_b->slave_a->master.
# Verifying that equipment is removed from master when the allocating client
# is destroyed, due to over allocation, directly and then re-added by slave
# broker
@setup.factory()
def t16(factory):
    pretty = '%s t16' % __file__
    print(pretty)

    PROFILE = {'type':'handset', 'pretty':'jane'}

    try:
        master = factory.make_master('master')
        slave_a = factory.make_share(master, 'slave_a', True, slow_down=0.1)
        slave_b = factory.make_share(slave_a, 'slave_b', True)

        if not verify_allocators_on_broker(pretty, master, 2):
            raise Exception('Failing allocator setup')

        # create clients for manipulation
        master_client = RemoteBroker(master.address, home=factory.HOME.path)
        slave_b_client = RemoteBroker(slave_b.address, home=factory.HOME.path)


        # Allocate three handsets
        h1 = slave_b_client.get(PROFILE)
        time.sleep(0.15)
        h2 = master_client.get(PROFILE)
        time.sleep(0.15)
        h3 = master_client.get(PROFILE)
        time.sleep(0.15)
    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    # Crash master broker client by trying to get a busy handset
    try:
        h4 = master_client.get(PROFILE)
    except:
        pass
    # Verifying that the allocated handset on the share allocator is removed
    # from the equipment list until the the slave updatets its sharing, which
    # is delayed with 100ms by the mocking slow_down=0.1
    master_list = master_client.list_equipment(PROFILE)
    if len(master_list) != 2:
        print('FAIL %s:Nr of equipment with profile: %s != 2, %s' %
              (pretty, PROFILE, json.dumps(master_list, indent=4)))
        return False
    maste_allocation_list = master_client.list_allocations_all()
    if len(maste_allocation_list) != 1:
        print('FAIL %s:Nr of allocated equipment with profile: %s != 1, %s' %
              (pretty, PROFILE, json.dumps(maste_allocation_list, indent=4)))
        return False

    # Sleep for 150 ms to let the update catch up
    time.sleep(0.15)

    # Verify that the slaves equipment ir re-added
    master_list = master_client.list_equipment(PROFILE)
    if len(master_list) != 3:
        print('FAIL %s:Nr of equipment with profile: %s != 3, %s' %
              (pretty, PROFILE, json.dumps(master_list, indent=4)))
        return False
    maste_allocation_list = master_client.list_allocations_all()
    if len(maste_allocation_list) != 1:
        print('FAIL %s:Nr of allocated equipment with profile: %s != 1, %s' %
              (pretty, PROFILE, json.dumps(maste_allocation_list, indent=4)))
        return False

    return True

# verifying yielding via one extra broker, slave_b->slave_a->master, after the
# share has stopped sharing the resource
@setup.factory()
def t17(factory):
    pretty = '%s t17' % __file__
    print(pretty)

    try:
        master  = factory.make_master('master')
        slave_a = factory.make_share(master, 'slave_a', True)
        slave_b = factory.make_share(slave_a, 'slave_b', True)

        if not verify_allocators_on_broker(pretty, master, 2):
            return False

        handset = master.get({'type': 'handset', 'serial':'slave_b-1'})
        slave_b.stop_sharing()

        time.sleep(1)
    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    try:
        master.yield_resources(handset)
    except Exception, e:
        print('FAIL %s: Unexpected Exception when trying to yield allocated '
              'recource on stopped slave: %s' % (pretty, e))

    return True

# Verify that rescources on master get power_state updates
@setup.factory()
def t18(factory):
    pretty = '%s t18' % __file__
    print(pretty)

    SERIAL = 'slave-1'

    try:
        master  = factory.make_master('master')
        slave = factory.make_share(master, 'slave', True)

        if not verify_allocators_on_broker(pretty, master, 1):
            return False

        time.sleep(1)

        expected_power_state = 'boot_completed'

        master_equipment = master.list_equipment()

        for e in master_equipment:
            if 'serial' in e:
                if e['serial'] == SERIAL:
                    power_state = e['power_state']

        if power_state != expected_power_state:
            raise Exception('Unexpected initial power_state: %s, expecting: %s'
                            % (power_state, expected_power_state))

    except Exception, e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    # Actual test starts

    expected_power_state = 'adb'

    slave.set_handset_power_state(SERIAL, expected_power_state)

    master_equipment = master.list_equipment()

    for e in master_equipment:
        if 'serial' in e:
            if e['serial'] == SERIAL:
                power_state = e['power_state']

    if power_state != expected_power_state:
        print('FAIL %s: Update of power_state failed, power_state: %s, '
              'expecting: %s' % (pretty, power_state, expected_power_state))

    return True


# Verify list equipment from specific allocator
@setup.factory()
def t19(factory):
    pretty = '%s t19' % __file__
    print(pretty)

    try:
        master = factory.make_master('master')
        master_equipment = master.list_equipment()
        share = factory.make_share(master, 'share', True)
        share_equipment = share.list_equipment()

        if not verify_allocators_on_broker(pretty, master, 1):
            return False

        time.sleep(1)

    except Exception as e:
        print('FAIL %s: Setup failed, Exception: %s' % (pretty, e.message))
        return False

    master_client = RemoteBroker(master.address, home=factory.HOME.path)

    allocators = master_client.list_allocators()

    # without defining allocator, expect to list all known equipment
    list_master = master_client.list_equipment()
    failure = None
    expected = master_equipment + share_equipment
    for exp in expected:
        match = False
        for lm in list_master:
            if exp == lm:
                match = True
                break
        if not match:
            failure = exp
            break

    if failure:
        print('FAIL %s: list_equipment without allocator did not list expected '
              'equipment: %s is missing.\n%s\nExpected:\n%s' % (pretty, failure,
                                                                list_master,
                                                                expected))
        return False
    if len(expected) != len(list_master):
        print("FAIL %s: list_equipment without allocator did not produce "
              "correct number of equipment: %s, "
              "expected: %s" % (pretty, len(expected), len(list_master)))
        return False

    # With allocator defined, expect all equipment belonging to that workstation
    # and nothing more.
    for a in allocators:
        failure = None
        list_eq = master_client.list_equipment(allocator=a)
        if a == 'local':
            target = master_equipment
        else:
            target = share_equipment
        for t in target:
            match = False
            for le in list_eq:
                if t == le:
                    match = True
                    break
            if not match:
                failure = t
                break

        if failure:
            print('FAIL %s: list_equipment failed for allocator %s, %s not '
                  'found in result: %s' % (pretty, a, failure, list_eq))
            return False
        # Make sure we don't get more results than expected.
        if len(target) != len(list_eq):
            print('FAIL %s: length of result from list_equipment %s mismatches '
                  'expected length: %s' % (pretty, len(list_eq), len(target)))
            return False

    return True

# regression test: check that multiple calls to start_sharing() from the same
# slave to the same master does not result in multiple shares at the master
@setup.factory()
def t20(factory):
    pretty = '%s t20' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=False)

    result = master.list_shares()
    if result != []:
        print(
            'FAIL %s: master has shares before sharing starts %s'
            % (pretty, result)
        )
        return False

    # start sharing and wait for the master to notice
    share.start_sharing()
    for i in range(10):
        result = master.list_shares()
        if result:
            break
        time.sleep(0.3)
    if len(result) != 1:
        print(
            'FAIL %s: master has more than one share after first start: %s'
            % (pretty, result)
        )
        return False

    # let the share start sharing again
    share.start_sharing()
    time.sleep(1) # must be enough
    result = master.list_shares()
    if len(result) != 1:
        print(
            'FAIL %s: master has more than one share after second start: %s'
            % (pretty, result)
        )
        return False

    return True

# regression test: check that multiple calls to start_sharing() from the same
# share does not result in multiple notifier processes
@setup.factory()
def t21(factory):
    pretty = '%s t21' % __file__

    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=False)

    rn1_addr = share.start_sharing()
    rn2_addr = share.start_sharing()

    rn1 = RemoteNotifier(tuple(rn1_addr), 1)
    rn2 = RemoteNotifier(tuple(rn2_addr), 1)

    try:
        rn1.ping()
        print('FAIL %s: could ping first notifier' % pretty)
        return False
    except (ConnectionTimeout, ConnectionRefused):
        pass # good
    except Exception, e:
        print('FAIL %s: wrong error: %s' % (pretty, e))
        return False

    try:
        rn2.ping()
    except Exception, e:
        print('FAIL %s: could not ping second notfier: %s' % (pretty, e))
        return False

    return True

# regression test: check that multiple calls to stop_sharing() from the same
# share does not crash the master.
@setup.factory()
def t22(factory):
    pretty = '%s t22' % __file__

    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=False)

    share.start_sharing()
    share.stop_sharing()
    share.stop_sharing()

    try:
        master.ping()
    except Exception, e:
        print('FAIL %s: could not ping master: %s' % (pretty, e))
        return False

    return True

# does the notifier keep track of its internal delta correctly if a sharing
# broker adds/removes equipment and workspaces before it can report everything
# to a remote master?

# does slave add new equipment to master on first discovery?

# multi-stage add/remove equipment (share->share->master)

# profile filling

# try to fool the system into allocating the same resource twice by restarting
# a share without notifying the master broker

# should there be a whole sub-suite about yielding? low priority for now as
# test jobs are not supposed to yield explicitly anyway
