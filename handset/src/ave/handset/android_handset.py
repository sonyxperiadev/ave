# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import re
import time
import signal
import pipes
import ctypes
import traceback
import string
import select
import errno
import random

from datetime        import datetime, timedelta
from types           import NoneType
from StringIO        import StringIO
from functools       import wraps
from xml.dom         import minidom

import ave.apk
import ave.cmd
import ave.handset.galatea

from ave.network.process        import Process
from ave.network.pipe           import Pipe
from ave.network.exceptions     import ConnectionTimeout
from ave.handset.profile        import HandsetProfile
from ave.handset.lister         import HandsetLister
from ave.handset.adb_handset    import run_adb, WHICH_ADB, AdbHandset
from ave.exceptions             import Timeout, RunError, AveException
from ave.exceptions             import Offline

LOGBUF_MAXSIZE = 16 * 1024 * 1024 # 16 megabytes
WAIT_FOR_PM_WRITE_SETTINGS = 15

# Class to handle logcat monitoring, used by the AndroidHandset class.
class LogcatMonitor(Process):
    cmd_pid  = -1
    cmd_fd   = -1
    log_path = None # path on test host
    log_file = None
    procname = None # process name as displayed by ps or top
    log_buf  = None # StringIO object
    pipe_r   = None # ave.network.pipe
    pipe_w   = None # ave.network.pipe
    poller   = None

    def __init__(self, serial, args, log_path=None, proc_name=None):
        if type(serial) not in [str, unicode]:
            raise Exception('serial must be a string')
        if type(args) != list:
            raise Exception('args must be a list of valid logcat arguments')
        if log_path and type(log_path) not in [str, unicode]:
            raise Exception('log_path must be a string')
        self.pipe_r       = Pipe()
        self.pipe_w       = Pipe()
        self.serial       = serial
        self.logcat_args  = args
        self.log_path     = log_path
        if not proc_name:
            proc_name = 'ave-logcat-monitor'
        Process.__init__(self, self.run, (), False, proc_name)

    def close_fds(self, exclude):
        exclude.append(self.pipe_r.r)
        exclude.append(self.pipe_r.w)
        exclude.append(self.pipe_w.r)
        exclude.append(self.pipe_w.w)
        Process.close_fds(self, exclude)

    def initialize(self):
        Process.initialize(self)
        self.log_buf = StringIO()
        if self.log_path:
            self.log_file = open(self.log_path, 'w')

    def send(self, obj):
        self.pipe_r.put(obj) # delivers one whole object

    def recv(self, timeout=None):
        return self.pipe_w.get(timeout)

    def _send(self, obj):
        self.pipe_w.put(unicode(obj, errors='replace'))

    def _recv(self, timeout=None):
        try:
            return self.pipe_r.get(timeout)
        except ConnectionTimeout:
            return None

    def handle_SIGTERM(self, signum, frame):
        self.kill_cmd()
        os._exit(os.EX_OK)

    def kill_cmd(self):
        if self.cmd_pid > 1:
            try:
                os.close(self.cmd_fd)
            except OSError, e:
                if e.errno == errno.EBADF:
                    pass # already closed
                else:
                    raise e
            try:
                os.kill(self.cmd_pid, signal.SIGKILL)
                os.waitpid(self.cmd_pid, 0)
            except OSError, e:
                if e.errno not in [errno.ECHILD, errno.ESRCH]:
                    raise Exception('unhandled errno: %d' % e.errno)
            self.cmd_pid = -1

    def run(self):
        self.begin()
        while True:
            try:
                self.once()
            except (OSError, IOError), e: # lost connection to logcat, restart
                self.log(
                    'Failed to read logcat from device %s: %s'
                    % (self.serial, e)
                )
                self.kill_cmd()
                time.sleep(2) # don't hammer ADB, it's such a frail flower
                self.begin()
            except Exception, e:
                traceback.print_exc()
                break # quit the monitor if we don't know what happened
        self.kill_cmd()

    def begin(self):
        run_adb(['-s', self.serial, 'shell', 'logcat', '-c'])
        cmd = [WHICH_ADB, '-s', self.serial, 'shell', 'logcat']
        cmd.extend(self.logcat_args)
        self.cmd_pid, self.cmd_fd = ave.cmd.run_bg(cmd)
        self.poller = select.poll()
        self.poller.register(self.cmd_fd, select.POLLIN)

    def once(self):
        # check if there is a request to get and clear accumulated logs
        msg = self._recv(timeout=0)
        if msg == 'get':
             self._send(self.log_buf.getvalue())
             self.log_buf = StringIO()

        # is there new logcat output to read?
        if not self.poller.poll(500): # millisecond timeout
            return

        # read logcat output and store it in a buffer, optionally to file too
        log = os.read(self.cmd_fd, 1000)
        if self.log_file:
            self.log_file.write(log)
            self.log_file.flush()
        if self.log_buf.tell() > LOGBUF_MAXSIZE:
            self.log_buf = StringIO() # start over to avoid OOM
        self.log_buf.write(log)

