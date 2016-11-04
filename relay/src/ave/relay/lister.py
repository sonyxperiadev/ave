# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import time
import json
import select

from ctypes import *

from ave.relay.profile      import BoardProfile
from ave.network.process    import Process
from ave.network.control    import RemoteControl
from ave.network.exceptions import *

class RelayLister(Process):
    c_library = None
    port      = 0
    authkey   = None
    serials   = None
    timeout   = None

    def __init__(self, port, authkey, logging):
        self.port     = port
        self.authkey  = authkey
        self.logging  = logging
        self.profiles = {} # map sysfs paths to device profiles
        self.load_libudev()
        Process.__init__(self, None, None, logging, 'ave-relay-lister')

    def list_equipment(self):
        udev = self.udev_new()
        return self.scan(udev)

    def find_device_node(self, sysfs_path):
        # the kernel should have claimed the raw USB CDC device and created
        # another device node to represent the serial device. find it.
        for (dirpath, dirname, filenames) in os.walk(sysfs_path):
            for node in dirname:
                if node.startswith('ttyACM'):
                    return os.path.join('/dev',node)
        raise Exception('kernel did not create serial device node')

    def is_equipment(self, dev):
        vendor  = self.get_sysattr(dev, 'idVendor')
        product = self.get_sysattr(dev, 'idProduct')
        if vendor == '04d8' and product == 'ffee':
            return True # devantech
        try:
            # QuancomBoard module not installed,
            # ignore quancom equipment
            from ave.relay.quancom import QuancomBoard
            if vendor == '0a7c' and product == '0014':
                return True  # quancom
        except:
            pass
        return False

    def get_vendor_name(self, dev):
        vendor  = self.get_sysattr(dev, 'idVendor')
        product = self.get_sysattr(dev, 'idProduct')
        if vendor == '04d8' and product == 'ffee':
            return 'devantech'
        if vendor == '0a7c' and product == '0014':
            return 'quancom'
        return None

    def get_product_name(self, dev):
        vendor  = self.get_sysattr(dev, 'idVendor')
        product = self.get_sysattr(dev, 'idProduct')
        if vendor == '04d8' and product == 'ffee':
            return 'usb-rly16l'
        if vendor == '0a7c' and product == '0014':
            return 'usbrel64'
        return None

    def make_profile(self, dev, sysfs_path, power_state):
        try:
            device_node = self.find_device_node(sysfs_path)
        except:
            device_node = None
        return BoardProfile({
           'vendor'     : self.get_vendor_name(dev),
           'product'    : self.get_product_name(dev),
           'serial'     : self.get_sysattr(dev, 'serial'),
           'sysfs_path' : sysfs_path,
           'device_node': device_node,
           'power_state': power_state
        })

    def scan(self, udev):
        enum = self.new_enum(udev)
        if not enum:
            raise Exception('new_enum() failed')
        if self.set_enum_filter(enum, 'usb'):
            raise Exception('set_enum_filter() failed')
        if self.scan_devs(enum):
            raise Exception('scan_devs() failed')

        result = []
        entry  = self.enum_get_list(enum)
        while entry:
            if not entry:
                break
            path = self.list_get_name(entry)
            dev  = self.syspath_to_device(udev, path)
            if self.is_equipment(dev):
                # create the basic equipment profile from the udev entry
                result.append(self.make_profile(dev, path, 'online'))
            self.unref_device(dev)
            entry = self.list_get_next(entry)
        return result

    def monitor(self, udev):
        mon = self.new_monitor(udev, 'udev')
        if not mon:
            raise Exception('new_monitor() failed')
        self.set_monitor_filter(mon, 'usb', 'usb_device')
        self.enable(mon)
        fd = self.fileno(mon)
        if not fd:
            raise Exception('failed to get fd')
        return mon, fd

    def run(self):
        udev = self.udev_new()
        if not udev:
            raise Exception('udev_new() failed')

        profiles = self.scan(udev)
        for p in profiles:
            self.profiles[p['sysfs_path']] = p
        self.report_equipment(profiles)

        mon, fd = self.monitor(udev)
        while True:
            try: # listen for actions
                self.listen(mon, fd)
            except KeyboardInterrupt:
                break
            except OSError:
                break
            except Exception, e:
                self.log(traceback.format_exc())
                self.log(e)

    def listen(self, monitor, fd):
        r, w, x = select.select([fd], [], [])
        if not (r or w or x):
            self.log('select() failed')

        def probe(device):
            # mandatory udev error handling. expected to never catch anything
            if not device:
                self.log('get_device() failed')
                return None
            sysfs_path = self.get_syspath(device)
            if not sysfs_path:
                self.log('get_syspath() failed')
                return None
            action = self.get_action(device)
            if not action:
                self.log('get_action() failed')
                return None
            # build the device profile
            if action == 'add':
                if not self.is_equipment(device):
                    return None
                profile = self.make_profile(device, sysfs_path, 'online')
                self.profiles[sysfs_path] = profile
                return profile
            elif sysfs_path in self.profiles:
                profile = self.profiles[sysfs_path]
                profile['power_state'] = 'offline'
                profile['device_node'] = None
                del(self.profiles[sysfs_path])
                return profile
            else: # some other USB device was removed
                pass

        device  = self.get_device(monitor)
        profile = probe(device)
        self.unref_device(device)
        if profile:
            self.report_equipment([profile])

    def report_equipment(self, profiles):
        self.log(
            'report equipment to server:\n%s' % json.dumps(profiles, indent=4)
        )
        remote_control = RemoteControl(('', self.port), self.authkey, timeout=5)
        try:
            remote_control.set_boards(profiles)
        except ConnectionClosed:
            self.log('lister: server closed the connection')
        except AveException, e:
            self.log(
                'ERROR: server raised exception: %s%s' % (e.format_trace(), e)
            )
        except Exception, e:
            self.log('WARNING: lister could not report: %s' % str(e))

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

    def load_libudev(self):
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
