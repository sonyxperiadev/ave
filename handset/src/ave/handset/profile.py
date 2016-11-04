# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.profile import Profile

class HandsetProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'handset'

    def __hash__(self):
        return hash(self['serial'])

    def __eq__(self, other):
        if not ('serial' in self and 'serial' in other):
            return False
        return self['serial'] == other['serial']

    def __ne__(self, other):
        return not self.__eq__(other)

    # TODO: remove product which is not in the profile for offline equipment

    def minimize(self, profile=None):
        r = {
            'type'       : 'handset',
            'serial'     : self['serial'],
            'sysfs_path' : self['sysfs_path'],
            'pretty'     : self['pretty'],
            'power_state': self['power_state'],
            'product.model':self['product.model'],
            'workstation':self['workstation']
        }
        if 'platform' in self:
            r['platform'] = self['platform']
        if 'usb.vid' in self:
            r['usb.vid'] = self['usb.vid']
        if profile:
            r.update(profile)
        return HandsetProfile(r)

