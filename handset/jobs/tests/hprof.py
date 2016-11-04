# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time

from decorators import smoke

# just get a package name from a list of running processes. this is used to
# make sure that a running process is used, otherwise there might be a failure
# for the wrong reason.
def _get_running_process(handset):
    processes = None
    for r in range(5):
        try:
            processes = handset.get_processes('com.android')
        except:
            pass
        if processes:
            return processes[0]
        time.sleep(2)
    return processes

# test invalid parameters to set_libc_debug_malloc()
def t01(w,h):
    pretty = '%s t01' % __file__
    print(pretty)

    f = w.make_tempfile()
    d = w.get_path()
    tests = {
        't1' : ('"on" must be a boolean value',(None,'package')),
        't2' : ('"on" must be a boolean value',(123,'package')),
        't3' : ('package must be a non-empty string',(False,None)),
        't4' : ('package must be a non-empty string',(False,123)),
    }
    for t in tests:
        msg, params = tests[t]
        try:
            h.set_libc_debug_malloc(*params)
            print(
                'FAIL %s: expected exception (%s) from set_libc_debug_malloc '
                'with parameters: %s' % (pretty, msg, params)
            )
            return False
        except Exception as e:
            if not msg in str(e):
                print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
                return False
    return True

# test set_libc_debug_malloc works as expected
# (leave in the state it was found)
def t02(w,h):
    pretty = '%s t02' % __file__
    print(pretty)

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    i = 0
    while(i < 2):
        # get initial value of the property
        try:
            h.get_property('libc.debug.malloc')
            s0 = True
        except Exception as e:
            if 'failed to get property with key: libc.debug.malloc' != e.message:
                print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
                return False
            s0 = False
        # call the method
        try:
            ldm_s0 = h.set_libc_debug_malloc(not s0, pkg, timeout=120)
            if ldm_s0 != s0:
                print(
                    'FAIL %s: unexpected value from set_libc_debug_malloc: %s '
                    '(expected == %s)' % (pretty, ldm_s0, s0)
                )
                return False
        except Exception as e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False
        # get new value
        try:
            h.get_property('libc.debug.malloc')
            s1 = True
        except Exception as e:
            if 'failed to get property with key: libc.debug.malloc' != e.message:
                print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
                return False
            s1 = False
        if s0 == s1: # should be a new value
            print(
                'FAIL %s: unexpected property value after execution of set_libc'
                '_debug_malloc: %s (expected != %s)' % (pretty, s1, s0)
            )
            return False
        i += 1
    return True

# check timeout exception on set_libc_debug_malloc
def t03(w,h):
    pretty = '%s t03' % __file__
    print(pretty)

    def _get_prop_val():
        try:
            h.get_property('libc.debug.malloc')
            return True
        except:
            return False

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    prop_val = _get_prop_val()
    # test timeout
    try:
        h.set_libc_debug_malloc(not prop_val, pkg, timeout=0.1)
        print('FAIL %s: expected timeout in set_libc_debug_malloc' % pretty)
        return False
    except Exception as e:
        if not 'timed out' in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    # restore property before returning
    finally:
        try:
            h.set_libc_debug_malloc(prop_val, pkg, timeout=120)
        except Exception as e:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False
    return True

# test invalid parameters to dump_heap()
def t04(w,h):
    pretty = '%s t04' % __file__
    print(pretty)

    f = w.make_tempfile()
    d = w.get_path()
    tests = {
        't1' : ('directory must be a non-empty string',(None,'package')),
        't2' : ('directory must be a non-empty string',(123,'package')),
        't3' : ('directory must be a non-empty string',('','package')),
        't4' : ('not an existing directory:',('path_does_not_exist','package')),
        't5' : ('not an existing directory:',(f,'package')),
        't6' : ('package must be a non-empty string',(d,'')),
        't7' : ('package must be a non-empty string',(d,None)),
        't8' : ('package must be a non-empty string',(d,123)),
        't9' : ('native must be a boolean value',(d,'pkg',None)),
        't10':('native must be a boolean value',(d,'pkg',"asd")),
        't11':('native must be a boolean value',(d,'pkg',123))
    }
    for t in tests:
        msg, params = tests[t]
        try:
            h.dump_heap(*params)
            print(
                'FAIL %s: expected exception (%s) from dump_heap with paramete'
                'rs: %s' % (pretty, msg, params)
            )
            return False
        except Exception as e:
            if not msg in str(e):
                print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
                return False
    return True

