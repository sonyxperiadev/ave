# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import json
import traceback

import ave.pwd
import ave.config

from ave.workspace       import Workspace
from ave.network.process import Process

from decorators import smoke

def setup(fn):
    def decorated_fn():
        w = Workspace()
        result = fn(w)
        if result:
            w.delete()
        return result
    return decorated_fn

# check that the default configuration directory is automatically created and
# contains all files
@setup
def t01(w):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        created, skipped = ave.config.create_default(w.path)
    except Exception, e:
        print('FAIL %s: could not create config: %s' % (pretty, e))
        return False

    base = os.path.join(w.path, '.ave', 'config')
    if not os.path.isdir(base):
        print('FAIL %s: config directory not created' % pretty)
        return False

    path = os.path.join(base, 'broker.json')
    if not os.path.isfile(path):
        print('FAIL %s: broker config not created' % pretty)
        return False

    path = os.path.join(base, 'usbrel64.json')
    if not os.path.isfile(path):
        print('FAIL %s: usbrel64 config not created' % pretty)
        return False

    path = os.path.join(base, 'authkeys.json')
    if not os.path.isfile(path):
        print('FAIL %s: authkeys config not created' % pretty)
        return False

    path = os.path.join(base, 'jenkins.json')
    if not os.path.isfile(path):
        print('FAIL %s: jenkins config not created' % pretty)
        return False

    path = os.path.join(base, 'gerrit.json')
    if not os.path.isfile(path):
        print('FAIL %s: authkeys config not created' % pretty)
        return False

    path = os.path.join(base, 'handset.json')
    if not os.path.isfile(path):
        print('FAIL %s: authkeys config not created' % pretty)
        return False

    if created != [
        os.path.join(base, 'broker.json'),
        os.path.join(base, 'usbrel64.json'),
        os.path.join(base, 'authkeys.json'),
        os.path.join(base, 'jenkins.json'),
        os.path.join(base, 'workspace.json'),
        os.path.join(base, 'gerrit.json'),
        os.path.join(base, 'panotti.json'),
        os.path.join(base, 'handset.json')
    ]:
        print('FAIL %s: wrong files created: %s' % (pretty, created))
        return False

    if skipped != []:
        print('FAIL %s: wrong files skipped: %s' % (pretty, skipped))
        return False

    return True

# check that ave.config.create_default() does not overwrite existing files
@smoke
@setup
def t02(w):
    pretty = '%s t2' % __file__
    print(pretty)

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)
    with open(os.path.join(base, 'broker.json'), 'w') as f:
        f.write('')
    with open(os.path.join(base, 'workspace.json'), 'w') as f:
        f.write('')

    created, skipped = ave.config.create_default(w.path)
    if created != [
        os.path.join(base, 'usbrel64.json'),
        os.path.join(base, 'authkeys.json'),
        os.path.join(base, 'jenkins.json'),
        os.path.join(base, 'gerrit.json'),
        os.path.join(base, 'panotti.json'),
        os.path.join(base, 'handset.json')
    ]:
        print('FAIL %s: wrong files created: %s' % (pretty, created))
        return False

    if skipped != [
        os.path.join(base, 'broker.json'),
        os.path.join(base, 'workspace.json')
    ]:
        print('FAIL %s: wrong files skipped: %s' % (pretty, skipped))
        return False

    return True

# check that loading and validating a correct authkeys config file works
@smoke
@setup
def t03(w):
    pretty = '%s t3' % __file__
    print(pretty)

    ave.config.create_default(w.path)

    try:
        authkeys = ave.config.load_authkeys(w.path)
    except Exception, e:
        print('FAIL %s: could not load authkeys config: %s' % (pretty, e))
        return False

    return True

