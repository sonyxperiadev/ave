import json
import traceback

import vcsjob
import setup

from ave.exceptions      import *
from ave.network.control import RemoteControl

# check that regular exceptions are re-raised as AveExceptions on the client
# side, with the .trace member set.
@setup.factory()
def t1(pretty, factory):
    ctrl = factory.make_control()
    try:
        ctrl.raise_plain_exception('Lorem ipsum dolor sit amet, etc')
        print('FAIL %s: exception not raised' % pretty)
        return False
    except AveException, e:
        if 'trace' not in e.details:
            print('FAIL %s: trace not set: %s' % (pretty, e))
            return False
        if e.details['trace'][0][2] != 'raise_plain_exception':
            print('FAIL %s: wrong trace: %s' % (pretty, e.details['trace']))
            return False

    return True

# check that ave exceptions are re-raised as AveExceptions on the client side,
# with the .trace member set.
@setup.factory()
def t2(pretty, factory):
    ctrl = factory.make_control()
    try:
        ctrl.raise_ave_exception({'message':'Lorem ipsum dolor sit amet'})
        print('FAIL %s: exception not raised' % pretty)
        return False
    except AveException, e:
        if 'trace' not in e.details:
            print('FAIL %s: trace not set: %s' % (pretty, e))
            return False
        if e.details['trace'][0][2] != 'raise_ave_exception':
            print('FAIL %s: wrong trace: %s' % (pretty, e.details['trace']))
            return False

    return True

# check AveException.format_trace()
@setup.factory()
def t3(pretty, factory):
    ctrl = factory.make_control()
    exc  = None

    try:
        ctrl.raise_ave_exception({'message':'Lorem ipsum dolor sit amet'}, 3)
        print('FAIL %s: exception not raised' % pretty)
        return False
    except AveException, e:
        exc = e

    try:
        text = exc.format_trace()
    except Exception, e:
        print('FAIL %s: could not format trace: %s' % (pretty, e))
        return False

    if len(text.split('self.raise_ave_exception')) != 4:
        print('FAIL %s: wrong trace length: %s' % (pretty, text))
        return False

    return True

# does the trace survive hops in a network?
@setup.factory()
def t4(pretty, factory):
    ctrl  = factory.make_control()
    proxy = factory.make_proxy(ctrl)

    try:
        proxy.raise_ave_exception({'message':'Lorem ipsum dolor sit amet'})
        print('FAIL %s: exception not raised' % pretty)
        return False
    except AveException, e:
        if 'proxied: ' not in e.details['message']:
            print('FAIL %s: exception not proxied: %s' % (pretty, e.details))
            return False
        if 'trace' not in e.details:
            print('FAIL %s: trace not set: %s' % (pretty, e))
            return False
        if e.details['trace'][0][2] != 'raise_ave_exception':
            print('FAIL %s: wrong trace: %s' % (pretty, e.details['trace']))
            return False

    return True

# test AveException.__str__() content
def t5():
    pretty = '%s t5' % __file__
    print(pretty)
    details = {
        'message': 'message1',
        'trace': [['module1', 0, 'method1', 'line code']]
    }
    expected = '''message1
Server side traceback:
  File "module1", line 0, in method1
    line code
'''
    try:
        raise AveException(details)
    except AveException, e:
        result = str(e)
        if result == expected:
            return True
    print('FAIL %s: unexpected exception content: %s' % (pretty, e))
    return False

# as t5 but without trace information in the exception
def t6():
    pretty = '%s t6' % __file__
    print(pretty)
    details = { 'message': 'message1' }
    expected = 'message1'

    try:
        raise AveException(details)
    except AveException, e:
        result = str(e)
        if result == expected:
            return True
    print('FAIL %s: unexpected AveException exception content.' % pretty)
    return False
