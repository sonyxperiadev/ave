import os
import json
import time
import traceback

from datetime import datetime, timedelta

from ave.profile              import Profile
from ave.handset.profile      import HandsetProfile
from ave.network.control      import RemoteControl
from ave.broker._broker       import RemoteBroker
from ave.exceptions           import Timeout
from ave.network.exceptions   import ConnectionClosed

import setup

# help function - wait for at least counts number of handsets with PM
def wait_equipment(broker, profiles):
    ok = False
    for i in range(10):
        count = 0
        for p in profiles:
            if broker.list_equipment(p):
                count += 1
        if count == len(profiles):
            return
        time.sleep(1)
    raise Timeout('timeout')

# check that add equipment to broker works as expected.
@setup.factory()
def t1(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    master  = factory.make_master('master', hsl_paths=[])
    port    = master.address[1]
    b       = RemoteControl(('',port), 'share_key', timeout=5)

    profile = HandsetProfile({
        'type'        : 'handset',
        'serial'      : 'ABC321',
        'sysfs_path'  : '/sys/devices/pci0000:00/0000:00:1a.7/usb1/1-99/',
        'vendor'      : '0fce',
        'product'     : '0xyz',
        'pretty'      : 'Zphone',
        'power_state' : 'boot_completed',
        'platform'    : 'android'
    })

    # add profile to broker
    b.add_equipment('local',[profile])
    if not profile in master.list_equipment():
        print(
            'FAIL %s: failed to add handset to broker: %s, %s'
            % (pretty, profile, master.list_equipment())
        )
        return False

    return True

# check that it's possible to
# 1) allocate a handset and verify it's not listed as available
# 2) reboot the handset and verify it's not listed as available after disconnect
# 3) yield  the handset and verify it's     listed as available again
# with a standalone single broker
@setup.factory()
def t2(factory, h1, h2, r1):
    pretty = '%s t2' % __file__
    print(pretty)

    h1p = h1.get_profile()
    h2p = h2.get_profile()
    hsl_paths = [h1p['sysfs_path'], h2p['sysfs_path']]
    b = factory.make_master('broker', hsl_paths=hsl_paths)

    h1p = {'type':'handset','serial':h1p['serial']}
    h2p = {'type':'handset','serial':h2p['serial']}

    try:
        wait_equipment(b, [h1p, h2p])
    except Timeout:
        print('FAIL %s: no handsets found' % pretty)
        return False

    h = b.get_resource({'type':'handset', 'serial':h1.get_profile()['serial']})

    profile = HandsetProfile(h.get_profile())
    if profile in b.list_available():
        print('FAIL %s: allocated handset listed as available' % pretty)
        return False

    # locally allocated equipment should still be listed with list_equipment
    if not profile in b.list_equipment():
        print('FAIL %s: allocated handset not in listed equipment' % pretty)
        return False

    # disconnect the handset and verify it's still allocated
    r1.set_circuit('usb.pc.vcc', False)
    try:
        h.wait_power_state('offline', timeout=5)
    except Exception, e:
        print('FAIL %s: wait for offline failed: %s' % (pretty, e))
        return False
    if profile in b.list_available():
        print('FAIL %s: offline handset is available' % pretty)
        return False

    try:
        # yield handset and verify it's now becoming available again
        b.yield_resources(profile)
        if profile not in b.list_available():
            print('FAIL %s: yielded handset not listed as available' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# check that it's possible to
# 1) allocate a handset and verify it's not listed as available
# 2) reboot the handset and verify it's not listed as available after reconnect
# 3) yield  the handset and verify it's     listed as available again
# when using 'shared' handset allocated via master
@setup.factory()
def t3(factory, h1, h2, r1):
    pretty = '%s t3' % __file__
    print(pretty)

    h1p = h1.get_profile()
    h2p = h2.get_profile()

    # create a master and a sharing slave (only slave will see real equipment)
    hsl_paths = [h1p['sysfs_path'], h2p['sysfs_path']]
    master = factory.make_master('master', hsl_paths=[])
    share  = factory.make_share(
        master, 'share', autoshare=True, hsl_paths=hsl_paths
    )
    try:
        wait_equipment(master, [h1p, h2p])
    except Timeout:
        print('FAIL %s: no handset found' % pretty)
        return False

    # allocate handsets and verify they're not listed as available
    h11 = master.get_resource({'type':'handset', 'serial':h1p['serial']})
    h21 = master.get_resource({'type':'handset', 'serial':h2p['serial']})
    profile1 = HandsetProfile(h11.get_profile())
    profile2 = HandsetProfile(h21.get_profile())
    if (profile1 in master.list_available()
    or  profile1 in master.list_available()):
        print('FAIL %s: allocated handset listed as available' % pretty)
        return False

    r1.set_circuit('usb.pc.vcc', False)
    try:
        h11.wait_power_state('offline', timeout=5)
    except Exception, e:
        print('FAIL %s: wait for offline failed: %s' % (pretty, e))
        return False
    r1.set_circuit('usb.pc.vcc', True)
    try:
        h11.wait_power_state('boot_completed', timeout=5)
    except Exception, e:
        print('FAIL %s: wait for boot_completed failed: %s' % (pretty, e))
        return False

    if profile1 in master.list_available():
        print('FAIL %s: handset available after reconnect' % pretty)
        return False

    # reconnect to master and verify the handsets become available again
    # (because they are reclaimed when the job drops the master)
    master = RemoteBroker(
        master.address, authkey=master.authkey, home=factory.HOME.path
    )
    ok = False
    for i in range(10):
        if profile1 not in master.list_available():
            time.sleep(0.3)
            continue
        if profile2 not in master.list_available():
            time.sleep(0.3)
            continue
        ok = True
        break
    if not ok:
        print('FAIL %s: yielded handset not listed as available' % pretty)
        return False

    return True

# restart the master broker during ongoing state discovery.
# verify that the restarted broker has correct information in the end.
@setup.factory()
def t4(factory, h1, h2, r1):
    pretty = '%s t4' % __file__
    print(pretty)

    h1p = h1.get_profile()
    h2p = h2.get_profile()

    # create a master and a share (only the share will see real equipment)
    hsl_paths = [h1p['sysfs_path'], h2p['sysfs_path']]
    handover  = factory.make_master('master', hsl_paths=[])
    share     = factory.make_share(
        handover, 'share', autoshare=True, hsl_paths=hsl_paths
    )

    try:
        wait_equipment(handover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: handsets not found in handover' % pretty)
        return False

    # allocate a handset
    handset = handover.get_resources({'type':'handset','serial':h1p['serial']})
    profile = HandsetProfile(handset.get_profile())

    # restart the master
    adoption,config,fdtx_path = handover.begin_handover() # stops listening
    takeover = factory.make_takeover('master', adoption, config, fdtx_path, [])
    try:
        handover.end_handover(1)
    except ConnectionClosed:
        pass # good. handover quits immediately because it has no local allocs
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: could not end handover: %s' % (pretty, str(e)))
        return False

    # wait until takeover's hsslister has reported power states
    try:
        wait_equipment(takeover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: remaining handset not found in takeover' % pretty)
        return False

    # verify that takeover know that the handset is allocated
    if profile in takeover.list_available():
        print(
            'FAIL %s: handset available in takeover: %s'
            % (pretty, '\n'.join('%s' % a for a in takeover.list_available()))
        )
        return False

    return True

# reconnect a shared handset during handover and verify that it doesn't show up
# as available in the takeover
@setup.factory()
def t5(factory, h1, h2, r1):
    pretty = '%s t5' % __file__
    print(pretty)

    h1p = h1.get_profile()
    h2p = h2.get_profile()

    # create a master and a share (only the share will see real equipment)
    hsl_paths = [h1p['sysfs_path'], h2p['sysfs_path']]
    handover  = factory.make_master('master', hsl_paths=[])
    share     = factory.make_share(
        handover, 'share', autoshare=True, hsl_paths=hsl_paths
    )

    try:
        wait_equipment(handover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: handsets not found in handover' % pretty)
        return False

    # allocate handset and save a profile
    handset = handover.get_resources({'type':'handset','serial':h1p['serial']})
    profile = HandsetProfile(handset.get_profile())

    # stop the handover
    adoption,config,fdtx_path = handover.begin_handover() # stops listening

    # reconnect the handset while neither broker is listening for updates
    r1.set_circuit('usb.pc.vcc', False)
    try:
        handset.wait_power_state('offline', 5)
    except Exception, e:
        print('FAIL %s: wait for offline failed: %s' % (pretty, e))
        return False
    r1.set_circuit('usb.pc.vcc', True)

    # start the takeover
    takeover = factory.make_takeover('master', adoption, config, fdtx_path, [])
    try:
        handover.end_handover(1)
    except ConnectionClosed:
        pass # good. handover quits immediately because it has no local allocs
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: could not end handover: %s' % (pretty, str(e)))
        return False

    # wait until takeover's hsslister has reported power states
    # wait until takeover's hsslister has reported power states
    h1p = {'type':'handset','serial':h1p['serial']}
    h2p = {'type':'handset','serial':h2p['serial']}
    try:
        wait_equipment(takeover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: handsets not found in takeover' % pretty)
        return False

    # verify that takeover know that the handset is allocated
    if profile in takeover.list_available():
        print(
            'FAIL %s: handset available in takeover: %s'
            % (pretty, '\n'.join('%s' % a for a in takeover.list_available()))
        )
        return False

    return True

# yield a shared handset during handover. check that it shows up as available
# in the takeover
@setup.factory()
def t6(factory, h1, h2, r1):
    pretty = '%s t6' % __file__
    print(pretty)

    h1p = h1.get_profile()
    h2p = h2.get_profile()

    # create a master and a share (only the share will see real equipment)
    hsl_paths = [h1p['sysfs_path'], h2p['sysfs_path']]
    handover  = factory.make_master('master', hsl_paths=[])
    # droppable connection:
    client    = RemoteBroker(handover.address, home=factory.HOME.path)
    share     = factory.make_share(
        handover, 'share', autoshare=True, hsl_paths=hsl_paths
    )

    try:
        wait_equipment(handover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: handsets not found in handover' % pretty)
        return False

    # allocate handset and save a profile
    handset = client.get_resources({'type':'handset','serial':h1p['serial']})
    profile = HandsetProfile(handset.get_profile())

    # stop the handover
    adoption,config,fdtx_path = handover.begin_handover() # stops listening

    # disconnect the handset while neither broker is listening for updates,
    # then drop the allocation entirely (disconnect from the handover). the
    # handset should show up as available in power state "boot_completed" in
    # the takeover
    r1.set_circuit('usb.pc.vcc', False)
    try:
        handset.wait_power_state('offline', 5)
    except Exception, e:
        print('FAIL %s: wait for offline failed: %s' % (pretty, e))
        return False
    del client
    r1.set_circuit('usb.pc.vcc', True)

    # start the takeover
    takeover = factory.make_takeover('master', adoption, config, fdtx_path, [])
    try:
        handover.end_handover(1)
    except ConnectionClosed:
        pass # good. handover quits immediately because it has no local allocs
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: could not end handover: %s' % (pretty, str(e)))
        return False

    # wait until takeover's hsslister has reported power states
    h1p = {'type':'handset','serial':h1p['serial']}
    h2p = {'type':'handset','serial':h2p['serial']}
    try:
        wait_equipment(takeover, [h1p, h2p])
    except Timeout:
        print('FAIL %s: handsets not found in takeover' % pretty)
        return False

    # verify that takeover know that the handset is allocated
    if profile not in takeover.list_available():
        print(
            'FAIL %s: handset not available in takeover: %s'
            % (pretty, '\n'.join('%s' % a for a in takeover.list_available()))
        )
        return False

    return True
