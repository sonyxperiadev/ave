def smoke(fn):
    setattr(fn, 'smoke', True)
    return fn

def test_by_assertion(f):
    from functools import wraps
    import sys, traceback
    @wraps(f)
    def decorated(*args, **kwargs):
        if not __debug__:
            raise Exception("Assertions are not enabled!")
        pretty = '%s %s' % (f.func_code.co_filename, f.func_name)
        print pretty
        try:
            retval = f(*args, **kwargs)
            if retval is None:
                return True
            assert retval, 'Test returned %s' % str(retval)
            return retval
        except AssertionError as e:
            msg = str(e).strip()
            if not msg:
                _,_,tb = sys.exc_info()
                _,_,_,msg = traceback.extract_tb(tb)[-1]
            print 'FAIL %s: %s' % (pretty, msg)
        except Exception as e:
            print 'FAIL %s:' % pretty
            traceback.print_exc()
        except BaseException as e:
            print 'ABORTED %s: %s' % (pretty, str(e))
            raise # re-raise
        return False
    return decorated
