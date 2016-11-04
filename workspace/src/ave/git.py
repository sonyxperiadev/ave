# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import re
import os

from datetime import datetime, timedelta

from ave.exceptions import RunError

import ave.cmd
import ave.config

def fix_env(fn):
    # make sure git finds its global .gitconfig
    os.environ['HOME'] = ave.config.load_etc()['home']
    # make sure ssh always reads its private key from $HOME/.ssh
    if 'SSH_AUTH_SOCK' in os.environ:
        del(os.environ['SSH_AUTH_SOCK'])
    return fn

def get_error_str(output):
    # parse output to an error message
    fatal_lines = ''
    lines = output.splitlines()
    for l in lines:
        if 'usage: git' in l:
            return ': Wrong usage. ' + l
        elif 'fatal: ' in l:
            fatal_lines += ': %s' % l.replace('fatal: ', '')
    if fatal_lines:
        return fatal_lines
    if lines:
        return lines[-1]
    return ': Unknown error'

@fix_env
def init(path, debug=False):
    '''
    Initialize a new git tree in the directory on 'path'. The directory
    must be empty.
    '''
    cmd = ['git','init',path]
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.init(%s)' % (path),
            out     = o,
            message = 'failed to initialize git tree at %s%s' % (path, error)
        )

@fix_env
def add(path, expr, debug=False):
    '''
    Add files covered by the expression 'expr' to the index in the git tree
    found on 'path'. E.g. 'add("relative/path/to/git/tree", "*.txt")'.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'add', expr]
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.add(%s,%s)' % (path, expr),
            out     = o,
            message = 'failed to add %s in %s%s' % (expr, path, error)
        )

@fix_env
def commit(path, comment, allow_empty=False, debug=False):
    '''
    Commit new changes added to the git tree found on 'path'. 'comment'
    must be a string. Set 'allow_empty=True' if the tree's index is empty
    and you want an empty commit generated.
    '''
    if allow_empty:
        extra = '--allow-empty'
    else:
        extra = ''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'commit',
           extra, '-m', '"%s"'%comment]
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.commit(%s,%s,%s)' % (path, comment, allow_empty),
            out     = o,
            message = 'failed to commit in %s%s' % (path, error)
        )

@fix_env
def is_git(path, debug=False):
    '''
    Return True if the directory found on 'path' is a git tree. Otherwise
    return False.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'ls-files']
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    return s == 0

@fix_env
def is_dirty(path, debug=False):
    '''
    Return True if the git tree found on 'path' has contents that is either
    staged or unstaged. Return False otherwise.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'status']
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.is_dirty(%s)' % (path),
            out     = o,
            message = 'failed to check if %s is dirty%s' % (path, error)
        )
    for line in o.splitlines():
        m = re.search('^nothing to commit', line)
        if m:
            return False
    return True

@fix_env
def clone(src, dst, timeout, debug=False, depth=1):
    '''
    Clone a git tree from the source 'src' to the destination 'dst'. The
    source may be a local file system path or any URL accepted by the
    'git clone' command line tool. Raise an exception if the call takes
    longer than 'timeout' seconds.
    '''

    cmd = ['git', 'clone', '--no-checkout', src, dst]
    if isinstance(depth, int) or isinstance(int(depth), int):
        cmd.extend(['--depth', str(depth)])
    (s, o, e) = ave.cmd.run(cmd, timeout=timeout, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.clone(%s,%s,%s)' % (src, dst, timeout),
            out     = o,
            message = 'failed to clone from %s to %s%s' % (src, dst, error)
        )

@fix_env
def fetch(src, dst, refspec, timeout, debug=False):
    '''
    Fetch deltas from the source 'src' to the destination 'dst' using the
    reference specification 'refspec'. Raise an exception if the call takes
    longer than 'timeout' seconds.
    '''
    cmd = ['git', '--git-dir=%s/.git'%dst, 'fetch', '-t', src, refspec]
    (s, o, e) = ave.cmd.run(cmd, timeout=timeout, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.fetch(%s,%s,%s,%s)' % (src,dst,refspec,timeout),
            out     = o,
            message = 'failed to fetch %s%s' % (refspec, error)
        )

@fix_env
def merge(path, refspec, debug=False):
    '''
    Merge the the commit specified by 'refspec' onto the currently checked
    out commit in the git tree found on 'path'.
    '''
    cmd = ['git','--git-dir=%s/.git'%path,'--work-tree='+path,'merge',refspec]
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.merge(%s,%s)' % (path,refspec),
            out     = o,
            message = 'failed to merge %s%s' % (refspec, error)
        )

# return two lists: local and remote branches
@fix_env
def list_branches(path, debug=False):
    '''
    Given a git tree found on 'path', return a tuple containing two list:
    one with the names of all local branches, and one with the names remote
    branches.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'branch', '-a']
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.list_branches(%s)' % (path),
            out     = o,
            message = 'failed to list branches in %s%s' % (path, error)
        )
    local  = []
    remote = []
    for line in o.splitlines():
        m = re.match('. (?P<branch>[^/]+)$', line)
        if m: # local branch
            local.append(m.group('branch'))
            continue
        m = re.match('  remotes/origin/(?P<branch>[^\s]+)$', line)
        if m:
            remote.append(m.group('branch'))
    return (local, remote)

