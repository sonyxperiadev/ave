# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import StringIO
import tempfile
import shutil

import ave.git
from ave.workspace import Workspace
from ave.exceptions import RunError

from decorators import smoke


class setup_ws(object):
    def __call__(self, fn):
        def decorated_fn():
            w = Workspace()
            res = fn(w)
            w.delete()
            return res

        return decorated_fn


# check that exceptions are raised if download_git is called with incomplete
# parameters
@setup_ws()
def t01(w):
    pretty = '%s t1' % __file__
    print(pretty)

    # src
    try:
        w.download_git(None, 'not_None', 'not_None')
        print(
            'FAIL %s: download_git() without first parameter did not fail'
            % pretty
        )
        return False
    except Exception, e:
        if 'failed to sync: must specify src, dst and refspec' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    # refspec
    try:
        w.download_git('not_None', None, 'not_None')
        print(
            'FAIL %s: download_git() without second parameter did not fail'
            % pretty
        )
        return False
    except Exception, e:
        if 'failed to sync: must specify src, dst and refspec' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that supported protocol info is printed if a non-git is given as source
@setup_ws()
def t02(w):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        w.download_git('/', 'nonsense', 'nonsense')
        print('FAIL %s: download of non-git did not fail' % pretty)
        return False
    except Exception, e:
        start = 'failed to clone from '
        end   = 'repository \'/\' does not exist'
        if start not in str(e) or end not in str(e):
            print('FAIL %s: expected other error message: %s' % (pretty, e))
            return False

    return True

# check that an exception is raised if non-local destination is given
@setup_ws()
def t03(w):
    pretty = '%s t3' % __file__
    print(pretty)

    # create a git tree in a temp directory to use for this test
    src = w.make_git('t3')

    try:
        w.download_git(src, dst='ssh://host', refspec='bleh')
        print(
            'FAIL %s: download_git() with garbage arguments should fail'
            % pretty
        )
        return False
    except Exception, e:
        return True

# check that basic downloading works
@setup_ws()
def t04(w):
    pretty = '%s t4' % __file__
    print(pretty)

    # set up source and destination in temporary directories
    src = w.make_git('t4_src')
    dst = w.make_tempdir()

    # fetch the source into the destination
    try:
        w.download_git(src, dst=dst, refspec='master')
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return

    # look for first commit from source in destination
    expected = ave.git.rev_list(src)[-1]
    if ave.git.rev_list(dst)[-1] != expected:
        print('FAIL %s: wrong first commit in destination' % pretty)
        return

    return True

# check that repeated downloading works
@setup_ws()
def t05(w):
    pretty = '%s t5' % __file__
    print(pretty)

    # set up a source tree
    src = w.make_git('t5')
    f = open(os.path.join(src, 'a_file'), 'w')
    f.write('bla bla bla')
    f.close()
    ave.git.add(src, '*')
    ave.git.commit(src, 'A commit')

    # set up the destination in a temporary dir
    dst = w.make_tempdir()

    # repeatedly fetch the source into the destination
    for i in range(5):
        try:
            w.download_git(src, dst=dst, refspec='master')
        except Exception, e:
            print('FAIL %s: download %d failed: %s' % (pretty, i, str(e)))
            return

    # look for dst/a_file
    if not os.path.isfile(os.path.join(dst, 'a_file')):
        print('FAIL %s: source file not in destination' % pretty)
        return

    return True



def make_multibranch_tree(w, name):
    path = w.make_git(name)

    # commit stuff on master
    f = open(os.path.join(path, 'file_1'), 'w')
    f.write('muppets are nice')
    f.close()
    ave.git.add(path, '*')
    ave.git.commit(path, 'master commit')

    # create branches
    ave.git.create_branch(path, 'A')
    ave.git.create_branch(path, 'B')

    # commit some crap on A
    ave.git.checkout(path, 'A')
    f = open(os.path.join(path, 'file_2'), 'w')
    f.write('bla bla bla')
    f.close()
    ave.git.add(path, '*')
    ave.git.commit(path, 'A commit')

    # commit even more nonsense on B
    ave.git.checkout(path, 'B')
    path = w.make_git(name)
    f = open(os.path.join(path, 'file_3'), 'w')
    f.write('foo barbara')
    f.close()
    ave.git.add(path, '*')
    ave.git.commit(path, 'B commit')

    return path



