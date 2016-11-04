# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import re
import os
import inspect
import traceback

from datetime import datetime

import ave.pwd
import ave.git
import vcsjob

from ave.broker import Broker

import tests.config
import tests.broker
import tests.restart
import tests.process
import tests.usb_power

def run_tests(functions, package, *argv):
    passed    = []
    failed    = []
    errors    = []

    for f in functions:
        try:
            if f[1](*argv):
                passed.append(f[0])
            else:
                failed.append(f[0])
        except Exception, e:
            traceback.print_exc()
            errors.append(f[0])

    return passed, failed, errors

def run_module(module, args, report=False):
    package   = 'ave.relay.%s' % module.__name__.split('.')[-1]
    functions = inspect.getmembers(module, inspect.isfunction)
    functions = [f for f in functions if re.match('t\d+', f[0])]
    target    = len(functions)
    passed,failed,errors = run_tests(functions, package, *args)
    return target,passed,failed,errors


def run_suite(modules, report=False):
    passed    = []
    failed    = []
    errors    = []
    target    = 0

    try:
        git_dir  = os.path.dirname(os.path.dirname(__file__))
        git_sha1 = ave.git.rev_list(git_dir, 1)[0]
    except Exception, e:
        git_sha1 = ''

    for m in modules:
        args = tuple()
        if type(m) == tuple:
            args = m[1]
            m = m[0]
        package = 'ave.relay.%s' % m.__name__.split('.')[-1]
        functions = inspect.getmembers(m, inspect.isfunction)
        functions = [f for f in functions if re.match('t\d+', f[0])]
        target += len(functions)
        p,f,e = run_tests(functions, package, *args)
        passed.extend(p)
        failed.extend(f)
        errors.extend(e)

    if len(passed) != target:
        return vcsjob.FAILURES
    return vcsjob.OK

def all_config(debug=False, report=False):
    result = run_suite([(tests.config, ())], report)

def all_broker(debug=False, report=False):
    result = run_suite([(tests.broker, ())], report)

def all_restart(debug=False, report=False):
    result = run_suite([(tests.restart, ())], report)

def all_process(debug=False, report=False):
    result = run_suite([(tests.process, ())], report)

def all_usb_power(debug=False, report=False):
    profiles = vcsjob.get_profiles()
    b = Broker()
    r,h = b.get(*profiles)
    result = run_suite([(tests.usb_power, (b,r,h))], report)
