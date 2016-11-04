# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import re
import time
import traceback
import errno

from ave.network.exceptions import RemoteTimeout, RemoteRunError
from ave.exceptions         import Timeout, RunError, Offline

import ave.cmd

from decorators import smoke

# can ampersand be used in parameter to adb shell commands?
def t01(w,h):
    pretty = '%s t1' % __file__
    print(pretty)

    # note that escaping the ampersand with a backslash "\&" does not work. it
    # would rely on host shell interpretation, but we don't use a shell on the
    # host side to execute the call to adb. AVE uses execvp() system call.

    # it is a bit of a mystery why adb shell accepts ['echo "HEJ & HELLO"'] but
    # not ['echo','"HEJ & HELLO"']. this means one cannot use "&" in commands
    # that require a multi-entry argument list for some *other* shell related
    # reason.

    # how to *not* do it with an ampersand in a shell argument
    try:
        echo = h.shell('echo "HEJ & HELLO"').strip()
        print('FAIL %s: shell() 1 did not fail: %s' % (pretty, echo))
        return False
    except Exception, e: # ADB looks for "HELLO" executable
        if 'no such executable' not in str(e):
            print('FAIL %s: wrong error 1: %s' % (pretty, e))
            return False

    # how to *also* not do it with an ampersand in a shell argument
    try:
        echo = h.shell(['echo', '"HEJ & HELLO"']).strip()
        print('FAIL %s: shell() 2 did not fail: %s' % (pretty, echo))
        return False
    except Exception, e: # ADB looks for "HELLO" executable
        if 'no such executable' not in str(e):
            print('FAIL %s: wrong error 2: %s' % (pretty, e))
            return False

    # how to work around the problem: put double quotes around the ampersand
    # argument and pass the entire command line as a single string in a single
    # entry list to shell(). this will build an execvp() call that corresponds
    # to this host shell command line:
    #   adb -s <serial> shell 'echo "HEJ & HELLO"'
    # which seems to be the only way to make ADB happy in this particular case.
    try:
        echo = h.shell(['echo "HEJ & HELLO"']).strip()
    except Exception, e:
        print('FAIL %s: shell failed: %s' % (pretty, e))
        return False

    if echo != 'HEJ & HELLO':
        print('FAIL %s: wrong echo: %s' % (pretty, echo))
        return False

    return True

# Tests that get_product_name() returns a non-empty value of type unicode
def t02(w,h):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        name = h.get_product_name()
    except Exception, e:
        print('FAIL %s: get_product_name() failed: %s' % (pretty, str(e)))
        return False
    if name is None:
        print('FAIL %s: get_product_name() returned: %s' % (pretty, name))
        return False
    elif type(name) not in [str, unicode]:
        print(
            'FAIL %s: get_product_name() returned wrong type: %s'
            % (pretty, type(name))
        )
        return False
    return True

# Test that get_build_label() returns correctly
def t04(w,h):
    pretty = '%s t4' % __file__
    print(pretty)

    try:
        label = h.get_build_label()
    except Exception, e:
        print('FAIL %s: get_build_label() failed: %s' % (pretty, str(e)))
        return False
    if label is None:
        print('FAIL %s: get_build_label() returned: %s' % (pretty, label))
        return False
    elif type(label) not in [str, unicode]:
        print(
            'FAIL %s: get_build_label() returned wrong type: %s'
            % (pretty, type(label))
        )
        return False
    return True

# Test that get_property returns correctly
@smoke
def t05(w,h):
    pretty = '%s t5' % __file__
    print(pretty)

    prop        = 'ro.board.platform'
    bad_prop    = 'ro.board.flatprom'
    try:
        # expect that ro.board.platform is always set
        platform = h.get_property(prop)
    except Exception, e:
        print('FAIL %s: get_property() failed: %s' % (pretty, str(e)))
        return False
    if platform is None:
        print('FAIL %s: get_property() returned: "%s"' % (pretty, platform))
        return False
    platform = None
    try:
        # expect that ro.board.flatprom is never set
        platform = h.get_property(bad_prop)
        print('FAIL %s: Expected exception on failure: %s' % (pretty, str(e)))
        return False
    except Exception, e:
        if platform:
            print('FAIL %s: Expected no return: %s' % (pretty, platform))
            return False
    return True

