# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import errno

from ave.workspace import Workspace, WorkspaceProfile

from decorators import smoke

FLOCKER = {
            "enable": False,
            "ftp": {
                "password": "ftpuser",
                "store": "/srv/www/flocker",
                "port": 21,
                "timeout": 30,
                "user": "ftpuser"
            },
            "host": "cnbjlx20050",
            "http": {
                "doc-root": "/srv/www",
                "port": 80
            }
        }

# TODO: use setup on most of the tests
class setup(object):

    def __call__(self, fn):
        def decorated_fn():
            w = Workspace()
            try:
                os.makedirs(os.path.join(w.path, '.ave', 'config'))
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise Exception(
                        'could not create directory at %s: %s' % (w.path,str(e))
                    )
            result = fn(w)
            if result:
                w.delete()
            return result
        return decorated_fn

# check that an empty home is handled correctly
@setup()
def t01(HOME):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        w = Workspace(home=HOME.path)
    except Exception, e:
        if 'no such configuration file: %s' % HOME.path not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))

    return True

# check that an exception is raised if there is no workspace config file
@setup()
def t02(HOME):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        w = Workspace(home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if not str(e).startswith('no such configuration file: %s' % HOME.path):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))

    return True

# check that an exception is raised if the config file content is incomplete
@setup()
def t03(HOME):
    pretty = '%s t3' % __file__
    print(pretty)

    # build the mock config file (empty)
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        json.dump({}, f)

    try:
        Workspace(uid='something', home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if str(e) != 'workspace root directory is not configured':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    # add required fields to the mock config file
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root': '~/.ave', 'tools':{},
            'flocker': FLOCKER
        }, f)
    try:
        Workspace(home=HOME.path)
    except Exception, e:
        print('FAIL %s: Workspace.__init__() failed: %s' % (pretty, str(e)))
        return

    return True

# check error message is OK when loading broken config file
@setup()
def t04(HOME):
    pretty = '%s t4' % __file__
    print(pretty)

    # build the mock config file (broken)
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        f.write('{ "root": "moo" ') # missing end bracket

    try:
        Workspace(uid='something', home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if 'workspace configuration file: Expecting' not in repr(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check error message is OK when loading config file with invalid content
@setup()
def t05(HOME):
    pretty = '%s t5' % __file__
    print(pretty)

    # build the mock config file
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )

    # invalid content. "root" has wrong type
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root': 1, 'tools': {}, 'flocker': FLOCKER
        }, f)
    try:
        Workspace(uid='something', home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if not str(e).endswith('current value=1 (type=<type \'int\'>)'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# outdated test
def t06():
    pretty = '%s t6' % __file__
    print(pretty)
    return True

# check error message is OK when loading config file with invalid content
@setup()
def t07(HOME):
    pretty = '%s t7' % __file__
    print(pretty)

    # build the mock config file
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )

    # invalid content. "jenkins" has wrong type
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        f.write(
            '{ "root": "string", "jenkins": ["wrong"], "tools": {}, '
            '"flocker":{ "host":"any", "port": 0, "enable": false} }'
        )
    try:
        Workspace(uid='something', home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if not str(e).endswith('value=[u\'wrong\'] (type=<type \'list\'>)'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check error message is OK when loading config file with invalid content
@smoke
@setup()
def t08(HOME):
    pretty = '%s t8' % __file__
    print(pretty)

    # build the mock config file
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )

    # invalid content. "wlan" has wrong type
    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        f.write(
            '{ "root": "string", "wlan": { "ssid": 5, "auth": [] }, '
            ' "tools": {}, "flocker":{ "host":"any", "port": 0, "enable": false } }'
        )
    try:
        Workspace(uid='something', home=HOME.path)
        print('FAIL %s: Workspace.__init__() did not fail' % pretty)
    except Exception, e:
        if not str(e).endswith(
            'value={u\'ssid\': 5, u\'auth\': []} (type=<type \'dict\'>)'
        ):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check user/env expanded correctly in attributes that hold file system paths
@smoke
@setup()
def t09(HOME):
    pretty = '%s t9' % __file__
    print(pretty)

    # build the mock config file
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )

    path = os.path.join(HOME.path, '.ave', 'config', 'workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root':'~/$HOME',
            'tools':{},
            'flocker': FLOCKER
        }, f)

    try:
        w2 = Workspace(uid='something', home=HOME.path)
    except Exception, e:
        print('FAIL %s: Workspace.__init__() failed: %s' % (pretty, str(e)))
        return

    value = w2.get_profile()['root']
    if value != '%s/%s' % (HOME.path, HOME.path):
        print('FAIL %s: wrong expansion: %s' % (pretty, value))
        return

    return True

