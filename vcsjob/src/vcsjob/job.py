# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os, signal, errno
import select
import sys
import getopt
import json
import copy
import time

import ave.cmd
import vcsjob # to get constant definitions
import tree

usage = '''
Syntax:
    vcsjob execute -j|--jobs <path> [-t|--tags <tags>] [-e|--env <env vars>]
'''

def get_opt(argv):
    (opts, args) = getopt.gnu_getopt(argv, 'j:e:t:', ['jobs=', 'env=', 'tags='])
    if args:
        args = ','.join(args)
        raise Exception('non-dashed options "%s" not recognized' % args)

    jobs_dir = None
    env_vars = []
    job_tags = []
    for (opt, arg) in opts:
        if   opt in ['-j', '--jobs']:
            jobs_dir = arg
        elif opt in ['-e', '--env']:
            env_vars = arg.split(',')
        elif opt in ['-t', '--tags']:
            job_tags = [a for a in arg.split(',') if a]

    if not jobs_dir:
        raise Exception('at least -j or --jobs must be specified')

    return (jobs_dir, job_tags, env_vars)

def make_log_dir(log_dir):
    if os.path.isdir(log_dir):
        return
    try:
        os.makedirs(log_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise Exception(
                'could not create log directory %s: %s' % (log_dir, str(e))
            )

def set_os_environ(env_vars):
    env = {}
    env_backup = copy.deepcopy(os.environ)

    # some variables must be preserved to retain correct character encoding of
    # file system paths, terminal output, etc. i.e. preserv them even if the
    # user has not asked for it:
    if 'LANG' in os.environ and 'LANG' not in env_vars:
        env_vars.append('LANG')

    for var in env_vars:
        if var not in os.environ:
            raise Exception('environment variable "%s" is not set' % var)
        env[var] = os.environ[var]

    os.environ.clear()
    for var in (env_vars or []):
        os.environ[var] = env[var]
    return env_backup

def restore_env(env_backup):
    os.environ.clear()
    for var in env_backup:
        os.environ[var] = env_backup[var]

def _execute(jobs_dir, path, env, profiles, log_file, guid, timeout=0):
    exe_path = os.path.realpath(os.path.join(jobs_dir, path))
    log_path = None
    if hasattr(log_file, 'name'): # logging to file, not stdout or stderr
        if log_file.name not in ['<stdout>', '<stderr>']:
            log_path = log_file.name
    info = {
        'exe'        : exe_path,
        'environment': dict(env),
        'profiles'   : profiles,
        'guid'       : guid
    }
    log_file.write('vcsjob: %s\n' % json.dumps(info, sort_keys=True))
    log_file.flush()

    vcsjob.set_profiles(profiles) # sets $VCSJOB_PROFILES
    vcsjob.set_log_path(log_path) # sets $VCSJOB_LOG_PATH
    vcsjob.set_guid(guid)         # sets $VCSJOB_GUID

    if timeout > 0:
        limit = time.time() + timeout
    else:
        limit = None

    pid, fd = ave.cmd.run_bg([exe_path], False)

    #if limit:
    while True:
        if limit:
            if time.time() > limit:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
                os.close(fd)
                return vcsjob.TIMEOUT

            try:
                timeout = max(0, limit - time.time())
                r, w, x = select.select([fd], [], [], timeout)
                if r:
                    tmp = os.read(fd, 4096)
                else:
                    continue
            except OSError, e:# child closed its pseudoterminal
                tmp = None
        else:
            try:
                tmp = os.read(fd, 4096)
            except OSError, e:
                tmp = None

        if not tmp:
            (_,status) = os.waitpid(pid, 0)
            os.close(fd) # make sure we don't run out of pseudoterminals

            # status is a 16 bit integer. low byte is the death signal,
            # if any. high byte is the normal exit status. the high bit
            # of the low byte indicates a core dump.
            core_dump    = (status & 0xff) >> 15
            death_signal =  status & 0xef
            normal_exit  = (status & 0xff00) >> 8
            if death_signal:
                return -death_signal
            return normal_exit
        log_file.write(tmp)
        log_file.flush()

def make_log_file(log_path):
    if log_path:
        make_log_dir(os.path.dirname(log_path))
        return open(log_path, 'w') # truncate!
    else:
        return sys.stderr

def set_log_path(path):
    if path:
        os.environ['VCSJOB_LOG_PATH'] = path
    elif 'VCSJOB_LOG_PATH' in os.environ:
        del os.environ['VCSJOB_LOG_PATH']
    else:
        pass

def get_log_path():
    if 'VCSJOB_LOG_PATH' in os.environ:
        return os.environ['VCSJOB_LOG_PATH']
    raise Exception('no log path set')

def check_jobs_dir(jobs_dir):
    if (not jobs_dir) or (not os.path.isdir(jobs_dir)):
        raise Exception('not a jobs directory: %s' % jobs_dir)
    return os.path.realpath(jobs_dir)

def execute_job(jobs_dir, job, env_vars, log_path, guid, timeout=0):
    # make sure the user cannot pass environment variables to jobs that are
    # not mentioned explicitly on the command line
    env_backup = set_os_environ(env_vars or [])

    tree.check_job(jobs_dir, job)
    log_file = make_log_file(log_path)

    try:
        status = _execute(
            jobs_dir, job['path'], os.environ, job['profiles'], log_file, guid, job.get('duration', timeout)
        )
    except KeyboardInterrupt:
        return vcsjob.NORUN
    except Exception, e:
        log_file.write(str(e)+'\n')
        log_file.flush()
        return vcsjob.NORUN
    finally:
        restore_env(env_backup) # executed just before return in except clause

    if status < 0:
        return vcsjob.KILLED
    return status

def execute_path(jobs_dir, exec_target, env_vars, log_path, timeout=0):
    # make sure the user cannot pass environment variables to jobs that are
    # not mentioned explicitly on the command line
    env_backup = set_os_environ(env_vars or [])

    jobs_dir = check_jobs_dir(jobs_dir)
    job      = {'path':exec_target}
    tree.check_job(jobs_dir, job)
    log_file = make_log_file(log_path) # start logging

    try:
        status = _execute(jobs_dir, exec_target, os.environ, [], log_file, None, timeout)
    except KeyboardInterrupt:
        return vcsjob.NORUN
    except Exception, e:
        log_file.write(str(e)+'\n')
        log_file.flush()
        return vcsjob.NORUN

    # restore environment variables
    restore_env(env_backup)

    log_file.flush() # stop logging

    # vcsjob status should be returned from the job
    # {OK, BUSY, FAILURES}, seen {0, 1024, 1280}:
    # should examine this further
    if status < 0:
        return vcsjob.KILLED
    return status

def execute_tags(jobs_dir, job_tags, env_vars, log_path=None):
    # make sure the user cannot pass environment variables to jobs that are
    # not mentioned explicitly on the command line
    env_backup = set_os_environ(env_vars or [])

    jobs_dir = check_jobs_dir(jobs_dir)
    log_file = make_log_file(log_path)
    jobs     = tree.load_dir(jobs_dir, job_tags or [])

    try:
        i = 0
        for job in jobs:
            # the filtered list will contain any tags from job_tags that
            # are not found in the job['tags'] list. don't run the job if
            # the list isn't empty:
            if job_tags and [t for t in job_tags if t not in job['tags']]:
                continue
            i += 1
            status = _execute(
                jobs_dir, job['path'], os.environ, job['profiles'], log_file,
                None, job.get('duration',0)
            )
    except KeyboardInterrupt:
        return vcsjob.NORUN
    except Exception, e:
        log_file.write(str(e)+'\n')
        log_file.flush()
        return vcsjob.NORUN
    finally:
        # restore environment variables
        restore_env(env_backup)

    if i == 0:
        log_file.write('WARNING: no jobs were executed')
        log_file.flush()
        return vcsjob.NORUN

    log_file.flush()

    return vcsjob.OK

def main(argv):
    try:
        (jobs_dir, job_tags, env_vars) = get_opt(argv)
    except Exception, e:
        sys.stderr.write('ERROR: %s\n' % str(e))
        sys.stderr.flush()
        return vcsjob.NORUN

    try:
        return execute_tags(jobs_dir, job_tags, env_vars)
    except Exception, e:
        sys.stderr.write('ERROR: %s\n' % str(e))
        sys.stderr.flush()
        return vcsjob.NORUN