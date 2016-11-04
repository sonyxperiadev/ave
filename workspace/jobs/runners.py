# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import inspect
import re
import os
import traceback

from datetime import datetime

import tests.config
import tests.documentation
import tests.git
import tests.jenkins
import tests.apk
import tests.flocker
import tests.flocker_performance


import tests.marionette
import tests.filesystem
import tests.apk_code_coverage

import tests.zip


import ave.git
import ave.pwd
import vcsjob

def run_tests(functions, params, package):
    passed    = []
    failed    = []
    errors    = []

    for f in functions:
        try:
            if f[1](*params):
                passed.append(f[0])
            else:
                failed.append(f[0])
        except Exception, e:
            traceback.print_exc()
            print(e)

            errors.append(f[0])
    return passed, failed, errors

def run_suite(modules, params, smoke=False, report=False):
    passed    = []
    failed    = []
    errors    = []
    target    = 0
    user      = ave.pwd.getpwuid_name(os.geteuid())

    start     = datetime.utcnow()

    try:
        git_dir  = os.path.dirname(os.path.dirname(__file__))
        git_sha1 = ave.git.rev_list(git_dir, 1)[0]
    except Exception, e:
        git_sha1 = ''

    for m in modules:
        package = 'ave.workspace.%s' % m.__name__.split('.')[-1]
        functions = inspect.getmembers(m, inspect.isfunction)
        functions = [f for f in functions if re.match('t\d+', f[0])]
        if smoke:
            functions = [f for f in functions if hasattr(f[1], 'smoke')]
        target += len(functions)
        p,f,e = run_tests(functions, params, package)
        passed.extend(p)
        failed.extend(f)
        errors.extend(e)


    if len(passed) != target:
        return vcsjob.FAILURES
    return vcsjob.OK

def all_smoke(report=False):
    modules = [
        tests.apk, tests.config, tests.git,
        tests.jenkins
    ]
    return run_suite(modules, (), True, report)


def all_config(report=False):
    return run_suite([tests.config], (), False, report)

def all_documentation(report=False):
    return run_suite([tests.documentation], (), False, report)

def all_git(report=False):
    return run_suite([tests.git], (), False, report)


def all_jenkins(report=False):
    return run_suite([tests.jenkins], (), False, report)

def all_apk(local=False, report=False):
    return run_suite([tests.apk], (local,), False, report)

def all_flocker(report=False):
    return run_suite([tests.flocker], (), False, report)

def all_flocker_performance(report=False):
    return run_suite([tests.flocker_performance], (), False, report)




def all_marionette(report=False):
    return run_suite([tests.marionette], (), False, report)

def all_filesystem(report=False):
    return run_suite([tests.filesystem], (), False, report)

def all_apk_code_coverage(local=False, report=False):
    return run_suite([tests.apk_code_coverage], (local,), False, report)


def all_zip(report=False):
    return run_suite([tests.zip], (), False, report)
