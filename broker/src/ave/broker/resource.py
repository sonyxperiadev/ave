# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.broker.session import RemoteSession

class RemoteWorkspace(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'workspace':
            raise Exception('not a workspace profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemoteHandset(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'handset':
            raise Exception('not a handset profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemotePowermeter(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'powermeter':
            raise Exception('not a powermeter profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemoteRelay(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'relay':
            raise Exception('not a relay profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemoteTestDrive(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'testdrive':
            raise Exception('not a testdrive profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemoteBeryllium(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'beryllium':
            raise Exception('not a beryllium profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)

class RemoteWlan(RemoteSession):

    def __init__(self, address, authkey, profile):
        if not profile['type'] == 'wlan':
            raise Exception('not a wlan profile: %s' % profile)
        RemoteSession.__init__(self, address, authkey, profile)
