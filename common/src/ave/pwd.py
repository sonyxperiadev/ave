import os
import sys

import ave.cmd

def getpwnam_dir(name):
    cmd = [
        '/usr/bin/python2', os.path.realpath(__file__), 'pwd.getpwnam.dir', name
    ]
    s,o,e = ave.cmd.run(cmd)
    o = o.strip()
    if s != 0:
        raise Exception(o)
    return o

def getpwuid_name(uid):
    uid = str(uid)
    cmd = [
        '/usr/bin/python2', os.path.realpath(__file__), 'pwd.getpwuid.name', uid
    ]
    s,o,e = ave.cmd.run(cmd)
    o = o.strip()
    if s != 0:
        raise Exception(o)
    return o

def getpwnam_uid(name):
    cmd = [
        '/usr/bin/python2', os.path.realpath(__file__), 'pwd.getpwnam.uid', name
    ]
    s,o,e = ave.cmd.run(cmd)
    o = o.strip()
    if s != 0:
        raise Exception(o)
    return int(o)

def getpwnam_gid(name):
    cmd = [
        '/usr/bin/python2', os.path.realpath(__file__), 'pwd.getpwnam.gid', name
    ]
    s,o,e = ave.cmd.run(cmd)
    o = o.strip()
    if s != 0:
        raise Exception(o)
    return int(o)

# a bug in winbindd or its client makes it close "inherited" file descriptors
# *before* it forks. it will in fact close one or more file descriptors which
# it does not own. unfortunately, the Python pwd module may use this backend on
# systems that authenticate against ActiveDirectory. so, calling pwd functions
# must be done in a context where no file descriptors can be clobbered (i.e.
# none were opened before the call). e.g. in a new process (__main__, below).
# it is not entirely safe to communicate with the new process over e.g. a pipe
# as winbindd could clobber *that* file descriptor. printing on stdout appears
# to be safe, so just execute __file__ as a separate program with some options
# to steer the use of pwd and print the result.
if __name__ == '__main__':
    import pwd

    if sys.argv[1] == 'pwd.getpwnam.dir':
        user = sys.argv[2]
        try:
            entry = pwd.getpwnam(user)
            print(entry.pw_dir)
            sys.exit(0)
        except KeyError:
            print('no such user: %s' % user)
            sys.exit(1)

    if sys.argv[1] == 'pwd.getpwuid.name':
        uid = int(sys.argv[2])
        try:
            entry = pwd.getpwuid(uid)
            print(entry.pw_name)
            sys.exit(0)
        except KeyError:
            print('no such user id: %d' % uid)
            sys.exit(1)

    if sys.argv[1] == 'pwd.getpwnam.uid':
        name = sys.argv[2]
        try:
            entry = pwd.getpwnam(name)
            print(str(entry.pw_uid))
            sys.exit(0)
        except KeyError:
            print('no such user name: %d' % uid)
            sys.exit(1)

    if sys.argv[1] == 'pwd.getpwnam.gid':
        name = sys.argv[2]
        try:
            entry = pwd.getpwnam(name)
            print(str(entry.pw_gid))
            sys.exit(0)
        except KeyError:
            print('no such user name: %d' % uid)
            sys.exit(1)
