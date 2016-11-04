# encoding=utf-8

import os
import sys
import json
import traceback
import StringIO

import vcsjob

from ave.workspace import Workspace

# check error messages for vcsjob.set_profiles()
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        vcsjob.set_profiles(123)
        print('FAIL %s: could set integer as profile' % pretty)
        return False
    except Exception, e:
        if 'profiles must be a list' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    try:
        vcsjob.set_profiles([123])
        print('FAIL %s: could set list of integer as profile' % pretty)
        return False
    except Exception, e:
        if 'profile is not a dictionary' not in str(e):
            print('FAIL %s: wrong error 2: %s' % (pretty, e))
            return False

    try:
        vcsjob.set_profiles([{'type':'ok'}, {'no':'type','field':'present'}])
        print('FAIL %s: could set profile without type' % pretty)
        return False
    except Exception, e:
        if '"type" field is missing' not in str(e):
            print('FAIL %s: wrong error 3: %s' % (pretty, e))
            return False

    try:
        vcsjob.set_profiles([{'type':'same'}, {'type':'same'}, {'type':'ok'}])
    except Exception, e:
        print('FAIL %s: could not set the same type twice: %s' % (pretty, e))
        return False

# check that the export of a single profile works
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    profiles = [{'type':'something'}]
    try:
        vcsjob.set_profiles(profiles)
    except Exception, e:
        print('FAIL %s: could not set profile: %s' % (pretty, e))
        return False

    if 'VCSJOB_PROFILES' not in os.environ:
        print('FAIL %s: $VCSJOB_PROFILES not set' % pretty)
        return False

    try:
        hints = json.loads(os.environ['VCSJOB_PROFILES'])
    except Exception, e:
        print('FAIL %s: could not parse $VCSJOB_PROFILES: %s' % (pretty, e))
        return False

    if hints != profiles:
        print('FAIL %s: wrong profiles: %s' % (pretty, hints))
        return False

    return True

# check that setting multiple profiles works
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    profiles = [{'type':'something'}, {'type':'else', 'more':'junk'}]
    try:
        vcsjob.set_profiles(profiles)
    except Exception, e:
        print('FAIL %s: could not set profiles: %s' % (pretty, e))
        return False

    if 'VCSJOB_PROFILES' not in os.environ:
        print('FAIL %s: $VCSJOB_PROFILES not set' % pretty)
        return False

    try:
        hints = json.loads(os.environ['VCSJOB_PROFILES'])
    except Exception, e:
        print('FAIL %s: could not parse $VCSJOB_PROFILES: %s' % (pretty, e))
        return False

    if hints != profiles:
        print('FAIL %s: wrong profiles: %s' % (pretty, profiles))
        return False

    return True

# check error messages for vcsjob.get_profiles()
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    vcsjob.set_profiles(None)

    if 'VCSJOB_PROFILES' in os.environ:
        print(
            'FAIL %s: set_profiles() did not clear environment variable: %s'
            % (pretty, os.environ['VCSJOB_PROFILES'])
        )
        return False

    try:
        vcsjob.get_profiles()
        print('FAIL %s: could get profiles' % pretty)
        return False
    except Exception, e:
        if 'no profiles' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    return True

# check that setting and getting profiles works
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    vcsjob.set_profiles(None)

    profiles = [{'type':'something'}, {'type':'else', 'more':'junk'}]
    vcsjob.set_profiles(profiles)

    try:
        hints = vcsjob.get_profiles()
    except Exception, e:
        print('FAIL %s: could not get hint: %s' % (pretty, e))
        return False

    if hints != profiles:
        print('FAIL %s: wrong profiles: %s' % (pretty, hints))
        return False

    return True

# check that unicode characters survive the mangling
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    # with u prefixes for the string literals
    profiles = [{u'type':u'sömething', u'är':u'"lurt"'}, {u'type':u'också'}]
    vcsjob.set_profiles(profiles)

    try:
        hints = vcsjob.get_profiles()
    except Exception, e:
        print('FAIL %s: could not get hints: %s' % (pretty, e))
        return False

    if hints != profiles:
        print('FAIL %s: wrong profiles: %s' % (pretty, hints))
        return False

    return True

# check that unicode characters survive the mangling
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    # without u prefixes for the string literals
    profiles = [{'type':'sömething', 'är':'"lurt"'}, {'type':'också'}]
    expected = [{u'type':u'sömething', u'är':u'"lurt"'}, {u'type':u'också'}]
    vcsjob.set_profiles(profiles)

    try:
        hints = vcsjob.get_profiles()
    except Exception, e:
        print('FAIL %s: could not get hints: %s' % (pretty, e))
        return False

    if hints != expected:
        print('FAIL %s: wrong profiles: %s' % (pretty, hints))
        print profiles
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

