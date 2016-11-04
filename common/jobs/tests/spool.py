# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import signal
import multiprocessing

import ave.cmd

from ave.workspace import Workspace
from ave.spool     import Spool, make_spool

def t1():
    pretty = '%s t1' % __file__
    print(pretty)
    
    w = Workspace('spool-t1')
    
    try:
        s = Spool(os.path.join(w.path, 'a name'))
        print('FAIL %s: created spool with spaces in the name' % pretty)
        return
    except Exception, e:
        if not str(e).startswith('path must not include spaces'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    w.delete()
    return True

def t2():
    pretty = '%s t2' % __file__
    print(pretty)
    
    w = Workspace('spool-t2')
    
    try:
        s = Spool(os.path.join(w.path, 'a_name'))
        print('FAIL %s: created spool in non-existing directory' % pretty)
        return
    except Exception, e:
        if not str(e).startswith('not a directory'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return
    
    w.delete()
    return True

def t3():
    pretty = '%s t3' % __file__
    print(pretty)
    
    w = Workspace('spool-t3')
    
    try:
        s = Spool(w.make_tempdir())
    except Exception, e:
        print('FAIL %s: could not create spool: %s' % (pretty, str(e)))
        return
    
    w.delete()
    return True

def t4():
    pretty = '%s t4' % __file__
    print(pretty)
    
    w = Workspace('spool-t4')
    d = w.make_tempdir()
    s = Spool(d)

    # create a file in the temp dir, regiter its file descriptor with the spool
    # and then check that reading from the spool produces the same content as
    # was written to the file
    pr, pw = os.pipe()
    os.write(pw, 'blaha di bla bla')
    os.close(pw)

    try:
        s.register(pr)
    except Exception, e:
        print('FAIL %s: could not register file descriptor: %s'%(pretty,str(e)))
        return

    try:
        result = s.read()
    except Exception, e:
        print('FAIL %s: could not read from spool: %s' % (pretty, str(e)))
        return
    if result != 'blaha di bla bla':
        print('FAIL %s: wrong contents: %s' % (pretty, result))
        return

    w.delete()
    return True

# check that Spool.read() throws an exception on timeout
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    def proc(fd):
        time.sleep(0.5)
        os.write(fd, 'will be caught')
        time.sleep(0.5)
        os.write(fd, 'will be missed')
        os.close(fd)

    w = Workspace('spool-t5')
    s = make_spool(os.path.join(w.path, 'a_spool'))
    pr, pw = os.pipe()
    s.register(pr)
    p = multiprocessing.Process(target=proc, args=(pw,))
    p.start()

    # first read times out
    try:
        result = s.read(1)
        print('FAIL %s: read(1) did not throw exception' % pretty)
        os.kill(p.pid, signal.SIGKILL)
        return
    except Exception, e:
        if str(e) != 'time out':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            os.kill(p.pid, signal.SIGKILL)
            return

    # second read only catches first message. timeout is larger than total time
    # needed to catch both messages but the function will return when the first
    # message arrives
    try:
        result = s.read(2000)
    except Exception, e:
        print('FAIL %s: read(2000) failed: %s' % (pretty, str(e)))
        os.kill(p.pid, signal.SIGKILL)
        return
    if result != 'will be caught':
        print('FAIL %s: wrong result: %s' % (pretty, result))
        os.kill(p.pid, signal.SIGKILL)
        return

    p.join()
    w.delete()
    return True

# check that make_spool fails when target path exists and is not a directory
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    w = Workspace('spool-t6')
    f = open(os.path.join(w.path, 'a_file'), 'w')
    f.close()

    try:
        make_spool(os.path.join(w.path, 'a_file', 'a_spool'))
        print('FAIL %s: make_spool() did not fail' % pretty)
        return
    except Exception, e:
        if not str(e).startswith('could not create directory at'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return
    
    w.delete()
    return True

# check that persistent spool contents are identical to joined fragments
# returned by Spool.read()
