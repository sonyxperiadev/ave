from ave.profile import Profile

class TestDriveProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'testdrive'

    def __hash__(self):
        return hash('testdrive') ^ hash(self['uid'])

    def __eq__(self, other):
        if not ('uid' in self and 'uid' in other):
            return False
        return self['uid'] == other['uid']

    def __ne__(self, other):
        return not self.__eq__(other)

    def minimize(self, profile=None):
        r = {
            'type'   : 'testdrive',
            'uid'    : self['uid'],
            'vendor' : 'spirent'
        }
        if profile:
            r.update(profile)
        return TestDriveProfile(r)

    def match(self, other):
        return Profile.match(self, other)

class TestDrive(object):
    profile = None

    def __init__(self, profile, home=None):
        self.profile = profile
        self.home = home

    def get_profile(self):
        return self.profile