# -*- coding: utf-8 -*-

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import json
import copy
import StringIO
import traceback

import vcsjob

from ave.workspace import Workspace

# redirect stdout to a testable buffer. keep a backup to undo the replacement
# after the test
def redirect():
    backup = sys.stderr
    sys.stderr = strio = StringIO.StringIO()
    return (strio, backup)

def undirect(backup):
    sys.stderr = backup

def backup_env():
    return copy.deepcopy(os.environ)

def restore_env(backup):
    os.environ.clear()
    for var in backup:
        os.environ[var] = backup[var]

# factory function to create a valid vcsjob tree
def make_vcsjob_tree(workspace, banner=None, coverage=None):
    path = workspace.make_tempdir()
    with open(os.path.join(path, '.vcsjob'), 'w') as f:
        job = { 'path': 'job.sh', 'tags':['THIS'] }
        if banner:
            job['banner'] = banner
        if coverage:
            job['coverage'] = coverage
        dot_file = { 'executables': [ job ] }
#        print json.dumps(dot_file, indent=4)
        json.dump(dot_file, f)
    with open(os.path.join(path, 'job.sh'), 'w') as f:
        f.write('#! /bin/bash\nprintenv\n')
    os.chmod(os.path.join(path, 'job.sh'), 0755)
    return path

# check for exception when get_opt() is invoked without arguments
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.job.get_opt([])
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.job.opt() without arguments should fail'
            % pretty
        )
        return
    if str(exc) != 'at least -j or --jobs must be specified':
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

# check for exception when get_opt() is invoked with garbage arguments
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.job.get_opt(['--fg', 'hubba'])
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.job.get_opt() with garbage arguments '
            'should fail ' % pretty
        )
        return

    if str(exc) != 'option --fg not recognized':
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

# check for exception when get_opt() is invoked with extra non-dashed arguments
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    exc = None
    try:
        result = vcsjob.job.get_opt(['non-dashed'])
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute.get_opt() with extra non-dashed argument '
            'should fail' % pretty
        )
        return

    if str(exc) != 'non-dashed options "non-dashed" not recognized':
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

# check that execute.main() passes on environment variables mentioned with the
# --env option, but not others
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t4')

    # create the jobs tree
    def make_vcsjob_tree():
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write('{ "executables": [ { "path": "printenv.sh" } ] }')
        f.close()
        f = open(os.path.join(path, 'printenv.sh'), 'w')
        f.write('#! /bin/bash\nprintenv\n')
        f.close()
        os.chmod(os.path.join(path, 'printenv.sh'), 0755)
        return path
    jobs = make_vcsjob_tree()

    env = backup_env()

    # set some environment variables
    os.environ['FOO'] = 'BAR'
    os.environ['COW'] = 'MOO'

    cwd_bak = os.getcwd()
    (strio, backup) = redirect()
    result = vcsjob.job.main(['--jobs='+jobs, '--env=FOO'], )
    undirect(backup)
    os.chdir(cwd_bak)
    restore_env(env)

    # check that FOO appeared in the set of environment variables that the
    # test job could see, but not COW
    found_foo = False
    found_cow = False
    for line in strio.getvalue().splitlines():
        if   line == 'FOO=BAR':
            found_foo = True
        elif line == 'COW=MOO':
            found_cow = True
    if not found_foo:
       print('FAIL %s: FOO was not set: %s' % (pretty, strio.getvalue()))
       return
    if found_cow:
        print('FAIL %s: COW was set: %s' % (pretty, strio.getvalue()))
        return

    w.delete()

# check that an error is given if no jobs dir is given to execute.run()
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.execute_tags(None, None, None)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_tags() without jobs_dir param should fail'
            % pretty
        )
        return

    if str(exc) != 'not a jobs directory: None':
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

# check that an error is given if a non-existant jobs dir is referenced
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    (strio, backup) = redirect()
    result = vcsjob.job.main(['--jobs=does_not_exist'])
    undirect(backup)

    if result == vcsjob.OK:
        print(
            'FAIL %s: vcsjob.job.main() with jobs_dir that points to a '
            'directory which does not exist should fail' % pretty
        )
        return
    result = strio.getvalue().split('\n')[0]
    if result != 'ERROR: not a jobs directory: does_not_exist':
        print('FAIL %s: error not shown:\n%s' % (pretty, strio.getvalue()))
        return

