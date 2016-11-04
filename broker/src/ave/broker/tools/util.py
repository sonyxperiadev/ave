# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import traceback

def trace(fn):
    def decorator(self, *vargs, **kwargs):
        try:
            return fn(self, *vargs, **kwargs)
        except Exception, e:
            traceback.print_exc()
            raise e
    return decorator
