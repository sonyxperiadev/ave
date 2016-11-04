# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys

import vcsjob

from ave.workspace import Workspace

# check that an error is given if no jobs dir is given to list_jobs.run()
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.list_jobs(None, None)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.list_jobs() without jobs_dir param should fail'
            % pretty
        )
        return

    if str(exc) != 'not a jobs directory: None':
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

# check that an error is given if a non-existant jobs dir is referenced
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        result = vcsjob.list_jobs(jobs_dir='does_not_exist', job_tags=None)
        print(
            'FAIL %s: vcsjob.list_jobs() with jobs_dir that points to a '
            'nonexistent directory should raise exception' % pretty
        )
    except Exception, e:
        if 'not a jobs directory: does_not_exist' != str(e):
            print('FAIL %s: wrong exception message: %s' % (pretty, str(e)))

# check that an error is given on .vcsjob file with syntax errors
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t3')

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
        vcsjob.list_jobs(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.list_jobs() with jobs_dir that points to an '
            'invalid jobs directory should fail' % pretty
        )
        return

    if not str(exc).startswith('could not load %s/.vcsjob: Expecting '%jobs):
        print('FAIL %s: wrong error message: "%s"' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the .vcsjob file contains a job without the
# "path" property
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t4')

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
        result = vcsjob.list_jobs(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.list_jobs(), jobs without path set should'
            'fail' % pretty
        )
        return

    if not str(exc).startswith('job does not have the "path" attribute: '):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the referenced job doesn't exist
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t5')

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
        vcsjob.list_jobs(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.list_jobs(), job with path set to a nonexistent '
            'target should fail' % pretty
        )
        return

    if not str(exc).startswith('no such file:'):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that an error is given if the referenced job isn't executable
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t6')

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
        vcsjob.list_jobs(jobs_dir=jobs)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.list_jobs() should fail if a referenced job '
            'isn\'t executable' % pretty
        )
        return

    if not str(exc).startswith('file is not executable:'):
        print('FAIL %s: error not shown:\n%s' % (pretty, str(exc)))
        return

    w.delete()

# check that jobs are skipped if there is a tag filter and the job does not
# have the tag
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    def make_vcsjob_tree(workspace):
        path = workspace.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write('{ "executables": [ { "path": "job.sh", "tags":["THIS"] } ] }')
        f.close()
        f = open(os.path.join(path, 'job.sh'), 'w')
        f.write('#! /bin/bash\nprintenv\n')
        f.close()
        os.chmod(os.path.join(path, 'job.sh'), 0755)
        return path

    w = Workspace(uid='vcsjob-execute-t7')
    jobs = make_vcsjob_tree(w)
    result = vcsjob.list_jobs(jobs_dir=jobs, job_tags=['THAT'])

    if result != []:
        print(
            'FAIL %s: vcsjob.list_jobs() returned a nonempty list even though '
            'there were no jobs to list' % pretty
        )
        return

    w.delete()

# check that tagged jobs are found as expected
def t8():
    pretty = '%s t8' % __file__
    print(pretty)

    w = Workspace(uid='vcsjob-execute-t8')

    def make_vcsjob_tree(workspace):
        path = workspace.make_tempdir()
        f = open(os.path.join(path, '.vcsjob'), 'w')
        f.write(
            '{ "executables": ['
            '{ "path": "job1.sh", "tags":["NICE", "THIS"] },'
            '{ "path": "job2.sh", "tags":["BAD", "THIS"] },'
            '{ "path": "job3.sh", "tags":["NICE", "THAT"] },'
            '{ "path": "job4.sh", "tags":["THIS"] },'
            '{ "path": "job-1.sh", "tags":["THAT"] },'
            '{ "path": "job-2.sh", "tags":["BAD", "THAT", "NICE", "THIS"] },'
            '{ "path": "job-100.sh", "tags":["THAT", "THIS"] },'
            '{ "path": "job0.sh" }'
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
        return path # End make_vcsjob_tree

    def verify_ret(pretty, path, exp_count, tags):
        try:
            result = vcsjob.list_jobs(path, tags)
            if len(result) != exp_count:

                print(
                    'FAIL %s: unexpected number of jobs returned: %d, expected'
                    ' : %d' % (pretty, len(result), exp_count)
                )
                return
        except Exception, e:
            print('FAIL %s: got exception: %s' % (pretty, str(e)))
            return

    path = make_vcsjob_tree(w)
    verify_ret(pretty, path, 3, ['NICE'])
    verify_ret(pretty, path, 2, ['BAD'])
    verify_ret(pretty, path, 1, ['NICE', 'BAD'])
    verify_ret(pretty, path, 4, ['THAT'])
    verify_ret(pretty, path, 5, ['THIS'])
    verify_ret(pretty, path, 2, ['THIS', 'THAT'])
    verify_ret(pretty, path, 0, ['THIS', 'BIZ'])
    verify_ret(pretty, path, 1, ['BAD', 'NICE', 'THAT'])
    verify_ret(pretty, path, 8, [])

    w.delete()

