# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import time

from ave.broker._broker     import RemoteBroker
from ave.network.exceptions import *
from ave.network.connection import find_free_port
from ave.relay.profile      import BoardProfile, RelayProfile

import setup

# check that relay equipment can be added to a broker. use mocked equipment
@setup.factory()
def t1(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    s = factory.make_server()

    # pretend to be a lister. add mocked boards to the server. expect them to
    # show up in the broker
    s.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])

    for i in range(3):
        relays = b.list_equipment({'type':'relay'})
        if relays:
            break
        time.sleep(0.5)
    if not relays:
        print('FAIL %s: no relays listed by broker' % pretty)
        return False

    try:
        relays = [RelayProfile(r) for r in relays]
    except Exception, e:
        print('FAIL %s: invalid board profiles: %s' % (pretty, relays))
        return False

    if (setup.RELAY_1 not in relays
    or  setup.RELAY_2 not in relays
    or  setup.RELAY_3 not in relays):
        print('FAIL %s: wrong boards: %s' % (pretty, relays))
        return False

    return True

# check that relays get added to a broker even if the relay server was started
# before the broker
@setup.factory()
def t2(pretty, factory):
    factory.write_config('devantech.json', {}) # TODO: get rid of this one
    factory.write_config('authkeys.json', setup.AUTHKEYS)

    sock,port = find_free_port()
    factory.write_config('broker.json', {'port':port, 'logging':False})
    broker = factory._make_broker(sock,port)

    s = factory.make_server()
    s.set_boards([setup.BOARD_1,setup.BOARD_2,setup.BOARD_3])

    time.sleep(1)
    broker.start()
    factory.processes.append(broker)
    b = RemoteBroker(('',port), 1, 'admin', factory.HOME.path)

    for i in range(3):
        relays = b.list_equipment({'type':'relay'})
        if relays:
            break
        time.sleep(0.5)
    if not relays:
        print('FAIL %s: no relays listed by broker' % pretty)
        return False

    try:
        relays = [RelayProfile(r) for r in relays]
    except Exception, e:
        print('FAIL %s: invalid board profiles: %s' % (pretty, relays))
        return False

    if (setup.RELAY_1 not in relays
    or  setup.RELAY_2 not in relays
    or  setup.RELAY_3 not in relays):
        print('FAIL %s: wrong relays: %s' % (pretty, relays))
        return False

    return True

def add_boards(server, boards, broker):
    server.set_boards(boards)
    for i in range(3):
        relays = broker.list_equipment({'type':'relay'})
        if relays:
            break
        time.sleep(0.5)
    if not relays:
        print('FAIL %s: no relays listed by broker' % pretty)
        return False
    return True

# check that relays can be allocated through the broker
@setup.factory()
def t3(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    s = factory.make_server()

    if not add_boards(s, [setup.BOARD_1,setup.BOARD_2,setup.BOARD_3], b):
        return False

    try:
        c = RemoteBroker(b.address, home=factory.HOME.path)
        r = c.get({'type':'relay'})
    except AveException, e:
        print('FAIL %s: could not allocate: %s' % (pretty, e))
        return False

    try:
        c = RemoteBroker(b.address, home=factory.HOME.path)
        r = c.get({'type':'relay', 'circuits':['handset.battery']})
    except AveException, e:
        print('FAIL %s: could not allocate: %s' % (pretty, e))
        return False

    if r.profile['uid'] not in ['abc3.a', 'abc3.b']:
        print('FAIL %s: wrong profile: %s' % (pretty, r.profile))
        return False

    return True

# check that yielded relays are reset by the broker
@setup.factory()
def t4(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    s = factory.make_server()

    if not add_boards(s, [setup.BOARD_1,setup.BOARD_2,setup.BOARD_3], b):
        return False

    c = RemoteBroker(b.address, home=factory.HOME.path)
    r = c.get({'type':'relay', 'circuits':['handset.battery']})
    r.set_circuit('handset.battery', False)

    # find the affected board in the serialized server state and remember its
    # changes
    server_state = s.serialize()
    board_state  = None
    for board in server_state['boards']:
        if r.profile['uid'].startswith(board['serial']):
            board_state = board['state']
    if not board_state:
        print('FAIL %s: could not find board in server state' % pretty)
        return False

    if 0 not in board_state:
        print(
            'FAIL %s: set_circuit() did not flip any port: %s'
            % (pretty, board_state)
        )
        return False

    del(c) # yield all allocated resources
    time.sleep(1)

    # get the board state again and check that it has been reset
    server_state = s.serialize()
    board_state  = None
    for board in server_state['boards']:
        if r.profile['uid'].startswith(board['serial']):
            board_state = board['state']
    if not board_state:
        print('FAIL %s: could not find board in server state' % pretty)
        return False

    if 0 in board_state:
        print(
            'FAIL %s: yielded relay was not reset: %s' % (pretty, board_state)
        )
        return False

    return True

# check that time stamps are returned when manipulating relays
@setup.factory()
def t5(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    s = factory.make_server()

    if not add_boards(s, [setup.BOARD_1,setup.BOARD_2,setup.BOARD_3], b):
        return False

    c = RemoteBroker(b.address, home=factory.HOME.path)
    r = c.get({'type':'relay', 'circuits':['handset.battery']})

    stamp1 = r.set_circuit('handset.battery', False)
    time.sleep(0.5)
    stamp2 = r.reset()

    if stamp1 == stamp2:
        print('FAIL %s: got same stamp twice: %s %s' % (pretty, stamp1, stamp2))
        return False

    if len(stamp1) != len(stamp2) != 7:
        print('FAIL %s: stamps have wrong length: %s' % (pretty,stamp1,stamp2))
        return False

    if [i for i in stamp1 if type(i) != int] != []:
        print('FAIL %s: stamp 1 not made of integers: %s' % (pretty, stamp1))
        return False

    if [i for i in stamp2 if type(i) != int] != []:
        print('FAIL %s: stamp 2 not made of integers: %s' % (pretty, stamp1))
        return False

    return True

# check that allocated relays cannot manipulate circuits that were not named
# in the allocation
@setup.factory()
def t6(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    b = factory.make_broker()
    s = factory.make_server()

    if not add_boards(s, [setup.BOARD_1,setup.BOARD_2,setup.BOARD_3], b):
        return False

    c = RemoteBroker(b.address, home=factory.HOME.path)
    r = c.get({'type':'relay', 'circuits':['handset.battery']})

    try:
        r.set_circuit('usb.pc.vcc', False)
        print('FAIL %s: could manipulate circuit' % pretty)
        return False
    except Exception, e:
        if 'named circuit not in allocated relay' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True
