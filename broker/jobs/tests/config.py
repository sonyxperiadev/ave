# coding=utf-8

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import traceback

import ave.config

from ave.workspace          import Workspace
from ave.broker._broker     import Broker, RemoteBroker
from ave.network.connection import find_free_port
from ave.network.exceptions import ConnectionClosed

FLOCKER = {
            "ftp": {
                "password": "ftpuser",
                "store": "/srv/www/flocker",
                "port": 21,
                "timeout": 30,
                "user": "ftpuser"
            },
            "host": "cnbjlx20050",
            "enable" : True,
            "http": {
                "doc-root": "/srv/www",
                "port": 80
            }
        }

def write_config(home, name, content):
    path = os.path.join(home, '.ave', 'config', name)
    with open(path, 'w') as f:
        f.write(content)

def setup(fn):
    def decorated_fn():
        HOME = Workspace()
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
        pm_config = {
            'logging' : False,
            'log_path': os.path.join(HOME.path, 'pm.log'),
            'map_path': os.path.join(HOME.path, 'pm.json')
        }
        write_config(HOME.path, 'powermeter.json', json.dumps(pm_config))
        result = fn(HOME)
        HOME.delete()
        return result
    return decorated_fn

# outdated test
def t1():
    pretty = '%s t1' % __file__
    print(pretty)
    return True

# check that an exception is raised if there is no workspace config file
@setup
def t2(HOME):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'no such configuration file: %s' % HOME.path not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading broken config file
@setup
def t3(HOME):
    pretty = '%s t3' % __file__
    print(pretty)

    # build the mock config file (broken)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "port": 4001 ') # missing end bracket

    try:
        Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'could not load broker configuration file: Expecting' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup
def t4(HOME):
    pretty = '%s t4' % __file__
    print(pretty)

    # build the mock config file with invalid content. "root" has wrong type
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "host": 1 }')

    try:
        Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).endswith('current value=1 (type=<type \'int\'>)'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check error message is OK when loading config file with invalid content
@setup
def t5(HOME):
    pretty = '%s t5' % __file__
    print(pretty)

    # build the mock config file with invalid content. "root" has wrong type
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "host": "valid", "port": "invalid" }')

    try:
        Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).endswith(
            'current value=invalid (type=<type \'unicode\'>)'
        ):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that configuration file overrides default values
@setup
def t6(HOME):
    pretty = '%s t6' % __file__
    print(pretty)

    # build the mock config files. any valid workspace configuration will do
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path,'w') as f:
        config = {
            'root':'~/workspaces',
            'env':[],
            'tools':{},
            'flocker': FLOCKER
        }
        json.dump(config, f)

    # invalid content. "root" has wrong type
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "host": "a.hostname.net", "port": 4001 }')

    try:
        b = Broker(home=HOME.path)
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: Broker.__init__() failed: %s' % (pretty, str(e)))
        return False

    profile = b.get_profile()
    if profile['host'] != 'a.hostname.net':
        print('FAIL %s: wrong hostname: %s' % (pretty, str(profile['host'])))
        return False
    if profile['port'] != 4001:
        print('FAIL %s: wrong port: %s' % (pretty, str(profile['port'])))
        return False

    return True

