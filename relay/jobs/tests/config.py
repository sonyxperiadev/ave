# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import traceback

import ave.relay.config

from ave.workspace       import Workspace
from ave.relay.server    import RelayServer, DEFAULT_PORT_NUMBER
from ave.relay.devantech import DevantechBoard as Relay
from ave.relay.profile   import RelayProfile, BoardProfile

import setup

FILENAME  = 'devantech.json'
PROFILE_1 = BoardProfile({
    'type':'relay','serial':'123','device_node':None, 'vendor':'devantech'
})
PROFILE_2 = BoardProfile({
    'type':'relay','serial':'456','device_node':None, 'vendor':'devantech'
})

# check that an exception is raised if there is no devantech config file
@setup.factory()
def t01(pretty, factory):
    try:
        dev = Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'no such config file: %s' % factory.HOME.path not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading broken config file
@setup.factory()
def t02(pretty, factory):
    # build a broken config file
    path = os.path.join(factory.HOME.path, '.ave', 'config', 'devantech.json')
    with open(path, 'w') as f:
        f.write('{ "serial": "foobar" ') # missing end bracket

    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('could not load config file: Expecting '):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup.factory()
def t03(pretty, factory):
    # build invalid config file
    factory.write_config(FILENAME, {'123':{'groups':{'a':None}}})
    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'group "a" is not a dictionary' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup.factory()
def t04(pretty, factory):
    # build invalid config file. groups must be string:integer dictionaries
    factory.write_config(FILENAME, {'123':{'groups':{'a':{'foo':'bar'}}}})
    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'circuit "foo" is not an integer' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup.factory()
def t05(pretty, factory):
    # build config file with invalid content. group contains a circuit with
    # an unknown label "foo"
    factory.write_config(FILENAME, {'123':{'groups':{'a':{'foo':5}}}})
    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'circuit identifier "foo" is invalid' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup.factory()
def t06(pretty, factory):
    # build invalid config file. circuit number is out of bounds
    factory.write_config(
        FILENAME, {'123':{'groups':{'a':{'usb.pc.vcc':9}}}}
    )
    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'port 9 is out of bounds' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that circuit numbers cannot be referenced more than once
