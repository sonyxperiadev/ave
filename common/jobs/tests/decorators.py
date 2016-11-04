def smoke(fn):
    setattr(fn, 'smoke', True)
    return fn