# check that loading and validating an invalid authkeys config file fails
@setup
def t04(w):
    pretty = '%s t4' % __file__
    print(pretty)

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)
    with open(os.path.join(base, 'authkeys.json'), 'w') as f:
        f.write('') # empty file

    try:
        authkeys = ave.config.load_authkeys(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'No JSON object could be decoded' not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that loading and validating an invalid authkeys config file fails
@setup
def t05(w):
    pretty = '%s t5' % __file__
    print(pretty)

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)
    with open(os.path.join(base, 'authkeys.json'), 'w') as f:
        f.write('["admin", "share"]')

    try:
        authkeys = ave.config.load_authkeys(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'contents is not a dictionary: <type \'list\'>' not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that loading and validating an invalid authkeys config file fails
@smoke
@setup
def t06(w):
    pretty = '%s t6' % __file__
    print(pretty)

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)
    with open(os.path.join(base, 'authkeys.json'), 'w') as f:
        f.write('{"admin":3}')

    try:
        authkeys = ave.config.load_authkeys(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'value of "admin" is not a string: <type \'int\'>' not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check error message when loading non-existent authkeys file
@setup
def t07(w):
    pretty = '%s t7' % __file__
    print(pretty)

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)

    try:
        authkeys = ave.config.load_authkeys(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        name = ave.pwd.getpwuid_name(os.getuid())
        if 'run "ave-config --bootstrap=%s"' % name not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# used by t8-t10. calls os._exit() so only use from within child process.
def check_fds(pretty, dump, ref):
    # check that 0-2 are the stdio file descriptors. i.e. that they are
    # connected to pseudo terminals.
    for i in range(3):
         if not dump[i].startswith('/dev/pts'):
             print('FAIL %s: wrong stdio file at %d: %s' % (pretty, i, dump[i]))
             os._exit(2)

    # any file descriptors in the range [3..max(all fds)] must be files that
    # were opened by this process. for this test we expect all of them to point
    # to the same file (the current .py file). otherwise they are not intact.
    if max(dump.keys()) <= 2:
        os._exit(0) # all OK
    for i in range(3, max(ref.keys())): # check that all ref keys are intact
        if not dump[i] == ref[i]:
            print('FAIL %s: clobbered fd at %d: %s' % (pretty, i, dump[i]))
            os._exit(5)

# check if ave.config.load_etc() clobbers file descriptors. this is a bug in
# winbindd which is used by PAM to implement a backend for Python's pwd module.
# we *have* to use the pwd module, so the global side effect (clobbering a file
# descriptor) must be hidden from the caller.
def t08():
    pretty = '%s t8' % __file__
    print(pretty)

    # check that the contents of /etc/ave/user will trigger a call to the pwd
    # module:
    with open('/etc/ave/user') as f:
        blob = json.load(f)
        if 'home' in blob:
            print(
                'BLOCKED %s: /etc/ave/user contains the "home" entry, which '
                'means this test cannot fail' % pretty
            )
            return False

    # start a new process that closes all fds except 0,1,2. let the process
    # open a bunch of file descriptors. then call functions in the pwd module
    # and check again which file descriptors got clobbered.

    class Clobber(Process):

        def close_fds(self, exclude):
            Process.close_fds(self, exclude) # don't change default behavior

        def run(self):
            path = os.path.realpath(__file__)

            for i in range(30):
                os.open(path, os.O_RDONLY)
            ref = self.list_fds()

            ave.config.load_etc()
            dump = self.list_fds()
            check_fds(pretty, dump, ref)

    c = Clobber()
    c.start()
    return c.join() == 0

# same as t8, but trigger the exception that would access pwd instead of loading
# the contents of /etc/ave/user.
def t09():
    pretty = '%s t9' % __file__
    print(pretty)

    # start a new process that closes all fds except 0,1,2. let the process
    # open a bunch of file descriptors. then call functions in the pwd module
    # and check again which file descriptors got clobbered.

    class Clobber(Process):

        def close_fds(self, exclude):
            Process.close_fds(self, exclude) # don't change default behavior

        def run(self):
            path = os.path.realpath(__file__)

            for i in range(30):
                os.open(path, os.O_RDONLY)
            ref = self.list_fds()

            try:
                ave.config.load('does_not_exist.json')
            except Exception, e:
                if 'no such configuration file' not in str(e):
                    print('FAIL %s: wrong error: %s' % (pretty, e))
                    os._exit(6)
            dump = self.list_fds()
            check_fds(pretty, dump, ref)

    c = Clobber()
    c.start()
    return c.join() == 0

# check that calls to create_etc() does not clobber file descriptors (as in t8
# and t9)
@setup
def t10(w):
    pretty = '%s t10' % __file__
    print(pretty)

    class Clobber(Process):

        def close_fds(self, exclude):
            Process.close_fds(self, exclude) # don't change default behavior

        def run(self):
            path = os.path.realpath(__file__)

            for i in range(30):
                os.open(path, os.O_RDONLY)
            ref = self.list_fds()

            try:
                ave.config.create_etc(w.make_tempfile(), 'root')
            except Exception, e:
                print('FAIL %s: could not create etc: %s' % (pretty, e))
                os._exit(6)

            dump = self.list_fds()
            check_fds(pretty, dump, ref)

    c = Clobber()
    c.start()
    return c.join() == 0

# check contents of generated etc file
@setup
def t11(w):
    pretty = '%s t11' % __file__
    print(pretty)

    path = w.make_tempfile()
    try:
        ave.config.create_etc(path, 'root')
    except Exception, e:
        print('FAIL %s: could not create etc: %s' % (pretty, e))
        return False

    with open(path) as f:
        blob = json.load(f)
        if 'home' not in blob or 'name' not in blob:
            print('FAIL %s: wrong etc content: %s' % (pretty, blob))
            return False

    return True
