# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import json
import signal
import psutil
import socket
import traceback

from ave.broker._broker     import Broker, RemoteBroker
from ave.broker.resource    import RemoteHandset
from ave.broker.session     import RemoteSession
from ave.broker.profile     import *
from ave.handset.profile    import HandsetProfile
from ave.network.process    import Process
from ave.network.pipe       import Pipe
from ave.network.connection import Connection, find_free_port
from ave.workspace          import Workspace

import setup

# start/stop a couple of times to check that port numbers are released
@setup.factory()
def t1(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    sock, port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()

    for i in range(10):
        try:
            broker = Broker(('',port), home=factory.HOME.path)
            broker.start()
            remote = RemoteBroker(('',port), 5, 'admin_key', factory.HOME.path)
            remote.stop(__async__=True)
            broker.join()
        except Exception, e:
            print('FAIL %s: stopping broker %d failed: %s' % (pretty,i,str(e)))
            return False

    return True

# check that get_profile() work
@setup.brokers([], 'master', [], True, False)
def t2(HOME, r):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        profile = r.get_profile()
    except Exception, e:
        print('FAIL %s: get_version() failed: %s' % (pretty, str(e)))
        return False
    if 'type' not in profile or profile['type'] != 'broker':
        print('FAIL %s: profile "type" field is wrong: %s' % (pretty, profile))
        return False

    return True

# check that list_handsets() works
@setup.brokers([], 'master', [], True, False)
def t3(HOME, r):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        devs = r.list_handsets()
    except Exception, e:
        print('FAIL %s: list_handsets() failed: %s' % (pretty, str(e)))
        return False
    for d in devs:
        if not 'type' in d:
            print('FAIL %s: "type" field is missing: %s' % (pretty, d))
            return False
        if not 'vendor' in d:
            print('FAIL %s: "vendor" field is missing: %s' % (pretty, d))
            return False
        if not 'product' in d:
            print('FAIL %s: "product" field is missing: %s' % (pretty, d))
            return False
        if not 'serial' in d:
            print('FAIL %s: "serial" field is missing: %s' % (pretty, d))
            return False
        if not 'pretty' in d:
            print('FAIL %s: "pretty" field is missing: %s' % (pretty, d))
            return False

    return True

# check that get_resource() fails on profiles that lack mandatory attributes
@setup.brokers([], 'master', [], True, False)
def t4(HOME, r):
    pretty = '%s t4' % __file__
    print(pretty)

    try:
        d = r.get_resource({'the':'"type"', 'field':'is', 'missing':None})
        print('FAIL %s: get_resource() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('profile "type" field is missing'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check that get_resource() works
@setup.factory()
def t5(factory):
    pretty = '%s t5' % __file__
    print(pretty)

    r = factory.make_master('master')

    # take whatever handset is first in the list and request it
    try:
        devs = r.list_handsets()
        w, d = r.get_resource({'type':'workspace'}, devs[0])
    except Exception, e:
        print('FAIL %s: get_resource() failed: %s' % (pretty, str(e)))
        return False
    if type(d) != RemoteHandset:
        print('FAIL %s: wrong return type: %s' % (pretty, type(d)))
        return False
    
    # check that the same handset cannot be allocated twice
    try:
        w, d = r.get_resource({'type':'workspace'}, devs[0])
        print('FAIL %s: allocated same handset twice: %s' % (pretty, d))
        return False
    except Exception, e:
        if not str(e).startswith('all such equipment busy'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that yield_resources() works
@setup.brokers([], 'master', [], True, False)
def t6(HOME, r):
    pretty = '%s t6' % __file__
    print(pretty)

    # take whatever handset is first in the list and request it
    devs = r.list_handsets()
    d = r.get_resource(devs[0])

    # check that the handset can be yielded exactly once
    try:
        r.yield_resources(d)
    except Exception, e:
        print('FAIL %s: yield_resources() failed: %s' % (pretty, str(e)))
        return False
    try:
        r.yield_resources(d)
        print('FAIL %s: yield_resources() did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('no such resource'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# check that allocating and yielding a handset can be done over and over
@setup.brokers([], 'master', [], True, False)
def t7(HOME, r):
    pretty = '%s t7' % __file__
    print(pretty)

    # take whatever handset is first in the list and request/yield it repeatedly
    devs = r.list_handsets()
    for i in range(5):
        try:
            w,d = r.get_resource({'type':'workspace'}, devs[0])
            allocs = r.list_allocations()
            if len(allocs) != 2:
                print('FAIL %s: not two allocations: %s' % (pretty, allocs))
                return False
            r.yield_resources(d)
            allocs = r.list_allocations()
            if len(allocs) != 1:
                print('FAIL %s: not one allocation: %s' % (pretty, allocs))
                return False
            r.yield_resources(w)
        except Exception, e:
            print('FAIL %s: iteration %d failed: %s' % (pretty, i, str(e)))
            return False

    allocs = r.list_allocations()
    if len(allocs) != 0:
         print('FAIL %s: not zero allocations: %s' % (pretty, allocs))
         return False
    return True

# check that allocation of workspaces with particular tools works
@setup.brokers([], 'master', [], True, False)
def t8(HOME, r):
    pretty = '%s t8' % __file__
    print(pretty)

    w = r.get_resource({'type':'workspace', 'tools':['sleep']})
    p = w.get_profile()

    if 'tools' not in p:
        print('FAIL %s: workspace profile has no tools: %s' % (pretty, p))
        return False

    if 'sleep' not in p['tools']:
        print('FAIL %s: workspace lacks the requested tools' % (pretty))
        return False

    return True

# check that close_session() reclaims all resources allocated to the session.
# start a separate process where a client runs. allocate a couple of resources
# and then die. afterwards the resources should be freed.
@setup.factory()
def t9(factory):
    pretty = '%s t9' % __file__
    print(pretty)

    r = factory.make_master('master')

    class Client(Process):

        def close_fds(self, exclude):
            exclude.extend([self.args[0].w, self.args[1].r])
            Process.close_fds(self, exclude)

        def run(self, q1, q2, address, home):
            # take whatever handset is available
            r2 = RemoteBroker(address, home=home)
            try:
                w, d = r2.get_resource({'type':'workspace'}, {'type':'handset'})
            except Exception, e:
                print('FAIL %s: got no handset: %s' % (pretty, str(e)))
                return
            # use the queue to synchronize with parent process. send the
            # profiles of the allocated handsets so that it has something to
            # look up in the sessions held by the broker
            q1.put([
                w.get_profile(),
                d.get_profile()
            ])
            q2.get() # block until parent signals, then die

    q1 = Pipe()
    q2 = Pipe()
    p = Client(args=(q1, q2, r.address, factory.HOME.path))
    p.start()

    profiles = [profile_factory(prof) for prof in q1.get()]
    # check that the resources really are allocated
    listing = r.list_allocations_all()
    for resource in profiles:
        if resource not in listing:
            print('FAIL %s: resource not allocated: %s' % (pretty, resource))
            return False

    q2.put('DIE DIE DIE!')
    p.join() # wait for death

    # check that the resources are freed. no message is sent out when resources
    # are freed, so we'll just have to wait a little and hope the situation has
    # been handled by the time we look up allocations.
    time.sleep(1)
    listing = r.list_allocations_all()
    for resource in profiles:
        if resource in listing:
            print('FAIL %s: resource not freed: %s' % (pretty, resource))
            return False

    # double check that the handset is available again
    listing = r.list_handsets()
    if profiles[1] not in listing:
        print('FAIL %s: handset not freed: %s' % (pretty, listing))
        return False

    # double check that the workspace is deleted from persistent storage
    workspace_path = os.path.join(profiles[0]['root'], profiles[0]['uid'])
    if os.path.isdir(workspace_path):
        print(
            'FAIL %s: persistent storage for workspace not deleted: %s'
            % (pretty, workspace_path)
        )
        return False

    return True

# check that resources are reclaimed on unscheduled client death
@setup.factory()
def t10(factory):
    pretty = '%s t10' % __file__
    print(pretty)

    class Client(Process):

        def close_fds(self, exclude):
            exclude.append(self.args[1].w)
            Process.close_fds(self, exclude)

        def run(self, address, queue, home):
            r2 = RemoteBroker(address, home=home)
            # take whatever handset is available
            try:
                w, d = r2.get_resource({'type':'workspace'}, {'type':'handset'})
            except Exception, e:
                print('FAIL %s: got no handset: %s' % (pretty, str(e)))
                return
            # use the queue to synchronize with parent process. send the
            # profiles of the allocated handsets so that it has something to
            # look up in the sessions held by the broker
            queue.put([
                w.get_profile(),
                d.get_profile()
            ])
            while True:
                time.sleep(1) # block forever until parent SIGKILLs the client

    r = factory.make_master('master')
    q = Pipe()
    p = Client(args=(r.address, q, factory.HOME.path))
    p.start()

    profiles = [profile_factory(prof) for prof in q.get()]
    # check that the handset really is allocated
    try:
        r.get_resource(profiles[1])
    except Exception, e:
        if not str(e).startswith('all such equipment busy'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    os.kill(p.pid, signal.SIGKILL) # kill the client
    p.join() # wait for death

    # check that the resources are freed. no message is sent out when resources
    # are freed, so we'll just have to wait a little and hope the situation has
    # been handled by the time we look up allocations.
    time.sleep(1)
    listing = r.list_allocations_all()
    for resource in profiles:
        if resource in listing:
            print('FAIL %s: resource not freed: %s' % (pretty, resource))
            return False

    # double check that the handset is available again
    listing = r.list_handsets()
    if profiles[1] not in listing:
        print('FAIL %s: handset not freed: %s' % (pretty, listing))
        return False

    return True

# check that resources are reclaimed on RemoteBroker.__del__()
@setup.factory()
def t11(factory):
    pretty = '%s t11' % __file__
    print(pretty)

    class Client(Process):

        def close_fds(self, exclude):
            exclude.extend([self.args[1].w, self.args[2].r])
            Process.close_fds(self, exclude)

        def run(self, address, q1, q2, home):
            # get own interface to the broker. expect all client's resources to
            # get reclaimed when the interface gets garbage collected
            r2 = RemoteBroker(address, home=home)
            # take whatever handset is available
            try:
                w, d = r2.get_resource({'type':'workspace'}, {'type':'handset'})
            except Exception, e:
                print('FAIL %s: got no handset: %s' % (pretty, str(e)))
                return
            # use the queue to synchronize with parent process
            q1.put([
                w.get_profile(),
                d.get_profile()
            ])
            q2.get() # wait for one sync message before deleting RemoteBroker
            del(r2)# note that no implementation of RemoteBroker.__del__() is
            # needed because the held socket will be garbage collected and
            # closed anyway.
            q1.put('deleted the RemoteBroker')
            while True:
                time.sleep(1)

    r = factory.make_master('master')
    q1 = Pipe()
    q2 = Pipe()
    p = Client(args=(r.address, q1, q2, factory.HOME.path))
    p.start()

    profiles = [profile_factory(prof) for prof in q1.get()]
    # check that the handset really is allocated
    try:
        r.get_resource(profiles[1])
    except Exception, e:
        if not str(e).startswith('all such equipment busy'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    q2.put('this is just synchronization')
    q1.get() # throw away another sync message

    # check that the resources are freed. no message is sent out when resources
    # are freed, so we'll just have to wait a little and hope the situation has
    # been handled by the time we look up allocations.
    time.sleep(1)
    listing = r.list_allocations_all()
    for resource in profiles:
        if resource in listing:
            print('FAIL %s: resource not freed: %s' % (pretty, resource))
            return False

    # double check that the handset is available again
    listing = r.list_handsets()
    if profiles[1] not in listing:
        print('FAIL %s: handset not freed: %s' % (pretty, listing))
        return False

    os.kill(p.pid, signal.SIGKILL)
    return True

# check that resources are reclaimed on unscheduled session death. there isn't
# really a way to crash a session so we'll just stop it instead. that will not
# cause it to freely yield any resources, but all its connections will be lost.
# the broker should react on that and reclaim all the session's resources.
@setup.factory()
def t12(factory):
    pretty = '%s t12' % __file__
    print(pretty)

    class Client(Process):

        def close_fds(self, exclude):
            exclude.extend([self.args[1].w, self.args[2].r])
            Process.close_fds(self, exclude)

        def run(self, address, q1, q2, home):
            r2 = RemoteBroker(address, home=home)
            try: # take whatever handset is available
                w, d = r2.get_resource({'type':'workspace'}, {'type':'handset'})
            except Exception, e:
                print('FAIL %s: got no handset: %s' % (pretty, str(e)))
                return
            q1.put([ # use the queue to synchronize with parent the process
                WorkspaceProfile(w.get_profile()),
                HandsetProfile(d.get_profile())])
            q2.get() # wait for one sync message before stopping
            session = RemoteSession(w.address, w.authkey)
            session.stop(__async__=True)
            q1.put('stopped the session')
            while True:
                time.sleep(1)

    r = factory.make_master('master')
    q1 = Pipe()
    q2 = Pipe()
    p = Client(args=(r.address, q1, q2, factory.HOME.path))
    p.start()

    profiles = [profile_factory(prof) for prof in q1.get()]
    # check that the handset really is allocated
    try:
        r.get_resource(profiles[1])
    except Exception, e:
        if not str(e).startswith('all such equipment busy'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            os.kill(p.pid, signal.SIGKILL)
            return False

    q2.put('this is just synchronization')
    q1.get() # throw away another sync message

    # check that the resources are freed. no message is sent out when resources
    # are freed, so we'll just have to wait a little and hope the situation has
    # been handled by the time we look up allocations.
    for i in range(10):
        ok = True
        listing = r.list_allocations_all()
        for resource in profiles:
            if resource in listing:
                ok = False
        if ok:
            break
        time.sleep(0.3)
    if not ok:
        print('FAIL %s: resource not freed: %s' % (pretty, resource))
        os.kill(p.pid, signal.SIGKILL)
        return False

    # double check that the handset is available again
    listing = r.list_handsets()
    if profiles[1] not in listing:
        print('FAIL %s: handset not freed: %s' % (pretty, listing))
        os.kill(p.pid, signal.SIGKILL)
        return False

    os.kill(p.pid, signal.SIGKILL)

    return True

# check that broker detects stopped sessions even if the client still has a
# lingering connection to the session
@setup.brokers([], 'master', [], True, False)
def t13(HOME, r):
    pretty = '%s t13' % __file__
    print(pretty)

    r = RemoteBroker(r.address, home=HOME.path)
    h = r.get_resources({'type':'handset'})
    p = h.get_profile()
    s = RemoteSession(h.address, h.authkey)
    s.stop(__async__=True)

    ok = False
    for i in range(10):
        if p not in r.list_allocations_all():
            ok = True
            break
        time.sleep(1)
    if not ok:
        print('FAIL %s: handset still allocated' % pretty)
        return False

    return True

# check that the error message is correct when trying to allocate equipment
# that doesn't exist
@setup.brokers([], 'master', [], True, False)
def t14(HOME, r):
    pretty = '%s t14' % __file__
    print(pretty)

    try:
        h = r.get_resources({'type':'handset', 'pretty':'betty boop'})
        print('FAIL %s: allocation did not fail' % pretty)
        return False
    except Exception, e:
        if not str(e).startswith('no such resource'):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# check that the broker doesn't go into 100% CPU utilization when it closes a
# session (i.e. on client disconnect)
@setup.factory()
def t15(factory):
    pretty = '%s t15' % __file__
    print(pretty)

    ws_config = {
        'root'   : factory.HOME.path,
        'env'    : [],
        'tools'  : {},
        'flocker': {
            "ftp": {
                "password": "ftpuser",
                "store": "/srv/www/flocker",
                "port": 21,
                "timeout": 30,
                "user": "ftpuser"
            },
            "host": "cnbjlx20050",
            "enable" : True,
            "http": {
                "doc-root": "/srv/www",
                "port": 80
            }
        }
    }
    factory.write_config('workspace.json', json.dumps(ws_config))

    sock, port = find_free_port()
    # set remote explicitly to avoid reading config from disk
    broker = Broker(
        ('',port), sock, remote={}, authkeys={'admin':None}, hsl_paths=[],
        home=factory.HOME.path
    )
    broker.start()
    proc   = psutil.Process(broker.pid)
    remote = RemoteBroker(address=('',port), home=factory.HOME.path)

    l = remote.list_available() # just to make sure the connection is up
    del remote                  # client disconnects itself

    # check the CPU utilization of the broker through it's PID
    result = True
    for i in range(10):
        if 'get_cpu_percent' in dir(proc):
            load = proc.get_cpu_percent() * psutil.NUM_CPUS
        else:
            load = proc.cpu_percent() * psutil.cpu_count()
        if load > 90.0:
            print('FAIL %s: runaway CPU load: %f' % (pretty, load))
            result = False
            break
        time.sleep(0.3)

    broker.terminate()
    broker.join()

    return result

# check that keeping the broker busy doesn't cause dropped connections. this is
# a regression test against a bug that involved the POLLNVAL error condition on
# polling objects.
@setup.brokers([], 'master', [], True, False)
def t16(HOME, r):
    pretty = '%s t16' % __file__
    print(pretty)

    result = True
    for i in range(20):
        r2 = RemoteBroker(r.address, home=HOME.path)
        try:
            h = r2.get_resources({'type':'handset'})
        except Exception, e:
            print('FAIL %s: iteration %d failed: %s' % (pretty, i, str(e)))
            result = False
            break

    return result

# check that it is available to allocate workspace with wifi capable and
# handset together
@setup.brokers([], 'master', [], True, False)
def t17(HOME, r):
    pretty = '%s t17' % __file__
    print(pretty)

    try:
        w, h = r.get_resources({'type':'workspace', 'wifi-capable': True},
                               {'type':'handset'})
    except Exception, e:
        print('FAIL %s: allocation did failed: %s'  % (pretty, str(e)))
        return False
    if w.get_wifi_ssid() != 'ssid':
        print('FAIL %s: wifi ssid match failed' % pretty)
        return False
    if w.get_wifi_pw() != 'password':
        print('FAIL %s: wifi password match failed' % pretty)
        return False

    return True

#check that can allocate multi same type resources from local machine
@setup.brokers([], 'master', [], False, False)
def t18(HOME, r):
    pretty = '%s t18' % __file__
    print(pretty)

    try:
        h1, h2 = r.get(({'type':'handset'},),({'type':'handset'},))
        p1 = h1.get_profile()
        if p1['serial'] != 'master-1':
            print('FAIL %s: wrong local serial: %s' % (pretty, p1))
            return False

        p2 = h2.get_profile()
        if p2['serial'] != 'master-2':
            print('FAIL %s: wrong local serial: %s' % (pretty, p2))
            return False
    except Exception, e:
        print('FAIL %s: could not allocate two handsets at the same' % pretty)
        print e
        return False

    return True

#check that can allocate multi stacked resources from the local machine
@setup.brokers([], 'master', [], False, False)
def t19(HOME, r):
    pretty = '%s t19' % __file__
    print(pretty)

    try:
        h1, r1, w1, h2, r2, w2 = r.get(
            ({'type':'handset'},{'type':'relay'},{'type':'workspace'}),
            ({'type':'handset'},{'type':'relay'},{'type':'workspace'}))

        ph1 = h1.get_profile()
        pr1 = r1.get_profile()
        pw1 = w1.get_profile()
        ph2 = h2.get_profile()
        pr2 = r2.get_profile()
        pw2 = w2.get_profile()

        if ph1['type'] != 'handset' and 'master-' not in ph1['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph1))
            return False

        if pr1['type'] != 'relay' and 'master-' not in pr1['uid']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, pr1))
            return False

        if pw1['type'] != 'workspace':
            print('FAIL %s: wrong local allocation: %s' % (pretty, pw1))
            return False

        if ph2['type'] != 'handset' and 'master-' not in ph2['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph2))
            return False

        if pr2['type'] != 'relay' and 'master-' not in pr2['uid']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, pr2))
            return False

        if pw2['type'] != 'workspace':
            print('FAIL %s: wrong local allocation: %s' % (pretty, pw2))
            return False

    except Exception, e:
        print('FAIL %s: could not allocate multi stacked resources at the same' % pretty)
        return False

    return True

#check that can allocate stacked resource and separated resource from the local machine
@setup.brokers([], 'master', [], False, False)
def t20(HOME, r):
    pretty = '%s t20' % __file__
    print(pretty)

    try:
        h1, r1, w1, h2 = r.get(
            ({'type':'handset'},{'type':'relay'},{'type':'workspace'}),
            {'type':'handset'})

        ph1 = h1.get_profile()
        pr1 = r1.get_profile()
        pw1 = w1.get_profile()
        ph2 = h2.get_profile()

        if ph1['type'] != 'handset' and 'master-' not in ph1['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph1))
            return False

        if pr1['type'] != 'relay' and 'master-' not in pr1['uid']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, pr1))
            return False

        if pw1['type'] != 'workspace':
            print('FAIL %s: wrong local allocation: %s' % (pretty, pw1))
            return False

        if ph2['type'] != 'handset' and 'master-' not in ph2['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph2))
            return False

    except Exception, e:
        print('FAIL %s: could not allocate stacked resource and'
              ' separated resource at the same' % pretty)
        return False

    return True

#check that can allocate multi same resources from shared machine
@setup.factory()
def t21(factory):
    pretty = '%s t21' % __file__
    print(pretty)

    #the master does not have local resources
    master = factory.make_master('master', hsl_paths='Nothing')
    slave  = factory.make_share(master, 'slave', True)
    time.sleep(1)

    try:
        h1, r1, w1, h2 = master.get(
            ({'type':'handset'},{'type':'relay'},{'type':'workspace'}),
            {'type':'handset'})

        ph1 = h1.get_profile()
        pr1 = r1.get_profile()
        pw1 = w1.get_profile()
        ph2 = h2.get_profile()

        if ph1['type'] != 'handset' and 'slave-' not in ph1['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph1))
            return False

        if pr1['type'] != 'relay' and 'slave-' not in pr1['uid']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, pr1))
            return False

        if pw1['type'] != 'workspace':
            print('FAIL %s: wrong local allocation: %s' % (pretty, pw1))
            return False

        if ph2['type'] != 'handset' and 'slave-' not in ph2['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph2))
            return False

    except Exception, e:
        print('FAIL %s: could not allocate stacked resource and'
              ' separated resource at the same' % pretty)
        print e
        return False

    return True

@setup.brokers(['forwarder'], 'master', [], True, False)
def t22(HOME, master, forwarder):
    pretty = '%s t22' % __file__
    print(pretty)

    # try to get pretty:mary twice from the local broker. the first should be
    # locally allocated, the second should be remotely allocated.
    h1, h2 = forwarder.get(({'type':'handset', 'pretty':'mary'},),
                           ({'type':'handset', 'pretty':'mary'},))

    p1 = h1.get_profile()
    if p1['serial'] != 'forwarder-1':
        print('FAIL %s: wrong local serial: %s' % (pretty, p1))
        return False

    p2 = h2.get_profile()
    if p2['serial'] != 'master-1':
        print('FAIL %s: wrong remote serial: %s' % (pretty, p2))
        return False

    return True

#check that can allocate stacked resource
@setup.brokers([], 'master', [], False, False, stacking='multi-messy')
def t23(HOME, r):
    pretty = '%s t23' % __file__
    print(pretty)

    try:
        h1, r1, h2, w1 = r.get({'type':'handset'},{'type':'relay'},
                               {'type':'handset'}, {'type':'workspace'})

        ph1 = h1.get_profile()
        pr1 = r1.get_profile()
        ph2 = h2.get_profile()
        pw1 = w1.get_profile()

        if ph1['type'] != 'handset' and 'master-' not in ph1['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph1))
            return False

        if pr1['type'] != 'relay' and 'master-' not in pr1['uid']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, pr1))
            return False

        if ph2['type'] != 'handset' and 'master-' not in ph2['serial']:
            print('FAIL %s: wrong local allocation: %s' % (pretty, ph2))
            return False

        if pw1['type'] != 'workspace':
            print('FAIL %s: wrong local allocation: %s' % (pretty, pw1))
            return False

    except Exception, e:
        print('FAIL %s: could not allocate stacked resource and'
              ' separated resource at the same' % pretty)
        return False

    return True

#check that cannot allocate non-stacked resource
@setup.brokers([], 'master', [], False, False, stacking='clean')
def t24(HOME, r):
    pretty = '%s t24' % __file__
    print(pretty)

    try:
        r.get({'type':'handset'},{'type':'relay'}, {'type':'handset'}, {'type':'workspace'})
        print('FAIL %s: allocate non-stacked resource and'
              ' separated resource at the same' % pretty)
        return False

    except Exception, e:
        if 'cannot allocate all equipment together' in str(e):
            return True
        else:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    return True