# check that Workspace.run() refuses to run tools that are not in the "tools"
# configuration section
@smoke
@setup()
def t10(HOME):
    pretty = '%s t10' % __file__
    print(pretty)

    # build the config file and create a workspace that uses it
    try:
        os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory at %s: %s' % (HOME.path, str(e))
            )
    path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root':'~',
            'tools':{'ls':'/bin/ls'},
            'flocker': FLOCKER
        }, f)
    w2 = Workspace(home=HOME.path)

    # check that Workspace.run() accepts 'ls' command but not others
    try:
        w2.run('ls -l')
    except Exception, e:
        print('FAIL %s: running registered tool failed: %s' % (pretty, str(e)))
        return

    try:
        w2.run('echo hello')
        print('FAIL %s: running unregistered tool did not fail' % pretty)
        return
    except Exception, e:
        if str(e) != 'no such tool available in this workspace: echo':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that Workspace.delete() works when the workspace contains hidden files
@smoke
def t11():
    pretty = '%s t11' % __file__
    print(pretty)

    w = Workspace()

    path = os.path.join(w.path, '.some', '.dir')
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create directory %s: %s' % (path, str(e))
            )
    with open(os.path.join(w.path, '.hidden'), 'w') as f:
        f.write('some content')
    with open(os.path.join(w.path, '.some', '.hidden'), 'w') as f:
        f.write('some content')
    with open(os.path.join(w.path, '.some', '.dir', '.hidden'), 'w') as f:
        f.write('some content')

    try:
        w.delete()
    except Exception, e:
        print('FAIL %s: could not delete workspace: %s' % (pretty, str(e)))
    return True

# check that a WorkspaceProfile can be created from a valid workspace config
@setup()
def t12(HOME):
    pretty = '%s t12' % __file__
    print(pretty)

    path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root':'~',
            'tools':{'ls':'/bin/ls'},
            'flocker': FLOCKER
        }, f)

    config = Workspace.load_config(path, home=HOME.path)
    try:
        profile = WorkspaceProfile(config)
    except Exception, e:
        print('FAIL %s: could not create profile: %s' % (pretty, str(e)))
        return False

    return True

# check that workspace profiles can be matched
@smoke
@setup()
def t13(HOME):
    pretty = '%s t13' % __file__
    print(pretty)

    path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(path, 'w') as f:
        json.dump({
            'root':'~',
            'tools':{'ls':'/bin/ls'},
            'flocker': FLOCKER
        }, f)
    config  = Workspace.load_config(path, HOME.path)
    profile = WorkspaceProfile(config)

    if not profile.match({'type':'workspace'}):
        print('FAIL %s: generic match failed' % pretty)
        return False

    if not profile.match({'type':'workspace','tools':['ls']}):
        print('FAIL %s: tools match failed' % pretty)
        return False

    workspace = Workspace('foobar', home=HOME.path)
    if not workspace.get_profile().match(profile):
        print('FAIL %s: non-uid match failed: %s' % (pretty, profile))
        return False

    if not workspace.get_profile().match({'type':'workspace','uid':'foobar'}):
        print('FAIL %s: uid match failed: %s' % pretty)
        return False

    return True