def pull(src, dst, refspec, timeout, debug=False):
    '''
    Pull deltas from the source 'src' to the destination 'dst' using the
    reference specification 'refspec'. Merge the deltas onto the currently
    checked out commit in 'dst'. Raise an exception if the call takes
    longer than 'timeout' seconds.
    '''
    fetch(src, dst, refspec, timeout, debug)
    merge(dst, 'FETCH_HEAD', debug)

def _refspec_shorthand(refspec):
    if refspec.startswith('refs/heads/'):
        return refspec[len('refs/heads/'):]
    if refspec.startswith('refs/tags/'):
        return refspec[len('refs/tags/'):]
    return refspec

@fix_env
def checkout(path, refspec, force=False, debug=False):
    '''
    Use the reference specification 'refspec' to check out a commit in the
    git tree found on 'path'. Note that the function cannot be used to
    check out files, only versions.
    '''
    if (not force) and is_dirty(path, debug):
        if debug:
            sys.stderr.write('Destination %s is dirty. cannot checkout\n'%path)
            sys.stderr.flush()
        raise RunError(
            cmd     = 'ave.git.checkout(%s,%s,%s)' % (path, refspec, force),
            out     = '',
            message = 'failed to check out %s: %s is dirty' % (refspec, path)
        )
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'checkout',
           _refspec_shorthand(refspec)]
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.checkout(%s,%s,%s)' % (path, refspec, force),
            out     = o,
            message = 'failed to checkout %s%s' % (refspec, error)
        )

