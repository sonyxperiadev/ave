# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import traceback

import tests.config
import tests.broker
import tests.session
import tests.stacks
import tests.handover
import tests.handset_lister
import tests.remote_forward
import tests.remote_share_basic
import tests.remote_share_stacks
import tests.share_workspace
import tests.spirent
import tests.hickup

def trace(fn):
    def decorated(*vargs, **kwargs):
        try:
            fn(*vargs, **kwargs)
        except:
            traceback.print_exc()
    return decorated

@trace
def all_config():
    tests.config.t1()
    tests.config.t2()
    tests.config.t3()
    tests.config.t4()
    tests.config.t5()
    tests.config.t6()
    tests.config.t7()
    tests.config.t8()
    tests.config.t9()
    tests.config.t10()
    tests.config.t11()
    tests.config.t12()
    tests.config.t13()
    tests.config.t14()
    tests.config.t15()
    tests.config.t16()
    tests.config.t17()
    tests.config.t18()
    tests.config.t19()
    tests.config.t20()
    tests.config.t21()
    tests.config.t22()
    tests.config.t23()

@trace
def all_broker():
    tests.broker.t1()
    tests.broker.t2()
    tests.broker.t3()
    tests.broker.t4()
    tests.broker.t5()
    tests.broker.t6()
    tests.broker.t7()
    tests.broker.t8()
    tests.broker.t9()
    tests.broker.t10()
    tests.broker.t11()
    tests.broker.t12()
    tests.broker.t13()
    tests.broker.t14()
    tests.broker.t15()
    tests.broker.t16()
    tests.broker.t17()
    tests.broker.t18()
    tests.broker.t19()
    tests.broker.t20()
    tests.broker.t21()
    tests.broker.t22()
    tests.broker.t23()
    tests.broker.t24()

@trace
def all_session():
    tests.session.t1()
    tests.session.t2()
    tests.session.t3()
    tests.session.t4()
    tests.session.t5()
    tests.session.t6()
    tests.session.t7()
    tests.session.t8()
    tests.session.t9()
    tests.session.t10()
    tests.session.t11()
    tests.session.t12()
    tests.session.t13()
    tests.session.t14()
    tests.session.t15()

@trace
def all_stacks():
    tests.stacks.t1()
    tests.stacks.t2()
    tests.stacks.t3()
    tests.stacks.t4()
    tests.stacks.t5()
    tests.stacks.t6()
    tests.stacks.t7()
    tests.stacks.t8()
    tests.stacks.t9()
    tests.stacks.t10()
    tests.stacks.t11()
    tests.stacks.t12()
    tests.stacks.t13()
    tests.stacks.t14()
    tests.stacks.t15()
    tests.stacks.t16()

@trace
def all_remote_forward():
    tests.remote_forward.t1()
    tests.remote_forward.t2()
    tests.remote_forward.t3()
    tests.remote_forward.t4()
    tests.remote_forward.t5()
    tests.remote_forward.t6()
    tests.remote_forward.t7()
    tests.remote_forward.t8()
    tests.remote_forward.t9()
    tests.remote_forward.t10()
    tests.remote_forward.t11()
    tests.remote_forward.t12()
    tests.remote_forward.t13()
    tests.remote_forward.t14()

@trace
def all_remote_share_basic():
    tests.remote_share_basic.t1()
    tests.remote_share_basic.t2()
    tests.remote_share_basic.t3()
    tests.remote_share_basic.t4()
    tests.remote_share_basic.t5()
    tests.remote_share_basic.t6()
    tests.remote_share_basic.t7()
    tests.remote_share_basic.t8()
    tests.remote_share_basic.t9()
    tests.remote_share_basic.t10()
    tests.remote_share_basic.t11()
    tests.remote_share_basic.t12()
    tests.remote_share_basic.t13()
    tests.remote_share_basic.t14()
    tests.remote_share_basic.t15()
    tests.remote_share_basic.t16()
    tests.remote_share_basic.t17()
    tests.remote_share_basic.t18()
    tests.remote_share_basic.t19()
    tests.remote_share_basic.t20()
    tests.remote_share_basic.t21()
    tests.remote_share_basic.t22()

@trace
def all_remote_share_workspace():
    tests.share_workspace.t1()
    tests.share_workspace.t2()
    tests.share_workspace.t3()
    tests.share_workspace.t4()
    tests.share_workspace.t5()
    tests.share_workspace.t6()
    tests.share_workspace.t7()
    tests.share_workspace.t8()
    tests.share_workspace.t9()
    tests.share_workspace.t10()
    tests.share_workspace.t11()
    tests.share_workspace.t12()

@trace
def all_remote_share_stacks():
    tests.remote_share_stacks.t1()
    tests.remote_share_stacks.t2()
    tests.remote_share_stacks.t3()
    tests.remote_share_stacks.t4()
    tests.remote_share_stacks.t5()
    tests.remote_share_stacks.t6()
    tests.remote_share_stacks.t7()
    tests.remote_share_stacks.t8()

@trace
def all_handover():
    tests.handover.t1()
    tests.handover.t2()
    tests.handover.t3()
    tests.handover.t4()
    tests.handover.t5()
    tests.handover.t6()
    tests.handover.t7()
    tests.handover.t8()
    tests.handover.t9()
    tests.handover.t10()
    tests.handover.t11()
    tests.handover.t12()
    tests.handover.t13()

@trace
def all_handset_lister(local=False):
    from ave.broker import Broker
    b = Broker()
    h1,r1 = b.get_resource(
        {'type':'handset'}, {'type':'relay', 'circuits':['usb.pc.vcc']}
    )
    h2 = b.get_resource({'type':'handset'})

    if local:
        from ave.handset.handset import Handset
        from ave.handset.profile import HandsetProfile
        h1 = Handset(HandsetProfile(h1.get_profile()))
        h2 = Handset(HandsetProfile(h2.get_profile()))

    # many of the tests manipulate r1 to disconnect h1. close it after each
    # test to make sure the handset is in a usable state
    tests.handset_lister.t1()
    tests.handset_lister.t2(h1,h2,r1)
    r1.set_circuit('usb.pc.vcc', True)
    h1.wait_power_state('boot_completed', 5)
    tests.handset_lister.t3(h1,h2,r1)
    r1.set_circuit('usb.pc.vcc', True)
    h1.wait_power_state('boot_completed', 5)
    tests.handset_lister.t4(h1,h2,r1)
    r1.set_circuit('usb.pc.vcc', True)
    h1.wait_power_state('boot_completed', 5)
    tests.handset_lister.t5(h1,h2,r1)
    r1.set_circuit('usb.pc.vcc', True)
    h1.wait_power_state('boot_completed', 5)
    tests.handset_lister.t6(h1,h2,r1)
    r1.set_circuit('usb.pc.vcc', True)
    h1.wait_power_state('boot_completed', 5)

@trace
def all_spirent():
    tests.spirent.t1()
    tests.spirent.t2()
    tests.spirent.t3()
    tests.spirent.t4()

@trace
def all_hickup():
    tests.hickup.t01()
    tests.hickup.t02()
    tests.hickup.t03()
    tests.hickup.t04()
