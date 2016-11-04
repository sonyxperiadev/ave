# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import traceback
import signal
import select
import time
import copy
import errno
import socket
import json

from ctypes           import *
from datetime         import datetime, timedelta

from ave.handset.profile    import HandsetProfile
from ave.network.control    import RemoteControl
from ave.network.process    import Process
from ave.network.exceptions import *

import ave.cmd
import ave.config

def handle_SIGTERM(signum, frame):
    os._exit(0)

def handle_SIGUSR1(signum, frame):
    pass # do not die

# ensures that SIGTERM is sent to this process when its parent dies
def set_PDEATHSIG():
    libc = CDLL('libc.so.6')
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

def set_PR_SET_NAME(name):
    libc = CDLL('libc.so.6')
    PR_SET_NAME = 15
    libc.prctl(PR_SET_NAME, name, 0, 0, 0)


def load_handset_config(path):
    config = ave.config.load(path)

    if 'handsets' not in config:
        raise Exception('invalid config file, no "handsets".')

    handset = config["handsets"]
    for h in handset:
        if not h.has_key('model'):
            raise Exception('invalid config file, no "model" entry: %s' % h)
        if not h.has_key('pretty'):
            raise Exception('invalid config file, no "pretty" entry: %s' % h)

        # Remove the limitation of the properties in handset.json
        '''
        entries = ['model', 'pretty', 'variant', 'shutdown', 'boot_to_service', 'magic', 'chipset']
        if not set(h.keys()).issubset(set(entries)):
            raise Exception('invalid config file, entries must be in %s' % entries)
        '''

    if 'vendors' not in config:
        config['vendors'] = []

    return config


def merge_handset_config(predefine=None, custom=None):
    if custom is None:
        home = ave.config.load_etc()['home']
        custom = os.path.join(home, '.ave', 'config', 'handset.json')
    if predefine is None:
        predefine = '/usr/share/ave/handset/handset.json'

    pre_config = load_handset_config(predefine)
    custom_config = []
    try:
        custom_config = load_handset_config(custom)
    except Exception, e:
        # if the local config file is invalid, ignore the local
        # config, and just use the lib config
        return pre_config

    pre_handsets = pre_config['handsets']
    custom_handsets = custom_config['handsets']

    pre_models = {}
    custom_models = {}
    for i in range(len(pre_handsets)):
        if pre_handsets[i]['model'] == None:
            continue
        else:
            pre_models[pre_handsets[i]['model'].lower()] = i

    for i in range(len(custom_handsets)):
        if custom_handsets[i]['model'] == None:
            continue
        else:
            custom_models[custom_handsets[i]['model'].lower()] = i

    for k in custom_models.keys():
        # if the value of "model" is None, or empty string
        # ignore it, and continue
        if not k or k.strip() == '':
            continue
        if k in pre_models.keys():
            pre_h = pre_handsets[pre_models[k]]
            custom_h = custom_handsets[custom_models[k]]
            pre_h['model'] = k
            pre_h['pretty'] = custom_h['pretty']
            if custom_h.has_key('variant'):
                pre_h['variant'] = custom_h['variant']
            elif pre_h.has_key('variant'):
                del pre_h['variant']
            if custom_h.has_key('shutdown'):
                pre_h['shutdown'] = custom_h['shutdown']
            elif pre_h.has_key('shutdown'):
                del pre_h['shutdown']
            if custom_h.has_key('magic'):
                pre_h['magic'] = custom_h['magic']
            elif pre_h.has_key('magic'):
                del pre_h['magic']
            if custom_h.has_key('boot_to_service'):
                pre_h['boot_to_service'] = custom_h['boot_to_service']
            elif pre_h.has_key('boot_to_service'):
                del pre_h['boot_to_service']
        else:
            loh = custom_handsets[custom_models[k]]
            loh['model'] = k
            pre_handsets.append(loh)

    pre_vendors = pre_config['vendors']
    custom_vendors = custom_config['vendors']
    if pre_vendors or custom_vendors:
        pre_vendors.extend(custom_vendors)
    return {'handsets': pre_handsets, 'vendors': pre_vendors}


