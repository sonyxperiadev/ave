import os
import sys
import time
import signal

from ave.network.pipe       import Pipe
from ave.network.process    import Process
from ave.network.control    import Control, RemoteControl
from ave.network.connection import find_free_port

import setup

# make some controls that defy SIGTERM so that an ordinary join() would block
# forever. use join_later() to get them anyway.
@setup.factory()
def t1(pretty, factory):

    class Defiant(Control):

        def handle_SIGTERM(self, signum, frame):
            pass # go on living

        @Control.rpc
        def ping(self):
            return 'pong', self.pid

        @Control.rpc
        def stop(self):
            Control.stop(self)

    class Spawner(Control):
        children = None

        @Control.rpc
        def spawn(self):
            if not self.children:
                self.children = []
            sock,port = find_free_port()
            d = Defiant(port, None, sock)
            d.start()
            self.children.append(d)
            return [d.pid, port]

        @Control.rpc
        def orphanize(self):
            if not self.children:
                return None
            child, self.children = self.children[0], self.children[1:]
            child.terminate()
            self.join_later(child)

        @Control.rpc
        def list_orphans(self):
            return [p.pid for p in self.deferred_joins]

    sock,port = find_free_port()
    spawner = Spawner(port, None, sock)
    spawner.start()
    factory.processes.append(spawner)
    master = RemoteControl(('',port), None, 1)

    defiers = []
    for i in range(5):
        pid, port = master.spawn()
        remote = RemoteControl(('',port), None, 5)
        defiers.append(remote)

    orphans = master.list_orphans()
    if orphans:
        print('FAIL %s: there are orphans: %s' % (pretty, orphans))
        return False

    for i in range(5):
        master.orphanize()

    orphans = master.list_orphans()
    if len(orphans) != 5:
        print('FAIL %s: there are not 5 orphans: %s' % (pretty, orphans))
        return False

    for remote in defiers:
        try:
            remote.ping()
        except Exception, e:
            print('FAIL %s: orphan died too soon: %s' % (pretty, remote))
            return False
        remote.stop(__async__=True)

    for i in range(10):
        orphans = master.list_orphans()
        if not orphans:
            break
        time.sleep(0.3)
    if orphans:
        print('FAIL %s: some orphans survived: %s' % (pretty, orphans))
        return False

    return True

# variant of t1 with regular processes. the processes don't actually put up
# much of a fight but don't behave well either. termination is done from the
# test instead of the spawner process. also, the orphans are collected already
# when started.
@setup.factory()
def t2(pretty, factory):

    class Defiant(Process):

        def handle_SIGTERM(self, signum, frame):
            time.sleep(5) # very poor behavior
            Process.handle_SIGTERM(self, signum, frame)

        def run(self):
            while True:
                time.sleep(1)

    class Spawner(Control):

        @Control.rpc
        def spawn(self):
            pids = []
            for i in range(500):
                d = Defiant()
                d.start()
                self.join_later(d)
                pids.append(d.pid)
            return pids

        @Control.rpc
        def list_orphans(self):
            return [p._pid for p in self.deferred_joins]

    sock,port = find_free_port()
    spawner = Spawner(port, None, sock)
    spawner.start()
    factory.processes.append(spawner)
    master = RemoteControl(('',port), None, 5)

    defiers = master.spawn()
    for pid in defiers:
        os.kill(pid, signal.SIGTERM)

    orphans = master.list_orphans()
    if len(orphans) != 500:
        print('FAIL %s: there are not 500 orphans: %s' % (pretty, orphans))
        return False

    for pid in defiers:
        os.kill(pid, signal.SIGKILL)

    for i in range(10):
        orphans = master.list_orphans()
        if not orphans:
            break
        time.sleep(0.3)
    if orphans:
        print('FAIL %s: some orphans survived: %d' % (pretty, len(orphans)))
        return False

    return True

# do stupid shit like deferring the same process twice, unstarted processes and
# processes that are not children of the spawner.
@setup.factory()
def t3(pretty, factory):

    class Defiant(Process):

        def run(self):
            while True:
                time.sleep(1)

    class Spawner(Control):

        def __init__(self, port, sock, not_a_child):
            Control.__init__(self, port, None, sock, logging=False)
            self.deferred_joins = [not_a_child]

        def run(self):
            self.join_later(not_a_child)
            Control.run(self)

        @Control.rpc
        def spawn(self):
            pids = []
            for i in range(5):
                d = Defiant()
                d.start()
                self.join_later(d)
                self.join_later(d) # add twice
                pids.append(d.pid)
            return pids

        @Control.rpc
        def stillbirth(self):
            for i in range(5):
                d = Defiant()
                self.join_later(d) # forgot to start

        @Control.rpc
        def list_orphans(self):
            return [p._pid for p in self.deferred_joins]

    not_a_child = Defiant()
    not_a_child.start()

    sock,port = find_free_port()
    spawner = Spawner(port, sock, not_a_child)
    spawner.start()
    factory.processes.append(spawner)
    master = RemoteControl(('',port), None, 5)

    master.stillbirth()
    defiers = master.spawn()
    orphans = master.list_orphans()

    # by now the deferred join should already have weeded out the impossible
    # processes and discarded them. that leaves the 5 double adds (10 procs).

    if len(orphans) != 10:
        print('FAIL %s: there are not 10 orphans: %s' % (pretty, orphans))
        return False

    for pid in defiers:
        os.kill(pid, signal.SIGTERM)

    for i in range(10):
        orphans = master.list_orphans()
        if not orphans:
            break
        time.sleep(0.3)
    if orphans:
        print('FAIL %s: some orphans survived: %d' % (pretty, len(orphans)))
        return False

    return True
