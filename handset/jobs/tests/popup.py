# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.
import time
from time import sleep

from decorators import smoke

RESET_TIMEOUT  = 240
REBOOT_TIMEOUT = 120

def is_package_enabled(handset, package):
    dump = handset.shell('pm list package -e')
    if package in dump:
        return True
    else:
        return False

# test that enable_package_verifier() works
@smoke
def t05(w, h):
    pretty = '%s t5' % __file__
    print(pretty)

    h.root()

    try:
        h.enable_package_verifier()
    except Exception, e:
        print('FAIL %s: enable_package_verifier() failed: %s' % (pretty, e))
        return False

    # if we can install galatea, the package verifier was not enabled. fail the
    # test even if installation fails because we don't know yet how to verify
    # the installation failure if the SDK version is less than 21. i.e. be truly
    # pessimistic until we know better.
    try:
        galatea_path = h.get_galatea_apk_path()
        h.reinstall(galatea_path)
    except Exception, e:
        if h.get_sdk_version >= 21:
            dump = h.shell(['dumpsys','window'])
            if "com.android.vending" in dump:
                return True
            else:
                return False

    return False

# test that disable_package_verifier() works
@smoke
def t06(w, h):
    pretty = '%s t6' % __file__
    print(pretty)

    h.root()

    try:
        h.disable_package_verifier()
    except Exception, e:
        print('FAIL %s: enable_package_verifier() failed: %s' % (pretty, e))
        return False

    # if we can install galatea, the package verifier was not enabled
    try:
        galatea_path = h.get_galatea_apk_path()
        h.reinstall(galatea_path)
    except Exception, e:
        print e
        return False

    return True

#test enable and disable usb mode chooser window
def t27(w,h):
    pretty = '%s t27' % __file__
    print(pretty)

    try:
        h.root()
        h.disable_usb_mode_chooser()
        time.sleep(2)
        for window in h.shell(['dumpsys', 'window']).splitlines():
            if 'UsbModeChooserActivity' in window:
                print('FAIL %s: disable usb mode chooser window failed' % pretty)
                return False

        h.enable_usb_mode_chooser()
        h.reboot()
        h.wait_power_state('boot_completed', timeout=120)
        h.root()
        time.sleep(2)
        for window in h.shell(['dumpsys', 'window']).splitlines():
            if 'UsbModeChooserActivity' in window:
                return True

        print('FAIL %s: enable usb mode chooser window failed' % pretty)
        return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
