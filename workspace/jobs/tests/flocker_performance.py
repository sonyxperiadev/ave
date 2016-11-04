# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
from threading import Thread
import shutil
import time
import ave.cmd

from ave.exceptions     import AveException
from ave.workspace      import Workspace
from ave.ftpclient      import FtpClient

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

    def get_workspace(self):
        if not self.HOME:
            self.HOME = Workspace()
        self.make_system()
        w = Workspace(home=self.HOME.path)
        self.make_files(w.path)
        return w

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
        test_data = os.path.join(os.path.dirname(__file__),
                            'testdata', '1920x1080.png')
        shutil.copy2(test_data, directory)

    def make_system(self):
        self.make_config('authkeys.json', {'admin':'admin'})

        workspace_cfg = {
            'root': '%s/.ave/workspaces' % self.HOME.path,
            'tools': {},
            'ftp': {
                'host': 'cnbjlnx145',
                'port': 21,
                'user': 'ftpuser',
                'password': 'ftpuser',
                'timeout': 360,
                'store': os.path.join('/srv/www', 'flocker')
            }
        }
        self.make_config('workspace.json', workspace_cfg)

def verify_data_connection_reuse(w, loop):
    try:
        # Ftp Client will login automatically during initialization
        ftp = FtpClient(w, w.config['ftp'])
    except AveException, e:
        print 'Test Loop %d: unexpected exception: %s' % (loop, str(e))
        return

    # Server side config: idle_session_timeout=300
    # Wait for ftp connection lost in 300 seconds
    time.sleep(360)
    if ftp.is_alive():
        print 'Test Loop %d: ftp connection still alive after 350 seconds in idle status' % (loop,)

def verify_robustness(w, loop):

    # Push string
    txt = 'Test Loop %d' % loop

    try:
        w.flocker_push_string(txt, dst='test.txt')
    except Exception, e:
        print 'Test Loop %d: failed to push string as exception %s' % (loop, str(e))
        return False

    # Push file
    file_name = '1920x1080.png'
    file_sum = w.get_checksum(file_name)

    try:
        w.flocker_push_file(file_name)
    except Exception, e:
        print 'Test Loop %d: failed to push file as exception %s' % (loop, str(e))
        return False

    try:
        w.flocker_get_file('test.txt', 'test_remote.txt')
        w.flocker_get_file('1920x1080.png', '1920x1080_remote.png')
    except Exception, e:
        print 'Test Loop %d: Failed to get files from remote as exception %s' % (loop, str(e))
        return False

    # Check pushed string
    remote_txt = w.cat('test_remote.txt')
    if txt != remote_txt:
        print 'Test Loop %d: remote string "%s" did not match original string "%s"' % (loop, remote_txt, txt)

    # Check pushed file
    if file_sum != w.get_checksum('1920x1080_remote.png'):
        print 'Test Loop %d: remote file did not match original file' % (loop,)

    w.delete()

#test robustness for ftp server
def t01():
    pretty = '%s t01' % __file__
    print(pretty)

    s = setup()

    total = 1000
    threads = []
    for i in range(0, total):
        try:
            w = s.get_workspace()
            thrd = Thread(target=verify_robustness,args=(w, i,))
            thrd.start()
            threads.append(thrd)
        except Exception, e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    print 'Started %d threads, wait until those threads terminate ... ' % total
    for ts in threads:
        ts.join()

    s.kill()
    return True

# To verify data connection reuse
def t02():
    pretty = '%s t02' % __file__
    print(pretty)

    s = setup()
    w = s.get_workspace()

    total = 1000
    threads = []
    for i in range(0, total):
        try:
            thrd = Thread(target=verify_data_connection_reuse,args=(w, i,))
            thrd.start()
            threads.append(thrd)
        except Exception, e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    print 'Started %d ftp connection, wait 6 minutes until those connections lost ... ' % total
    for ts in threads:
        ts.join()

    s.kill()
    return True

# Verify that restarting broker doesn't break flocker process
def t03():
    pretty = '%s t03' % __file__
    print(pretty)

    s = setup()

    total = 50
    threads = []
    for i in range(0, total):
        try:
            w = s.get_workspace()
            thrd = Thread(target=verify_robustness,args=(w, i,))
            thrd.start()
            threads.append(thrd)
        except Exception, e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    print 'Started %d threads to push files to flocker, wait until those threads terminate ... ' % total
    # Wait for pushing action starts
    time.sleep(10)

    # Restart broker
    (s, o, e) = ave.cmd.run('ave-broker --restart')
    print 'Restart broker successfully: %s ' % o

    for ts in threads:
        ts.join()

    return True