# check that the stack configuration can only be a list
@setup
def t7(HOME):
    pretty = '%s t7' % __file__
    print(pretty)

    # build the mock config files. invalid content. "stacks" has wrong type
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path,'w') as f:
        config = {
            'stacks': 'nost a list',
            'root':'~/workspaces',
            'env':[],
            'tools':{},
            'flocker': FLOCKER
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "stacks" must be on the'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that each stack must be a list of profiles
@setup
def t8(HOME):
    pretty = '%s t8' % __file__
    print(pretty)

    # invalid content. stacked profiles have wrong type
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "stacks": ["not a profile", ["also","not"]] }')

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "stacks" must be on the'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that stack profiles contain at least one property that can be used to
# uniquely identify a piece of equipment.
@setup
def t9(HOME):
    pretty = '%s t9' % __file__
    print(pretty)

    # invalid content. stacked profile does not contain unique identifiers
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "stacks": [[{"type":"handset", "pretty":"hallon"}]] }')

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('the stacked profile "{u\'type\': u\'handset'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that stacked profiles must contain the "type" attribute
@setup
def t10(HOME):
    pretty = '%s t10' % __file__
    print(pretty)

    # invalid content. stacked profile does not contain unique identifiers
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write('{ "stacks": [[{"serial":"1", "pretty":"hallon"}]] }')

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('the stacked profile "{u\'serial\': u\'1\','):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that stacked profiles that don't actually exist do NOT get rejected. 
# the equipment may come and go during the broker's execution cycle.
@setup
def t11(HOME):
    pretty = '%s t11' % __file__
    print(pretty)

    # any valid workspace configuration will do
    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')

    with open(path,'w') as f:
        config = {
            'root':'~/workspaces',
            'env':[],
            'tools':{},
            'flocker': FLOCKER
        }
        json.dump(config, f)

    config = {
        'stacks': [
            [
                {'type':'handset', 'serial':'1234'},
                {'type':'relay',   'uid':'a'}
            ],[
                {'type':'testdrive', 'uid':'a'},
                {'type':'relay',     'uid':'b'},
                {'type':'handset',   'imei':'c'}
            ]
        ]
    }
    # valid content. broker initialization should not fail
    path = os.path.join(HOME.path, '.ave', 'config', 'broker.json')
    with open(path, 'w') as f:
        f.write(json.dumps(config))

    try:
        b = Broker(home=HOME.path)
    except Exception, e:
        print('FAIL %s: Broker.__init__() failed: %s' % (pretty, str(e)))
        return False

    return True

# check that wellformed 'remote' entries are accepted
@setup
def t12(HOME):
    pretty = '%s t12' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = {
            'remote': { 'host': '0.0.0.0', 'port': 1, 'policy': 'forward' }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
    except Exception, e:
        print('FAIL %s: Broker.__init__() 1 failed: %s' % (pretty, str(e)))
        return False

    with open(path, 'w') as f:
        config = {
            'remote': {
                 'host': 'å.ä.ö', 'port': 00001,
                 'policy': 'share', 'authkey': 'admin_key'
            }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
    except Exception, e:
        print('FAIL %s: Broker.__init__() 2 failed: %s' % (pretty, str(e)))
        return False

    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        json.dump({ 'remote': None }, f)

    try:
        b = Broker(home=HOME.path)
    except Exception, e:
        print('FAIL %s: Broker.__init__() 3 failed: %s' % (pretty, str(e)))
        return False

    return True

# check that a malformed 'remote' entry is rejected
@setup
def t13(HOME):
    pretty = '%s t13' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = { 'remote': ['sunny', 'wheather'] }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "remote" must be on the fo'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry is rejected
@setup
def t14(HOME):
    pretty = '%s t14' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = {
            'remote': { 'host': 1.2 }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "remote" must be on the fo'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry is rejected
@setup
def t15(HOME):
    pretty = '%s t15' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = {
            'remote': { 'host': '0.0.0.0', 'port': 'string' }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "remote" must be on the fo'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry is rejected
@setup
def t16(HOME):
    pretty = '%s t16' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = {
            'remote': { 'host': '0.0.0.0', 'port': 1, 'policy': None }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker attribute "remote" must be on the fo'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry is rejected
@setup
def t17(HOME):
    pretty = '%s t17' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = {
            'remote': { 'host': '0.0.0.0', 'port': 1, 'policy': 'nonsense' }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('broker conguration: remote policy must be'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry with policy=share is rejected
@setup
def t18(HOME):
    pretty = '%s t18' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = { # don't set 'authkey' which is mandatory for remote sharing
            'remote': { 'host': '0.0.0.0', 'port': 1, 'policy': 'share' }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'remote sharing authkey not set' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that a malformed 'remote' entry with policy=share is rejected
@setup
def t19(HOME):
    pretty = '%s t19' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        config = { # try to use non-string authkey
            'remote': {
                'host': '0.0.0.0', 'port': 1,
                'policy': 'share', 'authkey': None
            }
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'remote sharing authkey must be a string' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that malformed config accounts/keys for use in @preauth() decorator are
# rejected
@setup
def t20(HOME):
    pretty = '%s t20' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','authkeys.json')
    with open(path, 'w') as f:
        config = [] # try to use non-dict
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'authkeys.json: contents is not a dictionary' not in unicode(e):
            print('FAIL %s: wrong error message: %s' % (pretty, unicode(e)))
            return False

    return True

# check that malformed config accounts/keys for use in @preauth() decorator are
# rejected
@setup
def t21(HOME):
    pretty = '%s t21' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','authkeys.json')
    with open(path, 'w') as f:
        config = { # try to use non-string account key
            'admin': 1.2
        }
        json.dump(config, f)

    try:
        b = Broker(home=HOME.path)
        print('FAIL %s: Broker.__init__() did not fail' % pretty)
        return False
    except Exception, e:
        if 'value of "admin" is not a string' not in unicode(e):
            print('FAIL %s: wrong error message: %s' % (pretty, unicode(e)))
            return False

    return True

# check that calls to stop() are rejected if the client doesn't use the admin
# authkey
@setup
def t22(HOME):
    pretty = '%s t22' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        json.dump({'logging':False}, f)
    sock,port = find_free_port()
    b = Broker(socket=sock, authkeys={'admin':'key'}, home=HOME.path)
    b.start()

    r = RemoteBroker(('',port), home=HOME.path)

    try:
        r.stop()
        print('FAIL %s: stop() did not fail' % pretty)
        b.join()
        return False
    except Exception, e:
        if 'not authorized to make this call' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            b.terminate()
            b.join()
            return False

    b.terminate()
    b.join()
    return False

# check that calls to stop() are accepted if the client knows the admin authkey
@setup
def t23(HOME):
    pretty = '%s t23' % __file__
    print(pretty)

    ave.config.create_default(HOME.path)
    path = os.path.join(HOME.path,'.ave','config','broker.json')
    with open(path, 'w') as f:
        json.dump({'logging':False}, f)
    sock,port = find_free_port()
    b = Broker(socket=sock, authkeys={'admin':'key'}, home=HOME.path)
    b.start()

    r = RemoteBroker(('',port), authkey='key', home=HOME.path)

    try:
        r.stop()
    except ConnectionClosed:
        pass # good
    except Exception, e:
        print('FAIL %s: admin authkey not accepted: %s' % (pretty, str(e)))
        b.terminate()
        b.join()
        return False

    b.terminate()
    b.join()
    return False
