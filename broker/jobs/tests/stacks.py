# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import errno
import traceback

from ave.broker.profile     import *
from ave.workspace          import Workspace
from ave.broker._broker     import RemoteBroker
from ave.broker.session     import RemoteSession
from ave.network.connection import find_free_port

import setup

# check that the mock setup works
@setup.brokers([], 'master', [], True, False)
def t1(HOME, r):
    pretty = '%s t1' % __file__
    print(pretty)

    expected = {
        'type':'handset', 'vendor':'foo', 'product':'bar',
        'serial':'master-1', 'pretty':'mary', 'workstation': 'slave-master.corpusers.net',
        'sysfs_path': '/', 'power_state': 'boot_completed',
        'platform':'android','product.model':'d1123'
    }
    handsets = r.list_handsets()
    if expected not in handsets:
        print('FAIL %s: mock handset equipment is wrong: %s' %(pretty,handsets))
        return False

    expected = {
        'type':'relay', 'uid':'master-a', 'pretty':'gustav',
        'circuits':{'usb.pc.vcc':1}, 'power_state':'online'
    }
    relays = r.list_relays()
    if expected not in relays:
        print('FAIL %s: mock relay equipment is wrong: %s' %(pretty,relays))
        return False
    return True

# allocate devices from the same stack
@setup.brokers([], 'master', [], True, False)
def t2(HOME, b):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        w,h,r = b.get_resources(
            {'type':'workspace'},
            {'type':'handset'},
            {'type':'relay'}
        )
    except Exception, e:
        print('FAIL %s: allocation failed: %s' % (pretty, str(e)))
        return False

    # check that returned types are correct
    types = [type(resource).__name__ for resource in [w, h, r]]
    if types != ['RemoteWorkspace', 'RemoteHandset', 'RemoteRelay']:
        print('FAIL %s: got wrong resource types: %s' % (pretty, types))
        return False

    # check that all resources belong to the same stack
    def in_stack(stack, resource):
        for equipment in stack:
            if resource.profile['type'] == equipment['type'] == 'handset':
                if resource.profile['serial'] == equipment['serial']:
                    return True
            if resource.profile['type'] == equipment['type'] == 'relay':
                if resource.profile['uid'] == equipment['uid']:
                    return True
        return False
    ok = False
    for stack in b.list_stacks():
        if in_stack(stack, h) and in_stack(stack, r):
            ok = True
            break
    if not ok:
        print('FAIL %s: equipment not allocated from the same stack' % pretty)
        return False

    return True