@smoke
def t06(w,h):
    pretty = '%s t6' % __file__
    print(pretty)

    try:
        h.root()
    except Exception, e:
        print('FAIL %s: root() failed: %s', (pretty, str(e)))
        return False
    return True

# Test that cat() returns correctly
def t07(w,h):
    pretty = '%s t7' % __file__
    print(pretty)
    # expect that init.rc is always available on dut
    cat_file = '/init.rc'
    try:
        h.root() # must be root to access init.rc
        cat_res = h.cat(cat_file)
    except Exception, e:
        print('FAIL %s: cat() failed: %s' % (pretty, str(e)))
        return False
    if cat_res is None:
        print('FAIL %s: cat() returned: %s' % (pretty, cat_res))
        return False
    elif type(cat_res) not in [str, unicode]:
        print(
            'FAIL %s: cat() returned wrong type: %s'
            % (pretty, type(cat_res))
        )
        return False
    return True

# Test of ls()
def t08(w,h):
    pretty = '%s t8' % __file__
    print(pretty)

    ls_path = '/system'
    try:
        # expect that /system always contains bin and lib
        ls_system = h.ls(ls_path)
    except Exception, e:
        print('FAIL %s: cat() failed: %s' % (pretty, str(e)))
        return False
    if ls_system is None:
        print('FAIL %s: ls() returned: %s' % (pretty, ls_system))
        return False
    if 'bin' not in ls_system:
        print('FAIL %s: on "ls": expected that /system contained bin' % pretty)
        return False
    if 'lib' not in ls_system:
        print('FAIL %s: on "ls": expected that /system contained lib' % pretty)
        return False
    return True

# Test of remount.
@smoke
def t13(w,h):
    pretty = '%s t13' % __file__
    print(pretty)

    def push_and_verify(tmp_file, tmp_file_path, path_system, expect):
        try:
            h.push(tmp_file_path, path_system)
            if tmp_file in h.ls(path_system):
                h.rm('%s/%s' % (path_system, tmp_file))
                if not expect:
                    print('FAIL %s: pushed file not expected on DUT' % pretty)
                    return False
            else:
                if expect:
                    print('FAIL %s: pushed file expected on DUT' % pretty)
                    return False
        except Exception, e:
            print('FAIL %s: %s' % (pretty, str(e)))
            return False
        return True

    h.disable_dm_verity(reboot=True)
    # Remount
    try:
        h.remount()
    except Exception, e:
        print('FAIL %s: %s' % (pretty, e))
        return False

    # promote file (AVE-189)
    tmp = w.make_tempfile()
    tmp_file_name = 'target.file'
    w.promote(tmp, tmp_file_name)

    # Push after remount, expect to succeed
    if not push_and_verify(tmp_file_name, w.get_path(), '/system', True):
        return False
    return True

