#coding=utf8

# Copyright (C) 2013-2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import time
import json
import signal

import ave.cmd

from ave.exceptions         import *
from ave.network.exceptions import *
from ave.network.connection import find_free_port
from ave.network.control    import Control, RemoteControl
from ave.network.pipe       import Pipe
from ave.network.process    import Process
from ave.workspace          import Workspace
from ave.panotti            import PanottiControl

class MockControl(Control):
    pipe   = None # used to shortcut communication in the tests
    proxee = None

    def __init__(self, port, authkey, socket, alt_keys=[], pipe=None,
        interval=None, proxee=None, home=None, max_tx=-1):
        Control.__init__(self, port, authkey, socket, alt_keys, interval, home)
        self.pipe   = pipe
        self.proxee = proxee
        self.max_tx = max_tx

    def run(self):
        Control.run(self)

    def shutdown(self, details=None):
        Control.shutdown(self, details)

    def close_fds(self, exclude):
        if self.pipe:
            exclude.append(self.pipe.w)
        Control.close_fds(self, exclude)

    def lost_connection(self, connection, authkey):
        if self.pipe:
            self.pipe.put(connection.address)

    def idle(self):
        if self.pipe:
            self.pipe.put('idle')

    def shutdown(self):
        if self.pipe:
            self.pipe.put('shutdown')
        Control.shutdown(self)

    @Control.rpc
    def sync_ping(self, alt=None):
        return alt or 'pong'

    @Control.rpc
    def async_ping(self):
        if self.pipe:
            self.pipe.put('pong')

    @Control.rpc
    def stop(self):
        Control.stop(self)

    @Control.rpc
    def raise_plain_exception(self, message):
        raise Exception(message)

    @Control.rpc
    def raise_ave_exception(self, details, depth=0):
        if self.proxee:
            details['message'] = 'proxied: ' + details['message']
            self.proxee.raise_ave_exception(details, depth)
        if depth > 0:
            self.raise_ave_exception(details, depth-1)
        raise AveException(details)

    @Control.rpc
    def raise_exit(self, msg='passed to client'):
        raise Exit(msg)

    @Control.rpc
    def raise_timeout(self):
        ave.cmd.run('sleep 10', timeout=1)

    @Control.rpc
    def raise_run_error(self):
        ave.cmd.run(['no_such_exe'])

    @Control.rpc
    def run_external(self, cmd):
        return ave.cmd.run(cmd)

    @Control.rpc
    def connect_remote(self, address, password):
        if type(password) == unicode:
            password = str(password)
        # bind control to self to prevent garbage collection
        self.outbound = RemoteControl(tuple(address), password, 1)
        self.add_connection(self.outbound.connect(1), password)
        return self.outbound.sync_ping()

    @Control.rpc
    def mock_death(self):
        # try to keep Control sockets open after process death by spawning a
        # subprocess and then commit suicide, using SIGKILL. the observable
        # behavior (when this works) is that the call to mock_death() never
        # returns to the client because no answer is sent (the process is dead)
        # while its open sockets keep lingering (is this due to a GC detail in
        # Python that keeps sockets open as long as a child process is still
        # around?). from the client's point of view, the call to mock_death
        # hangs indefinitely.
        # TODO: there is a race condition if the subprocess has not been fully
        # started when the parent gets SIGKILL'ed. should try to remove the call
        # to sync_ping(). however, this should not be a problem in real life
        # because all processes except the root broker process are governed by
        # their parents, which never receive SIGKILL. only the broker will ever
        # get SIGKILL'ed, and even that should never happen in real deployment.
        # a simple protection against that eventuality would be to respawn it
        # immediately on startup and register the spawn for PDEATHSIG, before
        # it starts accepting client connections, so that everything after this
        # point is guaranteed to be insulated from the race condition.
        sock, port = find_free_port()
        c = MockControl(port, 'authkey', sock)
        c.start()
        r = RemoteControl(('',port), 'authkey', timeout=5)
        try:
            r.connect(2)
        except Exception, e:
            traceback.print_exc()
            os.kill(self.pid, signal.SIGKILL) # suicide!
            return
        os.kill(self.pid, signal.SIGKILL) # suicide!

    @Control.rpc
    def whoami(self):
        return self.established[self.current_connection]

    @Control.rpc
    @Control.preauth('admin','root')
    def whoami_preauth(self):
        return self.established[self.current_connection]

    @Control.rpc
    def make_child(self):
        sock, port = find_free_port()
        child = MockControl(port, None, sock, home=self.home)
        child.start()
        return port, child.pid

    @Control.rpc
    def disable_death_signalling(self):
        Control.disable_death_signalling(self)

    @Control.rpc
    def stop_listening(self):
        Control.stop_listening(self)

    @Control.rpc
    def sleep(self, seconds):
        time.sleep(seconds)

    @Control.rpc
    def kill(self, sig=signal.SIGKILL):
        os.kill(self.pid, sig)

    @Control.rpc
    def set_connection_buf_sizes(self, recv_size, send_size):
        return list(self.current_connection.set_buf_sizes(recv_size, send_size))

    @Control.rpc
    def get_pid(self):
        return os.getpid()

    @Control.rpc
    def upper(self, message):
        return message.upper()

    def perform_rpc(self, method, resource, vargs, kwargs):
        if self.max_tx % 500 == 0:
            print('%d transactions to go' % self.max_tx)
        if self.max_tx != -1:
            self.max_tx -= 1
        if self.max_tx != 0:
            return Control.perform_rpc(self, method, resource, vargs, kwargs)
        Control.shutdown(self, 'max transactions limit reached')

    @Control.rpc
    def make_garbage(self):
        a = {'a':1, 'b':'hej', 'c':[chr(1),unichr(2),'hej'], 'd':{'e':'f'}}
        b = ''.join([chr(i) for i in range(256)])
        c = [1,2,3,''.join([chr(i) for i in range(256)]),chr(4),5,unichr(6)]
        d = {'value':''.join([chr(i) for i in range(256)])}
        e = ''.join([unichr(i) for i in range(256)])
        f = {'a':a, 'b':b, 'c':c, 'd':d, 'e':e}
        return f