# check that vcsjob.execute_job() passes profiles
@setup
def t8(w):
    pretty = '%s t8' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG'],'profiles':[{'type':'type','foo':'bar'}]}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import json\n' \
        + 'import vcsjob\n' \
        + 'print(json.dumps(vcsjob.get_profiles()))'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_job(w.path, job, log_path=log_path)
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            try:
                line = json.loads(line)
            except Exception, e:
                continue
            if line == job['profiles']:
                ok = True
                break

    if not ok:
        with open(log_path) as f:
            log = f.read()
            print('FAIL %s: log does not contain profile: %s' % (pretty, log))
            return False

    return True

# check that vcsjob.get_profiles() raises exception if the job passed to
# vcsjob.execute_job() did not contain any profiles
@setup
def t9(w):
    pretty = '%s t9' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG']}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import json\n' \
        + 'import vcsjob\n' \
        + 'print(json.dumps(vcsjob.get_profiles()))'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_job(w.path, job, log_path=log_path)
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            if 'Exception: no profiles set' in line:
                ok = True
                break
    if not ok:
        with open(log_path) as f:
            print('FAIL %s: exception not raised: %s' % (pretty, f.read()))
            return False

    return True

# like t8 but use the regular vcsjob.execute() to force the profiles to be read
# from disk
@setup
def t10(w):
    pretty = '%s t10' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG'],'profiles':[{'type':'type','foo':'bar'}]}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import json\n' \
        + 'import vcsjob\n' \
        + 'print(json.dumps(vcsjob.get_profiles()))'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_tags(w.path, ['TAG'], log_path=log_path)
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            try:
                line = json.loads(line)
            except Exception, e:
                continue
            if line == job['profiles']:
                ok = True
                break

    if not ok:
        with open(log_path) as f:
            log = f.read()
            print('FAIL %s: log does not contain profile: %s' % (pretty, log))
            return False

    return True

# same variation on t10 as t9 is on t8 (no profiles passed to job)
@setup
def t11(w):
    pretty = '%s t11' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG']}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import json\n' \
        + 'import vcsjob\n' \
        + 'print(json.dumps(vcsjob.get_profiles()))'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_tags(w.path, ['TAG'], log_path=log_path)
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            if 'Exception: no profiles set' in line:
                ok = True
                break

    if not ok:
        with open(log_path) as f:
            log = f.read()
            print('FAIL %s: log does not contain exception: %s' % (pretty, log))
            return False

    return True

#Adapt vcsjob for multipel allocation

def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    profiles = [[{'type':'handset'},{'type':'relay'}],[{'type':'hanset'},{'type':'workspace'}]]
    expected = [({u'type': u'handset'},{u'type': u'relay'}), ({u'type': u'hanset'}, {u'type': u'workspace'})]
    try:
        vcsjob.set_profiles(profiles)
    except Exception, e:
        print('FAIL %s: could not set profiles: %s' % (pretty, e))
        return False

    if 'VCSJOB_PROFILES' not in os.environ:
        print('FAIL %s: $VCSJOB_PROFILES not set' % pretty)
        return False
    try:
        hints = json.loads(os.environ['VCSJOB_PROFILES'])
    except Exception, e:
        print('FAIL %s: could not parse $VCSJOB_PROFILES: %s' % (pretty, e))
        return False
    if hints != profiles:
        print('FAIL %s: wrong profiles: %s' % (pretty, profiles))
        return False
    try:
        hints = vcsjob.get_profiles()

    except Exception, e:
        print('FAIL %s: could not get hints: %s' % (pretty, e))
        return False

    if hints != expected:
        print('FAIL %s: wrong profiles: %s' % (pretty, hints))
        print profiles
        return False

    return True

#Adapt vcsjob for multipel allocation
@setup
def t13(w):
    pretty = '%s t13' % __file__
    print(pretty)

    # cook a job, preserving sys.path for UNIT/ACCEPTANCE differences
    job = {'path':'job','tags':['TAG'],
           'profiles':[[{'type':'handset'}],[{'type':'hanset'},{'type':'workspace'}]]}
    exe = '#! /usr/bin/python2\n' \
        + 'import sys\n' \
        + 'sys.path = %s\n' % repr(sys.path) \
        + 'import json\n' \
        + 'import vcsjob\n' \
        + 'print(json.dumps(vcsjob.get_profiles()))'
        # look for the output from the last line in the test
    make_job(w, [job], exe)

    # store output from the job somewhere
    log_path = w.make_tempfile()

    try:
        vcsjob.execute_tags(w.path, ['TAG'], log_path=log_path)
    except Exception, e:
        print('FAIL %s: execute failed: %s' % (pretty, e))
        return False

    ok = False
    with open(log_path) as f:
        for line in f.readlines():
            try:
                line = json.loads(line)
            except Exception, e:
                continue
            if line == job['profiles']:
                ok = True
                break

    if not ok:
        with open(log_path) as f:
            log = f.read()
            print('FAIL %s: log does not contain profile: %s' % (pretty, log))
            return False

    return True