class AndroidHandset(AdbHandset):
    profile          = None
    monitors         = {}
    galatea_installed = False
    kernel_logging   = False
    _last_pm_modified_time = None

    def __init__(self, profile):
        AdbHandset.__init__(self, profile)

    def __del__(self):
        for m in self.monitors.itervalues():
            if m != None:
                m.terminate()
        AdbHandset.__del__(self)

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

    ### GALATEA MANAGEMENT #####################################################

    def galatea(fn):
        '''
        Galatea decorator used to ensure Galatea is installed on the handset
        before execution of a method dependent of Galatea.
        '''
        @wraps(fn)
        def decorator(self, *vargs, **kwargs):
            if not self.galatea_installed:
                self.reinstall_galatea(force=False)
            return fn(self, *vargs, **kwargs)
        return decorator

    def get_galatea_apk_path(self):
        return '/usr/share/ave/galatea/galatea.apk'

    def reinstall_galatea(self, path=None, timeout=30, force=True):
        '''
        Install Galatea on the handset.

        Args:
            path: Path to the Galatea apk. If None the default path where
                  Galatea is located upon AVE installation is used.

        Raises:
            Exception: If an error occured.
        '''
        version = self.get_sdk_version()
        if version < 19:
            raise Exception('Galatea only supports SDK API level >= 19.')
        if not path:
            path = self.get_galatea_apk_path()
        package_name = 'com.sonymobile.galatea'
        if not force and self.is_installed(package_name):
            try:
                latest_galatea_version = ave.apk.get_version(path)
                version = self.get_package_version(package_name)
                if version == latest_galatea_version:
                    return
            except Exception:
                pass # Should not fail the installation
        self.root()
        self.disable_package_verifier()
        # To avoid the failure "INSTALL_FAILED_UPDATE_INCOMPATIBLE",
        # uninstall galatea here.
        self.uninstall_galatea()
        self.install(path, timeout)

        self.galatea_installed = True

    def uninstall_galatea(self):
        '''
        Uninstall the Galatea apk.

        Raises:
            Exception: If an error occured.
        '''
        self.uninstall('com.sonymobile.galatea')
        self.galatea_installed = False

    def pm_disable(self, target):
        main_pkg = target.split('/')[0]
        if not self.is_installed(main_pkg):
            raise Exception('cannot disable %s (not installed)' % main_pkg)
        self.shell(['pm','disable', target])
        self._last_pm_modified_time = time.time()

    def pm_enable(self, target):
        main_pkg = target.split('/')[0]
        if not self.is_installed(main_pkg):
            raise Exception('cannot enable %s (not installed)' % main_pkg)
        self.shell(['pm','enable', target])
        self._last_pm_modified_time = time.time()

    def pm_ready(self):
        try:
            out = self.shell(['pm', 'list', 'packages'], timeout=5)
            error_msg = 'Error: Could not access the Package Manager. ' \
                        'Is the system running?'
            if not out or error_msg in out:
                return False
            return True
        except Exception, e:
            return False

    def get_power_state(self):
        power_state,sysfs = HandsetLister.get_handset_power_state(self.profile)
        # update sysfs path;in case the handset has been moved to a new USB port
        if sysfs and self.profile['sysfs_path']:
            self.profile['sysfs_path'] = sysfs
        if power_state == 'enumeration':
            if self.boot_completed():
                return 'boot_completed'
            if self.pm_ready():
                return 'package_manager'
            if self.has_adb():
                return 'adb'
            return 'enumeration'
        return power_state

    def wait_power_state(self, states, timeout=0):
        if type(states) in [str, unicode]:
            states = [states]
        elif type(states) != list:
            raise Exception('state must be a string or a list of strings')
        reachable_states = [
            'offline',
            'service',
            'enumeration',
            'adb',
            'package_manager',
            'boot_completed'
        ]
        for s in states:
            if s not in reachable_states:
                raise Exception('no such state: %s' % s)
        return AdbHandset.wait_power_state(self, states, timeout)

    def _wait_for_pm_write_settings(self):
        if self._last_pm_modified_time is not None and self.get_sdk_version() >= 23:
            gap = time.time() - self._last_pm_modified_time
            while gap < WAIT_FOR_PM_WRITE_SETTINGS:
                time.sleep(WAIT_FOR_PM_WRITE_SETTINGS - gap)
                gap = time.time() - self._last_pm_modified_time
        self._last_pm_modified_time = None

    def reboot(self, timeout=30):
        self._wait_for_pm_write_settings()
        self.galatea_installed = False
        AdbHandset.reboot(self, timeout)

    def restart_system(self, timeout=120):
        api_lvl = self.get_sdk_version()
        if api_lvl < 16:
            raise Exception(
                'restart_system() is not supported on API levels < 16; '
                'handset\'s API level is: %d' % api_lvl
            )
        self._wait_for_pm_write_settings()
        if type(timeout) != int or timeout < 1:
            raise Exception('timeout is not a positive integer: %s' % timeout)
        limit = datetime.now() + timedelta(seconds=timeout)

        self.shell('stop')

        time.sleep(2)
        while self.ps('zygote', exact=True):
            if datetime.now() > limit:
                raise Timeout(
                    'stopping the system timed out. zygote is still running'
                )
            time.sleep(1)

        self.shell('start')

        while not self.ps('zygote', exact=True):
            if datetime.now() > limit:
                raise Timeout(
                    'starting the system timed out. zygote is still not running'
                )
            time.sleep(1)

        def wait_toggle(value, wait, wanted):
            time.sleep(wait)
            while self.get_property('service.bootanim.exit') != value:
                if datetime.now() > limit:
                    raise Timeout(
                        'starting the system timed out. boot anim did not %s'
                        % wanted
                    )
                time.sleep(wait)

        # check that the boot animation exit flag turns to 0 and then to 1
        wait_toggle('0', 1, 'start')
        wait_toggle('1', 5, 'stop')

    def get_phone_number(self):
        self.root()
        sdk_version = self.get_sdk_version()
        if sdk_version < 18:
            parcel = self.shell('service call iphonesubinfo 5')
        elif sdk_version < 21:
            parcel = self.shell('service call iphonesubinfo 6')
        elif sdk_version < 22:
            parcel = self.shell('service call iphonesubinfo 11')
        else:
            parcel = self.shell('service call iphonesubinfo 13')
        # the parcel will look like this if the number is not available:
        # Result: Parcel(00000000 00000000 00000000  '............')

        # the parcel will look something like this on success:
        # Result: Parcel(
        #   0x00000000: 00000000 0000000e 0034002b 00320034 '........+.4.4.2.'
        #   0x00000010: 00380035 00340037 00300030 00310032 '5.8.7.4.0.0.2.1.'
        #   0x00000020: 00330039 00000000                   '9.3.....        ')

        # let's isolate the parts that start with a ' and concatenate those,
        # then remove all dots, then strip any trailing ' character. see what
        # is left: empty string == no number.
        parts  = ''.join([p[1:-1] for p in parcel.split() if p[0] == "'"])
        number = ''.join(parts.split('.'))
        number = number.strip("'")
        if not number:
            raise Exception('the SIM does not store its own phone number')
        return number

    ### UI MANIPULATION ########################################################

    def press_key(self, keycode):
        cmd = ['input', 'keyevent', str(keycode)]
        tmp = self.shell(cmd)
        if tmp:
            raise Exception('keypress failed: %s' % tmp)

    @galatea
    def open_status_bar(self):
        return ave.handset.galatea.open_status_bar(self)

    @galatea
    def scroll_down(self):
        return ave.handset.galatea.scroll_down(self)

    @galatea
    def scroll_up(self):
        return ave.handset.galatea.scroll_up(self)

    @galatea
    def id_visible(self, identity):
        return ave.handset.galatea.id_visible(self, identity)

    @galatea
    def is_checkbox_checked(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testIsCheckboxChecked'
        )

    @galatea
    def text_exact_visible(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testIsViewWithTextExact'
        )

    @galatea
    def text_regexp_visible(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testIsViewWithTextRegExp'
        )

    @galatea
    def click_item_with_id(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testClickItemWithId'
        )

    @galatea
    def long_click_item_with_id(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testLongClickItemWithId'
        )

    @galatea
    def click_item_with_text_exact(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testClickItemWithTextExact'
        )

    @galatea
    def long_click_item_with_text_exact(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testLongClickItemWithTextExact'
        )

    @galatea
    def click_item_with_text_regexp(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testClickItemWithTextRegExp'
        )

    @galatea
    def long_click_item_with_text_regexp(self, pattern):
        return ave.handset.galatea.text_pattern_method(
            self, pattern, 'testLongClickItemWithTextRegExp'
        )

    @galatea
    def wait_id_visible(self, identity, timeout=20):
        limit = datetime.now() + timedelta(seconds=timeout)
        while True:
            if datetime.now() > limit:
                raise Timeout('wait id visible timed out: %s' % identity)
            if self.id_visible(identity):
                return

    @galatea
    def wait_text_exact_visible(self, pattern, timeout=20):
        limit = datetime.now() + timedelta(seconds=timeout)
        while True:
            if datetime.now() > limit:
                raise Timeout('wait text exact visible timed out: %s' % pattern)
            if self.text_exact_visible(pattern):
                return

    @galatea
    def wait_text_regexp_visible(self, pattern, timeout=20):
        limit = datetime.now() + timedelta(seconds=timeout)
        while True:
            if datetime.now() > limit:
                raise Timeout('wait text regexp visible timed out: %s' %pattern)
            if self.text_regexp_visible(pattern):
                return

    @galatea
    def is_current_activity(self, name):
        return ave.handset.galatea.is_current_activity(self, name)

    def disable_usb_mode_chooser(self):
        self.pm_disable('com.android.settings/.deviceinfo.UsbModeChooserActivity')

    def enable_usb_mode_chooser(self):
        self.pm_enable('com.android.settings/.deviceinfo.UsbModeChooserActivity')

    def disable_package_verifier(self):
        if self.get_sdk_version() >= 23:
            self.shell(['settings put global package_verifier_enable 0'])
        elif self.get_sdk_version() >= 17:
            cmd = [
                'content','update',
                '--uri','content://settings/global',
                '--bind','value:i:0',
                '--where','name=\\"package_verifier_enable\\"'
            ]
            out = self.shell(cmd)
            if 'error' in out.lower():
                raise RunError(cmd, out, 'could not disable package verifier')

    def enable_package_verifier(self):
        if self.get_sdk_version() >= 23:
            self.shell(['settings put global package_verifier_enable 1'])
        elif self.get_sdk_version() >= 17:
            cmd = [
                'content','update',
                '--uri','content://settings/global',
                '--bind','value:i:1',
                '--where','name=\\"package_verifier_enable\\"'
            ]
            out = self.shell(cmd)
            if 'error' in out.lower():
                raise RunError(cmd, out, 'could not enable package verifier')

    def list_packages(self):
        cmd = ['pm', 'list', 'packages']

        try:
            packages = self.shell(cmd)
        except Exception, e:
            raise Exception('could not list packages: %s' % str(e))
        return [p[len('package:'):] for p in packages.split()]

    def list_permissions(self, args='-d -g'):
        if type(args) in [str, unicode]:
            args = args.split()
        else:
            args = []
        cmd = ['pm', 'list', 'permissions']
        cmd.extend(args)
        try:
            permissions = self.shell(cmd)
        except Exception, e:
            raise Exception('could not list permissions: %s' % str(e))
        return  str(permissions)

    def grant_permissions(self, package, permissions_name):
        api_lvl = self.get_sdk_version()
        if api_lvl < 23:
            raise Exception(
                'grant_permissions() is not supported on API levels < 23; '
                'handset\'s API level is: %d' % api_lvl
            )
        cmd = ['pm', 'grant', package, permissions_name]
        try:
            grant_info = self.shell(cmd)
        except Exception, e:
            raise Exception('could not grant permissions: %s' % str(e))
        if not grant_info:
            return True
        else:
            raise Exception('grant permissions error: %s' % str(grant_info))


    def revoke_permissions(self, package, permissions_name):
        api_lvl = self.get_sdk_version()
        if api_lvl < 23:
            raise Exception(
                'revoke_permissions() is not supported on API levels < 23; '
                'handset\'s API level is: %d' % api_lvl
            )
        cmd = ['pm', 'revoke', package, permissions_name]
        try:
            revoke_info = self.shell(cmd)
        except Exception, e:
            raise Exception('could not revoke permissions: %s' % str(e))
        if not revoke_info:
            return True
        else:
            raise Exception('revoke permissions error: %s' % str(revoke_info))

    def set_property(self, key, value, local=False):
        if not key or not value:
            raise Exception('both key and value must be given')
        if type(key) not in [str, unicode] or key == '':
            raise Exception('key must be a non-empty string')
        if type(value) not in [str, unicode] or value == '':
            raise Exception('value must be a non-empty string')

        if not local:
            AdbHandset.set_property(self, key, value)
        else:
            self.root()
            sdk = self.get_sdk_version()
            if sdk > 15:
                raise Exception(
                    'local.prop not supported on sdk versions > 15; handset\'s'
                    ' sdk version: %d' % sdk
                )
            kv = '%s=%s' % (key, value)
            if not 'local.prop' in self.ls('/data/'):
                self.shell(['echo', kv, '>>', '/data/local.prop'])
                return
            lines = self.cat('/data/local.prop').splitlines()
            self.clear_local_properties()
            added = False
            for line in lines:
                if line.startswith('%s=' % key):
                    added = True
                    self.shell(['echo', kv, '>>', '/data/local.prop'])
                elif line != '':
                    self.shell(['echo', line.strip(), '>>','/data/local.prop'])
            if not added:
                self.shell(['echo', kv, '>>', '/data/local.prop'])
            # check it all went well
            if 'local.prop' in self.ls('/data/'):
                props = self.cat('/data/local.prop')
                if kv not in props:
                    raise Exception('failed to set property: %s' % kv)
            else:
                raise Exception('failed to create /data/local.prop')

    def get_locale(self):
        sdk_version = self.get_sdk_version()
        if sdk_version <= 22:
            language_props = ['persist.sys.language', 'ro.product.locale.language']
            country_props  = ['persist.sys.country',  'ro.product.locale.region']

            language = None
            for prop in language_props:
                try:
                    language = self.get_property(prop)
                    break
                except Exception, e:
                    continue

            country = None
            for prop in country_props:
                try:
                    country = self.get_property(prop)
                    break
                except Exception, e:
                    continue

            if language and country:
                return '%s_%s' % (language, country)
            if language:
                return language
        else:
            locale_props = ['persist.sys.locale', 'ro.product.locale']
            for prop in locale_props:
                try:
                    locale = self.get_property(prop)
                    return locale.replace('-', '_')
                except Exception, e:
                    continue
        return ''

    def clear_local_properties(self):
        self.root()
        try:
            self.rm('/data/local.prop')
        except: # ignore if file does not exist
            pass
        if 'local.prop' in self.ls('/data/'):
            raise Exception('failed to clear local.prop')

    def is_installed(self, package):
        return package in self.list_packages()

    def install(self, apk_path, timeout=30, args=None):
        if not apk_path or not os.path.isfile(apk_path):
            raise Exception('no such apk file: %s' % apk_path)
        if args:
            regex = ur"(^(\-[lrtsdg])(\s\-[lrtsdg])*$)"
            if not type(args) in [str, unicode] or not re.match(regex, args):
                raise Exception('args of install: %s is not correct' % str(args))
            cmds = ['-s', self.profile['serial'], 'install', args, apk_path]
        else:
            cmds = ['-s', self.profile['serial'], 'install', apk_path]
        s,o = run_adb(cmds, timeout)
        if s != 0:
            message = 'Failed to execute: %s' % cmds
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        # also check output for failure indication
        # e.g. "Failure [INSTALL_FAILED_ALREADY_EXISTS]"
        for line in o.splitlines():
            if line.startswith('Failure'):
                raise Exception(line[len('Failure ['):-1])

    def uninstall(self, package):
        cmds = ['-s',self.profile['serial'], 'uninstall', package]
        s,o = run_adb(cmds)
        if s != 0:
            message = 'Failed to execute: %s' % cmds
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        # also check output for failure indication
        for line in o.splitlines():
            if line == 'Failure':
                raise Exception('could not uninstall: %s' % o)

    def reinstall(self, apk_path, timeout=30):
        if not apk_path or not os.path.isfile(apk_path):
            raise Exception('no such apk file: %s' % apk_path)
        cmds = ['-s', self.profile['serial'], 'install', '-r', apk_path]
        s,o = run_adb(cmds, timeout)
        if s != 0:
            message = 'Failed to execute: %s' % cmds
            state,sysfs = HandsetLister.get_handset_power_state(self.profile)
            if state == 'offline':
                raise Offline('Handset is offline. %s' % message)
            else:
                raise Exception(message)
        # also check output for failure indication
        # e.g. "Failure [INSTALL_FAILED_SHARED_USER_INCOMPATIBLE]"
        for line in o.splitlines():
            if line.startswith('Failure'):
                raise Exception(line[len('Failure ['):-1])

    def get_package_version(self, package):
        cmd = ['dumpsys', 'package', package]
        try:
            package_info = self.shell(cmd)
        except Exception, e:
            raise Exception('could not dumpsys for %s: %s' % (package, str(e)))
        version_line = None
        version_prefix = 'versionCode='
        for line in package_info.splitlines():
            line = line.strip()
            if line.startswith(version_prefix):
                version_line = line
                break
        if not version_line:
            raise Exception('can not find versionCode from "%s" by %s' %
                            (package_info, cmd))
        # version line is something like "versionCode=1 targetSdk=17"
        parts = line.split(' ', 1)
        return int(parts[0][len(version_prefix):])

    def clear_logcat(self, args=''):
        if type(args) in [str, unicode]:
            args = args.split()
        else:
            args = []
        cmd = ['-s',self.serial,'logcat','-c']
        cmd.extend(args)
        s,o = run_adb(cmd)
        if o:
            raise Exception('unexpected logcat output: %s' % o)

    def start_logcat(self, args='', log_file=None):
        if type(args) in [str, unicode]:
            args = args.split()
        mid = 0
        for i in range(1000000):
            mid = random.randint(1,1000000)
            if mid not in self.monitors:
                break
        if mid == 0:
            raise Exception('could not find a free monitor uid')
        m = LogcatMonitor(self.serial, args, log_file)
        m.start(synchronize=True)
        self.monitors[mid] = m
        return mid

    def stop_logcat(self, uid):
        self._validate_logcat_uid(uid)
        self.monitors[uid].terminate()
        self.monitors[uid].join(timeout=5)
        self.monitors[uid] = None # make sure the UID cannot be reused

    def get_logcat_log(self, uid, timeout=10):
        self._validate_logcat_uid(uid)
        m = self.monitors[uid]
        m.send('get')
        return m.recv(timeout)

    def _validate_logcat_uid(self, uid):
        if type(uid) != int:
            raise Exception('monitor uid must be an integer')
        if (uid not in self.monitors) or (not self.monitors[uid]):
            raise Exception('no monitor with that id: %d' % uid)

    def get_instrumentation_runners(self, package):
        o = self.shell(['pm','list','instrumentation',package])
        result = []
        for line in o.splitlines():
            m = re.search('instrumentation:(?P<package>.*?)\s*\(', line)
            if m:
                result.append(m.group('package').strip())
        return result

    def run_junit(
            self, output_path=None, test_package=None, runner=None,
            test_options=None, raw=None, timeout=0, timeout_kill=True
    ):
        output_file = None
        if output_path:
            output_file = open(output_path, 'a') # append
        try:
            return self._run_junit(
                output_file=output_file, test_package=test_package,
                runner=runner, test_options=test_options, raw=raw,
                timeout=timeout, timeout_kill=timeout_kill
            )
        finally:
            if output_file:
                output_file.close()

    def _run_junit(
            self, output_file=None, test_package=None, runner=None,
            test_options=None, raw=None, timeout=0, timeout_kill=True
    ):
        def _parse_package_name(runner=None, raw=None, output_file=None):
            def parse_runner(runner):
                lst = runner.split('/')
                if lst != []:
                    return lst[0]
                return None
            def parse_raw(raw):
                for l in raw.split():
                    if '/' in l:
                        return parse_runner(l)
                return None
            if runner:
                return parse_runner(runner)
            else:
                return parse_raw(raw)
            return None

        ##### TODO: remove this and use Handset.shell() when it raises RunError
        def execute_cmd(args, timeout=0, output_file=None):
            orig_args = args
            if type(args) in [str, unicode]:
                args = [a for a in args.split() if a != '']
            cmds = ['-s', self.profile['serial'], 'shell']
            cmds.extend(args)
            s,o = run_adb(cmds, timeout, output_file=output_file)
            if s != 0:
                message = 'Failed to execute: %s' % cmds
                state,sysfs=HandsetLister.get_handset_power_state(self.profile)
                if state == 'offline':
                    raise Offline('Handset is offline. %s' % message)
                else:
                    raise RunError(cmds, o, message)
            lines = o.splitlines()
            if (lines
            and lines[0].startswith('/system/')
            and lines[0].endswith('not found')):
                raise Exception('no such executable: %s' % orig_args)
            return o
        #######################################################################


        if not (test_package or runner or raw):
            raise Exception(
                'missing parameter: test_package, runner or raw must be given'
            )

        if test_package and not (runner or test_options or raw):
            if not type(test_package) in [str, unicode]:
                raise Exception(
                    'invalid type of test_package: %s' % type(test_package)
                )
            # must be installed on handset
            if not self.is_installed(test_package):
                raise Exception(
                    'no such test package on handset: %s' % test_package
                )
            # check that the apk has runners
            apk_runners = self.get_instrumentation_runners(test_package)
            if not apk_runners:
                # fallback for special case: ask test-SemcClock.apk for package
                # name results in: com.sonyericsson.organizer.tests, but it has
                # no instrumentation runner. an instrumentation runner can be
                # found with com.sonyericsson.organizer, thus a special case to
                # handle.
                apksplit = test_package.rsplit('.', 1)[0]
                apk_runners = self.get_instrumentation_runners(apksplit)
                if not apk_runners:
                    raise Exception(
                        'no runner in package: %s' % test_package
                    )
            if timeout > 0:
                limit = datetime.now() + timedelta(seconds=timeout)
            else:
                limit = None
            stdout_ret = ''
            output     = ''
            for r in apk_runners:
                cmd = ['am', 'instrument', '-r', '-w', r]
                # want to provide the aggregated output to the caller,
                try: # on exceptions too
                    stdout_ret = execute_cmd(cmd, timeout, output_file)
                    output = output + stdout_ret
                except Timeout, t: # aggregate output
                    t.out = output + t.out
                    if timeout_kill:
                        self.kill_junit_test(test_package)
                    raise t
                except RunError, err: # aggregate output
                    err.out = output + err.out
                    raise err
                # adjust timeout before next turn in the loop
                if timeout != 0:
                    # get time left and save value to timeout
                    new_delta = limit - datetime.now()
                    timeout = (new_delta.microseconds + (new_delta.seconds +
                        new_delta.days * 24 * 3600) * 10000000)/float(10000000)
                    if timeout <= 0:
                        raise Timeout({
                            'cmd'     : cmd,
                            'out'     : output,
                            'message' : 'instrumentation timed out'
                        })

        elif runner and not (test_package or raw):
            if not type(runner) in [str, unicode]:
                raise Exception(
                    'invalid type of runner: %s' % type(runner)
                )
            extras = []
            # check test_options and make a list to pass on
            if test_options:
                if not type(test_options) is dict:
                    raise Exception(
                        'invalid type of test_options: %s' % type(test_options)
                    )
                for key, value in test_options.items():
                    extras.extend(['-e', key, value])
            cmd = ['am', 'instrument', '-r']
            cmd.extend(extras) # (empty if not test_options)
            cmd.extend(['-w', runner])
            try:
                output = execute_cmd(cmd, timeout, output_file)
            except Timeout, t:
                if timeout_kill:
                    self.kill_junit_test(_parse_package_name(runner=runner))
                raise t
            # dont' catch RunError here

        elif raw and not (test_package or runner or test_options):
            if not type(raw) in [str, unicode]:
                raise Exception(
                    'invalid type of raw: %s' % type(raw)
                )
            cmd = 'am instrument ' + raw
            try:
                output = execute_cmd(cmd, timeout, output_file)
            except Timeout, t:
                if timeout_kill:
                    self.kill_junit_test(_parse_package_name(raw=raw))
                raise t
            # dont' catch RunError here

        else:
            raise Exception('invalid combination of parameters')
        if output:
            # small sanity check
            invalid_runner_msg       = 'INSTRUMENTATION_STATUS: Error=Unable '\
                'to find instrumentation info for: ComponentInfo{'
            invalid_class_msg        = 'INSTRUMENTATION_RESULT: longMsg=java' \
                '.lang.RuntimeException: Could not find test class.'
            invalid_testcase_pattern = 'INSTRUMENTATION_STATUS: stack=junit.' \
                'framework.AssertionFailedError: Method .* not found'
            runner_crashed_msg       = 'INSTRUMENTATION_RESULT: shortMsg=Pro' \
                'cess crashed'
            bad_component_msg        = 'Error: Bad component name:'
            if test_package and not (runner or test_options or raw):
                cmd = 'last executed: %s' % cmd
            # invalid runner
            if invalid_runner_msg in output or bad_component_msg in output:
                msg = 'invalid instrumentation runner'
                if runner:
                    msg = 'invalid instrumentation runner: %s' %runner
                raise RunError(cmd, output, msg)
            # invalid class
            if invalid_class_msg in output:
                msg = 'no such test class'
                raise RunError(cmd, output, msg)
            # invalid test case
            fa_list = re.findall(invalid_testcase_pattern, output)
            if fa_list:
                fa_list = re.findall('Method .* not found', fa_list[0])
                tc = fa_list[0]
                msg = 'no such test case: %s' % tc[7:-10]
                raise RunError(cmd, output, msg)
            # instrumentation runner process crashed
            if runner_crashed_msg in output:
                msg = 'instrumentation test run crash'
                raise RunError(cmd, output, msg)
            # no result means it did not finish (probably crash/dump)
            if not 'INSTRUMENTATION_RESULT:' in output:
                msg = 'instrumentation test run incomplete'
                raise RunError(cmd, output, msg)

        # return the output as a string
        return output

    def get_gsm_operator(self):
        '''Get the handset's GSM operator.'''
        operator = None
        try:
            return self.get_property('gsm.operator.alpha')
        except Exception, e:
            return None

    def kill_junit_test(self, package, timeout=10):
        # make sure to not kill something else
        def _validate_has_runners(package):
            if self.get_instrumentation_runners(package) != []:
                return True
            # special case
            short = package.rsplit('.', 1)[0]
            r = self.get_instrumentation_runners(short)
            if r != []:
                return True
            return False

        # verifying it's a true target
        def _get_instrumentation_targets(package):
            o = self.shell(['pm','list','instrumentation',package], timeout=5)
            if not o:
                package = package.rsplit('.', 1)[0] # try special case
                o = self.shell([
                    'pm','list','instrumentation',package],timeout=5
                )
            result = []
            for line in o.splitlines():
                m = re.search('target=(?P<package>.*?)\)', line)
                if m:
                    result.append(m.group('package').strip())
            return result

        def _kill_process_by_name(name):
            pids = self.get_processes(name=name, exact=True)
            for p in pids:
                self.shell('kill %s' % p['pid'], timeout=5)

        def _processes_seen(packages):
            for p in packages:
                if self.get_processes(name=p, exact=True) != []:
                    return True
            return False

        if not package:
            raise Exception('no package given')
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            limit = None
        if _validate_has_runners(package):
            self.root() # root; with license to kill
            targets = _get_instrumentation_targets(package)
            targets.append(package)
            # remove duplicated targets
            seen = set()
            targets = [x for x in targets if (
                x not in seen and not seen.add(x)
            )]
            # while any target is listed
            while(_processes_seen(targets)):
                if limit and datetime.now() > limit:
                    raise Timeout({
                        'cmd'    :'Handset.kill_junit_test(%s)' % (package),
                        'out'    :'',
                        'message':'kill junit test timed out'
                    })
                for t in targets:
                    _kill_process_by_name(t)
        else:
            raise Exception(
                'could not validate as instrumentation package: %s' % package
            )

    def is_mounted(self, path):
        if not path:
            raise Exception('no path given')
        if type(path) not in [str, unicode]:
            raise Exception('invalid type of path: %s' % type(path))

        mounts = self.shell('df', timeout=3).splitlines()

        #the commnd "df" in android N is diffrent from that in the other android version, so it need compatible
        #find the "Mounted" from the result's title
        if "Mounted" in mounts[0]:
            mounts = [line.split()[-1] for line in mounts if line and line[0] != 'F']
        else:
            mounts = [line.split()[0] for line in mounts if line and line[0] != 'F']

        # it's not enough to check if the path is found among the mountpoints.
        # the path may be a subdirectory to the mountpoint.
        for m in mounts:
            if path.startswith(m):
                try:
                    self.ls(path)
                    return True
                except Exception as e:
                    if 'No such file or directory' in str(e):
                        return False
                    raise e # on other exceptions
        return False

    def sdcard_mounted(self):
        path = self.shell('realpath $EXTERNAL_STORAGE').strip()
        return self.is_mounted(path)

    def extcard_mounted(self):
        tmp = self.shell('echo $SECONDARY_STORAGE').strip()
        if tmp:
            paths = tmp.split(':')
            for path in paths:
                path = self.shell('realpath %s' % path.strip())
                if 'usb' not in path:
                    return self.is_mounted(path.strip())
        else:
            return self._get_extcard_mounted_state()

    def _get_extcard_mounted_state(self):
        o = self.shell(['dumpsys', 'mount'])

        v_started = False
        vi_started = False

        # Parse dump logs to get all volumes info.
        volumes = []
        for line in o.split('\n'):
            if not v_started and 'Volumes:' in line:
                v_started = True
                continue
            if v_started:
                if not vi_started and 'VolumeInfo' in line:
                    vi_started = True
                    tmp_list = []
                    tmp_dict = {}
                    continue
                if vi_started and 'VolumeInfo' in line:
                    for tmp in tmp_list:
                        pair = tmp.split('=')
                        if pair and len(pair) == 2:
                            key = tmp.split('=')[0]
                            value = tmp.split('=')[1]
                            tmp_dict[key] = value
                    volumes.append(tmp_dict)
                    continue
                if vi_started:
                    tmp_list.extend(line.strip().split())
                if not line.strip():
                    break

        # We suppose only one sd card is inserted without any usb storage.
        # If no sd card was found, return False
        for v in volumes:
            if v['type'] == 'PUBLIC' and v['state'] == 'MOUNTED':
                    return True
        return False

    def list_gtest_tests(self, target):
        # target must be an executable file
        if not self.path_exists(target):
            raise Exception('target does not exist: %s' % target)
        if(not self.path_exists(target, file_type='file')
        or not self.path_exists(target, file_type='executable')):
            raise Exception('target is not an executable file: %s' % target)
        o = self.shell([target, '--gtest_list_tests'])
        tmp = ''
        res = []
        for l in o.splitlines():
            if l and not 'ALL TESTS SUCCEEDED' in l:
                if not l.startswith('  '):
                    tmp = l
                else:
                    res.append(tmp + l.strip())
        return res

    def run_gtest(self, target, result_path=None, args=[], timeout=0):
        ##### TODO: remove this and use Handset.shell() when it raises RunError
        def execute_cmd(args, timeout=0):
            orig_args = args
            if type(args) in [str, unicode]:
                args = [a for a in args.split() if a != '']
            cmds = ['-s', self.profile['serial'], 'shell']
            cmds.extend(args)
            s,o = run_adb(cmds, timeout)
            if s != 0:
                message = 'Failed to execute: %s' % cmds
                state,sysfs=HandsetLister.get_handset_power_state(self.profile)
                if state == 'offline':
                    raise Offline('Handset is offline. %s' % message)
                else:
                    raise RunError(cmds, o, message)
            lines = o.splitlines()
            if (lines
            and lines[0].startswith('/system/')
            and lines[0].endswith('not found')):
                raise Exception('no such executable: %s' % orig_args)
            setup_executed = False
            teardown_executed = False
            for line in lines:
                if line.startswith('[----------] Global test environment '
                                   'set-up'):
                    setup_executed = True
                if line.startswith('[----------] Global test environment '
                                   'tear-down'):
                    teardown_executed = True
            if not setup_executed or not teardown_executed:
                raise Exception('invalid executable: %s.\n%s' % (orig_args, o))
            return o
        #######################################################################

        # validation of parameter types
        if not target or not isinstance(target, basestring):
            raise Exception('target must be a non-empty string')
        if result_path:
            if not isinstance(result_path, basestring):
                raise Exception('result_path must be a non-empty string')
            if not os.path.exists(result_path):
                raise Exception('result_path does not exist: %s' % result_path)
            if(not os.path.isdir(result_path)
            or not os.access(result_path, os.W_OK)):
                raise Exception(
                    'result_path not a writable directory: %s' % result_path
                )
        if not isinstance(timeout, int):
            raise Exception('timeout must be an integer')
        if not isinstance(args, list):
            raise Exception('args must be a list of strings')
        for s in args:
            if not s or not isinstance(s, basestring):
                raise Exception('args must be a list of strings')
        # target must be an executable file
        if not self.path_exists(target):
            raise Exception('target does not exist: %s' % target)
        if(not self.path_exists(target, file_type='file')
        or not self.path_exists(target, file_type='executable')):
            raise Exception('target is not an executable file: %s' % target)

        cmd = [target]
        out_path, xml_path = None, None
        # create dir on handset
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if result_path:
            # create file paths/names
            out_name = '%s_output_%s.txt' % (os.path.basename(target),timestamp)
            xml_name = '%s_result_%s.xml' % (os.path.basename(target),timestamp)
            out_path = os.path.join(result_path, out_name)
            xml_path = os.path.join(result_path, xml_name)
            dut_dir = '/data/local/tmp/%s' % timestamp
            self.mkdir(dut_dir, parents=True)
            xml_on_dut = dut_dir + '/' + xml_name
            cmd.append('--gtest_output=xml:%s' % xml_on_dut)

        cmd.extend(args)
        o = execute_cmd(cmd, timeout=timeout)
        # get rid of empty lines
        lines = [l for l in o.splitlines() if l]
        output = '\n'.join(lines)
        if result_path:
            # write output to file
            fp = open(out_path, 'a') # (append)
            fp.write(output)
            fp.close()
            # get and remove XML result file from handset
            self.pull(xml_on_dut, xml_path)
            self.rm(dut_dir, recursive=True)

        return (output, out_path, xml_path)

    def set_libc_debug_malloc(self, on, package, timeout=45):
        def _check_timeout(limit):
            if limit and limit < datetime.now():
                raise Timeout({
                    'cmd'    : 'Handset.set_libc_debug_malloc(%s,%s,%s)' % (
                        on,package, org_timeout
                    ),
                    'out'    : '',
                    'message': 'set_libc_debug_malloc timed out'
                })

        # validate parameters
        if not isinstance(on, bool):
            raise Exception('"on" must be a boolean value')
        if not package or not isinstance(package, basestring):
            raise Exception('package must be a non-empty string')
        if not type(timeout) in [int, float]:
            raise Exception('timeout must be of type int or float')
        # setup timeout limit
        org_timeout = timeout
        limit = None
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        # check if the property is set
        try:
            self.get_property('libc.debug.malloc')
            was_set = True
        except Exception as e:
            if 'failed to get property with key: libc.debug.malloc' != str(e):
                raise e
            was_set = False
        # toggle property if needed (must run as root for this)
        if on and not was_set:
            self.root()
            self.set_property('libc.debug.malloc', '1')
        elif not on and was_set:
            self.root()
            self.clear_property('libc.debug.malloc')
        # stop / start and wait until the process is up and running again
        if (on and not was_set) or (not on and was_set):
            self.shell('stop')
            time.sleep(1)
            self.shell('start')
            while not self.get_processes(name=package, exact=True):
                _check_timeout(limit)
                time.sleep(1)
        return was_set

    def dump_heap(self, directory, package, native=False, timeout=30):
        def _get_adjusted_timeout(timeout, limit):
            if limit:
                new_delta = limit - datetime.now()
                timeout = (new_delta.microseconds + (new_delta.seconds +
                    new_delta.days*24*3600) * 10000000)/float(10000000)
                if timeout <= 0:
                    raise Timeout({
                        'cmd'    : 'Handset.dumpheap(%s,%s,%s,%s)' % (directory,
                        package, native, org_timeout),
                        'out'    : '',
                        'message': 'dumpheap timed out'
                    })
            return timeout

        # sanity checks
        if not directory or not isinstance(directory, basestring):
            raise Exception('directory must be a non-empty string')
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise Exception('not an existing directory: %s' % directory)
        if not package or not isinstance(package, basestring):
            raise Exception('package must be a non-empty string')
        if not isinstance(native, bool):
            raise Exception('native must be a boolean value')
        if not type(timeout) in [int, float]:
            raise Exception('timeout must be of type int or float')
        sdk = self.get_sdk_version()
        if sdk < 14:
            raise Exception(
                'dump_heap not supported on sdk versions < 14; handset\'s sdk '
                'version: %d' % sdk
            )
        # setup timeout limit
        org_timeout = timeout
        limit = None
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)

        cmd = ['am ','dumpheap']
        if native:
            key = 'libc.debug.malloc'
            # check that the required property is set
            try:
                self.get_property(key)
            except Exception as e:
                if 'failed to get property with key: %s' % key == str(e):
                    raise Exception(
                        'dump_heap on native heap requires property "%s" to be'
                        ' set, see Handset.set_libc_debug_malloc()' % key
                    )
                raise Exception(e)
            cmd.append('-n')
        # get the package's pids
        pids = self.get_processes(name=package, exact=True)
        if not pids: # retry once (have seen incorrectness here a few times)
            pids = self.get_processes(name=package, exact=True)
            if not pids:
                raise Exception('no process found for package: %s' % package)
        # for each pid found for package (normally only one)
        paths = []
        for p in pids:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name      = '%s-AVE-Generated-%s.hprof' % (p['name'], timestamp)
            target    = os.path.join(
                '/data', 'local', 'tmp', os.path.basename(name)
            )
            cmd.extend([str(p['pid']), target])
            # execute am dumpheap
            o = self.shell(cmd, timeout=timeout)
            # check if error
            if 'Error: Unknown process:' in o:
                self.rm(target)
                reason1 = 'not an application process'
                reason2 = 'application not debuggable'
                reason3 = 'process %s is no longer running' % p
                raise Exception(
                    'dump_heap failed: %s, %s or %s' % (reason1,reason2,reason3)
                )
            elif 'Error: Unable to open file:' in o:
                raise Exception(
                    'dump_heap failed: unable to open file %s on handset'%target
                )
            dest = os.path.join(directory, os.path.basename(target))
            if 'root' in self.shell(['ls','-l',target]).split():
                self.root() # must run as root to get files generated as root
            # resulting file is not always ready when am dumpheap returns,
            # make sure am dumpheap is done before pulling the file
            done = False
            while not done:
                timeout = _get_adjusted_timeout(timeout, limit)
                size0 = int(self.shell(['ls','-l',target]).split()[-4])
                time.sleep(0.5)
                size1 = int(self.shell(['ls','-l',target]).split()[-4])
                if size0 != 0 and size0 == size1:
                    done = True
            # pull hprof file
            timeout = _get_adjusted_timeout(timeout, limit)
            self.pull(target, dest, timeout=timeout)
            paths.append(dest)
            # clean up afterwards
            self.rm(target)
        return paths

    ### Doze AND App Standby ############################################
    def set_inactive(self, package, value):
        if self.get_sdk_version() < 23:
            raise Exception('App Standby is not supported on API levels < 23')
        else:
            self.shell(['am', 'set-inactive', package, value])

    def get_inactive(self, package):
        if self.get_sdk_version() < 23:
            raise Exception('App Standby is not supported on API levels < 23')
        else:
            state = self.shell(['am', 'get-inactive', package])
            return state

    def dumpsys_battery(self, operate='unplug'):
        if self.get_sdk_version() < 23:
            raise Exception('Doze is not supported on API levels < 23')
        else:
            self.shell(['dumpsys', 'battery', operate])

    def dumpsys_deviceidle(self, command, para=None):
        if self.get_sdk_version() < 23:
            raise Exception('Doze is not supported on API levels < 23')
        else:
            cmd = ['dumpsys', 'deviceidle', command]
            if para:
                cmd.extend([para])
            state = self.shell(cmd)
            return state