# check that an error is given on .vcsjob file with syntax errors
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t7')

    # create the jobs tree
    def make_vcsjob_tree():
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        # broken JSON file:
        f.write('{ "executables": [ { "path": "printenv.sh"')
        f.close()
        f = open(os.path.join(path, 'printenv.sh'), 'w')
        f.write('#! /bin/bash\nprintenv\n')
        f.close()
        os.chmod(os.path.join(path, 'printenv.sh'), 0755)
        return path
    jobs = make_vcsjob_tree()

    exc = None
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_tags() with --jobs that points to an '
            'invalid jobs directory should fail' % pretty
        )
        return

    if not str(exc).startswith('could not load %s/.vcsjob: Expecting '%jobs):
        print('FAIL %s: wrong error message: "%s"' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the .vcsjob file contains a job without the
# "path" property
def t8():
    pretty = '%s t8' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t8')

    # create the jobs tree
    def make_vcsjob_tree():
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
         # no "path" attr:
        f.write('{ "executables": [ { "PATH": "printenv.sh" } ] }')
        f.close()
        return path
    jobs = make_vcsjob_tree()

    exc = None
    try:
        result = vcsjob.execute_tags(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_tags() with --jobs that points to an '
            'invalid jobs directory should fail' % pretty
        )
        return

    if not str(exc).startswith('job does not have the "path" attribute: '):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the referenced job doesn't exist
def t9():
    pretty = '%s t9' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t9')

    # create the jobs tree
    def make_vcsjob_tree():
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write('{ "executables": [ { "path": "no_such_file" } ] }')
        f.close()
        return path
    jobs = make_vcsjob_tree()

    exc = None
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_tags() with --jobs that points to an '
            'invalid jobs directory should fail' % pretty
        )
        return

    if not str(exc).startswith('no such file:'):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the referenced job isn't executable
def t10():
    pretty = '%s t10' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t10')

    # create the jobs tree
    def make_vcsjob_tree():
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write('{ "executables": [ { "path": "not_executable" } ] }')
        f.close()
        f = open(os.path.join(path, 'not_executable'), 'w')
        return path
    jobs = make_vcsjob_tree()

    exc = None
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_tags() with --jobs that points to an '
            'invalid jobs directory should fail' % pretty
        )
        return

    if not str(exc).startswith('file is not executable:'):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that jobs are skipped if there is a tag filter and the job does not
# have the tag
def t11():
    pretty = '%s t11' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t11')
    jobs = make_vcsjob_tree(w)

    cwd_bak = os.getcwd()
    (strio, backup) = redirect()
    result = vcsjob.execute_tags(jobs_dir=jobs, job_tags=['THAT'])
    undirect(backup)
    os.chdir(cwd_bak)

    if result == vcsjob.OK:
        print(
            'FAIL %s: vcsjob.execute_tags() returned OK even though there were '
            'no jobs to run' % pretty
        )
        return
    result = strio.getvalue().split('\n')[0]
    if result != 'WARNING: no jobs were executed':
        print('FAIL %s: error not shown:\n%s' % (pretty, strio.getvalue()))
        return

    w.delete()

# check that an error is reported if --env is used with an environment variable
# that is not set
def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t12')
    jobs = make_vcsjob_tree(w)
    os.unsetenv('PATH')

    exc = None
    try:
        vcsjob.execute_tags(jobs, None, ['PATH'])
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.fetch.run() with junk --env did not fail'
            % pretty
        )
        return

    # check the error message
    if not str(exc).startswith('environment variable "PATH" is not set'):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that correct value is returned by vcsjob.execute_single()
