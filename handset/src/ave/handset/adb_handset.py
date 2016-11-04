# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import time
import tempfile
import signal
import shutil
import pipes
import socket
import traceback
import errno

from datetime        import datetime, timedelta

import ave.cmd
import ave.config

from ave.handset.profile      import HandsetProfile
from ave.handset.lister       import HandsetLister
from ave.exceptions           import Timeout, RunError, Offline
from ave.network.connection   import find_free_port
from ave.base_workspace import BaseWorkspace

HAS_ADB = None

def which_adb():
    global HAS_ADB
    if HAS_ADB is None:
        home = ave.config.load_etc()['home']
        cfg_path = BaseWorkspace.default_cfg_path(home)
        config = BaseWorkspace.load_config(cfg_path, home)
        if 'adb' in config['tools']:
            HAS_ADB = config['tools']['adb']
            return HAS_ADB
        else:
            cmd = ['which', 'adb']
            a, out, s = ave.cmd.run(cmd)
            if out:
                HAS_ADB = out.strip()
                return HAS_ADB
            else:
                raise Exception('Error:You need to set adb path to the environment variable '
                                'or config adb path in %s tools node like ("tools":{"adb":"/usr/bin/adb"})' % cfg_path)
    else:
        return HAS_ADB

WHICH_ADB = which_adb()

def run_adb(cmd, timeout=0, debug=False, bg=False, output_file=None):
    '''
    Method used by the Handset class to run adb. Used to ensure which adb
    binary is used for execution and report when the adb daemon is not running.
    '''
    if type(cmd) != list:
        raise Exception('must pass command line as list to run_adb()')
    if 'adb' in cmd[0]:
        raise Exception('caller of run_adb() does not choose which adb to use')
    cmd.insert(0, WHICH_ADB) # TODO: read value from config/workspace.json?
    if not bg:
        s,o,e = ave.cmd.run(cmd, timeout, debug, output_file=output_file)
        if o.startswith('* daemon not running'):
            raise RunError(cmd, o, 'ADB is caught in a reboot loop')
        return s,o # ave.cmd.run() always sets third return value to ''
    else:
        child_pid, child_fd = ave.cmd.run_bg(cmd,debug)
        return child_pid, child_fd

# class to enable adb forwarding. can be use with the "with" statement. cannot
# be used directly on client-side. only to be used internally in the handset
# classes.
class AdbForward(object):
    serial = None # a handset serial number
    local  = None # an ADB port expression
    remote = None # an ADB port expression

    def __init__(self, serial, remote):
        self.serial = serial
        self.remote = remote

    def __del__(self):
        try:
            # unfortunately ADB simply fails this a lot and there is nothing
            # one can really do about it
            self.disconnect()
        except Exception, e:
            pass # exception only caught to silence Python's default warning

    @staticmethod
    def list_all():
        cmd = ['forward', '--list']
        s,o = run_adb(cmd)
        if s != 0:
             raise Exception('could not list forwards: %s' % o.strip())
        forwards = []
        for line in o.strip().splitlines():
            serial, local, remote = line.split()
            forwards.append([serial, local, remote])
        return forwards

    @staticmethod
    def check_global_limits():
        cmd = ['forward', '--list']
        s,o = run_adb(cmd)
        o = o.strip()
        if s != 0:
             raise Exception('could not check global limits: %s' % o.strip())
        # ADB's internal buffer is limited to 64*1024 bytes and is subject to
        # overflow. make sure it never gets near the limit
        if len(o) > 63*1024: # no entry is a whole kilobyte long. i hope...
            raise Exception('ADB is close to buffer overflow: %d' % len(o))
        # ADB's internal description of the buffer cannot handle more than
        # 1024 entries without crashing. make sure it never gets there.
        count = len(o.splitlines())
        if count >= 900:
            raise Exception('ADB is close to forwarding entry limits: %s'%count)

    def connect(self):
        AdbForward.check_global_limits()

        # find a free port that isn't already forwarded and pass it to ADB
        attempts = 0
        # retry until a local port has been bound. redundant calls to connect()
        # have no effect because .local will be set the first time.
        while self.local == None:
            sock,port = find_free_port()
            # must close the associated socket before giving the port number to
            # ADB. it would be nice if ADB could to passed the open socket or
            # had an option to find a free port itself or whatever. yay! race
            # conditions!
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            cmd = ['-s', self.serial, 'forward', 'tcp:%d' % port, self.remote]
            s,o = run_adb(cmd)
            if s == 0:
                self.local = 'tcp:%d' % port
                break
            if attempts >= 10:
                o = o.splitlines()[0]
                raise Exception('could not set up port forwarding: %s' % o)

        return self.local

    def disconnect(self):
        if not self.local: # not connected, do nothing
            return
        cmd = ['-s', self.serial, 'forward', '--remove', self.local]
        s,o = run_adb(cmd)
        if s != 0:
            raise Exception('could not remove forwarded port: %s' % o.strip())
        self.local = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

