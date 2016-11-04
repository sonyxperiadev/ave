# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import re
import time
import traceback

from ave.network.exceptions import RemoteTimeout, RemoteRunError
from ave.exceptions         import Timeout, RunError

import ave.apk
import ave.cmd

from decorators import smoke


def download_apk_to_ws(pretty,w,label):
    path         = w.download_c2d('test-semcclock', label=label)
    unpacked     = w.unpack_c2d(path)
    apk_path     = unpacked.strip() + '/test/test-SemcClock.apk'
    return apk_path

# Checks if get_profile() returns a profile containing some expected values.
def t01(w,h,label):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        p = h.get_profile()
    except Exception, e:
        print('FAIL %s: get_profile: %s' % (pretty, e))
        return False
    if not 'type' in p:
        print('FAIL %s: "type" is missing: %s' % (pretty, p))
        return False
    if not 'platform' in p:
        print('FAIL %s: "platform" is missing: %s' % (pretty, p))
        return False
    if not 'serial' in p:
        print('FAIL %s: "serial" is missing: %s' % (pretty, p))
        return False
    if not 'pretty' in p:
        print('FAIL %s: "pretty" is missing: %s' % (pretty, p))
        return False
    return True

# Test that list_packages() returns correctly
def t03(w,h,label):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        pkgs = h.list_packages()
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: list_packages() failed: %s' % (pretty, str(e)))
        return False
    if pkgs is None:
        print('FAIL %s: list_packages() returned None' % pretty)
        return False
    elif type(pkgs) is not list:
        print('FAIL %s: list_packages() didn\'t return a list' % pretty)
        return False
    return True
# Test that list_permissions() returns correctly
def t04(w,h,label):
    pretty = '%s t4' % __file__
    print(pretty)

    try:
        permissions = h.list_permissions()
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: list_permissions() failed: %s' % (pretty, str(e)))
        return False

    if permissions.startswith('Dangerous Permissions:'):
        return True
    else:
        print('FAIL %s: list_permissions() didn\'t correct return:\n%s' % (str(permissions)))
        return False

#Test that grant_permissions() returns  correctly
def t05(w,h,label):
    pretty = '%s t5' % __file__
    print(pretty)

    package_name = 'com.example.android.system.runtimepermissions'
    permissions_test_apk=os.path.join(os.path.dirname(__file__), 'testdata',
                                'Application-debug.apk')

    if not h.is_installed(package_name):
        h.install(apk_path=permissions_test_apk)

    try:
        status=h.grant_permissions('com.example.android.system.runtimepermissions',
                                   'android.permission.WRITE_CONTACTS')
        if status is not True:
            return False
    except Exception, e:
        print ('FAIL %s: grant_permissions() execute error %s' % (pretty, str(e)))
        return False
    try:
        status=h.grant_permissions('com.example.android.system.runtimepermissions',
                                   'android.permission.DELETE_PACKAGES')
        print ('FAIL grant_permission() execute error %s' % status)
        return False
    except Exception, e:
        return True

#Test that revoke_permissions() returns  correctly
def t02(w,h,label):
    pretty = '%s t2' % __file__
    print(pretty)
    package_name = 'com.example.android.system.runtimepermissions'
    permissions_test_apk=os.path.join(os.path.dirname(__file__), 'testdata',
                                'Application-debug.apk')

    if not h.is_installed(package_name):
        h.install(apk_path=permissions_test_apk)

    try:
        status=h.revoke_permissions('com.example.android.system.runtimepermissions',
                                   'android.permission.WRITE_CONTACTS')
        if status is not True:
            return False
    except Exception, e:
        print ('FAIL %s: revoke_permissions() execute error %s' % (pretty, str(e)))
        return False
    try:
        status=h.revoke_permissions('com.example.android.system.runtimepermissions',
                                   'android.permission.DELETE_PACKAGES')
        print ('FAIL revoke_permission() execute error %s' % status)
        return False
    except Exception, e:
        return True

