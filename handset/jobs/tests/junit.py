import os
import traceback

from ave.exceptions import Timeout, RunError

from decorators import smoke

# Check that run_junit fails with bad output_path given
def t01(w,h,label):
    pretty = '%s t1' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path1 = None
    output_path2 = '/root/latjo_lajban.txt'
    output_path3 = '%s/path_does_not_exist/my_output_file.txt' % w.get_path()

    def check_bad_path(output_path):
        try:
            output = h.run_junit(output_path)
            print(
                'FAIL %s: expected exception: bad path: %s'
                %(pretty, output_path)
            )
            return False
        except:
            return True

    if not check_bad_path(output_path1): return False
    if not check_bad_path(output_path2): return False
    if not check_bad_path(output_path3): return False

    return True

# Expect exception (test_package and runner)
def t02(w,h,label):
    pretty = '%s t2' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path,
            test_package='com.random.pkg.name',
            runner='random/testrunner'
        )
        print(
            'FAIL %s: expected exception: (test_package and runner)' % (pretty)
        )
        return False
    except Exception, e:
        if e.message != 'invalid combination of parameters':
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Expect exception (test_package and test_options)
def t03(w,h,label):
    pretty = '%s t3' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path,
            test_package='com.random.pkg.name',
            test_options='class random.test.option.class'
        )
        print(
            'FAIL %s: expected exception: (test_package and test_options)'
            % (pretty)
        )
        return False
    except Exception, e:
        if e.message != 'invalid combination of parameters':
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Expect exception (runner and raw)
def t05(w,h,label):
    pretty = '%s t5' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path,
            runner='random/testrunner',
            raw='-r -w random.raw/InstrumentationTestRunner'
        )
        print('FAIL %s: expected exception: (test_package and raw)' % (pretty))
    except Exception, e:
        if e.message != 'invalid combination of parameters':
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Expect exception (raw and test_options)
def t06(w,h,label):
    pretty = '%s t6' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path,
            test_options='class random.test.option.class',
            raw='-r -w random.raw/InstrumentationTestRunner'
        )
        print(
            'FAIL %s: expected exception: (test_package and test_options)'
            % (pretty)
        )
        return False
    except Exception, e:
        if e.message != 'invalid combination of parameters':
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False

    return True

# Check 'test_options not dict'
def t07(w,h,label):
    pretty = '%s t7' % __file__
    print(pretty)

    # Setup parameters
    tr = 'com.sonyericsson.organizer.test/' \
            'com.sonyericsson.organizer.runners.UnitTestRunner'
    opt = 'class com.sonyericsson.organizer.worldclock.UWorldClockTests'
    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(output_path, runner=tr, test_options=opt)
        print('FAIL %s: expected exception on non-dict test_options' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('invalid type of test_options:'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Check that test_package must be installed if it is given
def t08(w,h,label):
    pretty = '%s t8' % __file__
    print(pretty)

    # Where the test execution output should be written to
    o = w.make_tempfile()
    try:
        bad_pkg = 'com.not.installed.package'
        output = h.run_junit(o, test_package=bad_pkg)
        print('FAIL %s: no exception on package_name: %s' % (pretty, bad_pkg))
        return False
    except Exception, e:
        if not str(e).startswith('no such test package on handset:'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

@smoke
def t09(w,h,label):
    pretty = '%s t9' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path,
            test_package='com.android.phone'
        )
        print(
            'FAIL %s: expected exception: no runner in package: %s'
            % (pretty, 'com.android.phone')
        )
        return False
    except Exception, e:
        if not str(e).startswith('no runner in package:'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Check that invalid types results in exceptions
def t15(w,h,label):
    pretty = '%s t15' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    # Check invalid types:
    try:
        output = h.run_junit(output_path, test_package=44)
        print(
            'FAIL %s: expected exception: invalid type (test_package)'
            % (pretty)
        )
        return False
    except Exception, e:
        pass

    try:
        output = h.run_junit(output_path, runner=[])
        print(
            'FAIL %s: expected exception on invalid type (runner)' % (pretty)
        )
        return False
    except Exception, e:
        pass

    try:
        output = h.run_junit(output_path, raw=0.77)
        print('FAIL %s: expected exception on invalid type (raw)' % (pretty))
        return False
    except Exception, e:
        pass
    return True

# Check that missing parameter results in an exception
def t16(w,h,label):
    pretty = '%s t16' % __file__
    print(pretty)

    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    # Check invalid types:
    try:
        output = h.run_junit(
            output_path, test_package=None, runner=None, raw=None
        )
        print('FAIL %s: expected exception: missing parameter' % (pretty))
        return False
    except Exception, e:
        if not str(e).startswith('missing parameter:'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# t45 moved to separate file local_execution.py t1

# Negative check: kill_junit_test() should only kill instrumentation processes
def t22(w,h,label):
    pretty = '%s t22' % __file__
    print(pretty)
    try:
        h.kill_junit_test('com.android.email')
        print(
            'FAIL %s: expected exception on a non-instrumentation package'
            % (pretty)
        )
        return False
    except Exception, e:
        if not str(e).startswith('could not validate as instrumentation'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Negative check: None cannot be given to kill_junit_test()
def t23(w,h,label):
    pretty = '%s t23' % __file__
    print(pretty)
    try:
        h.kill_junit_test(None)
        print('FAIL %s: expected exception; no package given' % (pretty))
        return False
    except Exception, e:
        if e.message != 'no package given':
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True
