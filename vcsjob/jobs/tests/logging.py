import os
import sys
import json
import StringIO

import vcsjob

from ave.workspace import Workspace

def setup(fn):
    def decorator():
        w = Workspace()
        result = fn(w)
        w.delete()
        return result
    return decorator

def redirect():
    backup = sys.stderr
    sys.stderr = strio = StringIO.StringIO()
    return (strio, backup)

def undirect(backup):
    sys.stderr = backup

def find_vcsjob_dir(path):
    if not path or path == '/':
        raise Exception('no .vcsjob file found')
    if os.path.exists(os.path.join(path, '.vcsjob')):
        return path
    return find_vcsjob_dir(os.path.dirname(path))

# first line in output will be different for different users. ignore it when
# comparing with actual outputs in tests
DEMO_OUTPUT = \
'''ignore this line
0
1
2
3
4
5
6
7
8
9
'''

# logging to file produces sane results
@setup
def t1(w):
    pretty = '%s t1' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_job.py')
    log  = os.path.join(w.path, 'log.txt')

    try:
        vcsjob.execute_single(root, job, [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    expected = [e.strip() for e in DEMO_OUTPUT.splitlines()[1:]]
    with open(log) as f:
        actual = f.read()
        actual = [a.strip() for a in actual.splitlines()[1:]]

    if actual != expected:
        print('FAIL %s: wrong logs: %s != %s' % (pretty, actual, expected))
        return False

    return True

# logging to file should be identical to logging to terminal, except for the
# vcsjob header which will have 'log' set in one case but not the other, and
# the jobs' own prints of environment variables, so ignore lines that start
# with "VCSJOB_LOG_PATH="
@setup
def t2(w):
    pretty = '%s t2' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    log  = os.path.join(w.path, 'log.txt')

    # produce reference output
    strio, backup = redirect()
    try:
        vcsjob.execute_tags(root, ['DEMO'], [], None)
    except Exception, e:
        undirect(backup)
        print('FAIL %s: could not produce reference: %s' % (pretty, e))
        return False
    undirect(backup)

    expected = strio.getvalue().splitlines()
    expected = '\n'.join(e for e in expected if not e.startswith('vcsjob: {'))

    # produce tested output
    try:
        vcsjob.execute_tags(root, ['DEMO'], [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    with open(log) as f:
        actual = f.read().splitlines()
        actual = [a for a in actual if not a.startswith('vcsjob: {')]
    actual = [a for a in actual if not a.startswith('VCSJOB_LOG_PATH=')]
    actual = '\n'.join(actual)

    if actual != expected:
        print('FAIL %s: wrong logs: %s != %s' % (pretty, actual, expected))
        return False

    return True

# check that exit status is reported correctly. (the logging feature changes
# the handling of jobs' exit status.)
@setup
def t3(w):
    pretty = '%s t3' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_exit_0.sh')
    log  = os.path.join(w.path, 'log.txt')

    try:
        status = vcsjob.execute_single(root, job, [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    if status != 0:
        print('FAIL %s: wrong exit status: %d' % (pretty, status))
        return False

    with open(log) as f:
        actual = f.read()
        actual = [a.strip() for a in actual.splitlines()]

    if (len(actual) != 1) or (not actual[0].startswith('vcsjob: {')):
        print('FAIL %s: wrong logs: %s' % (pretty, actual))
        return False

    return True

# check that exit status is reported correctly. (the logging feature changes
# the handling of jobs' exit status.)
@setup
def t4(w):
    pretty = '%s t4' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_exit_100.sh')
    log  = os.path.join(w.path, 'log.txt')

    try:
        status = vcsjob.execute_single(root, job, [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    if status != 100:
        print('FAIL %s: wrong exit status: %d' % (pretty, status))
        return False

    with open(log) as f:
        actual = f.read()
        actual = [a.strip() for a in actual.splitlines()]

    if (len(actual) != 1) or (not actual[0].startswith('vcsjob: {')):
        print('FAIL %s: wrong logs: %s' % (pretty, actual))
        return False

    return True

# check that exit status is reported correctly when the test job is signelled
# to death. (the logging feature changes the handling of jobs' exit status.)
@setup
def t5(w):
    pretty = '%s t5' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_suicide.py')
    log  = os.path.join(w.path, 'log.txt')

    try:
        status = vcsjob.execute_single(root, job, [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    if status != vcsjob.KILLED:
        print('FAIL %s: wrong exit status: %d' % (pretty, status))
        return False

    with open(log) as f:
        actual = f.read()
        actual = [a.strip() for a in actual.splitlines()]

    if len(actual) != 2 or actual[1] != 'SIGTERM suicide':
        print('FAIL %s: wrong logs: %s' % (pretty, actual))
        return False

    return True

# check that exit status is reported correctly when the tags filter doesn't
# include any job. (the logging feature changes the handling of jobs' exit
# status.)
@setup
def t6(w):
    pretty = '%s t6' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    log  = os.path.join(w.path, 'log.txt')

    try:
        status = vcsjob.execute_tags(root, ['NO_SUCH_TAG'], [], log)
    except Exception, e:
        print('FAIL %s: could not log to file: %s' % (pretty, e))
        return False

    if status != vcsjob.NORUN:
        print('FAIL %s: wrong exit status: %d' % (pretty, status))
        return False

    with open(log) as f:
        actual = f.read()
        actual = [a.strip() for a in actual.splitlines()]

    if actual != ['WARNING: no jobs were executed']:
        print('FAIL %s: wrong logs: %s' % (pretty, actual))
        return False

    return True

# check that exit codes have string representations
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    s = vcsjob.exit_to_str(vcsjob.OK)
    if s != 'vcsjob.OK':
        print('FAIL %s: vcsjob.OK != "vcsjob.OK": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.ERROR)
    if s != 'vcsjob.ERROR':
        print('FAIL %s: vcsjob.ERROR != "vcsjob.ERROR": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.NORUN)
    if s != 'vcsjob.NORUN':
        print('FAIL %s: vcsjob.NORUN != "vcsjob.NORUN": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.BLOCKED)
    if s != 'vcsjob.BLOCKED':
        print('FAIL %s: vcsjob.BLOCKED != "vcsjob.BLOCKED": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.BUSY)
    if s != 'vcsjob.BUSY':
        print('FAIL %s: vcsjob.BUSY != "vcsjob.BUSY": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.FAILURES)
    if s != 'vcsjob.FAILURES':
        print('FAIL %s: vcsjob.FAILURES != "vcsjob.FAILURES": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.NOLIST)
    if s != 'vcsjob.NOLIST':
        print('FAIL %s: vcsjob.NOLIST != "vcsjob.NOLIST": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.KILLED)
    if s != 'vcsjob.KILLED':
        print('FAIL %s: vcsjob.KILLED != "vcsjob.KILLED": %s' % (pretty, s))
        return False

    s = vcsjob.exit_to_str(vcsjob.NOFETCH)
    if s != 'vcsjob.NOFETCH':
        print('FAIL %s: vcsjob.NOFETCH != "vcsjob.NOFETCH": %s' % (pretty, s))
        return False

    try:
        s = vcsjob.exit_to_str(-1)
        print('FAIL %s: unknown exit code == "%s"' % (pretty, s))
        return False
    except:
        pass

    return True

# check that vcsjob.get_log_path() returns None if no log file was set when
# calling an execute function
@setup
def t8(w):
    pretty = '%s t8' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_logging.py')

    strio, backup = redirect()
    os.environ['PYTHONPATH'] = sys.path[0] # makes the UNIT scope work
    status = vcsjob.execute_single(root, job, ['PYTHONPATH'], None)
    undirect(backup)

    if status != 0:
        print('FAIL %s: VCSJOB_LOG_PATH was not None' % pretty)
        return False

    log = strio.getvalue().splitlines()
    if len(log) != 1:
        print('FAIL %s: a log path was logged: %s' % (pretty, log))
        return False

    return True

# check that vcsjob.get_log_path() returns the correct path
@setup
def t9(w):
    pretty = '%s t9' % __file__
    print(pretty)

    root = find_vcsjob_dir(__file__)
    job  = os.path.join('jobs', 'demo_logging.py')
    path = w.make_tempfile()

    os.environ['PYTHONPATH'] = sys.path[0] # makes the UNIT scope work
    status = vcsjob.execute_single(root, job, ['PYTHONPATH'], path)

    if status != 1:
        print('FAIL %s: VCSJOB_LOG_PATH was None' % pretty)
        return False

    with open(path) as f:
        log = f.read().splitlines()
        if log[1] != path:
            print('FAIL %s: wrong path logged: %s' % (pretty, log))
            return False

    return True
