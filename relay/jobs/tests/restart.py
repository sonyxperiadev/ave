# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import time

from ave.broker._broker     import RemoteBroker
from ave.network.exceptions import *
from ave.network.connection import find_free_port
from ave.relay.profile      import BoardProfile, RelayProfile

import setup

# check that handing over from one server to another works. check that the
# original server raises Restarting exceptions after the restart is initiated.
@setup.factory()
def t1(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)

    handover = factory.make_server()

    try:
        state = handover.begin_handover()
    except Exception, e:
        print('FAIL %s: could not begin handover: %s' % (pretty, e))
        return False

    try:
        profile = {'type':'relay','uid':'abc2.a'}
        handover.reset_board_group(profile)
    except Restarting:
        pass
    except Exception, e:
        print('FAIL %s: did not raise Restarting: %s' % (pretty, e))
        return False

    try:
        takeover = factory.make_server(state['boards'])
    except Exception, e:
        print('FAIL %s: could not create takeover: %s' % (pretty, e))
        return False

    try:
        handover.end_handover()
    except ConnectionClosed:
        pass
    except Exception, e:
        print('FAIL %s: wrong exception when ending handover: %s' % (pretty, e))
        return False

    return True

# check that boards are not reset during server restart
@setup.factory()
def t2(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()

    profile = {'type':'relay','uid':'abc2.a'}

    # create a server with a couple of boards. change the state of some circuit
    handover = factory.make_server()
    handover.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])
    handover.set_board_circuit(profile, 'usb.pc.vcc', False)

    try:
        state = handover.begin_handover()
    except Exception, e:
        print('FAIL %s: could not begin handover: %s' % (pretty, e))
        return False

    # create a replacement server, pretend that a lister is adding the same
    # boards to it as the original server
    try:
        takeover = factory.make_server(state['boards'])
        takeover.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])
    except Exception, e:
        print('FAIL %s: could not create takeover: %s' % (pretty, e))
        return False

    try:
        handover.end_handover()
    except: # ConnectionClosed
        pass

    # find the affected board in the replacement server state and check that
    # the circuit state is unaffected
    server_state = takeover.serialize()
    board_state  = None
    for board in server_state['boards']:
        if board['serial'] == 'abc2':
            board_state = board['state']
    if not board_state:
        print('FAIL %s: could not find board in server state' % pretty)
        return False

    if 0 not in board_state:
        print('FAIL %s: wrong board state: %s' % (pretty, board_state))
        return False

    return True

# check that real clients that allocated the resource through a broker cannot
# detect that a restart is ongoing
@setup.factory()
def t3(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    client = RemoteBroker(b.address)
    admin = RemoteBroker(b.address,authkey='admin')

    # create a server with a couple of boards
    handover = factory.make_server()
    handover.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])

    # wait for added boards to become available in the broker
    ok = False
    wanted = RelayProfile(setup.RELAY_3)
    for i in range(10):
        if wanted in admin.list_available():
            ok = True
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: boards not available' % pretty)
        return False

    # let the client allocate a relay and manipulate it to make sure it has
    # connected to the relay server
    relay = client.get({
        'type':'relay','circuits':['usb.pc.vcc','handset.battery']
    })
    relay.set_circuit('usb.pc.vcc', False)

    # hand over to the replacement server
    state = handover.begin_handover()
    takeover = factory.make_server(state['boards'], make_socket=False)
    takeover.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])
    handover.end_handover(__async__=True)

    try:
        relay.set_circuit('handset.battery', False)
    except AveException, e:
        print e.format_trace()
        print('FAIL %s: could not set battery circuit: %s' % (pretty, e))
        return False

    return True

