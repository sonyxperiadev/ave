#!/usr/bin/python2

# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from __future__ import print_function

import sys
import vcsjob
import common

from ave.utils.testjob import TestJob


def print(string):
    """
    Redefining print to write to stderr instead because stdout is redirected
    to a tmp file
    """
    sys.stderr.writelines("%s\n" % string)


class TestJobExecutionOrder(TestJob):
    execution_flow = None

    def __init__(self):
        TestJob.__init__(self)
        self.execution_flow = []
        self.execution_flow.append('init')

    def setup(self):
        self.execution_flow.append('setup')

    def pre(self):
        self.execution_flow.append('pre')

    def main(self):
        self.execution_flow.append('main')

    def post(self):
        self.execution_flow.append('post')

    def teardown(self):
        self.execution_flow.append('teardown')


class TestJobExecutionOrderExceptionInSetup(TestJobExecutionOrder):
    def setup(self):
        self.execution_flow.append('setup')
        raise Exception('testException')


class TestJobExecutionOrderExceptionInPre(TestJobExecutionOrder):
    def pre(self):
        self.execution_flow.append('pre')
        raise Exception('testException')


class TestJobWithEquipmentAllocation(TestJob):
    def equipment_assignment(self, profiles):
        self.handset, self.workspace = self.broker.get(*profiles)


def t1():
    """
    tests TestJob.__init__
    """
    pretty = common.get_test_pretty()
    print(pretty)

    tj = TestJob()
    if not tj.broker:
        print('FAIL %s: broker not created' % pretty)
        return False
    if not tj.logger_broker:
        print('FAIL %s: logger_broker not created' % pretty)
        return False
    if not tj.logger_workspace:
        print('FAIL %s: logger_workspace not created' % pretty)
        return False
    if not tj.logger:
        print('FAIL %s: logger not created' % pretty)
        return False
    if not tj.start_time:
        print('FAIL %s: start_time not set' % pretty)
        return False

    return True


def t2():
    """
    tests update_status finishing in ERROR
    """
    pretty = common.get_test_pretty()
    print(pretty)

    tj = TestJob()

    status_to_set = [
        vcsjob.OK,
        vcsjob.FAILURES,
        vcsjob.OK,
        vcsjob.ERROR,
        vcsjob.OK,
        vcsjob.FAILURES,
        vcsjob.BUSY
    ]

    expected_status = [
        vcsjob.OK,
        vcsjob.FAILURES,
        vcsjob.FAILURES,
        vcsjob.ERROR,
        vcsjob.ERROR,
        vcsjob.ERROR,
        vcsjob.ERROR
    ]

    for i in range(len(status_to_set)):
        tj.update_status(status_to_set[i])
        if tj.test_job_status != expected_status[i]:
            print('FAIL %s: start_time not set' % pretty)
            return False

    return True


def t3():
    """
    tests update_status finishing in BUSY
    """
    pretty = common.get_test_pretty()

    print(pretty)

    tj = TestJob()

    status_to_set = [
        vcsjob.OK,
        vcsjob.BUSY,
        vcsjob.OK,
        vcsjob.FAILURES,
        vcsjob.ERROR
    ]

    expected_status = [
        vcsjob.OK,
        vcsjob.BUSY,
        vcsjob.BUSY,
        vcsjob.BUSY,
        vcsjob.BUSY
    ]

    for i in range(len(status_to_set)):
        tj.update_status(status_to_set[i])
        if tj.test_job_status != expected_status[i]:
            print('FAIL %s: start_time not set' % pretty)
            return False

    return True


def t4():
    """
    tests execution order
    """
    pretty = common.get_test_pretty()
    print(pretty)

    tj = TestJobExecutionOrder()
    tj2 = TestJobExecutionOrder()

    expected_execution_order = \
        ['init', 'setup', 'pre', 'main', 'post', 'teardown']

    tj._execute()

    if expected_execution_order != tj.execution_flow:
        print('FAIL %s: Expected Execution flow: %s differs from Actual %s' %
              (pretty, expected_execution_order, tj.execution_flow))
        return False

    expected_execution_order = \
        ['init', 'setup', 'pre', 'main', 'post', 'pre', 'main', 'post',
         'teardown']

    tj2._execute(nr_of_iterations=2)

    if expected_execution_order != tj2.execution_flow:
        print('FAIL %s: Expected Execution flow: %s differs from Actual %s' %
              (pretty, expected_execution_order, tj2.execution_flow))
        return False

    return True


def t5():
    """
    tests execution order with Exception
    """
    pretty = common.get_test_pretty()
    print(pretty)

    tj = TestJobExecutionOrderExceptionInPre()
    tj2 = TestJobExecutionOrderExceptionInSetup()

    expected_execution_order = \
        ['init', 'setup', 'pre', 'post', 'teardown']

    tj._execute()

    if expected_execution_order != tj.execution_flow:
        print('FAIL %s: Expected Execution flow: %s differs from Actual %s' %
              (pretty, expected_execution_order, tj.execution_flow))
        return False

    expected_execution_order = \
        ['init', 'setup', 'teardown']

    tj2._execute(nr_of_iterations=2)

    if expected_execution_order != tj2.execution_flow:
        print('FAIL %s: Expected Execution flow: %s differs from Actual %s' %
              (pretty, expected_execution_order, tj2.execution_flow))
        return False

    return True


def t6():
    """
    tests TestJob setup raising exception without override of
    equipment_assignment
    """
    pretty = common.get_test_pretty()
    print(pretty)

    job_profiles = [
        {'type': 'handset'},
        {'type': 'workspace'}
    ]
    vcsjob.set_profiles(job_profiles)

    tj = TestJob()

    try:
        tj.setup()
        print('FAIL %s: setup worked without overriding equipment_assignment'
              % pretty)
        return False
    except Exception, e:
        overridden_exp = 'Equipment_assignment function must be overridden'
        if not overridden_exp in str(e):
            print('FAIL %s: setup raised unexpected exception: %s while '
                  'expectingin to contain: %s' % (pretty, e, overridden_exp))
            return False

    return True


def t7():
    """
    tests TestJob setup
    """
    pretty = common.get_test_pretty()
    print(pretty)

    job_profiles = [
        {'type': 'handset'},
        {'type': 'workspace'}
    ]
    vcsjob.set_profiles(job_profiles)

    tj = TestJobWithEquipmentAllocation()

    try:
        tj.setup()
    except Exception, e:
        print('FAIL %s: setup raised unexpected exception: %s' % (pretty, e))
        return False

    try:
        print(tj.handset.profile['serial'])
    except Exception, e:
        print('FAIL %s: setup failed to allocate a handset, not possible to'
              ' read profile->serial: %s' % (pretty, e))
        return False

    try:
        print(tj.workspace.profile['pretty'])
    except Exception, e:
        print('FAIL %s: setup failed to allocate a workspace, not possible to'
              ' read profile->pretty: %s' % (pretty, e))
        return False

    return True
