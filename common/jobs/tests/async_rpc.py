#coding=utf8

# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

from ave.network.control    import RemoteControl
from ave.network.exceptions import *

import setup

# check that the __async__ flag is honoured. expect a None result instead of
# the output from ave.cmd.run()
@setup.factory()
def t01(pretty, factory):
    c = factory.make_control(timeout=None)
    o = c.run_external('sleep 1', __async__=False)

    if o == None:
        print('FAIL %s: got None instead of ave.cmd.run() output' % pretty)
        return False

    if len(o) != 3:
        print('FAIL %s: output length != 3: %s' % (pretty, o))
        return False

    o = c.run_external('sleep 1', __async__=True)

    if o != None:
        print('FAIL %s: did nog get None from async call: %s' % (pretty, o))
        return False

    return True

# check that async connection attempts time out even if default timeout is None
# and the remote end is too busy to accept the connection
@setup.factory()
def t02(pretty, factory):
    c1 = factory.make_control(timeout=None)
    c2 = RemoteControl(c1.address, None, timeout=None)
    c1.run_external('sleep 2', __async__=True)

    try:
        c2.sync_ping(__async__=True)
        print('FAIL %s: implicit connection attempt did not time out' % pretty)
        return False
    except ConnectionTimeout:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception: %s' % (pretty, e))
        return False

    return True

# like t02, but establish the connection first
@setup.factory()
def t03(pretty, factory):
    c1 = factory.make_control(timeout=None)
    c2 = RemoteControl(c1.address, None, timeout=None)
    c2.connect(timeout=None)

    c1.run_external('sleep 2', __async__=True)

    try:
        # should not time out because the connection is already established
        o = c2.sync_ping(__async__=True)
    except Exception, e:
        print('FAIL %s: call failed: %s' % (pretty, e))
        return False

    if o != None:
        print('FAIL %s: wrong return value: %s' % (pretty, o))
        return False

    return True

# like t03 but do ping synchronously instead to check that this still works as
# expected@setup.factory()
@setup.factory()
def t04(pretty, factory):
    c1 = factory.make_control(timeout=None)
    c2 = RemoteControl(c1.address, None, timeout=None)
    c2.connect(timeout=None)

    c1.run_external('sleep 2', __async__=True)

    try:
        o = c2.sync_ping(__async__=False)
    except Exception, e:
        print('FAIL %s: call failed: %s' % (pretty, e))
        return False

    if o != 'pong':
        print('FAIL %s: wrong return value: %s' % (pretty, o))
        return False

    return True

# like t04 but __async__=False is implicit in the call to sync_ping()
@setup.factory()
def t05(pretty, factory):
    c1 = factory.make_control(timeout=None)
    c2 = RemoteControl(c1.address, None, timeout=None)
    c2.connect(timeout=None)

    c1.run_external('sleep 2', __async__=True)

    try:
        o = c2.sync_ping()
    except Exception, e:
        print('FAIL %s: call failed: %s' % (pretty, e))
        return False

    if o != 'pong':
        print('FAIL %s: wrong return value: %s' % (pretty, o))
        return False

    return True

