# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import re
import os
import shutil
import random
import httplib
from datetime import datetime
from datetime import timedelta

from ave.workspace import Workspace

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'testdata')

def generate_report(pretty, json_file):
    '''
    Generates a report from a static JSON result file
    '''
    # setup workspace
    ws = Workspace('test-files-marionette')
    ws_json_file = os.path.join(ws.make_tempdir(), json_file)
    # copy static json result file to workspace
    shutil.copyfile(os.path.join(TEST_DATA_PATH, json_file), ws_json_file)
    # create a random test name for decibel
    buff = []
    for i in range(10):
        buff.append(random.randint(0,9))
    name = ''.join(['%d' % i for i in buff])
    # create time stamp for report
    time = datetime.now()
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    end_time = (time + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    # try to generate report.

    # delete workspace.
    ws.delete()
    # check if decibel reported 200 (ok) in response.

    return name, start_time, end_time

def t01():
    '''
    Test that tries to send a passed marionette test to decibel.
    '''
    pretty = '%s t01' % __file__
    print(pretty)
    generate_report(pretty, 'passed.json')
    return True

def t02():
    '''
    Test that tries to send a failed marionette test to decibel.
    '''
    pretty = '%s t02' % __file__
    print(pretty)
    generate_report(pretty, 'failed.json')
    return True

def t03():
    '''
    Test that tries to send a erroneous marionette test to decibel.
    '''
    pretty = '%s t03' % __file__
    print(pretty)
    generate_report(pretty, 'error.json')
    return True

def t04():
    '''
    Test that tries to send a marionette test result wih multiple
    results to decibel.
    '''
    pretty = '%s t04' % __file__
    print(pretty)
    generate_report(pretty, 'multi_result.json')
    return True

def t05():
    '''
    This test verifies that the report stored at decibel is readable and
    contains the same data as the report sent from ave.
    '''
    pretty = '%s t05' % __file__
    print(pretty)
    # generate the report from static test data. name, start and end
    # values are used later in this test for verification.
    name, start, end,  = generate_report(pretty, 'passed.json')

    # read the run ID from the url entry in the response. this id is used for
    # retreiving the correct report from decibel when verifying the report
    # content.

    # setup request data.

    path = '/api/test-results/v1/search/'
    projection = '?projection=software,hardware,start,end,name'

    return True
