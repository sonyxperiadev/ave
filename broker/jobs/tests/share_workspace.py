# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import time
import errno
import traceback

from ave.network.connection import find_free_port
from ave.network.control    import Control
from ave.broker._broker     import Broker, RemoteBroker
from ave.broker.allocator   import LocalAllocator
from ave.broker.profile     import HandsetProfile, WorkspaceProfile
from ave.workspace          import Workspace

import setup

# check that anonymous workspaces can be allocated
@setup.factory()
def t1(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True)

    time.sleep(1)
    try:
        w,h = master.get_resources(
            {'type':'workspace'},{'type':'handset','serial':'slave-1'}
        )
    except Exception, e:
        print('FAIL %s: could not allocate workspace: %s' % (pretty, str(e)))
        return False

    # where did the workspace get created?
    root = w.get_profile()['root']
    if not root.endswith('slave'):
        print('FAIL %s: wrong workspace path: %s' % (pretty, root))
        return False
    return True

# check that specific workspaces can be matched, if they exist
@setup.factory()
def t2(factory):
    pretty = '%s t2' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True)

    time.sleep(1)
    # first request should just work
    w,h = master.get_resources(
        {'type':'workspace'},{'type':'handset','serial':'slave-1'}
    )

    # ask for the same workspace again
    try:
        uid = w.get_profile()['uid']
        w = master.get_resource({'type':'workspace', 'uid':uid})
    except Exception, e:
        print('FAIL %s: could not allocate workspace: %s' % (pretty, str(e)))
        return False

    # where did the workspace get created?
    profile = w.get_profile()
    if not profile['root'].endswith('slave'):
        print('FAIL %s: wrong workspace path: %s' % (pretty, profile['root']))
        return False

    # check that there is only one workspace in the slave
    avail = slave.list_workspaces()
    if len(avail) != 1 or avail[0]['uid'] != profile['uid']:
        print('FAIL %s: wrong slave avail: %s' % (pretty, avail))
        return False
    avail = master.list_workspaces()
    if len(avail) != 0:
        print('FAIL %s: wrong master avail: %s' % (pretty, avail))
        return False

    return True

# check that specific workspaces cannot be matched, if they don't exist
@setup.factory()
def t3(factory):
    pretty = '%s t3' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True)

    time.sleep(1)
    # ask for resources on the slave, including a workspace that doesn't exist
    try:
        w = master.get_resource(
            {'type':'workspace', 'uid':'does-not-exist'},
            {'type':'handset','serial':'slave-1'}
        )
        print('FAIL %s: could allocate workspace: %s')
        return False
    except Exception, e:
        if not str(e).startswith('no such workspace'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    # check that no workspace got created
    avail = slave.list_workspaces()
    if len(avail) != 0:
        print('FAIL %s: wrong slave avail: %s' % (pretty, avail))
        return False
    avail = master.list_workspaces()
    if len(avail) != 0:
        print('FAIL %s: wrong master avail: %s' % (pretty, avail))
        return False

    return True

# check that a specific request is routed to the correct slave. workspace uid
# must include broker specific prefix
@setup.factory()
def t4(factory):
    pretty = '%s t4' % __file__
    print(pretty)

    master  = factory.make_master('master', [])
    slave_a = factory.make_share(master, 'slave-a', True)
    slave_b = factory.make_share(master, 'slave-b', True)

    time.sleep(1)
    w,h = master.get_resource(
        {'type':'workspace'},
        {'type':'handset','serial':'slave-b-1'}
    )

    # check that no workspace got created
    profile = w.get_profile()
    if not profile['uid'].startswith('slave-b-'):
        print('FAIL %s: wrong prefix: %s' % (pretty, profile['uid']))
        return False
    avail = slave_a.list_workspaces()
    if len(avail) != 0:
        print('FAIL %s: wrong slave b avail: %s' % (pretty, avail))
        return False
    avail = slave_b.list_workspaces()
    if len(avail) != 1:
        print('FAIL %s: wrong slave b avail: %s' % (pretty, avail))
        return False

    return True

# check that workspaces that are allocated/freed in the slave are added/removed
# in the master
@setup.factory()
def t5(factory):
    pretty = '%s t5' % __file__
    print(pretty)

    master = factory.make_master('master')
    slave  = factory.make_share(master, 'slave', True)

    for i in range(10): # wait for non-local allocator to appear
        allocators = master.list_allocators()
        if len(allocators) > 1:
            break
        time.sleep(0.3)

    # make a new slave connection so that we can close it by garbage collecting
    # it. the 'slave' parameter is held by the setup, so del(slave) won't work
    client = RemoteBroker(slave.address, home=factory.HOME.path)

    # allocate directly from the slave
    w = client.get_resource({'type':'workspace'})

    # check that the master sees the new workspace
    ok = False
    for i in range(10):
        result = master.list_workspaces(None, allocators)
        if result:
            if result[0]['pretty'].startswith('slave'):
                ok = True
                break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: slave workspace was not added to master' % pretty)
        return False

    # free resources in the slave (by closing the session)
    del client

    # check that the master no longer sees the new workspace
    ok = False
    for i in range(10):
        result = master.list_workspaces(None, allocators)
        if not result:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: slave workspace was not removed from master' % pretty)
        return False

    return True

# like t5, but yield the resource instead of closing the session
@setup.factory()
def t6(factory):
    pretty = '%s t6' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True, [])

    time.sleep(1)
    allocators = master.list_allocators() # slave already registered in setup

    # allocate directly from the slave. reconnect to slave first to avoid using
    # admin access (the factory defaults the slave connection to use it).
    slave = RemoteBroker(slave.address, home=factory.HOME.path)
    w = slave.get_resource({'type':'workspace'})

    # check that the master sees the new workspace
    ok = False
    for i in range(10):
        result = master.list_workspaces(None, allocators)
        if result:
            if result[0]['pretty'] == 'slave':
                ok = True
                break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: slave workspace was not added to master' % pretty)
        return False

    # free resources in the slave (by disconnecting the client)
    slave.yield_resources(w)

    # check that the master no longer sees the new workspace
    ok = False
    for i in range(10):
        result = master.list_workspaces(None, allocators)
        if not result:
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: slave workspace was not removed from master' % pretty)
        return False

    return True