# check install raises exception if its parameters(args) are not correct
def t06(w,h,label):
    pretty = '%s t6' % __file__
    print(pretty)

    correct_args = ['-r', '-g', '-r -g', '-l -r -t -s -d -g']
    incorrect_args = ['-a', '-rg', '-r -a', '-abcdef']

    apk_path = h.get_galatea_apk_path()
    package = w.get_package_name(apk_path)

    for correct_arg in correct_args:
        try:
            h.uninstall(package)
            h.install(apk_path, args=correct_arg)
            if not h.is_installed(package):
                print('FAIL %s: apk was not installed by args[%s]'
                    % (pretty, correct_arg))
                return False
        except Exception, e:
            if 'args of install: %s is not correct' % correct_arg in str(e):
                print('FAIL %s: correct args [%s] were not accepted'
                    % (pretty, correct_arg))
                return False

    for incorrect_arg in incorrect_args:
        try:
            h.uninstall(package)
            h.install(apk_path, args=incorrect_arg)
            if h.is_installed(package):
                print('FAIL %s: apk was installed by args[%s]'
                    % (pretty, incorrect_arg))
                return False
        except Exception, e:
            if 'args of install: %s is not correct' % incorrect_arg not in str(e):
                print('FAIL %s: incorrect args [%s] were accepted'
                    % (pretty, incorrect_arg))
                return False
    h.uninstall(package)
    return True

# check install raises exception if apk does not exist on host
def t07(w,h,label):
    pretty = '%s t7' % __file__
    print(pretty)

    path = w.make_tempfile() + '.apk'

    try:
        print h.install(path)
        print('FAIL %s: could install path that does not exist' % pretty)
        return False
    except Exception, e:
        if 'no such apk file: ' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check reinstall raises exception if apk does not exist on host
def t08(w,h,label):
    pretty = '%s t8' % __file__
    print(pretty)

    path = w.make_tempfile() + '.apk'

    try:
        print h.reinstall(path)
        print('FAIL %s: could install path that does not exist' % pretty)
        return False
    except Exception, e:
        if 'no such apk file: ' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# Check that is_installed returns properly
