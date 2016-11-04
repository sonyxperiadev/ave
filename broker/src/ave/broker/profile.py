# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.profile             import Profile
from ave.handset.profile     import HandsetProfile
from ave.workspace           import WorkspaceProfile
from ave.base_workspace      import BaseWorkspaceProfile
from ave.relay.profile       import RelayProfile

try: # prefer profile from full installation, if available
    from ave.positioning.profile import TestDriveProfile
except: # use stub if positioning support is not installed
    from positioning import TestDriveProfile

try: # prefer profile from full installation, if available
    from ave.powermeter.profile  import PowermeterProfile
except: # use stub if powermeter support is not installed
    from powermeter import PowermeterProfile

try: # prefer profile from full installation, if available
    from ave.beryllium.profile import BerylliumProfile
except: # use stub if beryllium support is not installed
    from beryllium import BerylliumProfile

try: # prefer profile from full installation, if available
    from ave.wlan.profile import WlanProfile
except: # use stub if beryllium support is not installed
    from wlan import WlanProfile

class BrokerProfile(Profile):

    def __init__(self, values):
        try:    del values['authkeys']
        except: pass
        try:    del values['remote']['authkey']
        except: pass
        Profile.__init__(self, values)
        self['type'] = 'broker'

    def __hash__(self):
        return hash(id(self))

def profile_factory(profile):
    return factory(profile)

def factory(profile):
    if 'type' not in profile:
        raise Exception('profile "type" attribute is missing')
    if profile['type'] == 'workspace':
        return WorkspaceProfile(profile)
    if profile['type'] == 'handset':
        return HandsetProfile(profile)
    if profile['type'] == 'relay':
        return RelayProfile(profile)
    if profile['type'] == 'beryllium':
        return BerylliumProfile(profile)
    if profile['type'] == 'broker':
        return BrokerProfile(profile)
    if profile['type'] == 'testdrive':
        return TestDriveProfile(profile)
    if profile['type'] == 'wlan':
        return WlanProfile(profile)
    if profile['type'] == 'powermeter':
        return PowermeterProfile(profile)
    raise Exception('type %s not supported in profiles' % profile['type'])
