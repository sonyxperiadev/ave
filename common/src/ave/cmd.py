# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import pty
import select
import os
import signal
import sys
import time
import errno

from datetime import datetime, timedelta

from ave.exceptions import *

def run_bg(cmd, debug=False, cwd=''):
    # make sure 'cmd' is a list of strings
    if type(cmd) in [str, unicode]:
        cmd = [c for c in cmd.split() if c != '']
    if debug:
        sys.stderr.write(' '.join(cmd)+'\n')
        sys.stderr.flush()

    try:
        ( child_pid, child_fd ) = pty.fork()
    except OSError as e:
        raise RunError(cmd, None, message='pty.fork() failed: %s' % str(e))
    if child_pid == 0:
        try:
            if cwd != '':
                os.chdir(cwd)
            os.execvp(cmd[0], cmd)
        except Exception, e:
            raise RunError(cmd, None, 'os.execvp() failed: %s' % str(e))
    else:
        return child_pid, child_fd

def run(cmd, timeout=0, debug=False, cwd='', output_file=None):
    # make sure 'cmd' is a list of strings
    if type(cmd) in [str, unicode]:
        cmd = [c for c in cmd.split() if c != '']
    if debug:
        sys.stderr.write(' '.join(cmd)+'\n')
        sys.stderr.flush()
    if output_file and type(output_file) is not file:
        raise Exception('Parameter "output_file" must be type file')

    out = '' # keep a buffer of everything written to terminal by sub-process

    try:
        ( child_pid, fd ) = pty.fork()
    except OSError as e:
        raise RunError(cmd, None, message='pty.fork() failed: %s' % str(e))
    if child_pid == 0:
        try:
            if cwd != '':
                os.chdir(cwd)
            os.execvp(cmd[0], cmd)
        except Exception, e:
            raise RunError(cmd, None, 'os.execvp() failed: %s' % str(e))
    else:
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            limit = None
        p = select.poll()
        mask = (
            select.POLLERR | select.POLLHUP | select.POLLNVAL | select.POLLIN |
            select.POLLPRI
        )
        p.register(fd, mask)
        stop = False
        try:
            while (not stop):
                if limit and datetime.now() > limit:
                    raise Timeout(
                        {'cmd':cmd,'out':out,'message':'command timed out'}
                    )
                try:
                    events = p.poll(100) # milliseconds
                except select.error, e:
                    if e[0] == errno.EINTR:
                        continue # interrupted system call. try again.
                for efd, flags in events:
                    if debug:
                        sys.stderr.write('flags: 0x%02x\n' % flags)
                        sys.stderr.flush()
                    if (flags&select.POLLIN
                    or  flags&select.POLLPRI):
                        tmp = os.read(efd, 4096)
                        if debug:
                            sys.stderr.write('read %d\n' % len(tmp))
                            sys.stderr.write(tmp)
                            sys.stderr.write('\n')
                            sys.stderr.flush()
                        out += tmp
                        if output_file:
                            output_file.write(tmp)
                    elif (flags&select.POLLERR
                    or  flags&select.POLLHUP
                    or  flags&select.POLLNVAL):
                        stop = True # ONLY if no data was available.


        except Exception, e:
            os.kill(child_pid, signal.SIGKILL)
            os.waitpid(child_pid, 0)
            os.close(fd) # make sure we don't run out of pseudo terminals
            raise e
        s = os.waitpid(child_pid, 0)
        # since the return value is actually the high byte and the return
        # reason is the low byte of the 16-bit return value s[1], this is used
        # to get the real return value of the execution
        result = s[1]
        if result >> 15 == 1:
            a = 256-(result >> 8)
            a *= -1
        else:
            a = result >> 8
        os.close(fd) # make sure we don't run out of pseudo terminals

        return (a, out, '')

# this implementation is more portable but has two disadvantages:
#
# * sub-process not connected to a pseudo-terminal. this means that all output
#   written on stdout by 'cmd' will be buffered and eventually flushed according
#   to whatever defaults the underlying OS is using for NON-INTERACTIVE jobs.
#   i.e. output does not appear on screen until well after 'cmd' has finished.
# * sub-process is harder to kill completely. the implementation does put the
#   child into the same process group as the parent, but the parent may not be
#   the LEADER of that process group (a process connected to a pseudo-terminal
#   is the leader in all interactive use cases). i.e. killing the parent is not
#   guaranteed to bring down all sub-processes of the child. this is seen when
#   the child creates more processes and perhaps isn't too picky about waiting
#   for them to exit properly on SIGINT (CTRL-C). connecting all children to
#   the same pseudo-terminal solves the problem because all signals sent to the
#   process group leader get propagated to all children too.
#
#def _run_portable(cmd, timeout=0, debug=False):
#    import subprocess
#    if type(cmd) in [str, unicode]:
#        cmd = [c for c in cmd.split() if c != '']
#    if debug:
#        sys.stderr.write(' '.join(cmd)+'\n')
#        sys.stderr.flush()
#
#    if timeout > 0:
#        time_limit = datetime.now() + timedelta(seconds=timeout)
#    else:
#        time_limit = None
#    # use preexec_fn to put all child processes in a new process group (the
#    # call to os.setpgrp() creates a new process group with PGID==caller's PID,
#    # which is the Popen child). later, kill this group instead of just the
#    # immediate child. this solves problems with external programs who may or
#    # may not cause *their* children to die properly when they are killed. e.g.
#    # the way git starts ssh seems to have trouble with this and only git dies
#    # if such a subprocess is killed in a more regular way.
#    p = subprocess.Popen(
#            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
#            preexec_fn=lambda:os.setpgrp()
#        )
#
#    if time_limit:
#        while True:
#            time.sleep(1)
#            if p.poll() != None:
#                break
#            if datetime.now() > time_limit:
#                # killall processes in the child's process group:
#                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
#                p.wait() # "flush" all side effects of termination
#                raise RunError(cmd, '', '', 'command timed out')
#    o, e = p.communicate()
#    if debug:
#        if o:
#            sys.stderr.write(o)
#        if e:
#            sys.stderr.write(e)
#        sys.stderr.flush()
#    return (p.returncode, o, e)