@smoke
def t09(w,h,label):
    pretty = '%s t9' % __file__
    print(pretty)

    apk_path = h.get_galatea_apk_path()
    if not apk_path:
        return False
    package_name = package_name_test = output = None
    # Get package name from apk
    try:
        package_name = w.get_package_name(apk_path) # apk
        if not package_name:
            print(
                'FAIL %s: Could not get package name of apk: %s'
                % (pretty, apk_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    # Install or uninstall given apk
    def handle_installation(concerned_apk, install=True):
        try:
            if install:
                h.install(concerned_apk)
            else:
                h.uninstall(concerned_apk)
            return True
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False

    # Test "is_installed"; both when installed and not installed
    for i in range(2):
        try:
            pkgs_installed = h.list_packages()
            apk_installed = h.is_installed(package_name)
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False
        if apk_installed:
            if not package_name in pkgs_installed:
                print(
                    'FAIL %s: is_installed returned True - package not found a'
                    'mong installed pkgs' % pretty
                )
                return False
            if not handle_installation(package_name, install=False):
                return False
        else:
            if package_name in pkgs_installed:
                print(
                    'FAIL %s: is_installed returned False - package found amon'
                    'g installed pkgs' % pretty
                )
                return False
            if not handle_installation(apk_path):
                return False
    return True

# Check that install works with these conditions:
# 1) apk not installed
# 2) apk already installed
def t10(w,h,label):
    pretty = '%s t10' % __file__
    print(pretty)

    apk_path = h.get_galatea_apk_path()

    if not apk_path:
        return False
    package_name = package_name_test = output = None
    # Get package name from apk
    try:
        package_name = w.get_package_name(apk_path) # apk
        if not package_name:
            print(
                'FAIL %s: Could not get package name of apk: %s'
                % (pretty, apk_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    def test_install(package_name, apk_path_full):
        try:
            installed_before = h.is_installed(package_name)
            pkgs_installed = h.list_packages()
            num_pkgs_before = len(pkgs_installed)
            # test install
            h.install(apk_path_full)
            pkgs_installed = h.list_packages()
            num_pkgs_after = len(pkgs_installed)
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False
        if package_name not in pkgs_installed:
            print('FAIL %s: apk not listed on handset after install' % pretty)
            return False
        # if it was installed before, inc else eq
        if installed_before:
            if num_pkgs_before != num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after install; did'
                    'n\'t increase: before:%d != after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        else:
            if num_pkgs_before >= num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after install; bef'
                    'ore:%d >= after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        return True

    try:
        m_installed_before = h.is_installed(package_name)
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
        return False

    if m_installed_before:
        h.uninstall(package_name)
    if not test_install(package_name, apk_path):
        return False
    h.uninstall(package_name)
    return True

# Tests that uninstall works properly with these conditions:
# 1) apk installed
# 2) apk not installed
def t11(w,h,label):
    pretty = '%s t11' % __file__
    print(pretty)

    apk_path = h.get_galatea_apk_path()
    if not apk_path:
        return False
    package_name = package_name_test = output = None
    # Get package name from apk
    try:
        package_name = w.get_package_name(apk_path) # apk
        if not package_name:
            print(
                'FAIL %s: Could not get package name of apk: %s'
                % (pretty, apk_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    def test_uninstall(package_name):
        try:
            installed_before = h.is_installed(package_name)
            pkgs_installed = h.list_packages()
            num_pkgs_before = len(pkgs_installed)
            # test uninstall
            h.uninstall(package_name)
            pkgs_installed = h.list_packages()
            num_pkgs_after = len(pkgs_installed)
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False

        if package_name in pkgs_installed:
            print('FAIL %s: apk listed on handset after uninstall' % pretty)
            return False
        # if it was installed before, expect dec else eq
        if installed_before:
            if num_pkgs_before <= num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after uninstall; d'
                    'idn\'t decrease: before:%d >= after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        else:
            if num_pkgs_before != num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after uninstall; b'
                    'efore:%d != after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        return True

    try:
        m_installed_before = h.is_installed(package_name)
    except Exception, e:
        print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
        return False

    if not m_installed_before:
        h.install(apk_path)
    if not test_uninstall(package_name):
        return False
    return True

# Tests that reinstall works with these conditions:
# 1) apk not installed
# 2) apk already installed
@smoke
def t12(w,h,label):
    pretty = '%s t12' % __file__
    print(pretty)

    apk_path = h.get_galatea_apk_path()
    if not apk_path:
        return False
    package_name = package_name_test = output = None
    # Get package name from apk
    try:
        package_name = w.get_package_name(apk_path) # apk
        if not package_name:
            print(
                'FAIL %s: Could not get package name of apk: %s'
                % (pretty, apk_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    def test_reinstall(package_name, apk_path_full):
        try:
            installed_before = h.is_installed(package_name)
            pkgs_installed = h.list_packages()
            num_pkgs_before = len(pkgs_installed)
            # test reinstall
            h.reinstall(apk_path_full)

            pkgs_installed = h.list_packages()
            num_pkgs_after = len(pkgs_installed)
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False
        if package_name not in pkgs_installed:
            print('FAIL %s: apk not listed on handset after install' % pretty)
            return False
        # if it was installed before, inc else eq
        if installed_before:
            if num_pkgs_before != num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after reinstall; d'
                    'idn\'t increase: before:%d != after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        else:
            if num_pkgs_before >= num_pkgs_after:
                print(
                    'FAIL %s: unexpected number of packages after reinstall; b'
                    'efore:%d >= after:%d'
                    % (pretty, num_pkgs_before, num_pkgs_after)
                )
                return False
        return True

    try:
        m_installed_before = h.is_installed(package_name)
    except Exception, e:
        print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
        return False

    if not test_reinstall(package_name, apk_path):
        return False
    if m_installed_before:
        h.uninstall(package_name)
        if not test_reinstall(package_name, apk_path):
            return False
    else:
        if not test_reinstall(package_name, apk_path):
            return False
        h.uninstall(package_name)
    return True

# Check that property exists in /data/local.prop. NOTE: /data/local.prop is not
# supported on Jelly Bean and going forward due to security.
def t21(w,h,label):
    pretty = '%s t21' % __file__
    print(pretty)

    prop = 'property.locally.nice'
    val  = 'nice_value'

    # reset local properties
    try:
        h.clear_local_properties()
        h.reboot()
        h.wait_power_state('boot_completed', timeout=120)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    try: # set property and verify it's put into local.prop
        h.set_property(prop, val, local=True)
        cat_res = h.cat('/data/local.prop')
        kv = '%s=%s' % (prop, val)
        if not kv in cat_res:
            print('FAIL %s: expected %s in /data/local.prop' % (pretty, kv))
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    try: # verify that the set_property with local=True acts as expected
        value = h.get_property(prop) # property should not be set
        print('FAIL %s: expected exception' % (pretty))
        return False
    except Exception, e:
        pass # all good
    h.reboot()
    h.wait_power_state('boot_completed', timeout=120)
    try: # while booting local properties should be read from local.prop
        value = h.get_property(prop) # thus, reachable via get_property
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# Check clear_local_properties(), only supported on ICS and backwards.
def t28(w,h,label):
    pretty = '%s t28' % __file__
    print(pretty)

    prop = 'property.locally.clear'
    val  = 'value_to_clear'
    try:
        h.set_property(prop, val, local=True)
        if 'local.prop' not in h.ls('/data/'):
            print('FAIL %s: expected local.prop in /data/' % (pretty))
            return False
        h.clear_local_properties()
        if 'local.prop' in h.ls('/data/'):
            print('FAIL %s: didn\'t expect local.prop in /data/' % (pretty))
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# generate enormous shell output to check that the message passing doesn't
# break under such conditions
@smoke
def t50(w,h,label):
    pretty = '%s t50' % __file__
    print(pretty)

    for name in h.list_packages():
        try:
            dump = h.shell(['dumpsys','package',name])
        except Exception, e:
            print('FAIL %s: dumpsys %s failed: %s' % (pretty, name, str(e)))
            return False
    return True

# Expect exception on set_property(,,local=True) if sdk version > 15
def t55(w,h,label):
    pretty = '%s t55' % __file__
    print(pretty)

    if h.get_sdk_version() > 15:
        try:
            h.set_property('property.locally.nice', 'nice_value', local=True)
            print(
                'FAIL %s: expected exception on set_property(,,local=True) '
                'with sdk version > 15:' % (pretty)
            )
            return False
        except Exception, e:
            if not str(e).startswith('local.prop not supported on sdk version'):
                print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
                return False

        return True

# Test that the $EXTERNAL_STORAGE and $SECONDARY_STORAGE variables exist
@smoke
def t56(w,h,label):
    pretty = '%s t56' % __file__
    print(pretty)

    for var in ("EXTERNAL_STORAGE", "SECONDARY_STORAGE"):
        value = h.shell("echo $%s" % var).strip()
        if not value:
            print "FAIL %s: variable $%s does not exist" % (pretty, var)
            return False
    return True

# can the system be restarted? (not rebooted)
@smoke
def t57(w,h,label):
    pretty = '%s t57' % __file__
    print(pretty)

    # remember pid of zygote for future reference
    try:
        procs   = h.ps('zygote', True)
        old_pid = procs[0]['pid']
    except Exception, e:
        print('BLOCKED %s: zygote is not running? procs=%s' % (pretty, procs))
        return False

    try:
        h.restart_system()
    except Timeout, e:
        print('FAIL %s: %s' % (pretty, e))
        return False
    except Exception, e:
        print('FAIL %s: unknown error: %s' % (pretty, e))
        return False

    try:
        procs   = h.ps('zygote', True)
        new_pid = procs[0]['pid']
    except Exception, e:
        print('FAIL %s: home is not running? procs=%s' % (pretty, procs))
        return False

    # did the pid change?
    if new_pid == old_pid:
        print('FAIL %s: home did not restart' % pretty)
        return False

    return True

# check that get_package_version raise Exception if the package doesn't exist
def t61(w,h,label):
    pretty = '%s t61' % __file__
    print(pretty)

    expected_exception = 'can not find versionCode from '
    try:
        version = h.get_package_version('package.non-existing')
    except Exception, e:
        if expected_exception not in e.message:
            print('FAIL %s: unexpected exception: %s.' % (pretty, str(e)))
            return False
        return True
    print('FAIL %s: missing exception: %s.' % (pretty, expected_exception))
    return False

# check that get_galatea_apk_path return an existing path
def t66(w,h,label):
    pretty = '%s t66' % __file__
    print(pretty)

    path = h.get_galatea_apk_path()
    if not os.path.isfile(path):
        print('FAIL %s: file "%s" does not exist.' % (pretty, path))
        return False
    return True

# check that install_galatea works well in a handset with no galatea package
def t67(w,h,label):
    pretty = '%s t67' % __file__
    print(pretty)

    package_name = 'com.sonymobile.galatea'

    try:
        if h.is_installed(package_name):
            h.uninstall_galatea()
        h.reinstall_galatea(force=False)
        package_version = h.get_package_version(package_name)
        apk_version = ave.apk.get_version(h.get_galatea_apk_path())
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    if package_version != apk_version:
        print('FAIL %s: failed to install galatea.' % (pretty,))
        return False
    return True

# check that reinstall_galatea works well in a handset with old galatea package
def t68(w,h,label):
    pretty = '%s t68' % __file__
    print(pretty)

    package_name = 'com.sonymobile.galatea'

    try:
        if h.is_installed(package_name):
            h.uninstall_galatea()
        old_galatea = os.path.join(os.path.dirname(__file__), 'testdata', 'galatea-v-1.apk')
        h.reinstall_galatea(path=old_galatea, force=True)
        old_version = ave.apk.get_version(old_galatea)
        package_version = h.get_package_version(package_name)
        if package_version != old_version:
            print('FAIL %s: failed to install old galatea: %s, %s.' % (pretty,
                                            old_version, package_version))
            return False
    except Exception, e:
        print('FAIL %s: failed: %s' % (pretty, str(e)))
        return False

    try:
        h.reinstall_galatea(force=False)
        package_version = h.get_package_version(package_name)
        apk_version = ave.apk.get_version(h.get_galatea_apk_path())
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    if package_version != apk_version:
        print('FAIL %s: failed to install new galatea: %s, %s.' % (pretty,
                                        apk_version, package_version))
        return False
    return True

# check that reinstall_galatea works well in a handset with latest galatea package
def t69(w,h,label):
    pretty = '%s t69' % __file__
    print(pretty)

    package_name = 'com.sonymobile.galatea'
    try:
        h.reinstall_galatea(force=False) # After this, the galatea on the handset is the latest
        # TODO: how to check the installation is ignored?
        h.reinstall_galatea(force=False)
        package_version = h.get_package_version(package_name)
        apk_version = ave.apk.get_version(h.get_galatea_apk_path())
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    if package_version != apk_version:
        print('FAIL %s: failed to install galatea: %s, %s.' % (pretty,
                                        apk_version, package_version))
        return False
    return True

# can the system be booted to service
# this can be problematic
# Suggest to remove this case, test cases for flash have covered this test
# Generally handset goes to service mode or power-off after testing, this is
# not acceptable.
def REMOVE_t75(w, h, label):
    pretty = '%s t75' % __file__
    print(pretty)

    try:
        h.reboot(service=True)
    except Timeout, e:
        print('FAIL %s: %s' % (pretty, e))
        return False
    except Exception, e:
        print('FAIL %s: unknown error: %s' % (pretty, e))
        return False

    try:
        h.wait_power_state('service', 10)
    except Exception, e:
        print('FAIL %s: could not boot to service: %s' % (pretty, e))
        return False

    try:
        h.wait_power_state('boot_completed', 120)
    except Exception, e:
        print('FAIL %s: could not leave servicemode: %s' % (pretty, e))
        return False

    return True

#test app with Doze and App Standby
def t76(w,h,lable):
    pretty = '%s t76' % __file__
    print(pretty)

    try:
        h.dumpsys_battery()
        h.set_inactive('com.android.phone', 'true')
        state = h.get_inactive('com.android.phone')
        if 'true' not in state:
            print('FAIL %s: force the app into App Standby mode failed' % pretty)
            return False

        h.set_inactive('com.android.phone', 'false')
        state = h.get_inactive('com.android.phone')
        if 'false' not in state:
            print('FAIL %s: recover the app from idle failed' % pretty)
            return False

    except Exception, e:
        print('FAIL %s: App Standby mode failed: %s' % (pretty, e))
        return False

    h.dumpsys_battery('reset')
    h.dumpsys_battery()
    for i in range(60):
        state = h.dumpsys_deviceidle('step')
        if 'IDLE' in state:
            return True
        time.sleep(1)

    print('FAIL %s: the device state changes to idle failed' % pretty)
    return False