class AdbHandset(object):
    profile   = None
    forwarded = None # { local port expression : AdbForward, ... }

    def __new__(cls, profile, **kwargs):
        return object.__new__(cls)

    def __init__(self, profile, **kwargs):
        if type(profile) != HandsetProfile:
            raise Exception('type(profile) != HandsetProfile')
        self.profile   = profile
        self.forwarded = {}
        self.bgpids = []

    def __getattr__(self, attribute):
        return self.profile[attribute]

    def trace(fn):
        def decorator(self, *vargs, **kwargs):
            try:
                return fn(self, *vargs, **kwargs)
            except Exception, e:
                traceback.print_exc()
                raise e
        return decorator

    def get_profile(self):
        return self.profile

    def get_workstation(self):
        if self.profile['workstation']:
            return self.profile['workstation']
        else:
            raise Exception('could not get handset\'s workstation')

    def get_handset_config(self):
        from ave.handset.lister import merge_handset_config
        handsets = merge_handset_config()['handsets']
        for h in handsets:
            if h['model'] == self.get_product_model():
                return h
        return None

    ### Handset Properties #####################################################

    # Those properties can be used for allocation
    # Any child class should override the implement if needed or add its own
    # properties.

    def get_platform(self):
        try:
            self.ls('/system/bin/dalvikvm')
            return 'android'
        except:
            pass
        try:
            self.ls('/system/b2g/b2g')
            return 'firefox'
        except:
            pass
        return 'adb'

    def get_sdk_version(self):
        try:
            return int(self.get_property('ro.build.version.sdk'))
        except:
            return None

    def get_gsm_operator(self):
        '''Get the handset's GSM operator.'''
        operator = None
        try:
            return self.get_property('gsm.operator.alpha')
        except Exception, e:
            return None

    def get_apn_sim_operator(self):
        try:
            return self.get_property('gsm.apn.sim.operator.numeric').lower()
        except:
            return None

    def get_phone_type(self):
        try:
            return self.get_property('gsm.current.phone-type').lower()
        except:
            return None

    def get_network_type(self):
        try:
            return self.get_property('gsm.network.type').lower()
        except:
            return None

    def get_operator_country(self):
        try:
            return self.get_property('gsm.operator.iso-country').lower()
        except:
            return None

    def get_operator_isroaming(self):
        try:
            return self.get_property('gsm.operator.isroaming').lower()
        except:
            return None

    def get_operator_numeric(self):
        try:
            return self.get_property('gsm.operator.numeric').lower()
        except:
            return None

    def get_sim_operator(self):
        try:
            return self.get_property('gsm.sim.operator.alpha').lower()
        except:
            return None

    def get_gsm_capable(self):
        try:
            gsm_type = self.get_property('gsm.network.type').lower()
            if gsm_type in ['unknown', 'unknown,unknown']:
                return False
            else:
                return True
        except:
            return False

    def get_sim_country(self):
        try:
            return self.get_property('gsm.sim.operator.iso-country').lower()
        except:
            return None

    def get_sim_operator_numeric(self):
        try:
            return self.get_property('gsm.sim.operator.numeric').lower()
        except:
            return None

    def get_product_model(self):
        try:
            return self.get_property('ro.product.model').lower()
        except:
            return None

    def get_build_type(self):
        try:
            return self.get_property('ro.build.type')
        except:
            return None

    def get_product_name(self):
        try:
            return self.get_property('ro.product.name').lower()
        except:
            return None

    def get_private_sw_id(self):
        try:
            return self.get_property('persist.private_sw_id')
        except:
            return None

    def get_build_label(self):
        try:
            return self.get_property('ro.build.id')
        except:
            return None

    def update_profile(self, profile):
        profile['product.model'] = self.get_product_model()
        profile['product.name'] = self.get_product_name()
        profile['sdk.version'] = self.get_sdk_version()
        profile['sw.label'] = self.get_build_label()
        profile['gsm.operator'] = self.get_gsm_operator()
        profile['private_sw_id'] = self.get_private_sw_id()
        profile['apn.sim.operator'] = self.get_apn_sim_operator()
        profile['phone.type'] = self.get_phone_type()
        profile['network.type'] = self.get_network_type()
        profile['operator.country'] = self.get_operator_country()
        profile['operator.isroaming'] = self.get_operator_isroaming()
        profile['operator.numeric'] = self.get_operator_numeric()
        profile['sim.operator'] = self.get_sim_operator()
        profile['sim.country'] = self.get_sim_country()
        profile['sim.operator.numeric'] = self.get_sim_operator_numeric()
        profile['sw_type'] = self.get_build_type()
        profile['gsm-capable'] = self.get_gsm_capable()

        return profile

    ### PORT FORWARDING ########################################################

    # TODO: In my dreams, the adb -s flag would work for --list and --remove,
    #       and adb could take tcp:0 as a 'choose any free port' spec. Oh, and
    #       --no-rebind wouldn't fail 100% of the time.

    def _open_forwarded_port(self, remote):
        # look for an existing forwarding rule
        entry = None
        for rule in AdbForward.list_all():
            if rule[0] == self.profile['serial'] and rule[2] == remote:
                entry = rule[1]
                break

        if not entry:
            fwd   = AdbForward(self.profile['serial'], remote)
            entry = fwd.connect()
            self.forwarded[entry] = fwd

        return entry

    def open_forwarded_port(self, remote):
        try:
            return self._open_forwarded_port(remote)
        except Exception, e:
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % e.message)
            else:
                raise

    def _close_forwarded_port(self, entry):
        if entry == 'all':
            for fwd in self.forwarded.values():
                fwd.disconnect()
            self.forwarded = {}
            return

        if type(entry) not in [str, unicode]:
            raise Exception('invalid port forwarding entry: %s' % entry)

        if entry not in self.forwarded:
            raise Exception('no such port forwarding entry: %s' % entry)

        fwd = self.forwarded[entry]
        fwd.disconnect()
        del self.forwarded[entry]

    def close_forwarded_port(self, entry):
        try:
            return self._close_forwarded_port(entry)
        except Exception, e:
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % e.message)
            else:
                raise

    def _list_forwarded_ports(self, all_adb=False):
        if all_adb: # unfortunately needed for testing purposes
            return AdbForward.list_all()
        return [
            [fwd.serial, fwd.local, fwd.remote]
            for fwd in self.forwarded.values()
        ]

    def list_forwarded_ports(self, all_adb=False):
        try:
            return self._list_forwarded_ports(all_adb)
        except Exception, e:
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % e.message)
            else:
                raise

    ### POWER STATES ###########################################################

    def has_adb(self):
        try:
            if self.shell('ls -d /').strip('\r\n') == '/':
                return True
        except:
            return False
        return False

    def boot_completed(self):
        try:
            value = self.get_property('sys.boot_completed')
        except Exception, e:
            return False
        return value.strip() == '1'

    def get_power_state(self):
        power_state,sysfs = HandsetLister.get_handset_power_state(self.profile)
        # update sysfs path;in case the handset has been moved to a new USB port
        if sysfs and self.profile['sysfs_path']:
            self.profile['sysfs_path'] = sysfs
        if power_state == 'enumeration':
            if self.boot_completed():
                return 'boot_completed'
            if self.has_adb():
                return 'adb'
            return 'enumeration'
        return power_state

    def wait_power_state(self, states, timeout=0):
        if type(states) in [str, unicode]:
            states = [states]
        elif type(states) != list:
            raise Exception('state must be a string or a list of strings')

        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            limit = None
        while True:
            if limit and datetime.now() > limit:
                raise Timeout('wait power state timed out')
            current = self.get_power_state()
            if current in states:
                return current
            time.sleep(1)

    def reboot(self, timeout=30):
        self.close_forwarded_port('all')
        ok_states = ['adb', 'package_manager', 'boot_completed']
        if self.get_power_state() not in ok_states:
            raise Exception('cannot reboot. disconnected handset')
        # give all shell commands ten seconds to complete. this is really just
        # a safety mechanism. it should never ever take that long to issue a
        # reboot command.
        cmd = ['-s', self.profile['serial'], 'reboot']
        s,o = run_adb(cmd, timeout=timeout)
        # make sure the handset reboot has begun
        self.wait_power_state('offline', timeout=timeout)

    def disable_dm_verity(self, timeout=300, reboot=False):
        if self.get_sdk_version() < 19:
            return
        self.root()
        cmds = ['-s', self.profile['serial'], 'disable-verity']
        s, o = run_adb(cmds, timeout=5)
        if s != 0:
            if 'error: closed' in o:
                raise Exception('Disable dm-verity not supported: %s' % o)
            else:
                raise Exception('Failed to disable dm-verity: %s' % o)
        # The message "Now reboot ..." means the action was executed success,
        # otherwise, we think the action was already done or not supported and
        # we don't raise any exception in those situations.
        if ('Now reboot your device for settings to take effect' in o):
            if reboot:
                self.reboot()
                self.wait_power_state('boot_completed', timeout)

    def enable_dm_verity(self, timeout=300, reboot=False):
        # Enable dm-verity is supported since Android M (sdk-23)
        if self.get_sdk_version() < 23:
            return
        self.root()
        cmds = ['-s', self.profile['serial'], 'enable-verity']
        s, o = run_adb(cmds, timeout=5)
        if s != 0:
            if 'error: closed' in o:
                raise Exception('Enable dm-verity not supported')
            else:
                raise Exception('Failed to enabled dm-verity: %s' % o)
        # The message "Now reboot ..." means the action was executed success,
        # otherwise, we think the action was already done or not supported and
        # we don't raise any exception in those situations.
        if ('Now reboot your device for settings to take effect' in o):
            if reboot:
                self.reboot()
                self.wait_power_state('boot_completed', timeout)

    ### SUPER USER STUFF #######################################################

    def root(self):
        s,o = run_adb(['-s', self.serial, 'root'])
        if s != 0: # adb may be shaky; retry once on failure
            time.sleep(0.25)
            s,o = run_adb(['-s', self.serial, 'root'])
            if s != 0:
                message = 'could not become root: %s' % o
                state,sysfs=HandsetLister.get_handset_power_state(self.profile)
                if state == 'offline':
                    raise Offline('Handset is offline. %s' % message)
                else:
                    raise Exception(message)
            else:
                if o.strip().startswith('adbd cannot run as root'):
                    raise Exception(str(o))

        else:
            if o.strip().startswith('adbd cannot run as root'):
                raise Exception(str(o))

        while True:
            if self.has_adb():
                break
            time.sleep(0.5)

    def remount(self):
        self.root()
        s,o = run_adb(['-s', self.profile['serial'], 'remount'])
        if s != 0:
            message = 'Failed to execute remount: %s' % o
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        # if remount failed the exit code of the adb call still is 0, therefore
        # the output must be controlled as well.
        if 'remount failed' in o:
            raise Exception(o)
        return o

    ### FILE SYSTEM FUNCTIONALITY ##############################################

    def ls(self, path):
        result = self.shell(['ls', path])
        if 'No such file or directory' in result:
            raise Exception('No such file or directory: %s' % path)
        if 'Not a directory' in result:
            raise Exception('Not a directory: %s' % path)
        if 'Permission denied' in result:
            raise Exception('Permission denied: %s' % path)
        return result.split()

    def cat(self, target):
        # We want to avoid pulling an entire directory.
        if self.path_exists(target, 'directory'):
            raise Exception('target \'%s\' is a directory' % target)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, 'file.bin')
        try:
            self.pull(target, temp_path)
            with open(temp_path, 'rb') as temp_file:
                content = temp_file.read()
        except:
            shutil.rmtree(temp_dir)
            raise
        shutil.rmtree(temp_dir)
        return content

    def rm(self, target, recursive=False):
        cmd = ['rm']
        if recursive:
            cmd.append('-r')
        cmd.append(target)
        o = self.shell(cmd)
        if 'rm failed for' in o:
            # raise exception on failure but ignore non-existent target
            if not 'No such file or directory' in o:
                raise Exception(o)

    def mv(self, src, dst):
        self.shell(['mv', pipes.quote(src), pipes.quote(dst)])

    def mkdir(self, target, parents=False):
        cmd = ['mkdir']
        if parents:
            cmd.append('-p')
        cmd.append(pipes.quote(target))
        o = self.shell(cmd)
        if 'File exists' in o:
            raise Exception(o)

    def chmod(self, permissions, target):
        self.shell(['chmod', pipes.quote(permissions), pipes.quote(target)])

    def path_exists(self, path, file_type=None):
        flags = {'symlink':'-h','directory':'-d','file':'-f','executable':'-x'}

        def validate_type(key):
            if not key in flags.keys():
                raise Exception(
                    'invalid type %s. valid types: %s' % (key, flags.keys())
                )
            if not self.shell(['test', flags[key], path, '&&', 'echo', '"OK"']):
                return False
            return True

        try:
            self.ls(path)
            if not file_type:
                return True
            return validate_type(file_type)
        except Exception as e:
            if 'No such file or directory' in str(e):
                return False
            raise e # on other exceptions

    def push(self, src, dst, timeout=0):
        if os.path.basename(src).startswith('tmp'):
            msg = '''
            temp-files generated by the workspace are not possible to track
            after the test execution and thus the possibility to push these
            files to the handset has been restricted.

            In order to push a generated file, it must first be secured that
            the file can be resurrected during post mortem analysis.

            AVE offers two ways to do this: Either during write_tempfile()
            or with the specific workspace method promote(). Please refer to
            the API description for details.
            '''
            raise Exception(msg)
        if os.path.islink(src):
            src = os.readlink(src)
        cmds = ['-s', self.profile['serial'], 'push', src, dst]
        s,o = run_adb(cmds, timeout)
        if s != 0:
            message = 'Failed to execute: %s' % cmds
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        return o

    def pull(self, src, dst, timeout=0):
        dst  = os.path.abspath(dst) # makes exception msg easier to understand
        cmds = ['-s', self.profile['serial'], 'pull', src, dst]
        s,o = run_adb(cmds, timeout)
        if s != 0:
            message = 'Failed to execute %s: %s' % (cmds, o)
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        return o

    def take_screenshot(self, dst, timeout=20):
        if '/' in dst[-1:]:
            raise Exception('Destination must not be a folder: %s' %dst)

        if not dst:
            raise Exception('Destination must not be empty: %s' %dst)

        if dst.count('/') < 2:
            raise Exception('Destination must not be root: %s' %dst)

        cmds = ['-s', self.profile['serial'], 'shell', 'screencap', '-p', dst]
        s,o = run_adb(cmds,timeout)
        if s != 0:
            message = 'Failed to execute: %s' %cmds
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)

        return 0

    def is_mounted(self, mount_point):
        if not type(mount_point) in [str, unicode]:
            raise Exception('invalid type of mount_point: %s'%type(mount_point))

        def get_mount_points():
            mnt_list = []
            output = self.shell('mount', timeout=3)
            if output:
                for l in output.splitlines():
                    l = l.split()
                    if len(l) > 1:
                        mnt_list.append((l[0], l[1]))
            return mnt_list

        try:
            mount_points = get_mount_points()
            # check it's mounted
            for mp in mount_points:
                if mount_point in mp:
                    return True
        except:
            return False
        return False

    def wait_mounted(self, sdcard, ext_card, timeout=30):
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            raise Exception('timeout must be a positive value')
        waiting = True
        while waiting:
            if datetime.now() > limit:
                cmd = 'Handset.wait_mounted(%s,%s,%s)'%(sdcard,ext_card,timeout)
                raise Timeout({
                    'cmd'    : cmd,
                    'out'    :'',
                    'message':'wait mounted timed out'
                })
            try:
                waiting = ((sdcard and not self.sdcard_mounted())
                    or (ext_card and not self.extcard_mounted()))
            except:
                time.sleep(1) # might be offline

    ### PROCESS MANAGEMENT #####################################################

    def shell(self, args, timeout=0, bg = False):
        orig_args = args
        if type(args) in [str, unicode]:
            args = [a for a in args.split() if a != '']
        # Empty value was ignore when passing to some shell tool
        # We force change the empty value as ""
        if type(args) == list:
            temp = []
            for s in args:
                if s.strip() == '':
                    s = '\"%s\"' % s
                temp.append(s)
            args = temp
        cmds = ['-s', self.profile['serial'], 'shell']
        cmds.extend(args)
        #if the cmd run in background the return values are the child_pid and child_fd
        #else the the return value are the exit code of child process, and the content of
        # the stdout and stderr
        s,o = run_adb(cmds, timeout, bg=bg)
        if not bg:
            if s != 0: # only the case if host-side adb could not be executed at all
                message = 'Failed to execute: %s' % cmds
                state,sysfs = HandsetLister.get_handset_power_state(self.profile)
                if state == 'offline':
                    raise Offline('Handset is offline. %s' % message)
                else:
                    raise Exception(message)
            lines = o.splitlines()
            if (lines
            and lines[0].startswith('/system/')
            and lines[0].endswith('not found')):
                raise Exception('no such executable: %s' % orig_args)
            return o
        else:
            self.bgpids.append((s, o))
            return s, o

    def kill_background_cmd(self, pid, fd):
        try:
            os.close(fd)
        except OSError, e:
            if e.errno == errno.EBADF:
                pass # already closed
            else:
                raise e
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except OSError, e:
            if e.errno not in [errno.ECHILD, errno.ESRCH]:
                raise Exception('unhandled errno: %d' % e.errno)

    def get_processes(self, name=None, exact=False):
        return self.ps(name, exact)

    def ps(self, name=None, exact=False):
        ret   = []
        lines = self.shell('ps', timeout=5).splitlines()
        if name: # pids for matching name
            lines_list = [l.split() for l in lines if name in l]
            for p in lines_list:
                if exact and p[8] == name:
                    ret.append({'pid':p[1], 'name':p[8]})
                elif not exact and name in p[8]:
                    ret.append({'pid':p[1], 'name':p[8]})
        else: # all pids
            lines_list = [l.split() for l in lines if l]
            del lines_list[0] # omit first line with tabs' name
            for p in lines_list:
                ret.append({'pid':p[1], 'name':p[8]})
        return ret

    ### PROPERTY MANAGEMENT ####################################################

    def set_property(self, key, value):
        if not key or not value:
            raise Exception('both key and value must be given')
        if type(key) not in [str, unicode] or key == '':
            raise Exception('key must be a non-empty string')
        if type(value) not in [str, unicode] or value == '':
            raise Exception('value must be a non-empty string')

        self.root()
        self.shell(['setprop', key, value])
        if self.get_property(key) != value:
            raise Exception(
                'failed to set property: %s=%s' %(key, value)
            )

    def get_property(self, key):
        prop = self.shell(['getprop', key]).strip()
        if not prop:
            raise Exception('failed to get property with key: %s' % key)
        return prop

    def clear_property(self, key):
        if type(key) not in [str, unicode] or key == '':
            raise Exception('key must be a non-empty string')
        self.root()
        self.shell(['setprop', key, ''])
        try:
            self.get_property(key)
            # expect exception since get_property should return empty str
            raise Exception('failed to clear property: %s' % (key))
        except:
            pass
        # if the property is set in local.prop it should be removed therefrom
        if not 'local.prop' in self.ls('/data/'):
            return
        lines = self.cat('/data/local.prop').splitlines()
        self.clear_local_properties()
        for line in lines:
            if line == '':
                continue # omit empty lines
            if not line.startswith('%s=' % key):
                self.shell(['echo', line, '>>', '/data/local.prop'])
        # check it has been cleared
        if 'local.prop' in self.ls('/data/'):
            props = self.cat('/data/local.prop')
            if key in props:
                raise Exception('failed to clear property: %s' % key)

    ### CRASH HANDLING #########################################################

    def run_bugreport(self, directory):
        if not self.path_exists(directory):
            raise Exception('no such directory on handset: %s' % directory)
        if not self.path_exists(directory, file_type='directory'):
            raise Exception('not a directory: %s' % directory)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name      = 'BugReport-AVE-Generated-%s' % timestamp
        target    = os.path.join(directory, name)
        self.shell(['bugreport','>', target])
        return target

    def force_dump(self, timeout=0):
        self.root()
        self.close_forwarded_port('all')
        cmds = ['echo', 'c', '>', '/proc/sysrq-trigger']
        try:
            self.shell(cmds, timeout)
        except Exception, e:
            raise Exception('Failed force dump: %s' % str(e))

    def wait_for_path(self, path, file_type=None, timeout=0):
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            limit = None
        while True:
            if limit and datetime.now() > limit:
                raise Timeout('wait for path "%s" timed out' % path)
            if self.path_exists(path, file_type):
                break
            time.sleep(1)

    def __del__(self):
        while len(self.bgpids):
            item = self.bgpids.pop()
            pid = item[0]
            fd = item[1]
            self.kill_background_cmd(pid, fd)
