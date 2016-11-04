# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

OK       = 0 # operation went well
ERROR    = 1 # the test job crashed or raised uncaught exception
NORUN    = 2 # did not execute jobs
BLOCKED  = 3 # jobs could not satisify pre-conditions
BUSY     = 4 # jobs could not allocate necessary resources
FAILURES = 5 # jobs had failures
NOLIST   = 6 # failed to list jobs
KILLED   = 7 # job was signalled to death
NOFETCH  = 8 # failed to fetch jobs
TIMEOUT  = 9 # job is running out of the specified time

import vcs
import job
import tree
import profiles
import guid

# the two following functions are defined here so that the package can have
# function definitions. otherwise one would have to come up with API's that
# feel natural on the module level, which is hard. writing "vcsjob.fetch.run()"
# instead of just "vcsjob.fetch()" feel unnatural. it is also not an option to
# create a *module* called "vcsjob" since that would force the implementation
# to live in a single file.

def fetch(src, dst, refspec, depth=1, timeout=600):
    return vcs.fetch(src, dst, refspec, depth=depth, timeout=timeout)

def execute_tags(jobs_dir, job_tags=None, env_vars=[], log_path=None):
    return job.execute_tags(jobs_dir, job_tags, env_vars, log_path)

def execute_job(jobs_dir, job_dict, env=[], log_path=None, guid=None):
    return job.execute_job(jobs_dir, job_dict, env, log_path, guid)

def list_jobs(jobs_dir, job_tags=None):
    return tree.list_paths(jobs_dir, job_tags)

def load_jobs(jobs_dir, job_tags=[]):
    return tree.load_dir(jobs_dir, job_tags)

def set_profiles(job_profiles):
    profiles.set_profiles(job_profiles)

def get_profiles():
    return profiles.get_profiles()

def set_guid(job_guid):
    guid.set_guid(job_guid)

def get_guid():
    return guid.get_guid()

def exit_to_str(exit):
    if exit == OK:
        return 'vcsjob.OK'
    if exit == ERROR:
        return 'vcsjob.ERROR'
    if exit == NORUN:
        return 'vcsjob.NORUN'
    if exit == BLOCKED:
        return 'vcsjob.BLOCKED'
    if exit == BUSY:
        return 'vcsjob.BUSY'
    if exit == FAILURES:
        return 'vcsjob.FAILURES'
    if exit == NOLIST:
        return 'vcsjob.NOLIST'
    if exit == KILLED:
        return 'vcsjob.KILLED'
    if exit == NOFETCH:
        return 'vcsjob.NOFETCH'
    if exit == TIMEOUT:
        return 'vcsjob.TIMEOUT'
    raise Exception('unknown exit code: %i' % exit)

def set_log_path(path):
    return job.set_log_path(path)

def get_log_path():
    return job.get_log_path()

# OBSOLESCENT, DO NOT USE
def execute_single(jobs_dir, exec_target, env_vars=[], log_path=None):
    if exec_target is None:
        raise Exception('execution target: None')
    return job.execute_path(jobs_dir, exec_target, env_vars, log_path)