# Test that chmod works as expected
def t14(w,h):
    pretty = '%s t14' % __file__
    print(pretty)

    # promote file (AVE-189)
    tmp = w.make_tempfile()
    tmp_file_name = 'target.%s' %os.path.basename(tmp) # trick for unique name
    tmp_file_path = os.path.join(w.get_path(), tmp_file_name)
    w.promote(tmp, tmp_file_name)

    path_data = '/data'
    try:
        h.push(tmp_file_path, path_data)
    except Exception, e:
        print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
        return False

    def get_number(perm_bits):
        ret = 0
        if perm_bits[2] == '1':
            ret += 1
        if perm_bits[1] == '1':
            ret += 2
        if perm_bits[0] == '1':
            ret += 4
        return ret

    def parse_permission(permission):
        tmp_ret = ''
        perms_list = ['','','']
        i_range = range(1, 10)
        for i in i_range:
            if permission[i] == '-':
                tmp_ret = tmp_ret + '0'
            else:
                tmp_ret = tmp_ret + '1'
        perms_list[0] = tmp_ret[0:3]
        perms_list[1] = tmp_ret[3:6]
        perms_list[2] = tmp_ret[6:9]
        ret = '%d%d%d' % (
            get_number(perms_list[0]),
            get_number(perms_list[1]),
            get_number(perms_list[2])
        )
        return ret

    def get_permission(target):
        out = h.shell(['ls', '-l', '%s' % target])
        pattern = '[drwx-]{10}'
        fa_list = re.findall(pattern, out)
        pattern = '[drwx-]*'
        permission = re.findall(pattern, fa_list[0])
        return parse_permission(permission[0])

    def chmod_and_verify(expected_mode, target):
        try:
            h.chmod(expected_mode, target)
            actual_mode = get_permission(target)
            if actual_mode != expected_mode:
                print(
                    'FAIL %s: chmod failed to change file mode bits: exp: %s, '
                    'act:%s' % (pretty, expected_mode, actual_mode)
                )
                return False
        except Exception, e:
            traceback.print_exc()
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False
        return True

    target = '%s/%s' % (path_data, tmp_file_name)
    if tmp_file_name not in h.ls(path_data):
        print('FAIL %s: file %s not found in %s' % (pretty,tmp_file,path_data))
        return False
    if not chmod_and_verify("777", target):
        return False
    if not chmod_and_verify("753", target):
        return False
    if not chmod_and_verify("666", target):
        return False
    h.rm(target)
    return True

# Test of push, mkdir, mv, pull, rm
# baked together.
@smoke
def t15(w,h):
    pretty = '%s t15' % __file__
    print(pretty)

    tmp_file_path = w.make_tempfile()
    tmp_file_name = tmp_file_path.split('/')[-1]
    path_data = '/data'

    # promote file (AVE-189)
    tmp = w.write_tempfile('Once upon a time')
    tmp_file_name = 'target.%s' %os.path.basename(tmp) # trick for unique name
    tmp_file_path = os.path.join(w.get_path(), tmp_file_name)
    w.promote(tmp, tmp_file_name)

    file_path_dut = '%s/%s' % (path_data, tmp_file_name)
    new_dir = 'new_directory_15'
    new_dir_path_dut = '%s/%s' % (path_data, new_dir)

    def verify_exists(directory, file_name, expected=True):
        try:
            ls_dir = h.ls(directory)
        except Exception, e:
            print('FAIL %s: unexpected failure: %s' % (pretty, str(e)))
            return False
        if file_name in ls_dir:
            if not expected:
                print(
                    'FAIL %s: %s not expected in %s'
                    % (pretty, file_name, directory)
                )
                return False
        else:
            if expected:
                print(
                    'FAIL %s: expected %s in %s'
                    % (pretty, file_name, directory)
                )
                return False
        return True
    # Verify push
    if not verify_exists(path_data, tmp_file_name, expected=False):
        return False
    h.push(tmp_file_path, path_data)
    if not verify_exists(path_data, tmp_file_name):
        return False
    # Verify mkdir
    h.rm(new_dir_path_dut, True)
    h.mkdir(new_dir_path_dut)
    if not verify_exists(path_data, new_dir):
        return False
    # Verify mv
    h.mv(file_path_dut, new_dir_path_dut)
    if not verify_exists(path_data, tmp_file_name, expected=False):
        return False
    if not verify_exists(new_dir_path_dut, tmp_file_name):
        return False
    tmp_file_nn = 'test_new_name'
    h.mv('%s/%s' % (new_dir_path_dut, tmp_file_name),
         '%s/%s' % (new_dir_path_dut, tmp_file_nn))
    file_path_dut = '%s/%s' % (new_dir_path_dut, tmp_file_nn)
    if not verify_exists(new_dir_path_dut, tmp_file_name, expected=False):
        return False
    if not verify_exists(new_dir_path_dut, tmp_file_nn):
        return False
    # Verify pull
    pull_path = os.path.join(w.get_path(), tmp_file_nn)
    h.pull(file_path_dut, pull_path)
    if not os.path.exists(pull_path):
        print('FAIL %s: expected %s to exist' % (pretty, pull_path))
        return False
    # Verify rm
    h.rm(new_dir_path_dut, recursive=True)
    if not verify_exists(path_data, new_dir_path_dut, expected=False):
        return False
    return True

