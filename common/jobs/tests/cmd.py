# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import StringIO
import select
import signal
import traceback

import ave.cmd
from ave.workspace import Workspace

from ave.exceptions import *

from decorators import smoke

class RedirectedStderr(object):
    def __enter__(self):
        self._orig = sys.stderr
        self.io = StringIO.StringIO()
        sys.stderr = self.io

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stderr = self._orig

def setup(fn):
    def decorated_fn():
        w = Workspace()
        result = fn(w)
        if result:
            w.delete()
        return result
    return decorated_fn

# check that a Timeout is raised on timeout
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        ave.cmd.run(['sleep','10'], timeout=1)
        print('FAIL %s: there was no timout' % pretty)
        return
    except Timeout, e:
        pass # good
    except Exception, e:
        print('FAIL %s: wrong exception type: %s' % (pretty, type(e)))
        return
    if not e.message.endswith(' timed out'):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        return
    return True

# check that a strings are accepted and split on whitespace, that timeouts
# work
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    exc = None
    try:
        ave.cmd.run('sleep    10', timeout=1)
        print('FAIL %s: there was no timout' % pretty)
        return
    except Timeout, e:
        exc = e # good
    except Exception, e:
        print('FAIL %s: wrong exception type: %s' % (pretty, type(e)))
        return
    if exc.details['cmd'] != ['sleep','10']:
        print('FAIL %s: wrong RunError.cmd value %s' % (pretty, exc.cmd))
        return
    if exc.message != 'command timed out':
        print('FAIL %s: wrong error message: %s' % (pretty, exc.message))
        return
    return True

# check that debugging outputs turn on and off properly
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    def internal(dbg):
        # redirect stderr during cmd.run() so we can see afterwards what was really
        # written to the file descriptors
        redirect = RedirectedStderr()
        with redirect:
            (s, o, e) = ave.cmd.run(['echo','-n','hello'], debug=dbg)

        return redirect.io.getvalue()

    value = internal(dbg=True)
    expected = ['echo -n hello','hello']
    for x in expected:
        if x not in value:
            print('FAIL %s: "%s" missing in stderr: "%s"' % (pretty, x, value))
            return

    value = internal(dbg=False)
    if value != "":
        print('FAIL %s: non-empty stderr: "%s"' % (pretty, value))
        return

    return True

# check that the file descriptor returned by run_bg() is pollable
@smoke
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    pid, fd = ave.cmd.run_bg('echo hello')
    poller  = select.poll()
    poller.register(fd, select.POLLIN)
    events  = poller.poll(1000) # milliseconds
    tmp     = ''
    for e in events:
        if not (e[1] & select.POLLIN):
            print('FAIL %s: unexpected poll event: %d' % (pretty, e[1]))
            os.kill(pid, signal.SIGKILL)
        tmp += os.read(fd, 1024)
    if not tmp.startswith('hello'):
        print('FAIL %s: wrong result: "%s"' % (pretty, tmp))

    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    return True

# check that return value from executed program is correct
@smoke
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    # if we redirect stderr during cmd.run() we get rid of output from ls in
    # console, we only want to print failures here.
    with RedirectedStderr():
        (s, o, e) = ave.cmd.run(['ls'])
    if not s == 0:
        print(
            'FAIL %s: execution of "ls" returned: %d, expected: 0' % (pretty, s)
        )

    with RedirectedStderr():
        (s, o, e) = ave.cmd.run(['ls', 'thisdoesnotexist'], debug=True)
    if not s == 2:
        print(
            'FAIL %s: execution of "ls thisdoesnotexist" returned: %d, '
            'expected: 2' % (pretty, s)
        )
    return True

# check that we don't run into the OS limit on how many pseudo terminals can be
# allocated when using ave.cmd.run() a lot
@smoke
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    with open('/proc/sys/kernel/pty/max') as f:
        limit = int(f.read()) + 1
    for i in range(limit):
        try:
            ave.cmd.run('echo hello')
        except Exception, e:
            print('FAIL %s: error in iteration %d: %s' % (pretty, i, e))
            return False

    return True

# check that run() reads all the output -- regression test for when it didn't
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    from tempfile import NamedTemporaryFile
    # generate a file with some familiar content:
    with NamedTemporaryFile(mode='w', delete=False) as f:
        print >> f, "in the beginning, there was zero."
        for i in xrange(500):
            print >> f, "so you have", i
            print >> f, "if you add one to that"
            print >> f, "you get", i+1
        fname = f.name

    cmd = ['sh','-c','cat %s | while read line; do echo $line; done' % fname]
    # the bug was timing-dependent, so test lots of times...
    for i in xrange(1,100):
        status, out, err = ave.cmd.run(cmd)
        last = out.splitlines()[-1].strip()
        if last != "you get 500":
            print('FAIL %s: attempt %d, last line was "%s"' % (pretty, i, last))
            os.remove(fname)
            return False
    os.remove(fname)
    return True

# Check that possible to set working directory
@setup
def t8(w):
    pretty = '%s t8' % __file__
    print(pretty)
    try:
        ave.cmd.run('echo hello > test.txt', cwd=w.get_path())
    except Exception, e:
        print('FAIL %s: error writing to file: %s' % (pretty, e))
        return False
    try:
        ave.cmd.run_bg('echo hello > test_bg.txt', cwd=w.get_path())
    except Exception, e:
        print('FAIL %s: error writing to file (bg): %s' % (pretty, e))
        return False
    return True
