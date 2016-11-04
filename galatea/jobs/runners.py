# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os

from ave.broker import Broker

import tests.atf

def all_atf(local=False):
    b = Broker()

    if local:
        prefix = os.path.dirname(os.path.dirname(__file__))
        prefix = os.path.join(prefix, 'packaging')
    else:
        prefix = '/'
    apk_dir = os.path.join(prefix, 'usr','share','ave','galatea')

    h = b.get_resources({ 'type':'handset', 'platform':'android' })
    h.reinstall(os.path.join(apk_dir,'galatea-kk-mr1-shinano2.apk'))

    h.disable_keyguard()
    h.stay_awake(True)

    tests.atf.t1(h)
    tests.atf.t2(h)
    tests.atf.t3(h)
    tests.atf.t4(h)
    tests.atf.t5(h)
    tests.atf.t6(h)
    tests.atf.t7(h)
    tests.atf.t8(h)
    tests.atf.t9(h)
    tests.atf.t10(h)

    h.stay_awake(False)
