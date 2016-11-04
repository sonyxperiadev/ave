import os
import json

def set_profiles(profiles):
    if profiles == None:
        try:
            del os.environ['VCSJOB_PROFILES']
        except KeyError:
            pass
        return
    if type(profiles) != list:
        raise Exception('profiles must be a list of dictionaries: %s' %profiles)
    for p in profiles:
        if type(p) == dict:
            if 'type' not in p:
                raise Exception('"type" field is missing in profile": %s' % p)
            if type(p['type']) not in [str, unicode]:
                raise Exception('"type" field is not a string: %s' % p)
        elif type(p)  == list:
            for a in p:
                if 'type' not in a:
                    raise Exception('"type" field is missing in profile": %s' % a)
                if type(a['type']) not in [str, unicode]:
                    raise Exception('"type" field is not a string: %s' % a)
        else:
            raise Exception('profile is not a dictionary or list : %s' % p)
    os.environ['VCSJOB_PROFILES'] = json.dumps(profiles).encode('utf-8')

def get_profiles():
    # load the profiles
    if 'VCSJOB_PROFILES' in os.environ:
        env = os.environ['VCSJOB_PROFILES'].decode('utf-8')
        profiles = json.loads(env)
        multi_profiles = []

        for p in profiles:
            if type(p) == list:
                multi_profiles.append(tuple(p))
            else:
                multi_profiles.append(p)

    else:
        raise Exception('no profiles set')
    return multi_profiles
