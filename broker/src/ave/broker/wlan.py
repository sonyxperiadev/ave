# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

from ave.profile import Profile

class Wlan(object):

    def __init__(self, profile):
        raise Exception('INTERNAL ERROR: instantiating a dummy Wlan')


class WlanProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'wlan'

    def __hash__(self):
        return hash(self['uid'])

    def __eq__(self, other):
        if not ('uid' in self and 'uid' in other):
            return False
        return self['uid'] == other['uid']

    def __ne__(self, other):
        return not self.__eq__(other)

    def minimize(self, profile=None):
        r = {
            'type'       : 'wlan',
            'uid'        : self['uid']
        }
        if profile:
            r.update(profile)
        return WlanProfile(r)
