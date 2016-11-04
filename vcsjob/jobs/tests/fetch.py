# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import StringIO
import shutil

import ave.git

import vcsjob
import vcsjob.vcs

from ave.workspace import Workspace

# redirect stdout to a testable buffer. keep a backup to undo the replacement
# after the test
def redirect():
    backup = sys.stdout
    sys.stdout = strio = StringIO.StringIO()
    return (strio, backup)

def undirect(backup):
    sys.stdout = backup

# factory function. a git with two commits and a valid .vcsjob file
def make_vcsjob_tree(workspace):
    path = workspace.make_tempdir()
    f = open(os.path.join(path, '.vcsjob'), 'w')
    f.write('{ "jobs": [ { "path": "job.sh" } ] }')
    f.close()
    f = open(os.path.join(path, 'job.sh'), 'w')
    f.write('#! /bin/bash\nprintenv\n')
    f.close()
    os.chmod(os.path.join(path, 'job.sh'), 0755)
    ave.git.init(path)
    ave.git.add(path, '.')
    ave.git.commit(path, 'First commit')
    ave.git.create_branch(path, 'testing')
    f = open(os.path.join(path, 'foo.txt'), 'w')
    f.write('bar')
    f.close()
    ave.git.add(path, '.')
    ave.git.commit(path, 'Second commit')
    return path

# check that result is False when invoked without arguments
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.vcs.fetch(None, None, None)
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.vcs.run() without arguments should fail'
            % pretty
        )
        return

    if str(exc) != 'source, refspec and destination must be specified':
        print('FAIL %s: wrong message: %s' % (pretty, str(exc)))
        return

# check that usage info is printed if invoked with garbage options
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    (strio, backup) = redirect()
    result = vcsjob.vcs.main(['--fg','hubba'])
    undirect(backup)

    if result == vcsjob.OK:
        print(
            'FAIL %s: vcsjob.vcs.main() with garbage arguments should fail'
            % pretty
        )
        return

    message = strio.getvalue()
    if not message.startswith('ERROR: option --fg not recognized'):
        print('FAIL %s: wrong message: %s' % (pretty, message))
        return

# check that usage info is printed if invoked with extra non-dashed arguments
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    (strio, backup) = redirect()
    result = vcsjob.vcs.main(['non-dashed'])
    undirect(backup)

    if result == vcsjob.OK:
        print(
            'FAIL %s: vcsjob.vcs.main() with garbage arguments should fail'
            % pretty
        )
        return

    message = strio.getvalue()
    if not message.startswith('ERROR: non-dashed options "non-dashed" not '):
        print('FAIL %s: error not shown: %s' % (pretty, message))
        return

# check that usage info is printed if invoked without complete input (source,
# destination and refspec)
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    (strio, backup) = redirect()
    result = vcsjob.vcs.main(['--source=incomplete'])
    undirect(backup)

    if result == vcsjob.OK:
        print(
            'FAIL %s: vcsjob.vcs.main() with garbage arguments should fail'
            % pretty
        )
        return

    message = strio.getvalue()
    if not message.startswith('ERROR: source, refspec and destination must be'):
        print('FAIL %s: error not shown: %s' % (pretty, message))
        return

# check that supported protocol info is printed if a non-git is given as source
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    exc = None
    try:
        vcsjob.fetch('/', 'nonsense', 'nonsense')
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.fetch() with garbage arguments should fail'
            % pretty
        )
        return

    if str(exc) != 'supported protocols: git':
        print('FAIL %s: wrong message: %s' % (pretty, str(exc)))
        return

