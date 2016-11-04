# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import time
import traceback

from datetime  import datetime, timedelta
from functools import wraps

from ave.exceptions import Timeout
from ave.handset.adb_handset import AdbForward, run_adb

from decorators import smoke, test_by_assertion

def forward_cleanup(fn):
    @wraps(fn)
    def cleaner(h1, h2, *args, **kwargs):
        try:
            return fn(h1, h2, *args, **kwargs)
        finally:
            h1.close_forwarded_port('all')
            h2.close_forwarded_port('all')
    return cleaner

# Test that setting up the same forward twice in a row is not a problem.
@smoke
@test_by_assertion
@forward_cleanup
def t01(h,_):
    try:
        entry = h.open_forwarded_port('tcp:50111')
    except Exception, e:
        assert False, 'could not open/close the port once: %s' % e

    try:
        entry = h.open_forwarded_port('tcp:50111')
    except Exception, e:
        assert False, 'could not open/close the port twice: %s' % e

# Test that binding the same remote port twice at the same time is not a problem
@smoke
@test_by_assertion
@forward_cleanup
def t02(h,_):
    entry = h.open_forwarded_port('tcp:50111')
    try:
        entry = h.open_forwarded_port('tcp:50111')
    except Exception, e:
        assert False, 'could not open the port twice: %s' % e

# check that close_forwarded_port() can remove single entries
@smoke
@test_by_assertion
@forward_cleanup
def t03(h,_):
    # add the same remote port twice, then check that they were collapsed into
    # the same forwarding rule.
    local1 = h.open_forwarded_port('tcp:50668')
    local2 = h.open_forwarded_port('tcp:50668')

    forwards = h.list_forwarded_ports()
    assert len(forwards) == 1
    assert local1 in [f[1] for f in forwards]
    assert local2 in [f[1] for f in forwards]

    # closing one will close "both", which were really the same
    h.close_forwarded_port(local2)
    assert len(h.list_forwarded_ports()) == 0

# check that close_forwarded_port() can remove all entries
@smoke
@test_by_assertion
@forward_cleanup
def t04(h,_):
    h.open_forwarded_port('tcp:50669')
    h.open_forwarded_port('tcp:50669')

    h.close_forwarded_port('all')
    assert len(h.list_forwarded_ports()) == 0

# check that power cycling the handset removes all forwarded ports
@smoke
@test_by_assertion
@forward_cleanup
def t05(h,_):
    h.open_forwarded_port('tcp:50670')
    h.open_forwarded_port('tcp:50670')

    h.reboot()
    assert len(h.list_forwarded_ports()) == 0

    h.wait_power_state('boot_completed')
    assert len(h.list_forwarded_ports()) == 0

# check that we can't remove other devices' forwards
@smoke
@test_by_assertion
@forward_cleanup
def t06(h1,h2):
    # forward a couple of ports on both, then try to remove them through the
    # wrong handset.
    p1 = h1.open_forwarded_port('tcp:50671')
    p2 = h2.open_forwarded_port('tcp:50671')

    assert h1.list_forwarded_ports() == [[h1.profile['serial'],p1,'tcp:50671']]
    assert h2.list_forwarded_ports() == [[h2.profile['serial'],p2,'tcp:50671']]

    try:
        h1.close_forwarded_port(p2)
        assert False, 'closing p2 through h1 did not raise exception'
    except Exception, e:
        assert 'no such port forwarding entry' in str(e)

    assert h1.list_forwarded_ports() == [[h1.profile['serial'],p1,'tcp:50671']]
    assert h2.list_forwarded_ports() == [[h2.profile['serial'],p2,'tcp:50671']]

    h1.close_forwarded_port('all')

    assert h1.list_forwarded_ports() == []
    assert h2.list_forwarded_ports() == [[h2.profile['serial'],p2,'tcp:50671']]

# check that we can't remove a forward twice
@smoke
@test_by_assertion
@forward_cleanup
def t07(h,_):
    p1 = h.open_forwarded_port('tcp:50672')
    p2 = h.open_forwarded_port('tcp:50672')

    forwarded = h.list_forwarded_ports()
    assert [h.profile['serial'],p1,'tcp:50672'] in forwarded
    assert [h.profile['serial'],p2,'tcp:50672'] in forwarded
    assert p1 == p2

    h.close_forwarded_port(p1)
    try:
        h.close_forwarded_port(p1)
        assert False, 'could close the same port twice'
    except Exception, e:
        assert 'no such port forwarding entry: %s' % p1 in str(e), str(e)

# other input validation
@smoke
@test_by_assertion
@forward_cleanup
def t08(h,_):
    p1 = h.open_forwarded_port('tcp:50673')
    p2 = h.open_forwarded_port('tcp:50673')

    try:
        h.close_forwarded_port(None)
        assert False, 'could close entry None'
    except Exception, e:
        assert 'invalid port forwarding entry' in str(e), str(e)

    try:
        h.close_forwarded_port(123)
        assert False, 'could close entry 123'
    except Exception, e:
        assert 'invalid port forwarding entry' in str(e), str(e)

# check the global ADB limit on the number of simultaneous forwarders
@smoke
@test_by_assertion
@forward_cleanup
def t09(h1,h2):
    # ADB can not handle more than about 950 forwards *globally*. use them all
    # up with two handsets.
    # unfortunately the global limit varies a *lot* depending on whatever the
    # current stability of ADB happens to be. it's very unpredictable.
    taken = len(h1.list_forwarded_ports(all_adb=True))

    for i in range(450-(int(taken/2))):
        try:
            h1.open_forwarded_port('tcp:%d' % (2000+i))
            h2.open_forwarded_port('tcp:%d' % (3000+i))
        except Exception, e:
            print 'FAIL: %s' % e
            assert False, 'could not forward 900 ports: %s' % e

    try:
        h1.open_forwarded_port('tcp:5768') # whatever
        assert False, 'could forward 901 ports'
    except Exception, e:
        assert 'ADB is close to forwarding entry limits' in str(e), str(e)
