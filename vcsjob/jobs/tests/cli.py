# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys

import ave.cmd

from ave.workspace import Workspace

# show help and return non-zero when invoked without arguments
def t1(executable, sources):
    pretty = '%s t1' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''
    (s, o, e) = ave.cmd.run('%s %s execute' % (executable, sources))
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if o.splitlines()[0] != 'ERROR: at least -j or --jobs must be specified':
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# show help and return non-zero when invoked with garbage arguments
def t2(executable, sources):
    pretty = '%s t2' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    (s, o, e) = ave.cmd.run('%s %s execute --fg hubba' % (executable, sources))
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if o.splitlines()[0] != 'ERROR: option --fg not recognized':
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# check for graceful failure when there is valid jobs directory
def t3(executable, sources):
    pretty = '%s t3' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    (s, o, e) = ave.cmd.run(
        '%s %s execute --jobs=gobbly/gook' % (executable, sources)
    )
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.splitlines()[0].startswith('ERROR: not a jobs directory: '):
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# check that an error is given if no jobs were executed
def t4(executable, sources):
    pretty = '%s t4' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t4')

    # fetch something valid
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    cmd = '%s %s fetch -s %s -d %s -r master' % (
        executable, sources, valid, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: could not fetch:\n%s\n%s' % (pretty, o, e))
        return

    # put in a tags filter that doesn't include any tests
    cmd = '%s %s execute --jobs=%s --tags=NONSENSE' % (
        executable, sources, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if o.splitlines()[0] != 'WARNING: no jobs were executed':
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

    w.delete()

# check that an error is given if the .vcsjob file is completely broken
def t5(executable, sources):
    pretty = '%s t5' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t5')

    # fetch something valid
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    cmd = '%s %s fetch -s %s -d %s -r master' % (
        executable, sources, valid, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: could not fetch:\n%s\n%s' % (pretty, o, e))
        return

    # break the .vcsjob file
    f = open(os.path.join(target, '.vcsjob'), 'a')
    f.write('not valid syntax in a .vcsjob file')
    f.close()

    # put in a tags filter that doesn't include any tests
    cmd = '%s %s execute --jobs=%s --tags=NONSENSE' %(executable,sources,target)
    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.split('\n')[0].startswith('ERROR: could not load'):
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

    w.delete()

# check that an error is given if the .vcsjob file contains a job without the
# "path" property
def t6(executable, sources):
    pretty = '%s t6' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t6')

    # create a broken .vcsjob file
    target = w.make_tempdir()
    f = open(os.path.join(target, '.vcsjob'), 'w')
    f.write(
        '{ "executables": [ '
            '{ "PATH": "jobs/demo_job.py", "tags": ["DEMO"] } '
        '] }'
    )
    f.close()

    # put in a tags filter that doesn't include any tests
    cmd = '%s %s execute --jobs=%s --tags=NONSENSE' % (
        executable, sources, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.splitlines()[0].startswith('ERROR: job does not have the "path"'):
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

    w.delete()

# check that an error is given if the .vcsjob file refers to a job that does
# not exist
def t7(executable, sources):
    pretty = '%s t7' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t7')

    # create a broken .vcsjob file
    target = w.make_tempdir()
    f = open(os.path.join(target, '.vcsjob'), 'w')
    f.write('{ "executables": [ { "path": "does_not_exist" } ] }')
    f.close()

    # put in a tags filter that doesn't include any tests
    cmd = '%s %s execute --jobs=%s --tags=NONSENSE' % (
        executable, sources, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.splitlines()[0].startswith('ERROR: no such file: '):
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

    w.delete()

# check that an error is given if the .vcsjob refers to a file that is not
# executable
def t8(executable, sources):
    pretty = '%s t8' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t8')

    # fetch something valid
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    cmd = '%s %s fetch -s %s -d %s -r master' % (
        executable, sources, valid, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: could not fetch:\n%s\n%s' % (pretty, o, e))
        return

    # remove the executable flag on a job
    os.chmod(os.path.join(target, 'jobs', 'demo_job.sh'), 0644)

    cmd = '%s %s execute --jobs=%s --tags=EXECUTE' % (executable, sources, target)
    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.splitlines()[0].startswith('ERROR: file is not executable: '):
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

    w.delete()

# check that environment variables are only passed on to jobs if they are
# mentioned in the --env list.
def t9(executable, sources):
    pretty = '%s t9' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t9')

    # fetch something valid
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    cmd = '%s %s fetch -s %s -d %s -r master' % (
        executable, sources, valid, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: could not fetch:\n%s\n%s' % (pretty, o, e))
        return

    # set some environment variables
    os.environ['FOO'] = 'BAR'
    os.environ['COW'] = 'MOO'

    # filter in the FOO environment variable, but not COW
    cmd = '%s %s execute --jobs=%s -t DEMO -e FOO' % (executable,sources,target)
    (s, o, e) = ave.cmd.run(cmd)

    found_foo = False
    found_cow = False
    for line in o.splitlines():
        if   line == 'FOO=BAR':
            found_foo = True
        elif line == 'COW=MOO':
            found_cow = True
    if not found_foo:
       print('FAIL %s: FOO was not set: %s' % (pretty, o))
       return
    if found_cow:
        print('FAIL %s: COW was set: %s' % (pretty, o))
        return

    w.delete()

# show help and return non-zero when invoked without arguments
def t10(executable, sources):
    pretty = '%s t10' % __file__
    print(pretty)

    if sources:
        cmd = [executable, '-s', ','.join(sources)]
    else:
        cmd = [executable]

    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if o.splitlines()[1] != 'Syntax:':
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# show help and return non-zero when invoked with garbage arguments
def t11(executable, sources):
    pretty = '%s t11' % __file__
    print(pretty)

    if sources:
        cmd = [executable, '-s', ','.join(sources), '--fg', 'hubba']
    else:
        cmd = [executable, '--fg', 'hubba']

    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if o.splitlines()[1] != 'Syntax:':
        print('FAIL %s: help not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# show help and return non-zero when invoked without arguments
def t12(executable, sources):
    pretty = '%s t12' % __file__
    print(pretty)

    if sources:
        cmd = [executable, '-s', ','.join(sources), 'fetch']
    else:
        cmd = [executable, 'fetch']

    (s, o, e) = ave.cmd.run(cmd)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.startswith('ERROR: source, refspec and destination must be '):
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# show help and return non-zero when invoked with garbage arguments
def t13(executable, sources):
    pretty = '%s t13' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    (s, o, e) = ave.cmd.run(executable + '%s fetch --fg hubba' % sources)
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.startswith('ERROR: option --fg not recognized'):
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# check if url parsing fails gracefully. expect error code and printed help
def t14(executable, sources):
    pretty = '%s t14' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    (s, o, e) = ave.cmd.run(
        executable + '%s fetch -s gobbly/gook -d x -r y' % sources
    )
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if not o.startswith('ERROR: supported protocols: git'):
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return

# check that an error is given if user tries to fetch non-existent source
def t15(executable, sources):
    pretty = '%s t15' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t15')

    dst = w.make_tempdir()
    (s, o, e) = ave.cmd.run(
        '%s %s fetch --source=git://no.such.host/tree -d %s -r y'
        % (executable, sources, dst)
    )
    if s == 0:
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return
    if 'failed to clone from git://no.such.host/tree' not in o:
        print('FAIL %s: error not shown:\n%s' % (pretty, o))
        return
    if e:
        print('FAIL %s: stderr set:\n%s' % (pretty, e))
        return
    if os.path.exists(dst):
        print(
            'FAIL %s: failing a clone to an empty dir should cause the dir to '
            'be deleted.'
        )
        return

    w.delete()

# check that a vcsjob can fetch its own git tree
def t16(executable, sources):
    pretty = '%s t16' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t16')

    # pull the tree into a temporary directory
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    (s, o, e) = ave.cmd.run(
        '%s %s fetch -s %s -d %s -r master' % (executable,sources,valid,target)
    )
    if s != 0:
        print(o)
        print(e)
        print('FAIL %s: wrong return code: %s' % (pretty, s))
        return

    w.delete()

# check that a vcsjob can fetch its own git tree repeatedly
def t17(executable, sources):
    pretty = '%s t17' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t17')

    # pull the tree into a temporary directory
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    for i in range(5):
        cmd = '%s %s fetch -s %s -d %s -r master' % (
            executable, sources, valid, target
        )
        (s, o, e) = ave.cmd.run(cmd)
        if s != 0:
            print(o)
            print(e)
            print('FAIL %s: wrong return code: %s' % (pretty, s))
            return

    w.delete()

# check that all remote branches are always fetched explicitly
def t18(executable, sources):
    pretty = '%s t18' % __file__
    print(pretty)

    if sources:
        sources = ' -s ' + ','.join(sources)
    else:
        sources = ''

    w = Workspace(uid='vcsjob-cli-t4')

    sys.path.insert(0, os.getcwd())

    # pull the tree into a temporary directory, check that all remotes are
    # also locals afterwards
    valid  = 'git://review.sonyericsson.net/semctools/ave/vcsjob'
    target = w.make_tempdir()
    cmd = '%s %s fetch -s %s -d %s -r master' % (
        executable, sources, valid, target
    )
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: could not fetch master:\n%s\n%s' % (pretty, o, e))
        return
    (local, remote) = ave.git.list_branches(target)
    if local != remote:
        print(
            'FAIL %s: list of remote and local branches not equal: %s != %s'
            % (pretty, local, remote)
        )

    w.delete()

