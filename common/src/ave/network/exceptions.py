# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.exceptions import *

class ConnectionClosed(Exception):
    '''
    The connection was closed.
    '''
    def __init__(self, msg='connection closed'):
        Exception.__init__(self, msg)

class ConnectionTimeout(Exception):
    '''
    The connection timed out. I.e. no traffic could be read from, or written
    to, the conncetion within the time limit that had been set to govern all
    functions on the connection.
    '''
    def __init__(self, msg='timed out'):
        Exception.__init__(self, msg)

class ConnectionRefused(Exception):
    '''
    A connection could not be established because the other end refused it.
    '''
    def __init__(self, msg='connection refused'):
        Exception.__init__(self, msg)

class ConnectionInProgress(Exception):

    def __init__(self, msg='connection in progress'):
        Exception.__init__(self, msg)

class ConnectionAgain(Exception):

    def __init__(self, msg='connection again'):
        Exception.__init__(self, msg)

class ConnectionReset(Exception):

    def __init__(self, msg='connection reset'):
        Exception.__init__(self, msg)

# process exceptions

class Unstarted(Exception):
    pass

class Unwaitable(Exception):
    pass

class Unjoinable(Exception):
    pass

class Unknown(Exception):
    pass



# to be removed

class RemoteTimeout(Timeout):
    '''DEPRECATED, DO NOT USE. Prefer Timeout exception'''
    pass

class RemoteExit(Exit):
    '''DEPRECATED, DO NOT USE. Prefer Exit exception.'''
    pass

class RemoteAuthError(AuthError):
    '''DEPRECATED, DO NOT USE. Prefer AuthError exception'''
    pass

class RemoteRunError(RunError):
    '''DEPRECATED, DO NOT USE. Prefer RunError exception'''
    pass