# check that an error is printed if non-local destination is given
def t6():
    pretty = '%s t6' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t6')

    # create a git tree in a temp directory to use for this test
    src = make_vcsjob_tree(w)

    exc = None
    try:
        vcsjob.fetch(src, 'ssh://host', 'bleh')
    except Exception, e:
        exc = e

    if not exc:
        print(
            'FAIL %s: vcsjob.fetch() with garbage arguments should fail'
            % pretty
        )
        return

    if str(exc) != 'destination must be on a locally mounted file system':
        print('FAIL %s: wrong message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that basic fetching works
def t7():
    pretty = '%s t7' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t7')

    # set up source and destination in temporary directories
    src = make_vcsjob_tree(w)
    dst = w.make_tempdir()

    # fetch the source into the destination
    try:
        vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return

    # look for src/test.txt in the destination
    if not os.path.isfile(os.path.join(dst, '.vcsjob')):
        print('FAIL %s: source file not in destination' % pretty)
        return

    w.delete()

# check that repeated fetching works
def t8():
    pretty = '%s t8' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t8')

    # set up source and destination in temporary directories
    src = make_vcsjob_tree(w)
    dst = w.make_tempdir()

    # repeatedly fetch the source into the destination
    result = vcsjob.OK
    for i in range(5):
        try:
            result += vcsjob.fetch(src, dst, 'master')
        except Exception, e:
            print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
            return

    if result != vcsjob.OK:
        print('FAIL %s: wrong return value: %s' % (pretty, result))
        return

    # look for src/test.txt in the destination
    if not os.path.isfile(os.path.join(dst, '.vcsjob')):
        print('FAIL %s: source file not in destination' % pretty)
        return

    w.delete()

# check that vcsjob refuses to switch between branches if the destination tree
# is dirty.
def t9():
    pretty = '%s t9' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t9')

    src = make_vcsjob_tree(w)
    dst = w.make_tempdir()

    # pull the tree into a temporary directory, check that the current branch
    # is "master".
    try:
        result = vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return

    if result != vcsjob.OK:
        print('FAIL %s: wrong return value: %s' % (pretty, result))
        return

    branch = ave.git.branch(dst)
    if branch != 'master':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return

    # introduce some dirt
    f = open(os.path.join(dst, 'dirt'), 'w')
    f.write('some dirt for `git status` to pick up')
    f.close()

    # fetch again into the same directory, check that the checkout failed and
    # that "master" remains the current branch.
    exc = None
    try:
        result = vcsjob.vcs.run(['-s',src, '-d',dst, '-r','testing'])
    except Exception, e:
        exc = e

    if not exc:
        print('FAIL %s: fetch did not fail on dirty destination' % pretty)
        return

    branch = ave.git.branch(dst)
    if branch != 'master':
        print(
            'FAIL %s: wrong branch checked out after second fetch: %s'
            % (pretty, branch)
        )
        return

    w.delete()

# check that fetching to a non-existant directory works
def t10():
    pretty = '%s t10' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t10')

    # set up source and destination in temporary directories
    src = make_vcsjob_tree(w)

    # "create" a non-existant destination directory by removing a temporary dir
    dst = w.make_tempdir()
    shutil.rmtree(dst)

    # fetch the source into the destination
    try:
        result = vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return

    if result != vcsjob.OK:
        print('FAIL %s: wrong return value: %s' % (pretty, result))
        return

    # look for src/test.txt in the destination
    if not os.path.isfile(os.path.join(dst, '.vcsjob')):
        print('FAIL %s: source file not in destination' % pretty)
        return

    w.delete()

# check that fetching to a destination which is not a directory doesn't work
def t11():
    pretty = '%s t11' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t11')

    src = make_vcsjob_tree(w)

    # create a non-directory destination
    dst = os.path.join(w.make_tempdir(), 'some_file')
    with open(dst, 'w') as f:
        f.write('anything')
        f.close()

    # fetch the source into the destination
    exc = None
    try:
        result = vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        exc = e

    if not exc:
        print('FAIL %s: fetch did not fail' % pretty)
        return

    # check the error message
    if 'destination is not a directory:' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that fetching to a non-empty directory does not work
def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t12')

    src = make_vcsjob_tree(w)

    # set up destination in a temporary directory that contains some dirt
    dst = w.make_tempdir()
    f = open(os.path.join(dst, 'dirt.txt'), 'w')
    f.write('bar')
    f.close()

    exc = None
    try:
        vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        exc = e

    if not exc:
        print('FAIL %s: fetch did not fail' % pretty)
        return

    # check the error message
    if 'destination is not a git tree:' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that vcsjob refuses to pull same branch if the destination is dirty
def t13():
    pretty = '%s t13' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t13')

    src = make_vcsjob_tree(w)

    # pull the tree into a temporary directory, check that the current branch
    # is "master".
    dst = w.make_tempdir()

    try:
        vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        print('FAIL %s: could not fetch master: %s' % (pretty, str(e)))
        return
    branch = ave.git.branch(dst)
    if branch != 'master':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return

    # create another commit in the source
    f = open(os.path.join(src, 'foo.txt'), 'w+')
    f.write('')
    f.close()
    ave.git.add(src, '.')
    ave.git.commit(src, 'Second commit')

    # introduce some dirt in the destination
    f = open(os.path.join(dst, 'dirt'), 'w')
    f.write('some dirt for `git status` to pick up')
    f.close()

    # fetch again into the same directory, expect failure
    exc = None
    try:
        vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        exc = e

    if not exc:
        print('FAIL %s: fetch did not fail on dirty destination' % pretty)
        return

    # check the error message
    if 'can\'t pull into a dirty tree' not in str(exc):
        print('FAIL%s: wrong error message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that vcsjob can switch between branches in the destination tree
def t14():
    pretty = '%s t14' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t14')

    src = make_vcsjob_tree(w)

    # pull "master"
    dst = w.make_tempdir()

    try:
        result = vcsjob.fetch(src, dst, 'master')
    except Exception, e:
        print('FAIL %s: first fetch failed: %s' % (pretty, str(e)))
        return

    branch = ave.git.branch(dst)
    if branch != 'master':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return

    # pull "testing"
    try:
        result = vcsjob.fetch(src, dst, 'testing')
    except Exception, e:
        print('FAIL %s: second fetch failed: %s' % (pretty, str(e)))
        return
    branch = ave.git.branch(dst)
    if branch != 'testing':
        print(
            'FAIL %s: wrong branch checked out after second fetch: %s'
            % (pretty, branch)
        )
        return

    w.delete()

# check that vcsjob can switch between SHA1 id's in the destination tree
def t15():
    pretty = '%s t15' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t15')

    src = make_vcsjob_tree(w)
    ids = ave.git.rev_list(src)

    # pull "master"
    dst = w.make_tempdir()

    try:
        result = vcsjob.fetch(src, dst, ids[1])
    except Exception, e:
        print('FAIL %s: first fetch failed: %s' % (pretty, str(e)))
        return

    try:
        branch = ave.git.branch(dst)
        print(
            'FAIL %s: a branch is checked out after first fetch: %s'
            % (pretty, branch)
        )
        return
    except Exception, e:
        if 'no branch found' not in str(e):
            print('FAIL %s: wrong error message 1: %s' % (pretty, e))
            return
    sha1 = ave.git.rev_list(dst, 1)[0]
    if sha1 != ids[1]:
        print(
            'FAIL %s: wrong SHA1 checked out after first fetch: %s'
            % (pretty, sha1)
        )
        return

    # pull "testing"
    try:
        result = vcsjob.fetch(src, dst, ids[0])
    except Exception, e:
        print('FAIL %s: second fetch failed: %s' % (pretty, str(e)))
        return

    try:
        branch = ave.git.branch(dst)
        print(
            'FAIL %s: a branch is checked out after second fetch: %s'
            % (pretty, branch)
        )
        return
    except Exception, e:
        if 'no branch found' not in str(e):
            print('FAIL %s: wrong error message 2: %s' % (pretty, e))
            return
    sha1 = ave.git.rev_list(dst, 1)[0]
    if sha1 != ids[0]:
        print(
            'FAIL %s: wrong SHA1 checked out after second fetch: %s'
            % (pretty, sha1)
        )
        return

    w.delete()

# try to fetch a branch that doesn't exist
def t16():
    pretty = '%s t16' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t16')

    # set up source and destination in temporary directories
    src = make_vcsjob_tree(w)
    dst = w.make_tempdir()

    # fetch the source into the destination
    exc = None
    try:
        result = vcsjob.fetch(src, dst, 'no_such_branch')
    except Exception, e:
        exc = e

    if not exc:
        print('FAIL %s: fetch did not fail' % pretty)
        return

    # check the error message
    if 'failed to fetch no_such_branch' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        return

    w.delete()

# check that fetch, commit, fetch cycle works. i.e. first fetch "master", then
# create a new commit on "master", then fetch it again. the new commit should
# be visible in the checked out destination.
def t17():
    pretty = '%s t17' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t17')

    # set up the source
    src = make_vcsjob_tree(w)

    # set up an empty destination
    dst = w.make_tempdir()

    # first fetch
    vcsjob.fetch(src, dst, 'master')

    # check contents
    with open(os.path.join(dst, 'foo.txt'), 'r') as f:
        contents = f.read()
        if contents != 'bar':
            print('FAIL %s: wrong original content: %s' % (pretty, contents))
            return False

    # create new commit in source
    with open(os.path.join(src, 'foo.txt'), 'w') as f:
        f.write('barfly')
    ave.git.add(src, '.')
    ave.git.commit(src, 'Third commit')

    # second fetch
    vcsjob.fetch(src, dst, 'master')

    # check contents again
    with open(os.path.join(dst, 'foo.txt'), 'r') as f:
        contents = f.read()
        if contents != 'barfly':
            print('FAIL %s: wrong delta content: %s' % (pretty, contents))
            return False

    return True

# check that vcsjob.fetch create a shallow clone with a history truncated
# to the specified number of revisions.
def t18():
    pretty = '%s t18' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t18')

    src = 'git://review.sonyericsson.net/semctools/ave/vcsjob.git'
    dst = w.make_tempdir()

     # fetch the source into the destination
    try:
        vcsjob.fetch(src, dst, 'master', depth='2')
        cmd = ['git', '--git-dir=%s/.git' % dst, '--work-tree=' + dst, 'rev-list', 'HEAD', '--count']
        (s, o, e) = ave.cmd.run(cmd, timeout=100, debug=False)
        if int(o) != 2:
            print('FAIL %s: git clone parameter --depth is ignored in clones.' % pretty)
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return False

    w.delete()
    return True

# check that vcsjob.fetch can timeout as expected
def t19():
    pretty = '%s t19' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t19')

    src = 'git://review.sonyericsson.net/platform/prebuilts/misc.git'
    dst = w.make_tempdir()

     # fetch the source into the destination
    try:
        vcsjob.fetch(src, dst, 'oss/tools_r22.2', timeout=1)
        print('FAIL %s: it should be timeout') % pretty
        w.delete()
        return False
    except Exception, e:
        if 'command timed out' == str(e):
            w.delete()
            return True
        else:
            print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
            w.delete()
            return False

# check that vcsjob.fetch does not timeout in 600 seconds
def t20():
    pretty = '%s t20' % __file__
    print(pretty)

    w = Workspace('vcsjob-fetch-t20')

    src = 'git://review.sonyericsson.net/platform/prebuilts/misc.git'
    dst = w.make_tempdir()

     # fetch the source into the destination
    try:
        vcsjob.fetch(src, dst, 'oss/tools_r22.2')
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        w.delete()
        return False
    w.delete()
    return True