# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.profile import Profile

class BoardProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'board'

    def __hash__(self):
        return hash(self['serial'])

    def __eq__(self, other):
        if not ('serial' in self and 'serial' in other):
            return False
        return self['serial'] == other['serial']

    def match(self, other):
        if other['type'] != 'board':
            return False
        for key in other.keys():
            if key not in self or other[key] != self[key]:
                return False
        return True

class RelayProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'relay'

    def __hash__(self):
        return hash(self['uid'])

    def __eq__(self, other):
        if not ('uid' in self and 'uid' in other):
            return False
        return self['uid'] == other['uid']

    def __ne__(self, other):
        return not self.__eq__(other)

#    @Profile.debug
    def match(self, other):
        if other['type'] != 'relay':
            return False
        if ('uid' in other) and self['uid'] != other['uid']:
            return False
        if 'circuits' in other:
            if 'circuits' not in self:
                return False
            for c in other['circuits']:
                if c not in self['circuits']:
                    return False
        return True

    def minimize(self, profile=None):
        r = {
            'type'    : 'relay',
            'uid'     : self['uid'],
            'circuits': {}
        }
        if profile:
            for p in profile:
                if p == 'circuits':
                    for circuit in profile['circuits']:
                        r['circuits'][circuit] = self['circuits'][circuit]
                else:
                    r[p] = self[p]
        return RelayProfile(r)
