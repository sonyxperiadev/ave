# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.profile import Profile


class Beryllium(object):

    def __init__(self, profile):
        raise Exception('INTERNAL ERROR: instantiating a dummy Beryllim rig')


class BerylliumProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'beryllium'

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
            'type'       : 'beryllium',
            'uid'        : self['uid']
        }
        if profile:
            r.update(profile)
        return BerylliumProfile(r)
