# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

def smoke(fn):
    setattr(fn, 'smoke', True)
    return fn


def with_workspace(fn):
    from ave.workspace import Workspace
    def decorated_fn():
        w = Workspace()
        try:
            result = fn(w)
            return result
        except Exception:
            raise
        finally:
            w.delete()
    return decorated_fn
