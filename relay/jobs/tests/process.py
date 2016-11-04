import time
import traceback

from ave.network.connection import find_free_port
from ave.relay.lister       import RelayLister
from ave.relay.reporter     import Reporter
from ave.relay.server       import RelayServer

import setup

@setup.factory()
def t3(pretty, factory):
    try:
        l = RelayLister(0, None, False)
    except Exception, e:
        print('FAIL %s: could not create lister: %s' % (pretty, e))
        return False

    try:
        l.start()
    except Exception, e:
        print('FAIL %s: could not start lister: %s' % (pretty, e))
        return False

    try:
        l.terminate()
    except Exception, e:
        print('FAIL %s: could not terminate lister: %s' % (pretty, e))
        return False

    try:
        l.join()
    except Exception, e:
        print('FAIL %s: could not join lister: %s' % (pretty, e))
        return False

    return True

@setup.factory()
def t4(pretty, factory):
    try:
        r = Reporter(factory.HOME.path, False, [], 1)
    except Exception, e:
        print('could not create reporter: %s' % (pretty, e))
        return False

    try:
        r.start(daemonize=True)
    except Exception, e:
        print('FAIL %s: could not daemonize reporter: %s' % (pretty, e))
        return False

    try:
        r.terminate()
        print('FAIL %s: could terminate reporter' % (pretty, e))
        return False
    except Exception, e:
        pass

    time.sleep(1)

    return True

@setup.factory()
def t5(pretty, factory):
    factory.write_config('authkeys.json', setup.AUTHKEYS)
    broker = factory.make_broker()
    sock,port = find_free_port()
    factory.write_config('relay.json', {'port':port, 'logging':False})

    try:
        s = RelayServer(factory.HOME.path, None, None, sock)
    except Exception, e:
        print('could not create server: %s' % (pretty, e))
        return False

    try:
        s.start()
    except Exception, e:
        print('FAIL %s: could not start server: %s' % (pretty, e))
        return False

    time.sleep(2)

    try:
        s.terminate()
    except Exception, e:
        print('FAIL %s: could not terminate server: %s' % (pretty, e))
        return False

    try:
        s.join()
    except Exception, e:
        print('FAIL %s: could not join server: %s' % (pretty, e))
        return False

    return True
