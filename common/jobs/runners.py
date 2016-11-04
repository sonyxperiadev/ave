# Copyright (C) 2013-2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import gc
import re
import os
import inspect
import traceback

from datetime import datetime

import tests.config
import tests.documentation
import tests.cmd
import tests.spool
import tests.connection
import tests.control_sync
import tests.control_async
import tests.fdtx
import tests.exception
import tests.hickup
import tests.stress
import tests.panotti
import tests.process
import tests.pipe
import tests.daemon
import tests.defjoin
import tests.async_rpc

import ave.git
import ave.pwd
import vcsjob

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
            errors.append(f[0])
            traceback.print_exc()

    return passed, failed, errors

def run_suite(modules, smoke=False, report=False):
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
        package = 'ave.common.%s' % m.__name__.split('.')[-1]
        functions = inspect.getmembers(m, inspect.isfunction)
        functions = [f for f in functions if re.match('t\d+', f[0])]
        if smoke:
            functions = [f for f in functions if hasattr(f[1], 'smoke')]
        target += len(functions)
        p,f,e = run_tests(functions, package, *args)
        passed.extend(p)
        failed.extend(f)
        errors.extend(e)

    if len(passed) != target:
        return vcsjob.FAILURES
    return vcsjob.OK

def all_smoke(report, so_path):
    modules = [
        tests.config, tests.cmd, tests.documentation, tests.spool,
        tests.connection, tests.control, (tests.fdtx, (so_path,))
    ]
    return run_suite(modules, True, report)

def all_config(report=False):
    return run_suite([tests.config], False, report)

def all_cmd(report=False):
    return run_suite([tests.cmd], False, report)

def all_documentation(report=False):
    return run_suite([tests.documentation], False, report)

def all_spool(report=False):
    # tests for irrelevant functionality. don't run
    return run_suite([tests.spool], False, report)

def all_connection(report=False):
    return run_suite([tests.connection], False, report)

def all_control(report=False):
    run_suite([tests.control_sync],  False, report)
    run_suite([tests.control_async], False, report)

#    for i in range(100000):
#        tests.control_async.t28()
#        print 'num fds: %d' % len(os.listdir('/proc/%d/fd' % os.getpid()))
#        gc.collect()
#        pass

def all_fdtx(so_path=None, report=False):
    return run_suite([(tests.fdtx, (so_path,))], False, report)

def all_exception(report=False):
    return run_suite([tests.exception], False, report)

def all_hickup(report=False):
    return run_suite([tests.hickup], False, report)

def all_stress():
    return tests.stress.t1()

def all_panotti(report=False):
    return run_suite([tests.panotti], False, report)

def all_process(report=False):
    return run_suite([tests.process], False, report)

def all_pipe(report=False):
    return run_suite([tests.pipe], False, report)

def all_daemon(report=False):
    return run_suite([tests.daemon], False, report)

def all_defjoin(report=False):
    return run_suite([tests.defjoin], False, report)

def all_async_rpc(report=False):
    return run_suite([tests.async_rpc], False, report)
