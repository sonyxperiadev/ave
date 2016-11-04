# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

def smoke(fn):
    setattr(fn, 'smoke', True)
    return fn