class StepControl(MockControl):

    def new_connection(self, connection, authkey):
        if self.pipe:
            self.pipe.put('new_connection')

    def shutdown(self):
        if self.pipe:
            self.pipe.put('shutdown')

class factory(object):
    HOME      = None
    processes = None

    def __init__(self):
        pass

    def kill(self):
        for p in self.processes:
            p.terminate()
            try:
                p.join()
            except Unwaitable:
                pass

    def __call__(self, fn):
        def decorated(*args, **kwargs):
            pretty = '%s %s' % (fn.func_code.co_filename, fn.func_name)
            print(pretty)
            self.HOME = Workspace()
            self.processes = []
            os.makedirs(os.path.join(self.HOME.path, '.ave','config'))
            try:
                result = fn(pretty, self, *args, **kwargs)
            except:
                raise
            finally:
                self.kill()
                self.HOME.delete()
            return result
        return decorated

    def write_config(self, filename, config):
        path = os.path.join(self.HOME.path, '.ave','config',filename)
        with open(path, 'w') as f:
            json.dump(config, f)

    def make_control(self, home=None, authkey=None, max_tx=-1, timeout=1):
        sock,port = find_free_port()
        c = MockControl(port, authkey, sock, home=home, max_tx=max_tx)
        r = RemoteControl(('',port), None, timeout, home=home)
        c.start()
        self.processes.append(c)
        return r

    def make_proxy(self, target):
        sock,port = find_free_port()
        c = MockControl(port, None, sock, proxee=target)
        r = RemoteControl(('',port), None, 1)
        c.start()
        self.processes.append(c)
        return r

    def make_client(self, fn, *argv):
        p = Process(target=fn, args=argv)
        p.start()
        self.processes.append(p)
        return p

    def make_panotti_server(self, home):
        sock,port = find_free_port()
        c = PanottiControl(port, sock, home=home)
        r = RemoteControl(('',port), None, 1)
        c.start()
        self.processes.append(c)
        return r