# check that download_git refuses to switch between branches if the destination
# tree is dirty.
@setup_ws()
def t06(w):
    pretty = '%s t6' % __file__
    print(pretty)

    src = make_multibranch_tree(w, 't6')
    dst = w.make_tempdir()

    # pull the tree into a temporary directory, check that the current branch
    # is "master" and that the tree has the correct content
    try:
        w.download_git(src, 'master', dst)
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return
    branch = ave.git.branch(dst)
    if branch != 'master':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return
    ls = set(os.listdir(dst))
    if ls != set(['.git', 'file_1']):
        print('FAIL %s: wrong file list on "master" branch: %s' % (pretty, ls))
        return

    # download the source tree again, check that "A" is checked out afterwards
    # and that the tree has the right content
    try:
        w.download_git(src, 'A', dst)
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return
    branch = ave.git.branch(dst)
    if branch != 'A':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return
    ls = set(os.listdir(dst))
    if ls != set(['.git', 'file_1', 'file_2']):
        print('FAIL %s: wrong file list on "A" branch: %s' % (pretty, ls))
        return
    
    # download the source tree again, check that "B" is checked out afterwards
    # and that the tree has the right content
    try:
        w.download_git(src, 'B', dst)
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return
    branch = ave.git.branch(dst)
    if branch != 'B':
        print(
            'FAIL %s: wrong branch checked out after first fetch: %s'
            % (pretty, branch)
        )
        return
    ls = set(os.listdir(dst))
    if ls != set(['.git', 'file_1', 'file_3']):
        print('FAIL %s: wrong file list on "B" branch: %s' % (pretty, ls))
        return

    return True

# check that fetching to a non-existant directory works
@setup_ws()
def t07(w):
    pretty = '%s t7' % __file__
    print(pretty)

    src = w.make_git('t7')

    # "create" a non-existant destination directory by removing a temporary dir
    dst = w.make_tempdir()
    shutil.rmtree(dst)

    # fetch the source into the destination
    try:
        result = w.download_git(src, 'master', dst)
    except Exception, e:
        print('FAIL %s: fetch failed: %s' % (pretty, str(e)))
        return

    # look for first commit from source in destination
    expected = ave.git.rev_list(src)[-1]
    if ave.git.rev_list(dst)[-1] != expected:
        print('FAIL %s: wrong first commit in destination' % pretty)
        return

    return True

# check that fetching to a destination which is not a directory doesn't work
@setup_ws()
def t08(w):
    pretty = '%s t8' % __file__
    print(pretty)

    src = w.make_git('t8')

    # create a non-directory destination
    dst = os.path.join(w.make_tempdir(), 'dirt')
    f = open(dst, 'w')
    f.write('bla bla bla')
    f.close()

    # fetch the source into the destination
    try:
        result = w.download_git(src, 'master', dst)
        print('FAIL %s: fetch did not fail' % pretty)
        return
    except Exception, e:
        # check the error message
        if 'destination is not a directory:' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that fetching to a non-empty directory does not work
@setup_ws()
def t09(w):
    pretty = '%s t9' % __file__
    print(pretty)

    src = w.make_git('t9')

    # create a non-empty destination
    dst = w.make_tempdir()
    f = open(os.path.join(dst, 'dirt'), 'w')
    f.write('bla bla bla')
    f.close()

    try:
        w.download_git(src, 'master', dst)
        print('FAIL %s: fetch did not fail' % pretty)
        return
    except Exception, e:
        # check the error message
        if 'destination is not a git tree:' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that Workspace.download_git() refuses to pull same branch if the