# Verify wait_power_state() by rebooting and wait for handset to get ready.
@smoke
def t17(w,h):
    pretty = '%s t17' % __file__
    print(pretty)

    h.reboot()
    try:
        h.wait_power_state(['offline','enumeration'], timeout=20)
    except Exception, e:
        print('FAIL %s: wait for offline failed: %s' % (pretty, str(e)))
        return False
    try:
        h.wait_power_state('boot_completed', timeout=120)
    except Exception, e:
        print('FAIL %s: wait for boot completed failed: %s' % (pretty, str(e)))
        return False
    return True

# Check set_property on "persist." property
def t19(w,h):
    pretty = '%s t19' % __file__
    print(pretty)

    prop = 'persist.myfriday.superproperty'
    val  = 'cheers'

    # clear old value
    try:
        h.clear_property(prop)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    try:
        h.set_property(prop, val)
        cheers = h.get_property(prop)
        if not cheers == val:
            print('FAIL %s: unexpected value upon set_property()' % (pretty))
            return False
        h.reboot()
        h.wait_power_state('boot_completed', timeout=120)
        # verify upon reboot (it's persistent)
        cheers = h.get_property(prop)
        if not cheers == val:
            print('FAIL %s: unexpected value upon set_property()' % (pretty))
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# Check set_property on a non-persistent property
def t20(w,h):
    pretty = '%s t20' % __file__
    print(pretty)

    prop = 'unpersistent.proppy'
    val  = 'ciaobella'
    # clear old value
    try:
        h.clear_property(prop)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    try:
        h.set_property(prop, val)
        ciao = h.get_property(prop)

        if not ciao == val:
            print('FAIL %s: unexpected value upon set_property()' % (pretty))
            return False
        h.reboot()
        h.wait_power_state('boot_completed', timeout=120)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    try:
        # verify upon reboot (it's not persistent)
        noval = h.get_property(prop)
        print('FAIL %s: expected exception' % (pretty))
        return False
    except Exception, e:
        # no value - should generate exception => all good
        return True

# Check that clear_property raises exceptions
def t26(w,h):
    pretty = '%s t26' % __file__
    print(pretty)

    try:
        h.clear_property('')
        print('FAIL %s: expected exception on clear_property: \'\'' % (pretty))
        return False
    except:
        pass
    try:
        h.clear_property(None)
        print('FAIL %s: expected exception on clear_property: None' % (pretty))
        return False
    except:
        pass
    try:
        h.clear_property(['s'])
        print('FAIL %s: expected exception on clear_property: list' % (pretty))
        return False
    except:
        pass
    return True

# Check that clear_property works as expected in normal case
def t27(w,h):
    pretty = '%s t27' % __file__
    print(pretty)

    prop = 'my_new_prop.test'
    val  = 'only_testing'

    try:
        h.set_property(prop, val)
        res = h.get_property(prop) # make sure the property is set
        h.clear_property(prop)
        try:
            h.get_property(prop)
            print('FAIL %s: expected exception upon clear_property' % (pretty))
            return False
        except:
            return True
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