class HandsetLister(Process):
    port    = None
    authkey = None
    paths   = None # sysfs paths to filter. None selects all
    handset_config = None
    vendors = None


    # TODO: HSL to handle serials
    def __init__(self, port, authkey, paths=None, logging=True):
        self.port           = port
        self.authkey        = authkey
        self.activities     = {} # dict with processes, keys:sysfs_path
        self.serials        = {} # map sysfs paths to serial numbers
        self.paths          = paths
        self.config = merge_handset_config()
        self.vendors = self.config['vendors'][0]
        HandsetLister.handset_config = self.config['handsets']
        Process.__init__(
            self, target=self.run, logging=logging,
            proc_name='ave-handset-lister'
        )

    def run(self):
        self.set_signal_handlers()
        set_PR_SET_NAME('ave-handset-lister')
        HandsetLister.load_library(self)
        udev = self.udev_new()
        if not udev:
            raise Exception('udev_new() failed')
        # set initial state(s)
        self.begin(udev)
        mon, fd = self.setup_monitor(udev)
        while True:
            try:
                # listen for actions
                self.select_on_fd(mon, fd)
            except KeyboardInterrupt:
                break
            except OSError:
                break
            except:
                self.log(traceback.format_exc())

    def begin(self, udev):
        enum = self.new_enum(udev)
        if not enum:
            raise Exception('new_enum() failed')
        if self.set_enum_filter(enum, 'usb'):
            raise Exception('set_enum_filter() failed')
        if self.scan_devs(enum):
            raise Exception('scan_devs() failed')
        entry = self.enum_get_list(enum)
        while entry:
            if not entry:
                break
            path = self.list_get_name(entry)
            if self.paths != None and path not in self.paths:
                entry = self.list_get_next(entry)
                continue # ignore this device
            dev = self.syspath_to_device(udev, path)

            if  self.get_sysattr(dev, 'idVendor') not in self.vendors:
                self.unref_device(dev)
                entry = self.list_get_next(entry)
                continue # ignore non-Sony devices for now

            # report the device
            try:
                profile = self.make_udev_profile('add', path, dev)
                self.start_reporting('add', profile)
            except Exception, e:
                self.log('WARNING: %s' % e)
            self.unref_device(dev)
            entry = self.list_get_next(entry)

    def setup_monitor(self, udev):
        mon = self.new_monitor(udev, 'udev')
        if not mon:
            raise Exception('new_monitor() failed')
        self.set_monitor_filter(mon, 'usb', 'usb_device')
        self.enable(mon)
        fd = self.fileno(mon)
        if not fd:
            raise Exception('failed to get fd')
        return mon, fd

    # wait for state change
    def select_on_fd(self, mon, fd):
        try:
            r, w, x = select.select([fd], [], [])
        except select.error, e:
            if e[0] == errno.EINTR: # received e.g. SIGUSR1 (hickup)
                return # let caller decide how to proceed
        if not (r or w or x):
            raise Exception('select() failed')
        dev = self.get_device(mon)
        if not dev:
            raise Exception('get_device() failed')
        path = self.get_syspath(dev)
        if not path:
            raise Exception('get_syspath() failed')
        if self.paths != None and path not in self.paths:
            self.unref_device(dev)
            return # ignore this device
        action = self.get_action(dev)
        if not action:
            raise Exception('get_action() failed')
        if action == 'add' and self.get_sysattr(dev, 'idVendor') not in self.vendors:
            return

        try:
            profile = self.make_udev_profile(action, path, dev)
            self.start_reporting(action, profile)
        except Exception, e:
            self.log('WARNING: %s' % e)
        self.unref_device(dev)

    def make_udev_profile(self, action, path, dev):
        if action == 'add':
            # calculate slid
            ### currently not in use
            # busnum    = int(self.get_sysattr(dev, 'busnum'))
            # devnum    = int(self.get_sysattr(dev, 'devnum'))
            # slid      = (busnum << 8) | devnum
            # version   = self.get_sysattr(dev, 'version')
            pid = self.get_sysattr(dev, 'idProduct')
            # check state
            if pid == 'adde':
                state  = 'service'
                if path in self.serials:
                    serial = self.serials[path]
                else:
                    raise Exception(
                        'HSL sees unknown service equipment: %s' % path
                    )
            else:
                state  = 'enumeration'
                serial = self.get_sysattr(dev, 'serial')
                self.serials[path] = serial
            # early return:
            return {
                'type'       : 'handset',
                'serial'     : serial,
                'sysfs_path' : path,
                'usb.vid'    : self.get_sysattr(dev, 'idVendor'),
                'usb.pid'    : pid,
                'power_state': state
            }

        if action == 'remove':
            if path in self.serials:
                serial = self.serials[path]
            else:
                raise Exception('HSL sees unknown offline equipment: %s' % path)
            return {
                'type'       : 'handset',
                'serial'     : serial,
                'sysfs_path' : path,
                'power_state': 'offline'
            }

        raise Exception('unhandled action: %s' % action)

    def start_reporting(self, action, profile):
        # kill already running reporter, if any exists for this sysfs path
        if profile['sysfs_path'] in self.activities.keys():
            self.kill_if_alive(self.activities[profile['sysfs_path']])
        # start the reporter process
        p = Process(
            target = HandsetLister.report_to_broker,
            args   = (self.port, self.authkey, profile)
        )
        p.start()
        if action == 'add':
            self.activities[profile['sysfs_path']] = p
        else:
            p.join()

    # assumption: profile['power_state'] in ['enumeration','offline','service']
    @classmethod
    def report_to_broker(cls, port, authkey, profile):
        signal.signal(signal.SIGTERM, handle_SIGTERM)
        set_PDEATHSIG()
        set_PR_SET_NAME('ave-handset-reporter')

        if not 'serial' in profile.keys():
            raise Exception('handset serial not set in profile' % profile)

        remote_control = RemoteControl(('', port), authkey, timeout=5)
        def report(profile):
            #print('report %s' % profile)
            try:
                remote_control.add_equipment('local', [profile])
            except ConnectionClosed:
                #print('WARNING: broker closed connection when reporting')
                return
            except Exception, e:
                #print('WARNING: broker exception when reporting: %s' % e)
                return

        #add workstation name to handset's profile
        profile['workstation'] = socket.gethostbyaddr(socket.gethostname())[0]

        # handling offline and service. no need to check these again in the
        # extended property handling because a new udev event will be caught
        # if the USB connectvity changes
        if profile['power_state'] in ['offline', 'service']:
            report(profile)
            return

        # handling of "online" handsets. first figure out the power state of
        # the handset. then which platform is running on the handset. finally
        # query platform specific properties to give the broker more stuff to
        # match against allocation requests. repeat forever and keep reporting
        # to the broker
        from ave.handset.handset import Handset
        h = Handset(HandsetProfile(profile))

        limit = None
        while True:
            if limit and limit < datetime.now():
                limit = None
                profile['power_state'] = 'draining' # discovery timed out
                report(profile)
                time.sleep(10) # status unlikely to change soon
                continue

            old = copy.deepcopy(profile) # only report if any change is seen

            profile['power_state'] = cls.get_online_power_state(h)
            if profile['power_state'] == 'enumeration':
                if not limit:
                    limit = datetime.now() + timedelta(seconds=120)
                if profile != old:
                    report(profile)
                time.sleep(1.5) # a quick nap. status likely to change soon
                continue
            else:
                limit = None # avoid setting power state to draining

            # the platform must be determined before any other property because
            # extracting other properties may be implemented with functions that
            # have different implementations on different platforms. recreate
            # the handset object afterwards to give it the platform specific
            # implementation.
            profile['platform'] = h.get_platform()
            h = Handset(HandsetProfile(profile))
            profile = h.update_profile(profile)
            profile['pretty'] = cls.get_pretty(profile['product.model'])

            if profile != old:
                report(profile)
                time.sleep(3) # let it rest for a while
            else:
                time.sleep(6)  # let it rest a little longer
            continue

    @classmethod
    def get_pretty(cls, model):
        for h in cls.handset_config:
            if model.lower() == h['model']:
                return h['pretty'] if h.has_key('pretty') else None
        return None

    @classmethod
    def get_online_power_state(cls, h):
        if h.boot_completed():
            return 'boot_completed'
        try:
            if h.pm_ready():
               return 'package_manager'
        except:
            pass
        if h.has_adb():
            return 'adb'
        return 'enumeration'

    # if process p is still alive it should be terminated
    def kill_if_alive(self, p):
        try:
            if p and p.is_alive():
                p.terminate()
                p.join()
        except Exception, e:
            self.log('WARNING: kill if alive failed: %s' % e)

    def set_signal_handlers(self):
        signal.signal(signal.SIGTERM, handle_SIGTERM)
        signal.signal(signal.SIGUSR1, handle_SIGUSR1)
        set_PDEATHSIG()

    def select_dll(self):
        try:
            self.c_library = CDLL('libudev.so.1')
            return
        except:
            pass
        try:
            self.c_library = CDLL('libudev.so.0')
        except Exception, e:
            raise Exception('could not load libudev: %s' % e)

    @classmethod
    def load_library(cls, self):
        self.select_dll()

        self.udev_new = self.c_library.udev_new
        self.udev_new.restype = c_void_p
        self.udev_new.argtypes = []

        self.new_monitor = self.c_library.udev_monitor_new_from_netlink
        self.new_monitor.restype = c_void_p
        self.new_monitor.argtypes = [c_void_p, c_char_p]

        self.set_monitor_filter = (
            self.c_library.udev_monitor_filter_add_match_subsystem_devtype
        )
        self.set_monitor_filter.restype = c_int
        self.set_monitor_filter.argtypes = [c_void_p, c_char_p, c_char_p]

        self.enable = self.c_library.udev_monitor_enable_receiving
        self.enable.restype = c_int
        self.enable.argtypes = [c_void_p]

        self.fileno = self.c_library.udev_monitor_get_fd
        self.fileno.restype = c_int
        self.fileno.argtypes = [c_void_p]

        self.get_device = self.c_library.udev_monitor_receive_device
        self.get_device.restype = c_void_p
        self.get_device.argtypes = [c_void_p]

        self.get_syspath = self.c_library.udev_device_get_syspath
        self.get_syspath.restype = c_char_p
        self.get_syspath.argtypes = [c_void_p]

        self.get_action = self.c_library.udev_device_get_action
        self.get_action.restype = c_char_p
        self.get_action.argtypes = [c_void_p]

        self.get_sysattr = self.c_library.udev_device_get_sysattr_value
        self.get_sysattr.restype = c_char_p
        self.get_sysattr.argtypes = [c_void_p, c_char_p]

        self.unref_device = self.c_library.udev_device_unref
        self.unref_device.restype = c_void_p
        self.unref_device.argtypes = [c_void_p]

        self.new_enum = self.c_library.udev_enumerate_new
        self.new_enum.restype = c_void_p
        self.new_enum.argtypes = [c_void_p]

        self.set_enum_filter = self.c_library.udev_enumerate_add_match_subsystem
        self.set_enum_filter.restype = c_int
        self.set_enum_filter.argtypes = [c_void_p, c_char_p]

        self.scan_devs = self.c_library.udev_enumerate_scan_devices
        self.scan_devs.restype = c_int
        self.scan_devs.argtypes = [c_void_p]

        self.enum_get_list = self.c_library.udev_enumerate_get_list_entry
        self.enum_get_list.restype = c_void_p
        self.enum_get_list.argtypes = [c_void_p]

        self.list_get_next = self.c_library.udev_list_entry_get_next
        self.list_get_next.restype = c_void_p
        self.list_get_next.argtypes = [c_void_p]

        self.list_get_name = self.c_library.udev_list_entry_get_name
        self.list_get_name.restype = c_char_p
        self.list_get_name.argtypes = [c_void_p]

        self.syspath_to_device = self.c_library.udev_device_new_from_syspath
        self.syspath_to_device.restype = c_void_p
        self.syspath_to_device.argtypes = [c_void_p, c_char_p]

        self.unref_udev = self.c_library.udev_unref
        self.unref_udev.restype = c_void_p
        self.unref_udev.argtypes = [c_void_p]

        self.unref_enum = self.c_library.udev_enumerate_unref
        self.unref_enum.restype = c_void_p
        self.unref_enum.argtypes = [c_void_p]