# check that session ownership of workspaces is respected
#@setup.brokers([], 'master', ['slave'], True, True)
#def t7(HOME, master, slave):
@setup.factory()
def t7(factory):
    pretty = '%s t7' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True, [])

    time.sleep(1)
    allocators = master.list_allocators() # slave already registered in setup

    # allocate directly from the slave. reconnect to slave first to avoid using
    # admin access (the factory defaults the slave connection to use it).
    slave = RemoteBroker(slave.address, home=factory.HOME.path)
    w = slave.get_resource({'type':'workspace'})

    # wait for the workspace to show up in the master
    ok = False
    for i in range(10):
        result = master.list_workspaces(None, allocators)
        if result:
            if result[0]['pretty'] == 'slave':
                ok = True
                break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: slave workspace was not added to master' % pretty)
        return False

    # try to allocate the same workspace again but through the master. this
    # will cause a new session to be created in the slave, which shouldn't be
    # allowed to allocate the workspace because it's owned by the session that
    # was created in the original request
    try:
        uid = w.get_profile()['uid']
        w = master.get_resource({'type':'workspace', 'uid':uid})
        print('FAIL %s: session ownership not respected' % pretty)
        return False
    except Exception, e:
        if 'resource already allocated' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that other workspace attributes than uid can be matched. e.g. if the
# 'pretty' attributes of different slaves are known to the client.
@setup.factory()
def t8(factory):
    pretty = '%s t8' % __file__
    print(pretty)

    master = factory.make_master('master', [])
    slave  = factory.make_share(master, 'slave', True)

    time.sleep(1)
    allocators = master.list_allocators() # slave already registered in setup
    equipment  = master.list_equipment()

    try:
        w,h = master.get_resources(
            {'type':'workspace','pretty':'slave'},
            {'type':'handset'}
        )
    except Exception, e:
        print('FAIL %s: allocation failed: %s' % (pretty, str(e)))
        return False

    # check that the handset was visible in the master before allocation
    if HandsetProfile(h.get_profile()) not in equipment:
        print(
            'FAIL %s: handset was not visible in master before allocation: %s'
            % (pretty, equipment)
        )
        return False


    equipment  = master.list_equipment()
    # check that the handset is still listed in equipment
    if HandsetProfile(h.get_profile()) not in equipment:
        print(
            'FAIL %s: handset was not visible in master before allocation: %s'
            % (pretty, equipment)
        )
        return False

    # check that one of the slave handsets have been allocated from the master
    ok = False
    for i in range(10):
        equipment = master.list_available()
        if HandsetProfile(h.get_profile()) not in equipment:
            ok = True
            break
    if not ok:
        print('FAIL %s: slave handset not allocated on master' % pretty)
        return False

    return True

# workspace allocation should default to a local workspace, like handsets do,
# when there are shares involved
@setup.factory()
def t9(factory):
    pretty = '%s t9' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=True)

    ok = True
    for i in range(10):
        if master.list_shares() != []:
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: share did not register' % pretty)
        return False

    w = master.get({'type':'workspace'})
    if w.profile['pretty'] != 'master':
        print('FAIL %s: allocated on wrong host: %s' % (pretty, w.profile))
        return False

    return True

# explicitly allocate workspace from master, not the share
@setup.factory()
def t10(factory):
    pretty = '%s t10' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=True)

    ok = True
    for i in range(10):
        if master.list_shares() != []:
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: share did not register' % pretty)
        return False

    w = master.get({'type':'workspace', 'pretty':'master'})
    if w.profile['pretty'] != 'master':
        print('FAIL %s: allocated on wrong host: %s' % (pretty, w.profile))
        return False

    return True

# like t9, but with a share allocation done first
@setup.factory()
def t11(factory):
    pretty = '%s t11' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=True)

    ok = True
    for i in range(10):
        if master.list_shares() != []:
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: share did not register' % pretty)
        return False

    w = master.get({'type':'workspace', 'pretty':'share'})
    if w.profile['pretty'] != 'share':
        print('FAIL %s: did not allocate on share: %s' % (pretty, w.profile))
        return False

    w = master.get({'type':'workspace'})
    if w.profile['pretty'] != 'master':
        print('FAIL %s: allocated on wrong host: %s' % (pretty, w.profile))
        return False

    return True

# like t10 but with a share allocation done first
@setup.factory()
def t12(factory):
    pretty = '%s t12' % __file__
    print(pretty)

    master = factory.make_master('master')
    share  = factory.make_share(master, 'share', autoshare=True)

    ok = True
    for i in range(10):
        if master.list_shares() != []:
            break
        time.sleep(0.1)
    if not ok:
        print('FAIL %s: share did not register' % pretty)
        return False

    w = master.get({'type':'workspace', 'pretty':'share'})
    if w.profile['pretty'] != 'share':
        print('FAIL %s: did not allocate on share: %s' % (pretty, w.profile))
        return False

    w = master.get({'type':'workspace', 'pretty':'master'})
    if w.profile['pretty'] != 'master':
        print('FAIL %s: allocated on wrong host: %s' % (pretty, w.profile))
        return False

    return True
