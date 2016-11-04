# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from adb_handset     import AdbHandset
from android_handset import AndroidHandset
import importlib

def _cfg_find_subclass(vendorid):
    try:
        from ave.handset.lister import merge_handset_config
        config = merge_handset_config()['vendors'][0]
        if vendorid in config:
            subclass = config[vendorid]
            module = importlib.import_module("ave.handset."+subclass.split('.')[0])
            return getattr(module, subclass.split('.')[1])
        return None
    except Exception:
        raise Exception('ERROR: cant find subclass')


class Handset(object):

    def __new__(cls, profile, **kwargs):
        if ('platform' not in profile) or (profile['platform'] == 'adb'):
            return AdbHandset(profile, **kwargs)
        if profile['platform'] == 'android':
            if 'usb.vid' in profile:
                subclass = _cfg_find_subclass(profile['usb.vid'])
                if subclass:
                    return subclass(profile, **kwargs)
                return AndroidHandset(profile, **kwargs)
            else:
                return AndroidHandset(profile, **kwargs)

        raise Exception('ERROR: executed Handset.__init__() unreachable code')
