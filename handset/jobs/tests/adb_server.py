# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import time
import errno
import socket
import traceback
import signal

import vcsjob
import ave.cmd

from ave.network.connection import find_free_port
from ave.network.process    import Process
from ave.workspace          import Workspace
from ave.adb.server         import AdbServer
from ave.exceptions         import AveException

def setup(fn):
    def decorated(*vargs, **kwargs):
        pretty = '%s %s' % (fn.func_code.co_filename, fn.func_name)
        print(pretty)
        HOME = Workspace()
        try:
            result = fn(pretty, HOME, *vargs, **kwargs)
        except Exception, e:
            traceback.print_exc()
            result = vcsjob.ERROR
        HOME.delete()
        return result
    return decorated

def write_config(home, port, persist, demote):
    path   = os.path.join(home, '.ave','config','adb_server.json')
    try:
        os.makedirs(os.path.join(home, '.ave','config'))
    except os.error, e:
        if e.errno != errno.EEXIST:
            raise
    config = {}
    if port != None:
        config['port']    = port
    if persist != None:
        config['persist'] = persist
    if demote != None:
        config['demote']  = demote
    with open(path, 'w') as f:
        json.dump(config, f)

def find_one_server_process(port, timeout):
    ok = False
    while timeout > 0:
        pids = AdbServer.find_server_processes(port)
        if len(pids) == 1:
            return pids[0]
        timeout -= 0.5
        time.sleep(0.5)
    raise Exception('did not find the server process')

# start a server on the command line and check that the server class can find it
@setup
def t1(pretty, HOME):
    # need a free port number or the server will exit immediately
    sock,port   = find_free_port()
    sock.shutdown(socket.SHUT_RDWR) # close the socket since it can't be passed
    sock.close()                    # to ADB (which would have been very nice).
    cmd = ['/usr/bin/adb', '-P', str(port), 'start-server']
    os.system(' '.join(cmd))
    try:
        find_one_server_process(port, 10)
    except Exception, e:
        if 'did not find the server process' in str(e):
            print('FAIL %s: can not start adb server' % pretty)
            return False
        else:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    try:
        cmd = ['/usr/bin/adb', '-P', str(port), 'kill-server']
        os.system(' '.join(cmd))
    except Exception, e:
        print('FAIL %s: can not stop adb server' % pretty)
        return False

    return True

# write a valid config file and load it
@setup
def t2(pretty, HOME):
    write_config(HOME.path, 5037, True, True)

    try:
        AdbServer.load_config(HOME.path)
    except Exception, e:
        print('FAIL %s: could not load valid configuration: %s' % (pretty, e))
        return False

    return True

# write an invalid config file and fail to load it
@setup
def t3(pretty, HOME):
    write_config(HOME.path, 'blaha', None, None)
    try:
        AdbServer.load_config(HOME.path)
        print('FAIL %s: could load invalid configuration file' % pretty)
        return False
    except Exception, e:
        if '"port" value in' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    write_config(HOME.path, None, 'blaha', None)
    try:
        AdbServer.load_config(HOME.path)
        print('FAIL %s: could load invalid configuration file' % pretty)
        return False
    except Exception, e:
        if '"persist" value in' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    write_config(HOME.path, None, None, 'blaha')
    try:
        AdbServer.load_config(HOME.path)
        print('FAIL %s: could load invalid configuration file' % pretty)
        return False
    except Exception, e:
        if '"demote" value in' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    return True

# start a server on the command line, then ask an AdbServer object to kill it
@setup
def t4(pretty, HOME):
    sock,port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR) # close the socket since it can't be passed
    sock.close()                    # to ADB (which would have been very nice).
    cmd = ['/usr/bin/adb', '-P', str(port), 'start-server']
    os.system(' '.join(cmd))

    try:
        pid = find_one_server_process(port, 2)
    except Exception, e:
        if 'did not find the server process' in str(e):
            print('FAIL %s: can not start adb server' % pretty)
            return False
        else:
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False

    cfg = {'port':port, 'persist':False, 'demote':False, 'logging':False}
    srv = AdbServer(HOME.path, cfg)
    srv.kill_competition()

    try:
        find_one_server_process(port, 10)
    except Exception, e:
        if 'did not find the server process' in str(e):
            pass
        else:
            print('FAIL %s: first server did not die' % pretty)
            return False

    return True

# start a server through a separate process. kill it and check that it finishes
# because persist=False
@setup
def t5(pretty, HOME):
    sock,port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR) # close the socket since it can't be passed
    sock.close()                    # to ADB (which would have been very nice).

    config = {'port':port, 'persist':False, 'demote':False, 'logging':False}

    def concurrent(home, config):
        srv = AdbServer(home, config)
        srv.run()

    p = Process(target=concurrent, args=(HOME.path, config))
    p.start()

    try:
        find_one_server_process(port, 2)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, e))
        p.terminate()
        p.join()
        return False

    try:
        AdbServer.kill_all_servers()
    except AveException, e:
        if e.details['message'] == 'could not kill all competition':
            for proc in e.details['processes']:
                if proc['uid'] != 0: # ok to not be able to kill rooted adb
                    print('FAIL %s: %s' % (pretty, e))
                    return False

    try:
        p.join(3)
    except Exception, e:
        print('FAIL %s: could not join within 3 seconds: %s' % (pretty, e))
        p.terminate()
        p.join()
        return False

    return True

# like t5, but with persistence. the server will start again and again until we
# kill the process that created the AdbServer object
@setup
def t6(pretty, HOME):
    sock,port = find_free_port()
    sock.shutdown(socket.SHUT_RDWR) # close the socket since it can't be passed
    sock.close()                    # to ADB (which would have been very nice).

    config = {'port':port, 'persist':True, 'demote':False, 'logging':False}

    def concurrent(home, config):
        srv = AdbServer(home, config)
        srv.run()

    p = Process(target=concurrent, args=(HOME.path, config))
    p.start()

    seen = []
    for i in range(5):
        # find the current server
        pid = find_one_server_process(port, 4)
        if pid in seen:
            print('FAIL %s: pid %d was seen before: %s' % (pretty, pid, seen))
            p.terminate()
            p.join()
            return False
        seen.append(pid)

        # kill the current server. expect the next step in the loop to find a
        # new one in its place
        AdbServer.kill_all_servers(port)

    p.terminate()
    p.join()

    return True

# check that correct configuration defaults are set if no configuration file is
# available
@setup
def t7(pretty, HOME):
    try:
        srv = AdbServer()
    except Exception, e:
        traceback.print_exc
        print('FAIL %s: could not start without a config file: %s' % (pretty,e))
        return False

    if srv.port != 5037:
        print('FAIL %s: wrong default port value: %s' % (pretty, srv.config))
        return False

    if srv.persist != True:
        print('FAIL %s: wrong default persist value: %s' % (pretty, srv.config))
        return False

    if srv.demote != False:
        print('FAIL %s: wrong default demote value: %s' % (pretty, srv.config))
        return False

    return True