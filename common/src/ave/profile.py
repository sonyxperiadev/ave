# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import traceback

class Profile(dict):
    '''
    Profiles are essentially ``dict`` instances that implement ``__hash__()``,
    so that they can be used as indices into other dictionaries. AVE uses
    profiles to communicate information about allocatable resources.
    '''
    def __init__(self, values):
        self.update(values)

    def __hash__(self):
        raise Exception('Profile subclasses must implement __hash__()')

    @staticmethod
    def debug(fn):
        def decorator(self, *vargs, **kwargs):
            try:
                result = fn(self, *vargs, **kwargs)
                vargs = ', '.join(['%s' % str(v) for v in vargs])
                kwargs = ', '.join(
                    ['%s=%s' % (str(v), str(kwargs[v])) for v in kwargs]
                )
                print(
                    '%s.%s(%s, %s, %s) --> %s' % (
                        type(self).__name__, fn.__name__,
                        self, vargs, kwargs, str(result)
                     )
                )
                return result
            except Exception, e:
                traceback.print_exc()
                raise e
        return decorator

    def match(self, profile):
        '''
        Match this profile against another profile or a dictionary: Iterate
        over the keys in *profile* and check that *self* contains the same key
        with the same value.

        :arg profile: A *dict* or *Profile* instance.
        :returns: *True* if the matching succeeded, *False* otherwise.
        '''
        for p in profile:
            if p not in self:
                return False
            if profile[p] != self[p]:
                return False
        return True

    def minimize(self, profile=None):
        '''
        Return a copy of 'self' that contains the properties that are mandatory
        for the Profile subclass, plus the properties specified by *profile*.
        '''
        raise Exception('Profile subclasses must implement minimize()')

