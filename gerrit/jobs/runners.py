import sys

import vcsjob

import tests.events
import tests.review

from ave.gerrit       import events
from ave.network.pipe import Pipe

def all_events():
    res = True
    res &= tests.events.t1()
    res &= tests.events.t2()
    return res

def all_review():
    res = True
    res &= tests.review.t1()
    res &= tests.review.t2()
    res &= tests.review.t3()

    gerrit_listener_pipe = Pipe()
    gerrit_listener = events.GerritEventStream(pipe=gerrit_listener_pipe)
    gerrit_listener.start()

    res &= tests.review.t4(gerrit_listener)
    res &= tests.review.t5(gerrit_listener)
    res &= tests.review.t6(gerrit_listener)

    gerrit_listener.terminate()
    gerrit_listener.join()
    return res

def all_smoke():
    res = True
    res &= all_events()
    res &= all_review()

    if not res:
        sys.exit(vcsjob.FAILURES)
    sys.exit(vcsjob.OK)