# check that listing available workspaces works
@smoke
@setup()
def t14(HOME):
    pretty = '%s t14' % __file__
    print(pretty)

    cfg_path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(cfg_path, 'w') as f:
        json.dump({
            'root':'~/workspaces',
            'tools':{'ls':'/bin/ls'},
            'flocker': FLOCKER
        }, f)

    avail = Workspace.list_available(cfg_path, home=HOME.path)
    if avail != []:
        print('FAIL %s: list is not empty 1: %s' % (pretty, avail))
        return False

    w1 = Workspace('w1', home=HOME.path)
    expected = [WorkspaceProfile({'type':'workspace', 'uid':'w1'})]
    avail = Workspace.list_available(cfg_path, home=HOME.path)
    if len(avail) != 1 or avail != expected:
        print('FAIL %s: wrong available 1: %s' % (pretty, avail))
        return False

    w2 = Workspace(home=HOME.path)
    expected.append(WorkspaceProfile({'type':'workspace', 'uid':w2.uid}))
    avail = Workspace.list_available(cfg_path, home=HOME.path)
    if len(avail) != 2 or expected[1] not in avail:
        print('FAIL %s: wrong available 2: %s' % (pretty, avail))
        return False

    w1.delete()
    w2.delete()
    avail = Workspace.list_available(cfg_path, home=HOME.path)
    if avail != []:
        print('FAIL %s: list is not empty 2: %s' % (pretty, avail))
        return False

    return True

# check that validation of the pretty attribute is ok
@setup()
def t15(HOME):
    pretty = '%s t15' % __file__
    print(pretty)

    cfg_path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(cfg_path, 'w') as f:
        config = {
            'root':'$HOME/workspaces',# ok
            'tools':{'ls':'/bin/ls'}, # ok
            'pretty':{2.0:'crazy'},    # not ok
            'flocker': FLOCKER
        }
        json.dump(config, f)

    try:
        w = Workspace(home=HOME.path)
        print('FAIL %s: validation did not fail' % pretty)
        return False
    except Exception, e:
        if '"pretty" must be on the form {"pretty":<string>}' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check that the 'pretty' attribute can be matched and minimized
@smoke
@setup()
def t16(HOME):
    pretty = '%s t16' % __file__
    print(pretty)

    cfg_path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(cfg_path, 'w') as f:
        config = {
            'root':'~/workspaces',
            'tools':{'ls':'/bin/ls'},
            'pretty':'something.unique',
            'flocker': FLOCKER
        }
        json.dump(config, f)

    profile = Workspace(home=HOME.path).get_profile()
    if not profile.match({'type':'workspace', 'pretty':'something.unique'}):
        print('FAIL %s: match failed' % pretty)
        return False
    return True

# check that the uid is prefixed with the pretty attribute if it is set
@smoke
@setup()
def t17(HOME):
    pretty = '%s t17' % __file__
    print(pretty)

    cfg_path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(cfg_path, 'w') as f:
        config = {
            'root':'$HOME/workspaces',
            'tools':{},
            'pretty':'prefix',
            'flocker': FLOCKER
        }
        json.dump(config, f)

    profile = Workspace(home=HOME.path).get_profile()
    if not profile['uid'].startswith('prefix-'):
        print('FAIL %s: wrong prefix: %s' % (pretty, profile['uid']))
        return False
    return True

# check that the 'wlan' attribute can be matched
@setup()
def t18(HOME):
    pretty = '%s t18' % __file__
    print(pretty)

    cfg_path = os.path.join(HOME.path,'.ave','config','workspace.json')
    with open(cfg_path, 'w') as f:
        config = {
            'root':'~/workspaces',
            'tools':{'ls':'/bin/ls'},
            'flocker': FLOCKER,
            'wlan':{'ssid':'ave-test', 'auth':'ave-pw'}
        }
        json.dump(config, f)

    w = Workspace(home=HOME.path)
    if w.get_wifi_ssid() != 'ave-test':
        print('FAIL %s: wifi ssid match failed' % pretty)
        return False
    if w.get_wifi_pw() != 'ave-pw':
        print('FAIL %s: wifi password match failed' % pretty)
        return False
    return True
