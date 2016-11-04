# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import getopt
import subprocess
import json
import copy

import vcsjob # to get constant definitions
import ave.cmd

def check_job_path(jobs_dir, job):
    if 'path' not in job:
        raise Exception('job does not have the "path" attribute: %s' % job)
    if not isinstance(job['path'], basestring):
        raise Exception('"path" attribute is not a string: %s' % job)
    # check that 'path' is rooted in the same directory as the .vcsjob file
    if job['path'].startswith('/'):
        raise Exception('job path is not relative: %s' % job['path'])
    path = os.path.normpath(os.path.join(jobs_dir, job['path']))
    if not path.startswith(jobs_dir):
        raise Exception('job path is not inside the job tree: %s' % path)
    # also check that the job exists and is runnable
    if not os.path.isfile(path):
        raise Exception('no such file: %s' % path)
    if not os.access(path, os.X_OK):
        raise Exception('file is not executable: %s' % path)
    if 'profiles' not in job:
        job['profiles'] = None

def check_job_tags(job):
    if 'tags' not in job:
        job['tags'] = []
    if not isinstance(job['tags'], list):
        raise Exception('"tags" attribute is not a list: %s' % job['tags'])
    i = 1
    for tag in job['tags']:
        if not isinstance(tag, basestring):
            raise Exception('tag #%i is not a string: %s' % (i, job))
        i += 1

def check_job_banner(job):
    if 'banner' not in job:
        job['banner'] = ''
    if not isinstance(job['banner'], basestring):
        raise Exception('job\'s "banner" attribute must be a string: %s' % job)

def check_job_profiles(job):
    if 'profiles' not in job:
        job['profiles'] = None
    if job['profiles'] == None:
        return
    if not isinstance(job['profiles'], list):
        raise Exception('"profiles" attribute is not a list: %s' % job)
    i = 1
    for profile in job['profiles']:
        if isinstance(profile, dict):
            for key in profile:
                if not isinstance(key, basestring):
                    raise Exception(
                        'profile #%i contains non-string keys: %s' % (i, job)
                    )
        elif isinstance(profile, list):
            for p  in profile:
                if isinstance(p, dict):
                    for k in p:
                        if not isinstance(k, basestring):
                            raise Exception(
                                'profile #%i contains non-string keys: %s' % (i, job)
                                )
        else:
            raise Exception('profile #%i is not a dictionary or dict list: %s' % job)

def check_job_coverage(job):
    if 'coverage' not in job:
        job['coverage'] = None
    if not job['coverage']:
        return
    if type(job['coverage']) != list:
        raise Exception(
            'job\'s "coverage" attribute is not a list of strings: %s' % job
        )
    for item in job['coverage']:
        if type(item) not in [str, unicode]:
            raise Exception(
                'job\'s "coverage" attribute is not a list of strings: %s' % job
            )

def check_job_dirty(job):
    if 'dirty' not in job:
        job['dirty'] = False
    if not job['dirty']:
        return
    if type(job['dirty']) != bool:
        raise Exception(
            'job\'s "dirty" attribute is not a boolean value: %s' % job
        )

def check_job_virgin(job):
    if 'virgin' not in job:
        job['virgin'] = False
    if not job['virgin']:
        return
    if type(job['virgin']) != bool:
        raise Exception(
            'job\'s "virgin" attribute is not a boolean value: %s' % job
        )

def check_job_duration(job):
    if 'duration' not in job:
        # duration will be initialized during executing job/path/tags
        return
    if type(job['duration']) != int:
        raise Exception(
            'job\'s "duration" attribute is not an integer: %s' % job
        )

def check_job(jobs_dir, job):
    # check that all attributes have correct types
    check_job_path(jobs_dir, job)
    check_job_tags(job)
    check_job_banner(job)
    check_job_profiles(job)
    check_job_coverage(job)
    check_job_dirty(job)
    check_job_duration(job)
    check_job_virgin(job)

def load_dir(jobs_dir, job_tags):
    if (not jobs_dir) or (not os.path.isdir(jobs_dir)):
        raise Exception('not a jobs directory: %s' % jobs_dir)
    if not isinstance(job_tags, list):
        raise Exception('not a tags list: %s' % job_tags)

    jobs_dir = os.path.realpath(jobs_dir)
    rc_path = os.path.join(jobs_dir, '.vcsjob')
    try:
        rc = open(rc_path)
        jobs = json.load(rc)['executables']
    except Exception, e:
        raise Exception('could not load %s: %s' % (rc_path, str(e)))

    loaded = []
    for job in jobs:
        check_job(jobs_dir, job)

        # filter out jobs that don't have matching tags
        if [t for t in job_tags if t not in job['tags']] != []:
            # the filtered list contains tags that could not be matched. do
            # not include this job in the results
            continue

        loaded.append(job)

    return loaded

def list_paths(jobs_dir, job_tags):
    jobs  = load_dir(jobs_dir, job_tags or [])
    paths = []
    for j in jobs:
        paths.append(j['path'])
    return paths
