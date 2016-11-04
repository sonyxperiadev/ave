# encoding=utf-8

import os
import sys
import json
import traceback
import StringIO

import vcsjob

from ave.workspace import Workspace

# check basic set functionality
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        vcsjob.set_guid(123)
        print('FAIL %s: could set integer as guid' % pretty)
        return False
    except Exception, e:
        if 'guid is not a string' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    try: # unicode version
        vcsjob.set_guid(u'super_valid_"åäö_@%&#"')
    except Exception, e:
        print('FAIL %s: could not set valid unicode guid: %s' % (pretty, e))
        return False
    if 'VCSJOB_GUID' not in os.environ:
        print('FAIL %s: could not set environment with unicode string' % pretty)
        return False
    del os.environ['VCSJOB_GUID']

    try: # ascii version
        vcsjob.set_guid('super_valid_"åäö_@%&#"')
    except Exception, e:
        print('FAIL %s: could not set valid ascii guid: %s' % (pretty, e))
        return False
    if 'VCSJOB_GUID' not in os.environ:
        print('FAIL %s: could not set environment with ascii string' % pretty)
        return False
    del os.environ['VCSJOB_GUID']

    try:
        vcsjob.set_guid(None)
    except Exception, e:
        print('FAIL %s: could not reset guid: %s' % (pretty, e))
        return False
    if 'VCSJOB_GUID' in os.environ:
        env = os.environ['VCSJOB_GUID']
        print('FAIL %s: environment set after reset: "%s"' % (pretty, env))
        return False

    return True

# check basic get functionality
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    # unicode version
    vcsjob.set_guid(u'super_valid_"åäö_@%&#"')
    try:
        val = vcsjob.get_guid()
    except Exception, e:
        print('FAIL %s: could not get unicode guid: %s' % (pretty, e))
        return False
    if val != u'super_valid_"åäö_@%&#"':
        print('FAIL %s: guid did not survive environment: %s' % (pretty, val))
        return False

    # ascii version
    vcsjob.set_guid('super_valid_"åäö_@%&#"')
    try:
        val = vcsjob.get_guid()
    except Exception, e:
        print('FAIL %s: could not get unicode guid: %s' % (pretty, e))
        return False
    if val != u'super_valid_"åäö_@%&#"':
        print('FAIL %s: guid did not mangle into unicode: %s' % (pretty, val))
        return False

    # reset
    vcsjob.set_guid(None)
    try:
        val = vcsjob.get_guid()
        print('FAIL %s: getting reset guid did not raise exception' % pretty)
        return False
    except Exception, e:
        if 'guid not set' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

def setup(fn):
    def decorator():
        w = Workspace()
        result = fn(w)
        w.delete()
        return result
    return decorator

def make_job(w, jobs, exe):
    vcsjob = {
        'executables': jobs
    }
    path = os.path.join(w.path,'.vcsjob')
    with open(path, 'w') as f:
        f.write(json.dumps(vcsjob))

    path = os.path.join(w.path, 'job')
    with open(path, 'w') as f:
        f.write(exe)
    os.chmod(path, 0777)

# check that vcsjob.execute_job(guid=...) passes guid to child process
@setup
def t3(w):
    pretty = '%s t3' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG']}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import vcsjob\n' \
        + 'print("GUID: %s" % vcsjob.get_guid())'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_job(w.path, job, log_path=log_path, guid='abc_123')
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            if line.strip() == 'GUID: abc_123':
                ok = True
                break

    if not ok:
        with open(log_path) as f:
            log = f.read()
            print('FAIL %s: log does not contain guid: %s' % (pretty, log))
            return False

    return True

# check that $VCSJOB_GUID does not remain set after call to vcsjob.execute_job()
@setup
def t4(w):
    pretty = '%s t4' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG']}
    exe = '#! /usr/bin/python2\n'
    make_job(w, [job], exe)

    vcsjob.set_guid(None) # reset $VCSJOB_GUID
    log_path = w.make_tempfile() # store output from the job somewhere
    vcsjob.execute_job(w.path, job, log_path=log_path, guid='abc_123')

    try:
        value = vcsjob.get_guid()
        print('FAIL %s: VCSJOB_GUID remains set: %s' % (pretty, value))
        return False
    except:
        pass

    return True

# check that $VCSJOB_GUID returns to its previous value after a call to
# vcsjob.execute_job(guid=...)
@setup
def t5(w):
    pretty = '%s t5' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG']}
    exe = '#! /usr/bin/python2\n'
    make_job(w, [job], exe)

    vcsjob.set_guid('previous_value')
    log_path = w.make_tempfile() # store output from the job somewhere
    vcsjob.execute_job(w.path, job, log_path=log_path, guid='abc_123')

    try:
        value = vcsjob.get_guid()
    except Exception, e:
        print('FAIL %s: %s' % (pretty, e))
        return False

    if value != 'previous_value':
        print('FAIL %s: wrong value: %s' % (pretty, value))
        return False
         
    return True
