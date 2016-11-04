# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from ave.relay.devantech import DevantechBoard

class RelayBoard(object):

    def __new__(cls, profile, *argv, **kwargs):
        if profile['vendor'] == 'devantech':
            return DevantechBoard(profile, *argv, **kwargs)
        if profile['vendor'] == 'quancom':
            try:
                from ave.relay.quancom import QuancomBoard
                return QuancomBoard(profile, *argv, **kwargs)
            except:
                # This exception should never happen
                Exception('QuancomBoard module not installed.')
        raise Exception('unknown relay board: %s' % profile)