# test non-existing package name
def t05(w,h):
    pretty = '%s t05' % __file__
    print(pretty)

    try:
        pkg = 'no_process_found_for_package'
        h.dump_heap(w.get_path(), pkg)
        print(
            'FAIL %s: expected exception (dump_heap - no process)' % pretty
        )
        return False
    except Exception as e:
        if not 'no process found for package: ' in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# test dump_heap, verify file was pulled from handset, expect OK
@smoke
def t06(w,h):
    pretty = '%s t06' % __file__
    print(pretty)

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    try:
        paths = h.dump_heap(w.get_path(), pkg, timeout=120)
        if not paths:
            print('FAIL %s: no path received from dump_heap' % (pretty))
            return False
        for p in paths:
            if not p.endswith('.hprof'):
                print('FAIL %s: wrong file extension: %s' % (pretty, p))
                return False
            if not os.path.exists(p):
                print('FAIL %s: expected file to exist: %s' % (pretty, p))
                return False
            statinfo = os.stat(p)
            s = statinfo.st_size
            if not s > 0:
                print('FAIL %s: expected file size > 0: %s, %s' % (pretty,s,p))
                return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# test dump_heap with native=True, expect exception when libc.debug.malloc is
# not set before execution.
def t07(w,h):
    pretty = '%s t07' % __file__
    print(pretty)

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    # clear property
    try:
        prop_val = h.set_libc_debug_malloc(False, pkg, timeout=120)
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    # check the exception message
    try:
        paths = h.dump_heap(w.get_path(), pkg, native=True)
        print('FAIL %s: expected exception on dump_heap native' % (pretty))
        return False
    except Exception as e:
        if not str(e).startswith('dump_heap on native heap requires property '):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    # restore property
    try:
        h.set_libc_debug_malloc(prop_val, pkg, timeout=120)
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# test dump_heap with native=True, exepct OK
@smoke
def t08(w,h):
    pretty = '%s t08' % __file__
    print(pretty)

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    # set property
    try:
        prop_val = h.set_libc_debug_malloc(True, pkg, timeout=120)
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    # dump_heap
    try:
        paths = h.dump_heap(w.get_path(), pkg, native=True)
        if not paths:
            print('FAIL %s: no path received from dump_heap' % (pretty))
            return False
        for p in paths:
            if not p.endswith('.hprof'):
                print('FAIL %s: wrong file extension: %s' % (pretty, p))
                return False
            if not os.path.exists(p):
                print('FAIL %s: expected file to exist: %s' % (pretty, p))
                return False
            statinfo = os.stat(p)
            s = statinfo.st_size
            if not s > 0:
                print('FAIL %s: expected file size > 0: %s, %s' % (pretty,s,p))
                return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    # restore property
    try:
        h.set_libc_debug_malloc(prop_val, pkg, timeout=120)
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# check timeout exception on dump_heap
def t09(w,h):
    pretty = '%s t09' % __file__
    print(pretty)

    process = _get_running_process(h)
    if not process:
        print('FAIL %s: no running process found' % pretty)
        return False
    pkg = process['name']
    # test timeout
    try:
        paths = h.dump_heap(w.get_path(), pkg, timeout=0.1)
        print('FAIL %s: expected Timeout on dump_heap' % (pretty))
        return False
    except Exception as e:
        if not 'timed out' in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check dump_heap's exception message non-application process
def t10(w,h):
    pretty = '%s t10' % __file__
    print(pretty)

    process_name = '/init'
    # test timeout
    try:
        paths = h.dump_heap(w.get_path(), process_name)
        print('FAIL %s: expected unknown process failure on dump_heap'%(pretty))
        return False
    except Exception as e:
        err_msg = 'dump_heap failed: not an application process, application ' \
            'not debuggable or process {\'pid\': \'1\', \'name\': \'/init\'}' \
            ' is no longer running'
        if e.message != err_msg:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check invalid timeout gives an exception on dump_heap
def t11(w,h):
    pretty = '%s t11' % __file__
    print(pretty)

    # test timeout
    try:
        paths = h.dump_heap(w.get_path(), 'pkg', timeout='haha')
        print('FAIL %s: invalid type of timeout (dump_heap)' % (pretty))
        return False
    except Exception as e:
        if 'timeout must be of type int or float' != e.message:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check invalid timeout gives an exception on set_libc_debug_malloc
def t12(w,h):
    pretty = '%s t12' % __file__
    print(pretty)

    # test timeout
    try:
        h.set_libc_debug_malloc(True, 'pkg', timeout='haha')
        print('FAIL %s: invalid type of timeout (set_libc_debug_malloc)'%pretty)
        return False
    except Exception as e:
        if 'timeout must be of type int or float' != e.message:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True