def t13():
    pretty = '%s t13' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t13')

    def make_vcsjob_tree(workspace):
        path = workspace.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write(
            '{ "executables": ['
            '{ "path": "job1.sh", "tags":["THIS"] },'
            '{ "path": "job2.sh", "tags":["THIS"] },'
            '{ "path": "job3.sh", "tags":["THIS"] },'
            '{ "path": "job4.sh", "tags":["THIS"] },'
            '{ "path": "job-1.sh", "tags":["THIS"] },'
            '{ "path": "job-2.sh", "tags":["THIS"] },'
            '{ "path": "job-100.sh", "tags":["THIS"] },'
            '{ "path": "job0.sh", "tags":["THIS"] }'
            '] }')
        f.close()

        def write_file(path, ret_val):
            name = 'job%d.sh' % ret_val
            f = open(os.path.join(path, name), 'w')
            f.write('#! /bin/bash\nexit %d\n' % ret_val)
            f.close()
            os.chmod(os.path.join(path, name), 0755)
            return name

        f1 = write_file(path, 1)
        f2 = write_file(path, 2)
        f3 = write_file(path, 3)
        f4 = write_file(path, 4)
        f5 = write_file(path, -1)
        f6 = write_file(path, -2)
        f7 = write_file(path, -100)
        f8 = write_file(path, 0)

        return path, [f1, f2, f3, f4, f5, f6, f7, f8]

    def verify_ret(path, job, ret):
        backup = None
        try:
            (strio, backup) = redirect()
            result = vcsjob.execute_single(path, job)
            undirect(backup)
            if result != ret:
                print(
                    'FAIL: file %s returned: %d, expected : %d'
                    % (job, result, ret)
                )
                return
        except Exception, e:
            undirect(backup)
            print('FAIL %s: got exception: %s' % (pretty, str(e)))
            return

    path, jobs = make_vcsjob_tree(w)
    verify_ret(path, jobs[0], 1)
    verify_ret(path, jobs[1], 2)
    verify_ret(path, jobs[2], 3)
    verify_ret(path, jobs[3], 4)
    verify_ret(path, jobs[4], 255) # POSIX enforces exit status range 0-255,
    verify_ret(path, jobs[5], 254) # which means negative values wrap around
    verify_ret(path, jobs[6], 156) # from 0 to 255.
    verify_ret(path, jobs[7], 0)

    w.delete()

# check that an error is given if the referenced job doesn't exist
def t14():
    pretty = '%s t14' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t14')

    # create the jobs tree
    def make_vcsjob_tree(w):
        path = w.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write('{ "executables": [ { "path": "job.sh" } ] }')
        f.close()

        return path

    path = make_vcsjob_tree(w)
    exc = None
    backup = None
    try:
        job = 'job_does_not_exist.sh'
        (strio, backup) = redirect()
        result = vcsjob.execute_job(path, {'path':job}, [], None)
        undirect(backup)
        print(
            'FAIL %s: expected exception on job: %s'
            % (pretty, job)
        )
        return
    except Exception, e:
        undirect(backup)
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.execute_single() that points to an invalid job '
            'should fail' % pretty
        )
        return

    if not str(exc).startswith('no such file:'):
        print('FAIL %s: wrong error message:\n%s' % (pretty, str(exc)))
        return
    w.delete()

# check if trying to execute single job with exec_target=None raises an
# exception
def t15():
    pretty = '%s t15' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t15')
    path = make_vcsjob_tree(w)
    backup = None
    try:
        (strio, backup) = redirect()
        result = vcsjob.execute_single(path, exec_target=None, env_vars=['HOME'])
        undirect(backup)
        print('FAIL %s: exec_target=None should generate exception' % (pretty))
    except Exception, e:
        undirect(backup)
        if 'execution target: None' != str(e):
            print('FAIL %s: wrong error message:\n%s' % (pretty, str(e)))
            return
    w.delete()