# negative ls() test
def t51(w,h):
    pretty = '%s t51' % __file__
    print(pretty)

    try:
        result = h.ls('/no/such/file/or/directory')
        print('FAIL %s: listing did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if 'No such file or directory: /no/such' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# negative ls() test
@smoke
def t52(w,h):
    pretty = '%s t52' % __file__
    print(pretty)

    try:
        result = h.ls('/system/bin/cat/') # note the trailing slash
        print('FAIL %s: listing did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if e.message != 'Not a directory: /system/bin/cat/':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# negative shell() test: try to execute program that does not exist onboard
@smoke
def t53(w,h):
    pretty = '%s t53' % __file__
    print(pretty)

    try:
        result = h.shell('no_such_exe')
        print('FAIL %s: execution did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if e.message != 'no such executable: no_such_exe':
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False

    return True

# regression test: zero length strings in .ls() output
@smoke
def t54(w,h):
    pretty = '%s t54' % __file__
    print(pretty)

    try:
        result = h.ls('/')
    except Exception, e:
        print('FAIL %s: ls failed: %s' % (pretty, str(e)))
        return False

    l1 = len(result)
    l2 = len([r for r in result if r])
    if l1 != l2:
        print('FAIL %s: empty lines in result: %s' % (pretty, result))
        return False

    return True

# Check that different basic calls to Handset.ps() return expected
# values
def t61(w,h):
    pretty = '%s t61' % __file__
    print(pretty)
    try:
        # get all pids should definitely return more than zero pids
        pids = h.ps()
        if len(pids) <= 0:
            print('FAIL %s: got no pids' % (pretty))
            return False
        # expect several processes with com.android in process name
        pids = h.ps('/system/bin', exact=False)
        if len(pids) <= 0:
            print(
                'FAIL %s: expected several processes for com.android' %(pretty)
            )
            return False
        # expect no process with these names:
        pids = h.ps('qwertyasdfgzxcvb123', exact=False)
        pids2 = h.ps('qwertyasdfgzxcvb123', exact=True)
        if len(pids) + len(pids2) > 0:
            print('FAIL %s: found unexpected processes' % (pretty))
            return False
        pids = h.ps('/init', exact=True)
        if len(pids) != 1:
            print('FAIL %s: expected to find process for \'/init\'' % (pretty))
            return False
        pids = h.ps('init')
        if len(pids) < 1: # may find more than one matching this "init"
            print(
                'FAIL %s: expected to find matching process for \'init\''
                % (pretty)
            )
            return False
    except Exception, e:
        traceback.print_exc()
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# verify path_exists() on existing path
def t62(w,h):
    pretty = '%s t62' % __file__
    print(pretty)

    path = '/data'
    if not h.path_exists(path):
        print('FAIL %s: expected path to exist: %s' % (pretty, path))
        return False
    return True

# verify path_exists() on non-existing path
def t63(w,h):
    pretty = '%s t63' % __file__
    print(pretty)

    path = '/testdir/deluxe/123abc987XyZ-asdfgh'
    if h.path_exists(path):
        print('FAIL %s: did not expect path to exist: %s' % (pretty, path))
        return False
    return True

# verify path_exists() by checking file type: directory
def t64(w,h):
    pretty = '%s t64' % __file__
    print(pretty)

    path = '/data' # directory
    if not h.path_exists(path, file_type='directory'):
        print(
            'FAIL %s: expected path to be an existing directory: %s'
            % (pretty, path)
        )
        return False
    return True

# negative test of path_exists(), checking file type: directory
def t65(w,h):
    pretty = '%s t65' % __file__
    print(pretty)

    path = '/init.rc' # regular file
    if h.path_exists(path, file_type='directory'):
        print('FAIL %s: incorrect result, not a directory: %s' % (pretty, path))
        return False
    return True

# verify path_exists() by checking file type: regular file
def t66(w,h):
    pretty = '%s t66' % __file__
    print(pretty)

    path = '/init.rc' # regular file
    if not h.path_exists(path, file_type='file'):
        print(
            'FAIL %s: expected path to be an existing regular file: %s'
            % (pretty, path))
        return False
    return True

# negative test of path_exists(), checking file type: regular file
def t67(w,h):
    pretty = '%s t67' % __file__
    print(pretty)

    path = '/data' # directory
    if h.path_exists(path, file_type='file'):
        print('FAIL %s: incorrect result, not a regular file: %s'%(pretty,path))
        return False
    return True

# verify path_exists() by checking file type: symlink
def t68(w,h):
    pretty = '%s t68' % __file__
    print(pretty)

    path = '/d' # symlink
    if not h.path_exists(path, file_type='symlink'):
        print(
            'FAIL %s: expected path to be an existing symlink: %s'
            % (pretty, path)
        )
        return False
    return True

# negative test of path_exists(), checking file type: symlink
def t69(w,h):
    pretty = '%s t69' % __file__
    print(pretty)

    path  = '/init.rc' # regular file
    path2 = '/data'    # directory
    if h.path_exists(path, file_type='symlink'):
        print('FAIL %s: incorrect result, not a symlink: %s' % (pretty, path))
        return False
    if h.path_exists(path2, file_type='symlink'):
        print('FAIL %s: incorrect result, not a symlink: %s' % (pretty, path2))
        return False
    return True

# negative test of path_exists(), checking invalid file type
def t70(w,h):
    pretty = '%s t70' % __file__
    print(pretty)

    path  = '/init.rc' # regular file
    try:
        h.path_exists(path, file_type='invalid_type')
        print('FAIL %s: expected exception due to invalid file type' % (pretty))
        return False
    except Exception as e:
        if not 'invalid type invalid_type. valid types:' in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# try mkdir with parents=True and verify with path_exists()
def t71(w,h):
    pretty = '%s t71' % __file__
    print(pretty)

    p1 = '/data/local/tmp/abc123def'
    p2 = p1 + '/x/y/z'
    try:
        h.mkdir(p2, parents=True)
        if h.path_exists(p2, file_type='directory'):
            h.rm(p1, recursive=True)
            return True
        print('FAIL %s: expected directory to exist upon mkdir' % (pretty))
        return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

# check that mkdir on existing directory raises exception
def t72(w,h):
    pretty = '%s t72' % __file__
    print(pretty)

    p1 = '/data/local/tmp/abc123def'
    try:
        h.mkdir(p1, parents=True)
        h.mkdir(p1)
        print('FAIL %s: expected exception (mkdir on existing dir)' % pretty)
        return False
    except Exception as e:
        if 'File exists' not in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    finally:
        try:
            h.rm(p1, recursive=True)
        except:
            pass
    return True

# check that cat() raises exception if the wanted file does not exist
def t73(w,h):
    pretty = '%s t73' % __file__
    print(pretty)

    try:
        result = h.cat('does-not-exist')
        print('FAIL %s: cat did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if 'does not exist' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that take_screenshot() raises exception if the destination is empty
def t74(w,h):
    pretty = '%s t74' % __file__
    print(pretty)

    try:
        result = h.take_screenshot('')
        print('FAIL %s: take_screenshot did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if 'must not be empty' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that take_screenshot() raises exception if the destination is a folder
def t75(w,h):
    pretty = '%s t75' % __file__
    print(pretty)

    try:
        result = h.take_screenshot('/sdcard/')
        print('FAIL %s: take_screenshot did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if 'must not be a folder' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that take_screenshot() raises exception if the destination is in root
def t76(w,h):
    pretty = '%s t76' % __file__
    print(pretty)

    try:
        result = h.take_screenshot('/screenshot.png')
        print('FAIL %s: take_screenshot did not fail: %s' % (pretty, result))
        return False
    except Exception, e:
        if 'must not be root' not in str(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    return True

# check that take_screenshot() works by positive test
def t77(w,h):
    pretty = '%s t77' % __file__
    print(pretty)

    timenow=str(int(time.time()))
    dstfilename = '/sdcard/'+timenow+'.png'
    try:
        result = h.take_screenshot(dstfilename)
        result2 = h.ls(dstfilename)
        if timenow not in str(result2):
            print('FAIL %s: failed to generate screenshot' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: failed: %s' % (pretty, e))
        return False
    return True

# check that take_screenshot() works even if destination file exists
def t78(w,h):
    pretty = '%s t78' % __file__
    print(pretty)

    try:
        result = h.take_screenshot('/sdcard/existing.png')
    except Exception, e:
        print('FAIL %s: failed: %s' % (pretty, e))
        return False

    try:
        result = h.take_screenshot('/sdcard/existing.png')
    except Exception, e:
        print('FAIL %s: failed when destination exists: %s' % (pretty, e))
        return False
    return True

# Verify wait_for_path can return normal if the path exists.
def t79(w,h):
    pretty = '%s t79' % __file__
    print(pretty)

    try:
        h.wait_for_path('/system', timeout=10)
    except Exception, e:
        print('FAIL %s: wait for directory "/system" failed: %s' % (
            pretty, str(e)))
        return False
    return True

# Verify wait_for_path raise timeout exception if the path don't exist.
def t80(w,h):
    pretty = '%s t80' % __file__
    print(pretty)

    try:
        h.wait_for_path('/system-non', timeout=10)
    except Timeout, e:
        return True
    print('FAIL %s: wait for directory "/system-non" should raise Timeout'
          ' exception: %s' % (pretty, ))
    return False

# Verify Offline is raised when running adb cmd on an offline handset
def t81(w,h):
    pretty = '%s t81' % __file__
    print(pretty)

    try:
        h.reboot()
        time.sleep(0.5)
        h.ls('/')
    except Offline, e:
        return True
    finally:
        try:
            h.wait_power_state('boot_completed', timeout=120)
        except Exception, e:
            print('FAIL %s: wait for boot completed failed: %s' % (pretty, str(e)))
            return False
    print('FAIL %s: ls directory on a rebooting handset should raise Offline'
          ' exception: %s' % (pretty, ))
    return False

#verify can execute an command in background
def t83(w, h):
    pretty = '%s t83' % __file__
    print(pretty)

    before = time.time()
    h.shell('logcat', bg=True)
    after = time.time()

    delta = after - before
    if delta < 1:
        return True
    else:
        print('FAIL %s: command does not run in background' % pretty)
        return False

#verify the kill background command method work properly
def t84(w, h):
    pretty = '%s t84' % __file__
    print(pretty)

    h.root()
    pid, fd = h.shell('logcat', bg=True)
    time.sleep(3)

    try:
        h.kill_background_cmd(pid, fd)
    except Exception, e:
        print('FAIL %s: Fail to kill background command, error: %s' % (pretty, str(e)))
        return False

    return True


# Test of push post AVE-189 (disable push of tmp-files)
@smoke
def t85(w,h):
    pretty = '%s t85' % __file__
    print(pretty)
    h.disable_dm_verity(reboot=True)
    # Remount
    try:
        h.remount()
    except Exception, e:
        print('FAIL %s: %s' % (pretty, e))
        return False

    tmp_file_path = w.make_tempfile()

    # must not be possible to push
    try:
        h.push(tmp_file_path, '/data')
    except Exception as e:
        if 'temp-files generated by the workspace are not possible' in str(e):
            return True
        else:
            print('FAIL %s: wrong exception raised %s' % (pretty, str(e)))
            return False
    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of push promoted file post AVE-189 (disable push of tmp-files)
@smoke
def t86(w,h):
    pretty = '%s t86' % __file__
    print(pretty)
    h.disable_dm_verity(reboot=True)
    # Remount
    try:
        h.remount()
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    expected = u'<xml><test>hej</test></xml>'
    temp_file = w.write_tempfile(expected)
    handset_path = os.path.join('/data', temp_file)
    # must not be possible to push
    try:
        h.push(temp_file, handset_path)
    except Exception as e:
        if 'temp-files generated by the workspace are not possible' in str(e):
            pass
        else:
            print('FAIL %s: wrong exception raised %s' % (pretty, str(e)))
            return False

    # promote the file
    target = 'props.xml'
    target_path = os.path.join(w.get_path(), target)
    result = w.promote(temp_file, target)
    handset_path = os.path.join('/data', target)

    # now the target can be pushed
    h.push(target_path, handset_path)

    # verify the file content
    pull_to = os.path.join(w.make_tempdir(), target_path)
    h.pull(handset_path, pull_to)

    actual = w.cat(pull_to)

    if actual != expected:
        print('FAIL %s: the pulled file content was corrupt %s / %s' %
                (pretty, expected, actual))
        return False

    return True

# Test of handset.ls could handle the situation: permission denied
def t87(w, h):
    pretty = '%s t87' % __file__
    print(pretty)

    # Reboot device and then /root cannot be listed
    h.reboot()
    h.wait_power_state('boot_completed', timeout=120)

    # must not be possible to list
    try:
        h.ls('/root')
    except Exception as e:
        if 'Permission denied' in str(e):
            pass
        else:
            print('FAIL %s: wrong exception raised %s' % (pretty, str(e)))
            return False

    # restarts the adbd daemon with root permissions, then
    # /root is able to be listed.
    h.root()
    try:
        h.ls('/root')
    except Exception as e:
        print('FAIL %s: unexpected exception raised %s' % (pretty, str(e)))
        return False

    return True

