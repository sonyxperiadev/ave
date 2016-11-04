# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys
import json
import errno
import socket
import random

import ave.cmd
import ave.pwd

flocker = {
    "enable": False,
    'host': '',
    'ftp': {
        'port':  None,
        'user': '',
        'password': '',
        'timeout': 30,
        'store': ''
    },
    'http': {
        'port': None,
        'doc-root': ''
    }
}

def rand_authkey():
    result = []
    for i in range(10):
        result.append(random.randint(0,9))
    return ''.join(['%d' % i for i in result])

def create_default(home):
    created = []
    skipped = []

    # create the default AVE configuration
    try:
        os.makedirs(os.path.join(home, '.ave', 'config'))
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    path = os.path.join(home, '.ave', 'config', 'broker.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'host'  : socket.gethostbyaddr(socket.gethostname())[0],
                'port'  : 4000,
                'stacks': [],
                'remote': {}
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'usbrel64.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump({}, f)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'authkeys.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'admin': rand_authkey(),
                'share': rand_authkey(),
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'jenkins.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'auth': {
                    '<jenkins host>': {
                        'method': None
                    }
                }
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'workspace.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'pretty' : socket.gethostbyaddr(socket.gethostname())[0],
                'root'   : '~/.ave',
                'jenkins': '',
                'tools': {},
                'flocker': flocker,
                'proxy': '',
                'wlan': {
                    'ssid': '',
                    'auth': ''
                },
                'wifi-capable' : False
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'gerrit.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'host': '',
                'port': 29418,
                'user': 'REPLACE THIS WITH THE NAME PART OF YOUR EMAIL ADDRESS'
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'panotti.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'enabled': False,
                'host'   : '<UPDATE>',
                'port'   : 5984,
                'db'     : 'panotti'
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    path = os.path.join(home, '.ave', 'config', 'handset.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {
                'handsets':[
                    {'model':None, 'pretty':None, 'variant':None, 'shutdown':0,
                     'boot_to_service':None, 'magic':[]}
                ]
            }
            json.dump(config, f, indent=4)
        created.append(path)
    else:
        skipped.append(path)

    return created, skipped

def load(path):
    if not os.path.exists(path):
        user = ave.pwd.getpwuid_name(os.getuid())
        raise Exception(
            'no such configuration file: %s\n\nrun "ave-config --bootstrap=%s" '
            'to create one with default values' % (path, user)
        )

    config = None
    with open(path) as f:
        try:
            config = json.load(f)
        except Exception, e:
            raise Exception(
                'invalid config file %s: not valid JSON encoding: %s' % (path,e)
            )

    if type(config) != dict:
        raise Exception(
            'invalid config file %s: contents is not a dictionary: %s'
            % (path, type(config))
        )

    return config

def load_authkeys(home):
    path = os.path.join(home, '.ave', 'config', 'authkeys.json')
    config = load(path)
    for key in config:
        if not config[key]:
            continue

        if type(key) not in [str, unicode]:
            raise Exception(
                'invalid config file %s: key "%s" is not a string: %s'
                % (path, key, type(key))
            )
        if type(config[key]) not in [str, unicode]:
            raise Exception(
                'invalid config file %s: value of "%s" is not a string: %s'
                % (path, key, type(config[key]))
            )
        if type(config[key]) == unicode: # convert to ascii representation
            config[key] = config[key].encode('utf8')
    return config

prompt = (
'''You must select which user should be used to run AVE. Note that this user
 should have fully configured access to Gerrit. Most workstation users should
 specify their own user name here (the "23-number" if you work at Sony Mobile
 Communications)

 Type a valid user name and press return: '''
)

def create_etc(path='/etc/ave/user', user=None):
    etc = False

    if path == '/etc/ave/user':
        if os.geteuid() != 0: # are we running with effective user ID as root?
            raise Exception('must call as root')

    # check if a run-as user is already selected
    if os.path.exists(path):
        try:
            with open(path) as f:
                user = json.load(f)['name']
                etc  = True
        except:
            pass

    if not user: # ask lab owner to select a run-as user
        user = raw_input(prompt).strip()

    home = ave.pwd.getpwnam_dir(user)
    uid = ave.pwd.getpwnam_uid(user)

    if not etc: # generate /etc/ave/user
        try:
            os.makedirs(os.path.dirname(path))
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise Exception('could not create /etc/ave: %s' % str(e))

        try:
            with open(path, 'w') as f:
                f.write(json.dumps({ 'name':user, 'home':home, 'uid':uid }, indent=4))
        except IOError, e:
            raise Exception('could not create /etc/ave/user: %s' % str(e))

    return user

def load_etc():
    if os.path.exists('/etc/ave/user'):
        try:
            f = open('/etc/ave/user')
            j = json.load(f)
            if 'name' not in j:
                raise Exception('invalid /etc/ave/user: no "name" entry: %s'%j)
            if 'home' not in j: # backward compatibility
                j['home'] = ave.pwd.getpwnam_dir(j['name'])
            if 'uid' not in j:
                uid = ave.pwd.getpwnam_uid(j['name'])
                j['uid'] = uid
            return j
        except Exception, e:
            raise Exception('could not load /etc/ave/user: %s' % e)
    raise Exception('/etc/ave/user does not exist')
