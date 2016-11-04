#!/usr/bin/python2

# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserv


from __future__ import print_function

import sys
import ave.utils.logger
from ave.utils.logger import Logger
import common
from ave.workspace import Workspace
from ave.broker import Broker
import uuid
import base64
import urllib2



#Redefining print to write to stderr instead because stdout is redirected to a
# tmp file
def print(string):
    sys.stderr.writelines("%s\n" % string)


def t1():
    pretty = common.get_test_pretty()
    print(pretty)

    b = Broker()
    w = b.get({'type':'workspace'})
    file_name = 'test.log'

    guid = common.generate_id()

    logger = Logger(w,guid,file_path=file_name)

    result = logger.log_it('i', 'Test')

    flocker_url = '%s/%s' % (logger.parse_flocker_data(result)[0], file_name)

    log_file = urllib2.urlopen(flocker_url)

    lines = []

    for line in log_file:
        lines.append(line)

    exp_data = [
        'Initiating Test Job Log in flocker',
        'Test'
    ]

    for i in range(len(exp_data)):
        if exp_data[i] not in lines[i]:
            print('FAIL %s: Unexpected first line in log: %s, expected text "%s" '
                  'not found.' % (pretty, lines[i], exp_data[i]))
            return False

    return True


def t2():
    pretty = common.get_test_pretty()
    print(pretty)

    b = Broker()
    w = b.get({'type':'workspace'})
    file_name = 'test.log'

    guid = base64.urlsafe_b64encode(uuid.uuid1().bytes).replace('=', '')

    logger = Logger(w,guid,file_path=file_name)

    # log to get url
    result = logger.log_it('i', '')

    logger.set_lowest_log_level('w')

    test_text = 'Test that should not be written to log'

    logger.log_it('i', test_text)

    flocker_url = '%s/%s' % (logger.parse_flocker_data(result)[0], file_name)

    log_file = urllib2.urlopen(flocker_url)

    for line in log_file:
        if test_text in line:
            print('FAIL %s: "%s" found in log when log level was to low' %
                  (pretty, test_text))
            return False

    return True


def t3():
    """
    Verifying that a temporary down flocker connection does not cause dropped
    log lines
    """
    pretty = common.get_test_pretty()
    print(pretty)

    b = Broker()
    w = b.get({'type':'workspace'})
    file_name = 'test.log'
    test_text = 'Log Line 2'

    guid = base64.urlsafe_b64encode(uuid.uuid1().bytes).replace('=', '')

    logger = MockLoggerFlockerDown(w, guid, file_path=file_name)

    logger.log_it('i', 'Log Line 1')
    logger.fail_flocker = True
    logger.log_it('i', test_text)
    result = logger.log_it('i', 'Log Line 3')
    logger.fail_flocker = False
    result = logger.log_it('i', 'Log Line 4')
    flocker_url = '%s/%s' % (logger.parse_flocker_data(result)[0], file_name)

    log_file = urllib2.urlopen(flocker_url)

    found = False
    for line in log_file:
        if test_text in line:
            found = True
    if not found:
        print('FAIL %s: "%s" not found in log, should have been saved while '
              'flocker was down' % (pretty, test_text))
        return False
    return True


def t4():
    """
    Verifying that Flocker log ling is shouted to panotti when flocker comes up
    if it is down at init
    """
    pretty = common.get_test_pretty()
    print(pretty)

    b = Broker()
    w = b.get({'type':'workspace'})
    file_name = 'test.log'
    test_text = 'http:'

    guid = base64.urlsafe_b64encode(uuid.uuid1().bytes).replace('=', '')

    logger = MockLoggerFlockerDown(w, guid, file_path=file_name,
                                   fail_flocker=True)

    logger.log_it('i', 'Log Line 1')
    logger.fail_flocker = False
    result = logger.log_it('i', 'Log Line 2')
    flocker_url = '%s/%s' % (logger.parse_flocker_data(result)[0], file_name)

    log_file = urllib2.urlopen(flocker_url)

    found = False
    for line in log_file:
        if test_text in line:
            found = True
    if not found:
        print('FAIL %s: "%s" not found in log, should have been saved while '
              'flocker was down' % (pretty, test_text))
        return False
    return True




class MockException(Exception):
    pass


class MockLoggerFlockerDown(Logger):
    def __init__(self, workspace, guid, file_path='test_job_log.txt',
                 lowest_level='x', fail_flocker=False):
        super(MockLoggerFlockerDown, self).__init__(workspace, guid, file_path,
                                                    lowest_level)
        self.fail_flocker = fail_flocker

    def _push_message(self, message):
        if not self.fail_flocker:
            return self.workspace.flocker_push_string(message,
                                                      self.file_path)
        else:
            raise MockException('Mocking Flocker down')