# check invalid type (list of strings) of banner results in an exception
def t16():
    pretty = '%s t16' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t16')
    jobs = make_vcsjob_tree(w, banner=['list','of','strings'])
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
        print('FAIL %s: expected exception (invalid banner - list)' % (pretty))
    except Exception, e:
        if not str(e).startswith('job\'s "banner" attribute must be a string:'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
    w.delete()

# check invalid type (integer) of banner results in an exception
def t17():
    pretty = '%s t17' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t17')
    jobs = make_vcsjob_tree(w, banner=13)
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
        print('FAIL %s: expected exception (invalid banner - int)' % (pretty))
    except Exception, e:
        if not str(e).startswith('job\'s "banner" attribute must be a string:'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
    w.delete()

# check "" is a valid value for banner
def t18():
    pretty = '%s t18' % __file__
    print(pretty)

    w      = Workspace(uid='vcsjob-execute-t18')
    jobs   = make_vcsjob_tree(w, banner='""')
    backup = None
    try:
        (strio, backup) = redirect()
        vcsjob.execute_tags(jobs_dir=jobs)
        undirect(backup)
    except Exception, e:
        undirect(backup)
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
    w.delete()

# check special characters in banner
def t19():
    pretty = '%s t19' % __file__
    print(pretty)

    w      = Workspace(uid='vcsjob-execute-t18')
    jobs   = make_vcsjob_tree(w, banner='"Angry jobs! €¤!^~ü#¤/=!¤$£.åäöÅÄÖ"')
    backup = None
    try:
        (strio, backup) = redirect()
        vcsjob.execute_tags(jobs_dir=jobs)
        undirect(backup)
    except Exception, e:
        undirect(backup)
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
    w.delete()







# check that invalid type of coverage (a string) results in an exception
def t20():
    pretty = '%s t20' % __file__
    print(pretty)

    w = Workspace()
    jobs = make_vcsjob_tree(w, coverage='not a list of strings')
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
        print('FAIL %s: expected exception (invalid coverage)' % (pretty))
    except Exception, e:
        if '"coverage" attribute is not a list of strings' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
    w.delete()

# check that invalid type of coverage (list of ints) results in an exception
def t21():
    pretty = '%s t21' % __file__
    print(pretty)

    w = Workspace()
    jobs = make_vcsjob_tree(w, coverage=['list','of','ints',1,2,3])
    try:
        vcsjob.execute_tags(jobs_dir=jobs)
        print('FAIL %s: expected exception (invalid coverage)' % (pretty))
    except Exception, e:
        if '"coverage" attribute is not a list of strings' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
    w.delete()

# check special characters in coverage items
def t22():
    pretty = '%s t22' % __file__
    print(pretty)

    w      = Workspace()
    jobs   = make_vcsjob_tree(w, coverage=['Angry! €¤!^','~ü#¤/=!¤$£.åäöÅÄÖ"'])
    backup = None
    try:
        (strio, backup) = redirect()
        vcsjob.execute_tags(jobs_dir=jobs)
        undirect(backup)
    except Exception, e:
        undirect(backup)
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
    w.delete()

# check that invalid type of dirty (a string) results in an exception
def t23():
    pretty = '%s t23' % __file__
    print(pretty)

    w      = Workspace()
    pwd = os.path.dirname(__file__)
    job_dir = os.path.dirname(os.path.dirname(pwd))
    job = {"path":"jobs/duration_test","dirty":"dirty"}

    try:
        vcsjob.execute_job(job_dir, job, None, None, None)
        print('FAIL %s: expected exception (invalid dirty)' % (pretty))
    except Exception, e:
        if '"dirty" attribute is not a boolean value' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
    w.delete()

# check that invalid type of virgin (a string) results in an exception
def t24():
    pretty = '%s t24' % __file__
    print(pretty)

    w      = Workspace()
    pwd = os.path.dirname(__file__)
    job_dir = os.path.dirname(os.path.dirname(pwd))
    job = {"path":"jobs/duration_test","virgin":"virgin"}

    try:
        vcsjob.execute_job(job_dir, job, None, None, None)
        print('FAIL %s: expected exception (invalid dirty)' % (pretty))
    except Exception, e:
        if '"virgin" attribute is not a boolean value' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
    w.delete()

# check that invalid type of duration (a string) results in an exception
def t25():
    pretty = '%s t25' % __file__
    print(pretty)

    w      = Workspace()
    pwd = os.path.dirname(__file__)
    job_dir = os.path.dirname(os.path.dirname(pwd))
    job = {"path":"jobs/duration_test","duration":"duration"}

    try:
        vcsjob.execute_job(job_dir, job, None, None, None)
        print('FAIL %s: expected exception (invalid dirty)' % (pretty))
    except Exception, e:
        if '"duration" attribute is not an integer' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, str(e)))
    w.delete()