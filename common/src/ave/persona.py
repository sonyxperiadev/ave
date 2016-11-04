# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import errno
import traceback

import ave.pwd
import ave.config

# UNIX implementation follows. no WIN32 implementation currently available

def become_user(name):
    '''
    Change the current process' effective UID to that of the given user name.
    Can only be called by super user 0. This function is only intended for use
    from the ``init`` process during system boot.

    :arg name: An OS user name. Must be found in the ``password`` database, or
        a replacement authentication system.
    :returns: The user's home directory.
    '''
    uid = ave.pwd.getpwnam_uid(name)
    gid = ave.pwd.getpwnam_gid(name)

    if os.geteuid() == uid:
        return

    if os.geteuid() != 0:
        raise Exception('only root can execute with modified privileges')
    try:
        os.setgid(gid) # must be done before changing euid
        os.setuid(uid)
    except OSError, e:
        if e.errno == errno.EPERM:
            raise Exception(
                'could not execute with modified privileges: %s' % str(e)
            )
    return ave.pwd.getpwnam_dir(name)

def create_user(name, comment, home): # TODO: remove this function? no usage?
    if os.geteuid() != 0:
        raise Exception('only root can create new users')
    try:
        ave.pwd.getpwnam_uid(name)
        return # good, account already exists
    except KeyError:
        pass

    os.system(
        'useradd --user-group --system --expiredate="" --create-home '
        ' --home=%s --comment="%s" %s' % (home, comment, name)
    )
