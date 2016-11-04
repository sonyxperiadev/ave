# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import time

from ave.workspace          import Workspace

class setup(object):
    HOME      = None
    processes = None

    def __init__(self):
        self.processes = []

    def kill(self):
        for p in self.processes:
            p.terminate()
            p.join()
        self.HOME.delete()

    def __call__(self, fn):
        def decorated(*args, **kwargs):
            self.HOME = Workspace()
            self.make_system()
            w = Workspace(home=self.HOME.path)
            self.make_files(w.path)
            try:
                result = fn(self.HOME.path, w, *args, **kwargs)
            except:
                self.kill()
                raise
            self.kill()
            return result
        return decorated

    @property
    def conf_dir(self):
        return os.path.join(self.HOME.path, '.ave', 'config')

    def make_config(self, which, config):
        if not os.path.exists(self.conf_dir):
            os.makedirs(self.conf_dir)
        path = os.path.join(self.conf_dir, which)
        with open(path, 'w') as f:
            f.write(json.dumps(config))
        return path

    def make_files(self, directory):
        with open(os.path.join(directory, 'hola.txt'), 'w') as f:
            f.write('hola hola')
        with open(os.path.join(directory, 'nihao.txt'), 'w') as f:
            f.write('nihao nihao')

    def make_system(self):
        self.make_config('authkeys.json', {'admin':'admin'})

        workspace_cfg = {
            'root': '%s/.ave/workspaces' % self.HOME.path,
            'tools': {},
            'flocker':{
                'enable': False,
                'host': 'cnbjlnx147',
                'ftp': {
                    'port':21,
                    'user':'ftpuser',
                    'password': 'ftpuser',
                    'timeout': 10,
                    'store': os.path.join('/srv/www', 'flocker')
                },
                'http': {
                    'port':81,
                    'doc-root': '/srv/www'
                }
            }
        }
        self.make_config('workspace.json', workspace_cfg)

# push some strings
@setup()
def t01(home, w):
    pretty = '%s t01' % __file__
    print(pretty)

    try:
        w.flocker_push_string('hej hej', dst='hej.txt')
    except Exception, e:
        print('FAIL %s: could not push: %s' % (pretty, e))
        return False

    try:
        meta = w.flocker_push_string('hello hello\n', dst='hej.txt')
    except Exception, e:
        print('FAIL %s: could not push again: %s' % (pretty, e))
        return False

    try:
        meta = w.flocker_push_string('hello hello', dst='subdir/hello.txt')
    except Exception, e:
        print('FAIL %s: could not push: %s' % (pretty, e))
        return False

    try:
        meta = w.flocker_push_string('hello world', dst='subdir/hello.txt')
    except Exception, e:
        print('FAIL %s: could not push again: %s' % (pretty, e))
        return False
    return True

# push file
@setup()
def t02(home,w):
    pretty = '%s t02' % __file__
    print(pretty)

    try:
        meta = w.flocker_push_file('hola.txt')
    except Exception, e:
        print('FAIL %s: could not push: %s' % (pretty, e))
        return False

    return True

#push file in subdirectory
@setup()
def t03(home, w):
    pretty = '%s t03' % __file__
    print(pretty)

    try:
        meta = w.flocker_push_file(
            os.path.join(w.path,'nihao.txt'), dst='first/third/forth/hello.txt'
        )
        meta = w.flocker_push_file(
            os.path.join(w.path,'hola.txt'), dst='first/third/forth/world.txt'
        )
    except Exception, e:
        print('FAIL %s: could not push: %s' % (pretty, e))
        return False

    return True

