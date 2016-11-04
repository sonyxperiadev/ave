# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import traceback

# install an exception hook that prints an uncaught exception with the previous
# hook, and also prints the server side trace in case of an AveException that
# has a trace attached.
# do like this to use the exception hook. useful in development of AVE servers:
# sys.excepthook = ave.exceptions.amend_excepthook(sys.excepthook)
def amend_excepthook(hook):
    def ave_excepthook(cls, exc, tb):
        hook(cls, exc, tb) # always run original hook
        # if the exception is an AveException with a trace, then print it too
        if isinstance(exc, AveException) and exc.has_trace():
            sys.stderr.write('\nAVE server side exception trace:\n')
            exc.print_trace()
    return ave_excepthook


class AveException(Exception):
    details = None # {<string>:<base type>, ...}

    def __init__(self, details):
        if not type(details) == dict:
            raise Exception('AveException details must be a dictionary')
        for key in details:
            if type(key) not in [str, unicode]:
                raise Exception('AveException detail keys must be strings')
        if 'message' not in details:
            raise Exception('AveException details must have message field')
        if 'type' not in details:
            details['type'] = type(self).__name__
        self.details = details

    def __str__(self):
        message = self.message.encode('utf8')
        trace   = self.format_trace()
        if trace:
            trace = trace.encode('utf8')
            return '%s\nServer side traceback:\n%s' % (message, trace)
        return message

    def __getattr__(self, attribute):
        return self.details[attribute]

    # this property is needed to silence a BaseException deprecation warning
    @property
    def message(self):
        return self.details['message']

    def json(self):
        return self.details

    def has_trace(self):
        return 'trace' in self.details and self.trace != None

    def format_trace(self):
        if self.has_trace():
            # convert trace entries back to tuples. the trace member was
            # set by the server side rpc mechanism. rpc messages cannot
            # contain tuples (incompatible with JSON) so the entries were
            # converted to lists.
            convert = []
            for entry in self.trace:
                convert.append(tuple(entry))
            formatted = traceback.format_list(convert)
            return ''.join(formatted)
        return ''

    def print_trace(self):
        sys.stderr.write(self.format_trace())
        sys.stderr.flush()

class Timeout(AveException):
    '''
    Indicates that an operation timed out.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class Exit(AveException):
    '''
    Indicates that an operation could not be performed because the hosting
    service (e.g the broker) has terminated in a controlled manner.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class AuthError(AveException):
    '''
    Used internally in the client/broker, client/session, and other ``Control``
    based handshakes.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class RunError(AveException):
    '''
    Indicates that an externally called tool has failed.

    :arg cmd: The command that was passed to ``ave.cmd.run()``.
    :arg out: The output that was produced by the call.
    :arg message: A free form text message.
    '''
    def __init__(self, cmd, out, message=''):
        details = {
            'cmd'    : cmd     or '',
            'ptyout' : out     or '', # OBSOLESCENT. prefer RunError.out
            'out'    : out     or '',
            'message': message or ''
        }
        AveException.__init__(self, details)

    def __str__(self):
        return '%s:\n%s:\n%s' % (
            self.cmd, self.message.encode('utf8'), self.out.encode('utf8')
        )

class Restarting(AveException):
    '''
    Indicates that an operation could not be performed because the hosting
    service (e.g the broker) has restarted and is no longer accepting new calls
    to the old instance.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class Terminated(AveException):
    '''
    Indicates that a background activity has terminated. Background activities
    are typically long running processes, such as flashing a handset or making
    a flashable image, that AVE starts in the background and lets the client
    poll for completion.

    :arg details: A dictionary with activity specific entries. Must contain a
        "message" entry (a string). *details* may also be be a string in which
        case it will be treated as a dictionary with a "message" entry.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class Offline(AveException):
    '''
    Indicates that an handset is offline.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class CompositionServerResponseNot200Exception(AveException):
    '''
    Indicates that the response code of composition server was not 200

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class CompositionServerResponseHttpRetryCode(AveException):
    '''
    Indicates that the request was failed as composition server issue, user should
    try to request again. Retry HTTP codes:
        502,  # Bad Gateway
        503,  # Service (temporarily) unavailable
        504   # Gateway timeout

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class CompositionServerResponseOrderFailed(AveException):
    '''
    Indicates that the result of order composition was failed.

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

class CompositionDownloadImagesFailed(AveException):
    '''
    Indicates that the composition was failed when downloading images

    :arg details: A free form text message.
    '''
    def __init__(self, details):
        if type(details) in [str, unicode]:
            details = {'message': details}
        AveException.__init__(self, details)

def exception_factory(details):
    if type(details) != dict:
        details = {'message':details}
    if 'type' not in details:
        details['type'] = 'Exception'
    if details['type'] == 'Timeout':
        return Timeout(details)
    if details['type'] == 'Exit':
        return Exit(details)
    if details['type'] == 'AuthError':
        return AuthError(details)
    if details['type'] == 'RunError':
        return RunError(details['cmd'], details['out'], details['message'])
    if details['type'] == 'Restarting':
        return Restarting(details)
    if details['type'] == 'Terminated':
        return Terminated(details)
    if details['type'] == 'OverflowError':
        return OverflowError(details['message'])
    if details['type'] == 'Offline':
        return Offline(details)
    return AveException(details)
