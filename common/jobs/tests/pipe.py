from ave.network.pipe       import Pipe
from ave.network.exceptions import *

# does .get(timeout=0) time out immediately if when there are no more messages?
def t01():
    pretty = '%s t01' % __file__
    print(pretty)

    p = Pipe()
    p.put('hello')

    try:
        msg = p.get(timeout=0)
    except Exception, e:
        print('FAIL %s: first get() failed: %s' % (pretty, e))
        return False

    try:
        msg = p.get(timeout=0)
    except ConnectionTimeout:
        pass # good
    except Exception, e:
        print('FAIL %s: second get() failed: %s' % (pretty, e))
        return False

    return True