# check metadata
@setup()
def t04(home, w):
    pretty = '%s t04' % __file__
    print(pretty)

    meta = w.flocker_set_metadata(contact='foo@bar.com', asset='abc123')
    meta = w.flocker_set_metadata(asset='def456',comment='moo')

    expected = {
        'comment' : 'moo',
        'url'     : {'port': 81, 'path':'flocker/' + w.ftpclient.dirname, 'host':w.config['flocker']['host']},
        'asset'   : 'def456',
        'contact' : 'foo@bar.com',
    }

    if meta != expected:
        print('FAIL %s: wrong metadata: %s' % (pretty, meta))
        return False

    return True

#test metadata file is updated on server
@setup()
def t05(home, w):
    pretty = '%s t05' % __file__
    print(pretty)

    w.flocker_set_metadata(contact='foo@bar.com', asset='abc123', comment='moo')
    #upload the metadata file to server
    w.ftpclient.update_metadata_file()
    #reset the metadata then uploaded the metadata file again
    meta = w.flocker_set_metadata(contact='foo@bar.com', asset='def456', comment='moo')
    w.ftpclient.update_metadata_file()

    expected = {
        'comment' : 'moo',
        'url'     : {'port': 81, 'path':'flocker/' + w.ftpclient.dirname, 'host':w.config['flocker']['host']},
        'asset'   : 'def456',
        'contact' : 'foo@bar.com',
    }

    #retrieve the metadata file from server and check its content
    filename = w.ftpclient.dirname + '.json'
    cwd = w.ftpclient.store
    w.ftpclient.ftp.cwd(cwd)
    cmd = 'RETR ' + filename
    lines = []
    def callback(line):
        lines.append(line)

    w.ftpclient.ftp.retrbinary(cmd, callback)
    config = json.loads(''.join(lines))

    if config != expected:
        print('FAIL %s: metadata is not updated on server: %s' % (pretty, meta))
        return False

    return  True

# push from two workspaces to the same remote dir
@setup()
def t06(home, w):
    pretty = '%s t06' % __file__
    print(pretty)

    meta = w.flocker_push_string('hej hej',     dst='hej.txt')
    meta = w.flocker_push_string('hello hello', dst='hello.txt')

    w = Workspace(home=home)
    with open(os.path.join(w.path, 'hola.txt'), 'w') as f:
        f.write('hola hola')

    # only need to provide key in first call to the second workspace
    meta = w.flocker_push_file('hola.txt', key=meta['key'])
    meta = w.flocker_push_string('nihao nihao', dst='hello.txt')

    #verify all the file is located in the same remote dir
    w.ftpclient.ftp.cwd(meta['key'])
    lines = w.ftpclient.list_remote_files()
    expectedfile = ['hej.txt', 'hello.txt', 'hola.txt']
    if lines != expectedfile:
        print('FAIL %s: could not push file from different workspace: %s' % (pretty, str(expectedfile)))
        return False

    w.flocker_get_file('hello.txt', 'test_remote.txt')
    remote_txt = w.cat('test_remote.txt')
    expectedtxt = 'hello hellonihao nihao'

    if expectedtxt != remote_txt:
        print("FAIL %s: could not push string from different workspace to same file" % (pretty, expectedtxt))
        return False

    return True

#Adding a friendly prefix on a folder name
@setup()
def t07(home, w):
    pretty = '%s t07' % __file__
    print(pretty)

    w = Workspace(home=home)
    custom_key = 'friendly_prefix_%s' % time.strftime("%H:%M:%S")
    # test custome_key not existed
    meta = w.flocker_push_string('hej hej', dst='hej.txt')
    try:
        w.flocker_initial(existing_key=custom_key)
    except Exception, e:
        if 'Could not access friendly_prefix' not in str(e):
            return False
    # creat custome key
    w.flocker_initial(custom_key=custom_key)
    meta = w.flocker_push_string('hello hello', dst='hello.txt')
    existing_key = meta['key']
    if not meta['key'].startswith(custom_key):
        return False
    w.flocker_initial(existing_key=existing_key)
    meta = w.flocker_push_string('hej hej', dst='hej.txt')
    if meta['key'] != existing_key:
        return False
    return True
