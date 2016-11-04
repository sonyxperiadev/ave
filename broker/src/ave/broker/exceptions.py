# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.exceptions import AveException

class BrokerException(AveException):
    def __init__(self, details):
        if type(details) in [str,unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class Busy(BrokerException):
    pass

class NoSuch(BrokerException):
    pass

class Shared(BrokerException):
    def __init__(self, details=''):
        BrokerException(details)

class Duplicate(BrokerException):
    pass

class NotOwner(BrokerException):
    pass

class NotAllocated(BrokerException):
    pass

def exception_factory(e):
    if not isinstance(e, AveException):
        raise Exception('not an AveException: %s' % e)
    if e.type == 'Busy':
        return Busy(e.details)
    if e.type == 'NoSuch':
        return NoSuch(e.details)
    if e.type == 'Shared':
        return Shared(e.details)
    if e.type == 'Duplicate':
        return Duplicate(e.details)
    if e.type == 'NotOwner':
        return NotOwner(e.details)
    if e.type == 'NotAllocated':
        return NotAllocated(e.details)
    return e