@setup.factory()
def t07(pretty, factory):
    # build invalid config file. circuit number is used twice
    factory.write_config(FILENAME, {
        '123':{ 'groups':{
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':2} }}})
    try:
        Relay(PROFILE_1, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'port 2 is used more than once' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a valid configuration is accepted
@setup.factory()
def t08(pretty, factory):
    # build valid config file
    factory.write_config(FILENAME, {
        '123':{ 'groups': {
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}}},
        '456':{ 'groups': {
            'group_1':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'group_2':{'usb.pc.vcc':5, 'usb.pc.d+':6}}} })
    try:
        r = Relay(PROFILE_1, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: could not initialize: %s' % (pretty, str(e)))
        return False

    expect = {
        'groups': {
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':4},
        },
        'defaults': [1,1,1,1,1,1,1,1]
    }
    if r.config != expect:
        print('FAIL %s: wrong config applied: %s' % (pretty, r.config))
        return False

    return True

# check that a config that does not mention the serial used in the device
# profile is not accepted
@setup.factory()
def t09(pretty, factory):
    # build invalid config file
    factory.write_config(FILENAME, {
        '123':{ 'groups': {
            'group_1':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'group_2':{'usb.pc.vcc':3, 'usb.pc.d+':4}}},
        '456':{ 'groups': {
            'group_1':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'group_2':{'usb.pc.vcc':3, 'usb.pc.d+':4}}} })
    try:
        profile = BoardProfile({
            'type':'relay','serial':'serial_3','device_node':None,
            'vendor':'devantech'
        })
        Relay(profile, home=factory.HOME.path)
        print('FAIL %s: __init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'no values for device with serial' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that multiple relays can be created from the same config if "serial" is
# set to "*" in the config
@setup.factory()
def t10(pretty, factory):
    # build valid config file
    factory.write_config(FILENAME, {
        '*':{ 'groups':{
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}}} })
    try:
        r1 = Relay(PROFILE_1, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: first __init__() failed: %s' % (pretty, e))
        return False

    try:
        r2 = Relay(PROFILE_2, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: first __init__() failed: %s' % (pretty, e))
        return False

    expect = {
        'groups': {
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}
        },
        'defaults':[1,1,1,1,1,1,1,1]
    }
    if r1.config != expect:
        print('FAIL %s: wrong config 1 applied: %s' % (pretty, r1.config))
        return False
    if r2.config != expect:
        print('FAIL %s: wrong config 2 applied: %s' % (pretty, r2.config))
        return False

    return True

# check that an explicit mention of a serial number in the configuration has
# precendence over the "*" wildcard
@setup.factory()
def t11(pretty, factory):
    # build valid config file
    factory.write_config(FILENAME, {
        '*':{ 'groups':{
                'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
                'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}}},
        '456':{ 'groups':{
                'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
                'b':{'usb.pc.vcc':5, 'usb.pc.d+':6}}} })

    try:
        r1 = Relay(PROFILE_1, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: first __init__() failed: %s' % (pretty, e))
        return False

    try:
        r2 = Relay(PROFILE_2, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: first __init__() failed: %s' % (pretty, e))
        return False

    expect = {
        'groups':{
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}
        },
        'defaults':[1,1,1,1,1,1,1,1]
    }
    if r1.config != expect:
        print('FAIL %s: wrong config 1 applied: %s' % (pretty, r1.config))
        return False

    expect = {
        'groups':{
            'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
            'b':{'usb.pc.vcc':5, 'usb.pc.d+':6}
        },
        'defaults':[1,1,1,1,1,1,1,1]
    }
    if r2.config != expect:
        print('FAIL %s: wrong config 2 applied: %s' % (pretty, r2.config))
        return False

    return True

# check that default values for circuits are understood
@setup.factory()
def t12(pretty, factory):
    # build valid config file
    factory.write_config(FILENAME, {
        '*':{
            'groups': {
                'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
                'b':{'usb.pc.vcc':3, 'usb.pc.d+':4}},
            'defaults':[1,0,1,0,1,1,1,1]},
        '456':{
            'groups':{
                'a':{'usb.pc.vcc':1, 'usb.pc.d+':2},
                'b':{'usb.pc.vcc':5, 'usb.pc.d+':6}},
            'defaults':[0,1,0,1,0,0,0,0]} })

    try:
        r = Relay(PROFILE_1, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: __init__() failed: %s' % (pretty, e))
        return False

    if r.config['defaults'] != [1,0,1,0,1,1,1,1]:
        print('FAIL %s: wrong defaults 1: %s' % (pretty, r.config['defaults']))
        return False

    try:
        r = Relay(PROFILE_2, home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: __init__() failed: %s' % (pretty, e))
        return False

    if r.config['defaults'] != [0,1,0,1,0,0,0,0]:
        print('FAIL %s: wrong defaults 2: %s' % (pretty, r.config['defaults']))
        return False

    return True

# check that the absence of config file for relay server is ok
@setup.factory()
def t13(pretty, factory):
    factory.write_config('authkeys.json', {'admin':None}) # always needed

    try:
        r = RelayServer(home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: __init__() failed: %s' % (pretty, e))
        return False

    if r.config != {'port':DEFAULT_PORT_NUMBER, 'logging':True}:
        print('FAIL %s: wrong config: %s' % (pretty, r.config))
        return False

    return True

# check that an empty config file for relay server is ok
@setup.factory()
def t14(pretty, factory):
    factory.write_config('authkeys.json', {'admin':None}) # always needed
    factory.write_config('relay.json', {})

    try:
        r = RelayServer(home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: __init__() failed: %s' % (pretty, e))
        return False

    if r.config != {'port':DEFAULT_PORT_NUMBER, 'logging':True}:
        print('FAIL %s: wrong config: %s' % (pretty, r.config))
        return False

    return True

# check that a valid config file is accepted
@setup.factory()
def t15(pretty, factory):
    factory.write_config('authkeys.json', {'admin':None}) # always needed
    factory.write_config('relay.json', {'port':12345, 'logging':False})

    try:
        r = RelayServer(home=factory.HOME.path)
    except Exception, e:
        print('FAIL %s: __init__() failed: %s' % (pretty, e))
        return False

    if r.config != {'port':12345, 'logging':False}:
        print('FAIL %s: wrong config: %s' % (pretty, r.config))
        return False

    return True

# can a valid devantech config file be generated but not overwritten?
@setup.factory()
def t16(pretty, factory):
    try:
        ave.relay.config.write_devantech_config(factory.HOME.path)
    except Exception, e:
        print('FAIL %s: could not write config: %s' % (pretty, e))
        return False

    try:
        ave.relay.config.write_devantech_config(factory.HOME.path)
        print('FAIL %s: could overwrite existing config' % pretty)
        return False
    except Exception, e:
        if 'will not overwrite' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True
