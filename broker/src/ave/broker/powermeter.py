# Copyright (C)  Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.


from ave.profile import Profile


class Powermeter(object):

    def __init__(self, profile):
        raise Exception('INTERNAL ERROR: instantiating a dummy Powermeter')

class PowermeterProfile(Profile):

    def __init__(self, values):
        if ('type' not in values) or (values['type'] != 'powermeter'):
            raise Exception('invalid powermeter profile values: %s' % values)
        Profile.__init__(self, values)

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
            'type'       : 'powermeter',
            'uid'        : self['uid'],
            'product'    : self['product'],
            'device_node': self['device_node']
        }
        if profile:
            r.update(profile)
        return PowermeterProfile(r)