### GET POWER STATE - USED BY HANDSET CLASS ONLY ##############################

    # for handset with given profile returning (enumeration | offline | service)
    @classmethod
    def get_handset_power_state(cls, profile):
        state = None
        if 'serial' not in profile.keys() and 'sysfs_path' not in profile:
            raise Exception('no serial or sysfs_path in profile %s:' % profile)
        hsl = HandsetLister(0, '')
        HandsetLister.load_library(hsl)
        # new udev
        udev = hsl.udev_new()
        if not udev:
            raise Exception('udev_new() failed')
        # set initial state(s)
        enum = hsl.new_enum(udev)
        if not enum:
            raise Exception('new_enum() failed')
        if hsl.set_enum_filter(enum, 'usb'):
            raise Exception('set_enum_filter() failed')
        if hsl.scan_devs(enum):
            raise Exception('scan_devs() failed')
        entry = hsl.enum_get_list(enum)
        while entry:
            if not entry:
                break
            path = hsl.list_get_name(entry)
            dev = hsl.syspath_to_device(udev, path)
            vid = hsl.get_sysattr(dev, 'idVendor')
            if vid not in hsl.vendors:
                # not Sony device, skip
                hsl.unref_device(dev)
                entry = hsl.list_get_next(entry)
                continue
            pid = hsl.get_sysattr(dev, 'idProduct')
            if((profile['sysfs_path'] and profile['sysfs_path'] == path)
            and pid == 'adde'):
                state  = 'service'
            else:
                serial = hsl.get_sysattr(dev, 'serial')
                if profile['serial'] and profile['serial'] == serial:
                    hsl.unref_udev(udev)
                    hsl.unref_enum(enum)
                    hsl.unref_device(dev)
                    return 'enumeration', path
            hsl.unref_device(dev)
            entry = hsl.list_get_next(entry)

        hsl.unref_udev(udev)
        hsl.unref_enum(enum)

        if not state:
            return 'offline', None
        return state, None