# destination is dirty
@smoke
@setup_ws() # TODO: check that this runs on smoke, (order of smoke and setup)
def t10(w):
    pretty = '%s t10' % __file__
    print(pretty)

    src = make_multibranch_tree(w, 't10')

    # pull the tree into a temporary directory, check that the current branch
    # is "master".
    dst = w.make_tempdir()

    try:
        w.download_git(src, 'master', dst)
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
    f = open(os.path.join(src, 'foo.txt'), 'w')
    f.write('bar')
    f.close()
    ave.git.add(src, '*')
    ave.git.commit(src, 'Second commit')

    # introduce some dirt in the destination
    f = open(os.path.join(dst, 'dirt'), 'w')
    f.write('some dirt for `git status` to pick up')
    f.close()

    # fetch again into the same directory, expect failure
    try:
        ave.git.checkout(dst, 'B', True)
        w.download_git(src, 'B', dst)
        w.download_git(src, 'master', dst)
        print('FAIL %s: fetch did not fail on dirty destination' % pretty)
        return
    except Exception, e:
        # check the error message
        if 'can\'t pull into a dirty tree' not in str(e):
            print('FAIL%s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that Workspace.download_git() can switch between SHA1 id's in the
# destination tree
@smoke
@setup_ws()
def t11(w):
    pretty = '%s t11' % __file__
    print(pretty)

    src    = make_multibranch_tree(w, 't11')
    master = ave.git.rev_list(src, 1, 'master')[0]
    A      = ave.git.rev_list(src, 1, 'A')[0]

    dst = w.make_tempdir()

    # pull "master", but as SHA1 id
    try:
        result = w.download_git(src, master, dst)
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
    except Exception as e:
        if 'failed to get branch at' not in str(e):
            print('FAIL%s: wrong error message: %s' % (pretty, str(e)))
            return

    sha1 = ave.git.rev_list(dst, 1, 'HEAD')[0]
    if sha1 != master:
        print(
            'FAIL %s: wrong SHA1 checked out after first fetch: %s'
            % (pretty, sha1)
        )
        return
    ls = set(os.listdir(dst))
    if ls != set(['.git', 'file_1']):
        print('FAIL %s: wrong file list on "master" branch: %s' % (pretty, ls))
        return

    # pull "A", but as SHA1 id
    try:
        result = w.download_git(src, A, dst)
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
    except Exception as e:
        if 'failed to get branch at' not in str(e):
            print('FAIL%s: wrong error message: %s' % (pretty, str(e)))
            return

    sha1 = ave.git.rev_list(dst, 1, 'HEAD')[0]
    if sha1 != A:
        print(
            'FAIL %s: wrong SHA1 checked out after second fetch: %s'
            % (pretty, sha1)
        )
        return
    ls = set(os.listdir(dst))
    if ls != set(['.git', 'file_1', 'file_2']):
        print('FAIL %s: wrong file list on "A" branch: %s' % (pretty, ls))
        return

    return True

# try to fetch a branch that doesn't exist
@setup_ws()
def t12(w):
    pretty = '%s t12' % __file__
    print(pretty)

    src = w.make_git('t12')
    dst = w.make_tempdir()

    # fetch the source into the destination
    try:
        result = w.download_git(src, 'no_such_branch', dst)
        print('FAIL %s: fetch did not fail' % pretty)
        return
    except Exception, e:
        # check the error message
        if 'failed to fetch no_such_branch' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that can't download git outside workspace.path
@setup_ws()
def t13(w):
    pretty = '%s t13' % __file__
    print(pretty)

    src = w.make_git('t13')
    dst = '/tmp/ave/test_download_git-t13'

    try:
        w.download_git(src, 'master', dst)
        print('FAIL %s: downloading to outside path did not fail' % pretty)
        return
    except Exception, e:
        # check the error message
        if not str(e).startswith('can not store git tree outside workspace'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that the workspace path is a combination of root and uid, that temp
# dirs are created under it, that git can be created in it but not outside
# workspace
@smoke
@setup_ws()
def t14(w):
    pretty = '%s t14' % __file__
    print(pretty)

    if w.path != os.path.join(w.root, w.uid):
        print('FAIL %s: the path is wrong: %s' % (pretty, w.path))
        return

    t = w.make_tempdir()
    if not t.startswith(os.path.join(w.root, w.uid)):
        print('FAIL %s: temporary dir created on wrong path: %s' % (pretty, t))
        return

    # create git in tempdir
    try:
        g = w.make_git(t)
    except Exception, e:
        print('FAIL %s: could not create git in tempdir: %s' % (pretty, str(e)))
        return
    # check that parent of git is path
    if not g == t:
        print('FAIL %s: created git in wrong path: %s' % (pretty, g))
        return

    # create git in OS tempdir should fail
    try:
        dst = tempfile.mkdtemp(prefix='test_download_git-t14')
        dst = w.make_git(dst)
        print('FAIL %s: make git in OS tempdir dit not fail' % pretty)
        return
    except Exception, e:
        # check error message
        if not str(e).startswith('can not create git outside workspace'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return
    finally:
        shutil.rmtree(dst)
    return True

# check that downloading from the internal review site works
@smoke
@setup_ws()
def t15(w):
    pretty = '%s t15' % __file__
    print(pretty)

    t = w.make_tempdir()

    try:
        w.download_git(
            'git://review.sonyericsson.net/platform/external/bison', 'master', t
        )
    except Exception, e:
        print('FAIL %s: downloading failed: %s' % (pretty, str(e)))
        return

    if not os.path.exists(os.path.join(t, 'AUTHORS')):
        print('FAIL %s: did not find download directory' % pretty)
        return

    return True

# check that timeouts work
@smoke
@setup_ws()
def t16(w):
    pretty = '%s t16' % __file__
    print(pretty)

    t = w.make_tempdir()

    try:
        w.download_git(
            'git://review.sonyericsson.net/kernel/msm', 'maint', t, timeout=3
        )
        print('FAIL %s: download did not time out' % pretty)
        return
    except Exception, e:
        if not str(e).endswith(' timed out'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return

    return True

# check that default download paths for git trees is under path/git/, in a tree
# named after the source.
@setup_ws()
def t17(w):
    pretty = '%s t17' % __file__
    print(pretty)

    try:
        path = w.download_git(
            'git://review.sonyericsson.net/platform/external/bison', 'master'
        )
    except Exception, e:
        print('FAIL %s: downloading failed: %s' % (pretty, str(e)))
        return

    if not path == os.path.join(w.path, 'git', 'bison'):
        print('FAIL %s: wrong download path: %s' % (pretty, path))
        return

    if not os.path.exists(os.path.join(path, 'AUTHORS')):
        print('FAIL %s: did not find download directory' % pretty)
        return

    return True

# Check exception is raised when no remote.origin.url found in git
@setup_ws()
def t18(w):
    pretty = '%s t18' % __file__
    print(pretty)

    ave.git.init(w.get_path())
    try:
        url = ave.git.get_git_url(w.get_path())
        print('FAIL %s: expected exception: no remote.origin.url in git: %s'
            % (pretty, w.get_path())
        )
        return
    except Exception, e:
        expect = 'failed to get git remote.origin.url in %s' % w.get_path()
        if expect not in str(e):
            print('FAIL %s: wrong exception message: %s' % (pretty, str(e)))
            return

    return True

# Check that get_git_url works properly on a valid git
@setup_ws()
def t19(w):
    pretty = '%s t19' % __file__
    print(pretty)

    real_git_url = 'git://review.sonyericsson.net/semctools/ave/workspace'
    # Download the git to be sure we have a valid path to check on.
    try:
        path = w.download_git(real_git_url, 'master')
    except Exception, e:
        print('FAIL %s: downloading failed: %s' % (pretty, str(e)))
        return
    # Fetch the url
    fetched_url = ave.git.get_git_url(path)
    # Expect the fetched url to be equal to original url
    if fetched_url != real_git_url:
        print(
            'FAIL %s: unexpected value of git url:\n."%s".exp:\n."%s".'
            % (pretty, fetched_url, real_git_url)
        )
        return

    return True

# check that sync, commit, sync cycle works. i.e. first sync "master", then
# create a new commit on "master", then sync it again. the new commit should
# be visible in the destination.
@smoke
@setup_ws()
def t20(w):
    pretty = '%s t20' % __file__
    print(pretty)

    # set up the source
    src = w.make_tempdir()
    with open(os.path.join(src, 'foo.txt'), 'w') as f:
        f.write('bar')
    ave.git.init(src)
    ave.git.add(src, '.')
    ave.git.commit(src, 'first commit')

    # set up an empty destination
    dst = w.make_tempdir()

    # first fetch
    ave.git.sync(src, dst, 'master')

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
    ave.git.commit(src, 'second commit')

    # second fetch
    ave.git.sync(src, dst, 'master')

    # check contents again
    with open(os.path.join(dst, 'foo.txt'), 'r') as f:
        contents = f.read()
        if contents != 'barfly':
            print('FAIL %s: wrong delta content: %s' % (pretty, contents))
            return False

    return True

# check that ave.git.init() raises a correct RunError when initializing with
# path = <a file>
@setup_ws()
def t21(w):
    pretty = '%s t21' % __file__
    print(pretty)

    temp_file = w.make_tempfile()

    try:
        ave.git.init(temp_file)
        print('FAIL %s: git init on file as path did not fail' % (pretty))
        return False
    except RunError as e:
        if e.cmd != 'ave.git.init(%s)' % (temp_file):
            print('FAIL %s: wrong cmd in RunError: %s' % (pretty, e.cmd))
            return False
        start = 'failed to initialize git tree at %s' % temp_file
        if(not e.message.startswith(start)
        or not e.message.endswith('File exists')):
            print('FAIL %s: wrong message in RunError: %s' % (pretty, e.message))
            return False

    return True

# check get_error_str works as expected on wrong usage
# by sending "-z" to git init
@setup_ws()
def t22(w):
    pretty = '%s t22' % __file__
    print(pretty)

    try:
        ave.git.init('-z ' + w.get_path())
        print('FAIL %s: git init with "-z" did not fail' % (pretty))
        return False
    except RunError as e:
        msg = "error: unknown switch `z'"
        if msg not in str(e):
            print(
                'FAIL %s: wrong message in RunError: %s' % (pretty, str(e))
            )
            return False

    return True

# check that ave.git.add() raises a correct RunError when an expression doesn't
# match any files
@setup_ws()
def t23(w):
    pretty = '%s t23' % __file__
    print(pretty)

    t = w.make_tempdir()

    try:
        ave.git.init(t)
    except RunError as e:
        print('FAIL %s: unexpected error: %s' % (pretty, str(e)))
        return False

    exp = '*.py'
    # no such files in git
    try:
        ave.git.add(t, exp)
        print('FAIL %s: git add on non-existing files did not fail' % pretty)
        return False
    except RunError as e:
        if e.cmd != 'ave.git.add(%s,%s)' % (t, exp):
            print('FAIL %s: wrong cmd in RunError: %s' % (pretty, e.cmd))
            return False
        start = 'failed to add %s in %s: ' % (exp, t)
        end   = 'pathspec \'*.py\' did not match any files'
        if e.message != start + end:
            print('FAIL %s: wrong error message on add: %s' % (pretty, str(e)))
            return False

    return True

# check errors on methods* when using a directory that is not a git tree:
@setup_ws()
def t24(w):
    pretty = '%s t24' % __file__
    print(pretty)

    t       = w.make_tempdir()
    exp     = '*.txt'
    m       = 'Should not be possible'
    git_err = 'Not a git repository: \'%s/.git\'' % t
    refs    = 'dummyref'
    b       = 'dummybranch'

    def check_error(e, cmd, msg, name):
        if e.cmd != cmd:
            print('FAIL %s: wrong cmd %s in RunError: %s' % (pretty,cmd,e.cmd))
            return False
        if e.message != msg:
            print('FAIL %s: wrong error message on %s: %s'%(pretty,name,str(e)))
            return False
        return True

    def test(fn, args, name, exp_cmd, exp_msg):
        try:
            fn(*args)
            print('FAIL %s: %s on non-git path did not fail' % (name, pretty))
            return False
        except RunError as e:
            if not check_error(e, exp_cmd, exp_msg, name):
                return False
        return True

    # add
    fn      = ave.git.add
    args    = (t, exp)
    exp_cmd = 'ave.git.add(%s,%s)' % (t, exp)
    exp_msg = 'failed to add %s in %s: %s' % (exp, t, git_err)
    if not test(fn, args, 'add', exp_cmd, exp_msg):
        return False
    # commit
    fn      = ave.git.commit
    args    = (t, m)
    exp_cmd = 'ave.git.commit(%s,%s,False)' % (t, m)
    exp_msg = 'failed to commit in %s: %s' % (t, git_err)
    if not test(fn, args, 'commit', exp_cmd, exp_msg):
        return False
    # is_dirty
    fn      = ave.git.is_dirty
    args    = (t,)
    exp_cmd = 'ave.git.is_dirty(%s)' % t
    exp_msg = 'failed to check if %s is dirty: %s' % (t, git_err)
    if not test(fn, args, 'is_dirty', exp_cmd, exp_msg):
        return False
    # merge
    fn      = ave.git.merge
    args    = (t, refs)
    exp_cmd = 'ave.git.merge(%s,%s)' % (t, refs)
    exp_msg = 'failed to merge %s: %s' % (refs, git_err)
    if not test(fn, args, 'merge', exp_cmd, exp_msg):
        return False
    # list_branches
    fn      = ave.git.list_branches
    args    = (t,)
    exp_cmd = 'ave.git.list_branches(%s)' % t
    exp_msg = 'failed to list branches in %s: %s' % (t, git_err)
    if not test(fn, args, 'list branches', exp_cmd, exp_msg):
        return False
    # checkout
    fn      = ave.git.checkout
    args    = (t, refs, True)
    exp_cmd = 'ave.git.checkout(%s,%s,True)' % (t, refs)
    exp_msg = 'failed to checkout %s: %s' % (refs, git_err)
    if not test(fn, args, 'checkout', exp_cmd, exp_msg):
        return False
    # branch
    fn      = ave.git.branch
    args    = (t,)
    exp_cmd = 'ave.git.branch(%s)' % t
    exp_msg = 'failed to get branch at %s: %s' % (t, git_err)
    if not test(fn, args, 'branch', exp_cmd, exp_msg):
        return False
    # create_branch
    fn      = ave.git.create_branch
    args    = (t,b,refs)
    exp_cmd = 'ave.git.create_branch(%s,%s,%s)' % (t,b,refs)
    exp_msg = 'failed to create branch %s (%s) at %s: %s' % (b,refs,t,git_err)
    if not test(fn, args, 'create branch', exp_cmd, exp_msg):
        return False
    # rev_list
    fn      = ave.git.rev_list
    args    = (t,)
    exp_cmd = 'ave.git.rev_list(%s,0,HEAD)' % t
    exp_msg = 'failed to list revisions at %s (HEAD): %s' % (t,git_err)
    if not test(fn, args, 'list revisions', exp_cmd, exp_msg):
        return False
    # get_git_url
    fn      = ave.git.get_git_url
    args    = (t,)
    exp_cmd = 'ave.git.get_git_url(%s,0)' % t
    exp_msg = 'failed to get git remote.origin.url: '\
              'Not a git repository: \'%s\'' % t
    if not test(fn, args, 'get_git_url', exp_cmd, exp_msg):
        return False

    return True



# check that ave.git.clone create a shallow clone with a history truncated
# to the specified number of revisions.
# A shallow repository has a number of limitations
@smoke
@setup_ws()
def t25(w):
    pretty = '%s t25' % __file__
    print(pretty)
    src = make_multibranch_tree(w, 't25')
    dst = w.make_tempdir()
    try:
        w.download_git('git://review.sonyericsson.net/semctools/ave/workspace.git', 'master', dst, depth=1)
        cmd = ['git', '--git-dir=%s/.git' % dst, '--work-tree=' + dst, 'rev-list', 'HEAD', '--count']
        (s, o, e) = ave.cmd.run(cmd, timeout=100, debug=False)
        if int(o) != 1:
            print('FAIL %s: git clone parameter --depth is ignored in clones.' % pretty)
    except Exception, e:
        print('FAIL %s: could not create a shallow clone: %s' % (pretty, e))
        return
