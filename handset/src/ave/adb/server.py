# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import json
import psutil
import signal
import traceback
import time
import errno

import ave.config
import ave.persona

from ave.exceptions import AveException
from ave.handset.adb_handset    import WHICH_ADB

class AdbServer(object):
    pid = -1
    fd  = -1

    def __init__(self, home=None, config=None):
        if not home:
            home = ave.config.load_etc()['home']
        self.home = home

        if config == None:
            config = AdbServer.load_config(self.home)
        self.config = config

    @property
    def port(self):
        return self.config['port']

    @property
    def persist(self):
        return self.config['persist']

    @property
    def demote(self):
        return self.config['demote']

    @property
    def logging(self):
        if 'logging' in self.config:
            return self.config['logging'] == True
        return True # default to True if not set in config

    @classmethod
    def find_server_processes(cls, port=None):
        result = []
        for p in psutil.process_iter():
            try:
                if isinstance(type(p).cmdline, property):
                    pname = p.name
                    cmdline = p.cmdline
                else:
                    pname = p.name()
                    cmdline = p.cmdline()
                if pname == 'adb':
                    if 'fork-server' in cmdline and 'server' in cmdline:
                        if port != None and str(port) not in cmdline:
                            continue
                        result.append(p)
            except psutil.NoSuchProcess:
                continue
        return result

    @classmethod
    def kill_all_servers(cls, port=None, excepted=None):
        procs = AdbServer.find_server_processes(port)
        fail  = []
        for proc in procs:
            if proc.pid == excepted:
                continue
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except Exception, e:
                try:
                    path = proc.path
                except AttributeError:
                    # process has no path when executed by upstart? no matter,
                    # just set it to nothing.
                    path = None
                if isinstance(type(proc).cmdline, property):
                    pname   = proc.name
                    ppid    = proc.ppid
                    cmdline = proc.cmdline
                    uids    = proc.uids
                    gids    = proc.gids
                else:
                    pname   = proc.name()
                    ppid    = proc.ppid()
                    cmdline = proc.cmdline()
                    uids    = proc.uids()
                    gids    = proc.gids()
                details = {
                    'pid' : proc.pid,
                    'ppid': ppid,
                    'name': pname,
                    'path': path,
                    'cmd' : cmdline,
                    'uid' : uids,
                    'gid' : gids
                }
                fail.append(details)
        if fail:
            raise AveException({
                'message':'could not kill all competition',
                'processes': fail
            })

    @classmethod
    def load_config(cls, home):
        config = None

        path = os.path.join(home, '.ave', 'config', 'adb_server.json')
        if os.path.exists(path):
            try:
                with open(path) as f:
                    config = json.load(f)
            except Exception, e:
                raise Exception('could not load adb configuration file: %s' % e)
        else:
            config = {}

        # validate: fill in defaults
        if 'port' not in config:
            config['port'] = 5037
        if 'persist' not in config:
            config['persist'] = True
        if 'demote' not in config:
            config['demote'] = True

        # validate: check types
        if type(config['port']) != int:
            raise Exception(
                'config error: "port" value in %s is not an integer: %s'
                % (path, config['port'])
            )
        if type(config['persist']) != bool:
            raise Exception(
                'config error: "persist" value in %s is not a boolean: %s'
                % (path, config['persist'])
            )
        if type(config['demote']) != bool:
            raise Exception(
                'config error: "demote" value in %s is not a boolean: %s'
                % (path, config['demote'])
            )
        return config

    def log(self, message):
        if self.logging:
            sys.stderr.write(message+'\n')
            sys.stderr.flush()

    def kill_competition(self):
        self.log('killing all competition')
        try:
            AdbServer.kill_all_servers(excepted=self.pid)
        except AveException, e:
            self.log('%s' % e)
        except Exception, e:
            self.log('INTERNAL ERROR: could not kill competition: %s' % e)

    def pid_exists(self, pid):
        """Check whether pid exists in the current process table."""
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError, e:
            return e.errno == errno.EPERM
        else:
            return True

    def start_server(self):
        self.log('starting new ADB server')
        os.environ['ADB_CPU_AFFINITY_BUG6558362'] = '1'

        # ADB_VENDOR_KEYS is a colon separated list of paths to company wide
        # private keys, so called "vendor keys".
        vendor_key_dir = '/usr/share/ave/handset'
        userdebug_key = os.path.join(vendor_key_dir, 'adbkey_userdebug')
        if os.path.exists(userdebug_key):
            os.environ['ADB_VENDOR_KEYS'] = userdebug_key

        # If HOME isn't set, adb will not know where to look for the .android
        # directory, if started by init. After reboots for example.
        os.environ['HOME'] = self.home

        # Use "start-server" instead of "fork-server server" as it cannot work
        # with latest adb offered in platform-tools 23.1.0
        cmd = [WHICH_ADB, '-P', str(self.port), 'start-server']
        # Use os.system instead of ave functions(ave.cmd.run and run_bg) as they
        # cannot start adb server
        os.system(' '.join(cmd))

        # As the father process of adb server is "1", we find it from
        # current process table and only keep one adb server
        procs = self.find_server_processes(self.port)
        if procs and len(procs) == 1:
            self.pid = procs[0].pid

    def stop_server(self):
        self.log('stopping the ADB server')
        try:
            os.kill(self.pid, signal.SIGKILL)
        except Exception, e:
            raise Exception('could not SIGKILL adb server process: %s' % e)

    def run(self):
        self.log('configuration: %s' % self.config)
        try:
            while True:
                self.kill_competition()
                self.start_server()
                # Wait for completion of adb process
                while self.pid_exists(self.pid):
                    time.sleep(1)
                if not self.persist:
                    break
        except Exception:
            traceback.print_exc()
        self.log('stopping')