# try to allocate two devices together, but from different stacks
@setup.brokers([], 'master', [], True, False)
def t3(HOME, b):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        w,h,r = b.get_resource(
            {'type':'workspace'},
            {'type':'handset', 'serial':'master-3'},
            {'type':'relay', 'uid':'master-a'}
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
@setup.brokers([], 'master', [], True, False)
def t4(HOME, b):
    pretty = '%s t4' % __file__
    print(pretty)

    w,h = b.get_resource(
        {'type':'workspace'},
        {'type':'handset', 'serial':'master-2'}
    )

    # allocation should include two relays because all stacks that contain the
    # handset do so
    r1 = None
    r2 = None
    for a in b.list_collateral():
        if a == {'type':'relay', 'uid':'master-a'}:
            r1 = a
        if a == {'type':'relay', 'uid':'master-b'}:
            r2 = a
    if not (r1 and r2):
        print('FAIL %s: the relays were not claimed' % pretty)
        return False

    return True

# check that the broker returns resources in the order they were requested
@setup.brokers([], 'master', [], True, False)
def t5(HOME, b):
    pretty = '%s t5' % __file__
    print(pretty)

    request = [{'type':'workspace'}, {'type':'handset'}, {'type':'relay'}]
    # cycle through the request to try the rotated permutations
    for i in range(3):
        request.insert(0, request.pop())
        try:
            allocation = b.get_resource(*request)
        except Exception, e:
            print('FAIL %s: allocation %d failed: %s' % (pretty, i, str(e)))
            return False
        request_order    = [r['type'] for r in request]
        allocation_order = [a.profile['type'] for a in allocation]
        if allocation_order != request_order:
            print(
                'FAIL %s: allocation %d has wrong order: %s'
                % (pretty, i, allocation)
            )
            return False
        b.yield_resources(*allocation)

    return True

# check that all resources are freed when the client disconnects
@setup.brokers([], 'master', [], True, False)
def t6(HOME, b):
    pretty = '%s t6' % __file__
    print(pretty)

    for i in range(3):
        # the broker connection will be garbage collected between iterations,
        # causing the broker to free all resources allocated to the client.
        b2 = RemoteBroker(b.address, home=HOME.path)
        try:
            w,h,r = b2.get_resource(
                {'type':'workspace'},
                {'type':'handset'},
                {'type':'relay'}
            )
        except Exception, e:
            print('FAIL %s: allocation %d failed: %s' % (pretty, i, str(e)))
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
@setup.brokers([], 'master', [], True, False)
def t7(HOME, b):
    pretty = '%s t7' % __file__
    print(pretty)

    w,r0 = b.get_resource(
        {'type':'workspace'}, {'type':'relay', 'uid':'master-a'}
    )
    try:
        r1 = b.get_resource({'type':'relay', 'uid':'master-b'})
    except Exception, e:
        print('FAIL %s: second allocation failed: %s' % (pretty, str(e)))
        return False

    return True

# check that allocations/yields cause/remove the correct collateral
@setup.brokers([], 'master', [], True, False)
def t8(HOME, b):
    pretty = '%s t8' % __file__
    print(pretty)

    # allocate relay a to get handset 1 and 2 marked as collateral
    w,r = b.get_resource(
        {'type':'workspace'}, {'type':'relay', 'uid':'master-a'}
    )

    # check that the collateral is correct
    collateral = b.list_collateral()
    if len(collateral) != 2:
        print('FAIL %s: wrong amount of collateral: %s' % (pretty, collateral))
        return False
    for serial in ['master-1', 'master-2']:
        if {'type':'handset', 'serial':serial} not in collateral:
            print(
                'FAIL %s: handset %s not in collateral: %s'
                % (pretty, serial, collateral)
            )
            return False

    # yield relay a and check that all collateral is removed
    b.yield_resources(r)

    # check the collateral
    collateral = b.list_collateral()
    if collateral != []:
        print('FAIL %s: there is collateral left: %s' % (pretty, collateral))
        return False

    return True

# like t8 but with multi-stage allocations. collateral that is shared by the
# allocations should not be removed until all such allocations are yielded
@setup.brokers([], 'master', [], True, False)
def t9(HOME, b):
    pretty = '%s t9' % __file__
    print(pretty)

    # allocate relay a to get handset 1 and 2 marked as collateral
    w1,r1 = b.get_resource(
        {'type':'workspace'}, {'type':'relay', 'uid':'master-a'}
    )

    # allocate relay b to get handset 2 and 3 marked as collateral
    w2,r2 = b.get_resource(
        {'type':'workspace'}, {'type':'relay', 'uid':'master-b'}
    )

    # check that the collateral is correct
    collateral = b.list_collateral()
    if len(collateral) != 3:
        print('FAIL %s: wrong amount of collateral: %s' % (pretty, collateral))
        return False
    for serial in ['master-1', 'master-2', 'master-3']:
        if {'type':'handset', 'serial':serial} not in collateral:
            print(
                'FAIL %s: handset %s not in collateral: %s'
                % (pretty, serial, collateral)
            )
            return False

    # check that handset 2 remains as collateral (together with handset 1) when
    # relay 2 is freed
    b.yield_resources(r2)

    # check that the collateral is correct
    collateral = b.list_collateral()
    if len(collateral) != 2:
        print(
            'FAIL %s: wrong amount of collateral left: %s'
            % (pretty, collateral)
        )
        return False
    for serial in ['master-1', 'master-2']:
        if {'type':'handset', 'serial':serial} not in collateral:
            print(
                'FAIL %s: handset %s not left in collateral: %s'
                % (pretty, serial, collateral)
            )
            return False


# check that yielding a resource frees up related collateral
@setup.brokers([], 'master', [], True, False)
def t10(HOME, b):
    pretty = '%s t10' % __file__
    print(pretty)

    # allocate relay a to get handset 1 and 2 marked as collateral
    w,r = b.get_resource(
        {'type':'workspace'}, {'type':'relay', 'uid':'master-a'}
    )

    # check that the collateral is correct
    collateral = b.list_collateral()
    if len(collateral) != 2:
        print('FAIL %s: wrong amount of collateral: %s' % (pretty, collateral))
        return False
    for serial in ['master-1', 'master-2']:
        if {'type':'handset', 'serial':serial} not in collateral:
            print(
                'FAIL %s: handset %s not in collateral: %s'
                % (pretty, serial, collateral)
            )
            return False

    # first try to allocate handset 1 and 2. both should fail. the first will
    # fail because of the rules surrounding collateral. the second will fail
    # because the session gets killed immediately when the first allocation
    # fails.
    try:
        h = b.get_resource({'type':'handset', 'serial':'master-1'})
        print('FAIL %s: could allocate handset 1' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('all such equipment busy'):
            print('FAIL %s: wrong error message 1: %s' % (pretty, str(e)))
            return False
    try:
        h = b.get_resource({'type':'handset', 'serial':'master-2'})
        print('FAIL %s: could allocate handset 1' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('session closed'):
            print('FAIL %s: wrong error message 2: %s' % (pretty, str(e)))
            return False

    # relay a should now be available again, but not to the currently open
    # session (because it has failed allocations). check that collateral is
    # empty, then start a new session and check that everything is available.

    # check the collateral
    collateral = b.list_collateral_all()
    if collateral != []:
        print('FAIL %s: there is collateral left: %s' % (pretty, collateral))
        return False

    # check that all equipment is available
    relays    = b.list_relays()
    handsets  = b.list_handsets()
    available = b.list_available()
    for i in range(len(handsets)):
        if not handsets[i] in available:
            print('FAIL %s: handset %d not available: %s'%(pretty,i,available))
            return False
    for i in range(len(relays)):
        if not relays[i] in available:
            print('FAIL %s: relay %d not available: %s' % (pretty,i,available))
            return False

    return True

# check that the broker picks all resources from the same stack
@setup.brokers([], 'master', [], True, False)
def t11(HOME, b):
    pretty = '%s t11' % __file__
    print(pretty)

    r,h = b.get_resource(
        {'type':'relay','uid':'master-b'}, {'type':'handset'}
    )
    profile = h.get_profile()
    if profile['serial'] not in ['master-2', 'master-3']:
        print('FAIL %s: wrong handset: %s' % (pretty, profile))
        return False

    return True

# check that the broker picks all resources from the same stack
@setup.brokers([], 'master', [], True, False)
def t12(HOME, b):
    pretty = '%s t12' % __file__
    print(pretty)

    r,h = b.get_resource(
        {'type':'relay'}, {'type':'handset','serial':'master-3'}
    )
    profile = r.get_profile()
    if profile['uid'] != 'master-b':
        print('FAIL %s: wrong relay: %s' % (pretty, profile))
        return False

    return True

# check that complex allocations respect collateral caused by simple allocations
@setup.brokers([], 'master', [], True, False)
def t13(HOME, b):
    pretty = '%s t13' % __file__
    print(pretty)

    # handset 2 has both relays as collateral if allocated by itself
    h = b.get_resource({'type':'handset','serial':'master-2'})

    try:
        r,h = b.get_resource({'type':'relay'}, {'type':'handset'})
        print('FAIL %s: could allocate collateral: %s'%(pretty,r.get_profile()))
        return False
    except Exception, e:
        if e.message != 'cannot allocate all equipment together':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that complex allocations that include workspaces don't accidentally add
# workspace profiles to the internal equipment stacks. regression test.
@setup.brokers([], 'master', [], True, False)
def t14(HOME, b):
    pretty = '%s t14' % __file__
    print(pretty)

    for i in range(3):
        b2 = RemoteBroker(b.address, home=HOME.path)

        result = b2.get_resource(
            {'type':'relay', 'uid':'master-a'},
            {'type':'handset', 'serial':'master-1'},
            {'type':'workspace'}
        )
        if len(result) != 3:
            print('FAIL %s: wrong number of resources: %s' % (pretty, result))
            return False

        b2.yield_resources(*result)

    return True

# check that stacked equipment can be matched against properties that are not
# visible in the stack, but are in the equipment's full profile
@setup.brokers([], 'master', [], True, False)
def t15(HOME, b):
    pretty = '%s t15' % __file__
    print(pretty)

    try:
        r,h = b.get_resource(
            {'type':'relay', 'pretty':'gustav'},
            {'type':'handset', 'pretty':'mary'}
        )
    except Exception, e:
        print('FAIL %s: allocation failed: %s' % (pretty, str(e)))
        return False

    try:
        r,h = b.get_resource(
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
@setup.brokers([], 'master', [], True, False)
def t16(HOME, b):
    pretty = '%s t16' % __file__
    print(pretty)

    r,h = b.get_resource(
        {'type':'relay', 'circuits':['handset.battery']},
        {'type':'handset'}
    )
    p = r.get_profile()
    e = {
        u'type'       : u'relay',
        u'uid'        : u'master-b',
        u'circuits'   : { 'handset.battery':2 },
        u'power_state': 'online'
    }
    if p != e:
        print('FAIL %s: wrong relay profile: %s' % (pretty, p))
        return False

    return True