@fix_env
def branch(path, debug=False):
    '''
    Return the name of the currently active branch in the git tree found on
    'path'.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'branch']
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        raise RunError(
            cmd     = 'ave.git.branch(%s)' % (path),
            out     = o,
            message = 'failed to get branch at %s%s' % (path, error)
        )
    for line in o.splitlines():
        m = re.search('^\* (?P<branch>.*)', line)
        if m:
            branch = m.group('branch')
            if branch == '(no branch)' or branch.startswith('(HEAD detached at'):
                raise RunError(
                    cmd     = 'ave.git.branch(%s)' % (path),
                    out     = o,
                    message = 'failed to get branch at %s: no branch found' % (path)
                )
            return branch


def _same_branch(path, refspec, debug=False):
    active = branch(path, debug)
    if not active:
        return False # path is not tracking a branch
    return active == refspec

@fix_env
def create_branch(path, branch, refspec=None, debug=False):
    '''
    Create a new branch in the git tree found on 'path'. Optionally use
    'refspec' to specify which commit to use as branch point. Otherwise the
    currently checked out commit will be used as branch point.
    '''
    cmd = ['git', '--git-dir=%s/.git'%path, 'branch', branch]
    if refspec:
        cmd.append(refspec)
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        refs  = ' (%s)' % refspec if refspec else ''
        msg   = 'failed to create branch %s%s at %s%s'%(branch,refs,path,error)
        raise RunError(
            cmd     = 'ave.git.create_branch(%s,%s,%s)' % (path,branch,refspec),
            out     = o,
            message = msg
        )

@fix_env
def rev_list(path, limit=0, refspec=None, debug=False):
    '''
    List revisions by SHA1 id's in the git tree found on 'path'. Optionally
    limit the list to 'limit' revisions. Optionally use 'refspec' to set
    the starting point for the listing (defaults to "HEAD").
    '''
    if not refspec:
        refspec = 'HEAD'
    cmd = ['git', '--git-dir=%s/.git'%path, 'rev-list']
    if limit:
        cmd.extend(['--max-count=%d'%limit, refspec])
    else:
        cmd.append('--all')
    (s, o, e) = ave.cmd.run(cmd, debug=debug)
    if s != 0:
        error = get_error_str(o)
        msg   = 'failed to list revisions at %s (%s)%s' % (path,refspec,error)
        raise RunError(
            cmd     = 'ave.git.rev_list(%s,%s,%s)' % (path,limit,refspec),
            out     = o,
            message = msg
        )
    return [line for line in o.splitlines()]

def _recalc_timeout(time_limit):
    if not time_limit:
        return 0
    if datetime.now() > time_limit:
        raise Exception('sync timed out')
    # never return 0 as it implies that there is no timeout
    return (time_limit - datetime.now()).seconds or 1

def sync(src, dst, refspec, timeout=0, debug=False, depth=1):
    '''
    Synchronize a destination tree 'dst' with a source tree 'src', then
    check out the commit designated by 'refspec'. 'refspec' must be a
    branch name or an SHA1 commit id. Raise an exception if the call takes
    longer than 'timeout' seconds. Raise an exception if the destination
    tree is dirty. It is safe to use this function to repeatedly
    synchronize a source into the same destination, using different
    reference specifications each time.
    '''
    command_str = 'ave.git.sync(%s,%s,%s,%s)' % (src, dst, refspec, timeout)
    if not (src and dst and refspec):
        raise RunError(
            cmd     = command_str,
            out     = '',
            message = 'failed to sync: must specify src, dst and refspec'
        )

    if timeout:
        time_limit = datetime.now() + timedelta(seconds=timeout)
    else:
        time_limit = None

    # git assumes that unqualified refspecs are branches (then the qualifier
    # should be "refs/heads/"). fix up the refspec after the same assumption
    # if it isn't qualified
    #if not refspec.startswith('refs/'):
    #    refspec = 'refs/heads/%s' % refspec

    if not os.path.exists(dst):
        os.makedirs(dst)
    if not os.path.isdir(dst):
        raise RunError(
            cmd     = command_str,
            out     = '',
            message = 'destination is not a directory: %s' % dst
        )

    # clone if destination is empty
    if not os.listdir(dst):
        timeout = _recalc_timeout(time_limit)
        clone(src, dst, timeout, debug, depth)
        # fetch the wanted refspec if it doesn't show up in the rev-list. this
        # is the normal case for deltas that have been pushed to Gerrit and not
        # yet merged into a branch.
        try:
            rev_list(dst, 1, refspec, debug)
        except RunError:
            timeout = _recalc_timeout(time_limit)
            fetch(src, dst, '%s:%s' % (refspec, refspec), timeout,debug)

        # check out the wanted refspec
        checkout(dst, refspec, True, debug)
        return True

    # didn't clone. will pull or fetch instead

    # destination must be a git tree if we are going to fetch into it
    if not is_git(dst, debug):
        raise RunError(
            cmd     = command_str,
            out     = '',
            message = 'destination is not a git tree: %s' % dst
        )

    # fetch the wanted refspec if it doesn't show up in the rev-list
    try:
        rev_list(dst, 1, refspec, debug)
    except RunError:
        timeout = _recalc_timeout(time_limit)
        fetch(src, dst, '%s:%s' % (refspec, refspec), timeout, debug)

    # if the refspec is a branch and the destination has the same branch
    # checked out (not necessarily the same delta), then pull the refspec

    (local, remote) = list_branches(dst, debug)
    if refspec in remote:
        if _same_branch(dst, refspec, debug):
            # make sure the destination isn't dirty because then we can't pull
            if is_dirty(dst, debug):
                raise RunError(
                    cmd     = command_str,
                    out     = '',
                    message = 'can\'t pull into a dirty tree'
                )
            timeout = _recalc_timeout(time_limit)
            pull(src, dst, refspec, timeout, debug)
            return True

    # didn't pull. checkout instead
    checkout(dst, refspec, True, debug)

    return True

@fix_env
def get_git_url(path, timeout=0, debug=False):
    '''
    Get the remote origin url of the git. Raise an exception if the call takes
    longer than 'timeout' seconds.
    '''
    # path must be a git tree
    if not is_git(path, debug):
        raise RunError(
            cmd     = 'ave.git.get_git_url(%s,%s)' % (path,timeout),
            out     = '',
            message = 'failed to get git remote.origin.url: Not a git reposi' \
                      'tory: \'%s\'' % path
        )
    cmd = [
        'git', '--git-dir=%s/.git'%path, '--work-tree='+path, 'config',
        '--get', 'remote.origin.url'
    ]
    (s, o, e) = ave.cmd.run(cmd, timeout=timeout, debug=debug)
    if s == 0:
        o = o.strip('\r\n')
        return o
    raise RunError(
        cmd     = 'ave.git.get_git_url(%s,%s)' % (path,timeout),
        out     = o,
        message = 'failed to get git remote.origin.url in %s' % path
    )
