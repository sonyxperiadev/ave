# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import re
import os
import inspect
import traceback
import json
import time

from datetime import datetime

import ave.git
import ave.pwd
import ave.panotti
import vcsjob

from ave.broker import Broker
from ave.broker.exceptions import Busy, NoSuch
from ave.handset.handset import Handset, AndroidHandset
from ave.handset.profile import HandsetProfile
from ave.exceptions import Exit
from ave.utils.logger import Logger

import tests.android
import tests.lister
import tests.galatea
import tests.gtest
import tests.junit
import tests.adb
import tests.forwarding
import tests.popup
import tests.hprof
import tests.adb_server

KEYCODE_HOME = 3

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

def run_module(module, args, smoke=False, report=False, logger = None):
    package   = 'ave.handset.%s' % module.__name__.split('.')[-1]
    if logger:
        logger.log_it('d', '%s: %s' %(package, datetime.utcnow()))
    functions = inspect.getmembers(module, inspect.isfunction)
    functions = [f for f in functions if re.match('t\d+', f[0])]
    if smoke:
        functions = [f for f in functions if hasattr(f[1], 'smoke')]
    target    = len(functions)
    passed,failed,errors = run_tests(functions, package, *args)
    return target,passed,failed,errors

class PatchedAndroidHandset(AndroidHandset):

    def __init__(self, profile):
        AndroidHandset.__init__(self, profile)

    def get_galatea_apk_path(self):
        original_galatea_path = AndroidHandset.get_galatea_apk_path(self)
        project_root = os.path.dirname(os.path.dirname(__file__))
        galatea_root = os.path.join(os.path.dirname(project_root), 'galatea')
        return os.path.join(galatea_root, 'packaging', original_galatea_path[1:])

def allocate_by_profiles(local=False):
    # get profiles from vcsjob file and attempt to allocate the resources.
    # return as a tuple including the broker:
    #     (<broker>, <allocated 1>, <allocated 2>,...)
    profiles = vcsjob.get_profiles()
    b = Broker()
    try:
        allocated = b.get(*profiles)
    except (Busy, NoSuch, Exit) as e:
        print('BUSY: %s' % e)
        sys.exit(vcsjob.BUSY)
    res = [b]
    allocated = [allocated] if not '__iter__' in dir(allocated) else allocated
    for a in allocated:
        if local and a.profile['type'] == 'handset':
            if a.profile['platform'] == 'android':
                a = PatchedAndroidHandset(HandsetProfile(a.get_profile()))
            else:
                a = Handset(HandsetProfile(a.get_profile()))
        res.append(a)
    return tuple(res)

def run_smoke_off_site(report=True):
    passed  = []
    failed  = []
    errors  = []
    target  = 0
    logger_broker = Broker()
    logger_ws = logger_broker.get({'type':'workspace'})
    try:
        guid = vcsjob.get_guid()
    except Exception as e:
        guid = 'local_guid'
    logger = Logger(logger_ws, guid)

    b,w,h = allocate_by_profiles()
    logger.log_it('d', 'allocated: %s' % json.dumps([h.profile, w.profile],indent=3))

    label = h.get_build_label()

    t,p,f,e = run_module(tests.popup, (w, h), True, report, logger)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.adb, (w,h), True, report, logger)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.android, (w,h,label), True, report, logger)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.gtest, (w,h), True, report, logger)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    if len(passed) != target:
        return vcsjob.FAILURES
    return vcsjob.OK

def run_smoke_1(report=False):
    passed  = []
    failed  = []
    errors  = []
    target  = 0

    b,w,h = allocate_by_profiles()
#    print('allocated: %s' % json.dumps([h.profile, w.profile],indent=3))
    label = h.get_build_label()

    t,p,f,e = run_module(tests.adb, (w,h), True, report)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.android, (w,h,label), True, report)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.gtest, (w,h), True, report)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    t,p,f,e = run_module(tests.junit, (w,h,label), True, report)
    target += t
    passed.extend(p)
    failed.extend(f)
    errors.extend(e)

    if len(passed) != target:
        return vcsjob.FAILURES
    return vcsjob.OK

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
        package = 'ave.handset.%s' % m.__name__.split('.')[-1]
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

def all_misc_android(local=False, report=False):
    b,w,h  = allocate_by_profiles(local=local)
    label = h.get_build_label()
    result = run_suite([(tests.android, (w,h,label))], False, report)
    sys.exit(result)

def all_lister(local=False, report=False):
    b,h1 = allocate_by_profiles(local=local)
    try:
        h2 = b.get({'type':'handset'})
    except (Busy, NoSuch, Exit) as e:
        print('BUSY: %s' % e)
        sys.exit(vcsjob.BUSY)

    result = run_suite([(tests.lister, (h1,h2))], False, report)
    sys.exit(result)

def all_galatea(local=False, report=False):
    b,h = allocate_by_profiles(local=local)
    result = run_suite([(tests.galatea, (h,))], False, report)
    h.press_key(3) # 3 == KEYCODE_HOME
    sys.exit(result)

def all_gtest(local=False, report=False):
    b,w,h  = allocate_by_profiles(local=local)
    result = run_suite([(tests.gtest, (w,h))], False, report)
    sys.exit(result)

def all_junit(local=False, report=False):
    b,w,h  = allocate_by_profiles(local=local)
    label = h.get_build_label()
    result = run_suite([(tests.junit, (w,h,label))], False, report)
    sys.exit(result)

def all_adb(local=False):
    b,w,h  = allocate_by_profiles(local=local)
    result = run_suite([(tests.adb, (w,h))], False, False)
    sys.exit(result)

def all_forwarding(local=False):
    b,h1 = allocate_by_profiles(local)
    # a companion handset is needed for some of the tests
    try:
        h2 = b.get({'type':'handset'}) # any ADB handset will do
    except (Busy, NoSuch), e:
        print('BUSY: %s' % e)
        sys.exit(vcsjob.BUSY)
    if local:
        h2 = Handset(HandsetProfile(h2.get_profile()))

    result = run_suite([(tests.forwarding, (h1,h2))], False, False)
    sys.exit(result)

def all_popup(local=False):
    b,w,h = allocate_by_profiles(local=local)
    result = run_suite([(tests.popup, (w,h))], False, False)
    sys.exit(result)

def all_hprof(local=False, report=False):
    b,w,h  = allocate_by_profiles(local=local)
    result = run_suite([(tests.hprof, (w,h))], False, report)
    sys.exit(result)

def all_adb_server(report=False):
    result = run_suite([(tests.adb_server, ())], False, report)
    sys.exit(result)

