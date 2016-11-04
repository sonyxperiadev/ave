# coding: utf-8

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from datetime import datetime, timedelta

class Timeout(Exception):
    pass

KEYCODE_HOME = 3

def make_cmd(function, extras=None):
    package = 'com.sonymobile.galatea'
    runner  = '%s/.TestRunner' % package
    test    = '%s.Galatea#%s' % (package, function)
    cmd     = ['am', 'instrument', '-r', '-e', 'class', test]
    if extras:
        cmd.extend(extras)
    cmd.extend(['-w', runner])
    return cmd

def press_key(h, keycode):
    cmd = ['input', 'keyevent', str(keycode)]
    tmp = h.shell(cmd)
    if tmp:
        raise Exception('keypress failed: %s' % tmp)

def open_status_bar(h):
    if status_bar_is_open(h):
        return True
    tmp = h.shell(make_cmd('testOpenStatusBar'))
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def status_bar_is_open(h):
    cmd = ['dumpsys', 'window', 'windows']
    tmp = h.shell(cmd)
    lines = tmp.split('\r\n')
    for line in lines:
        if 'mCurrentFocus' in line and 'StatusBar' in line:
            return True
    else:
        return False
    raise Exception('unhandled output: %s' % tmp)

def scroll_down(h):
    tmp = h.shell(make_cmd('testScrollDown'))
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def scroll_up(h):
    tmp = h.shell(make_cmd('testScrollUp'))
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def id_visible(h, identity):
    cmd = make_cmd('testIsViewWithIdPresent', ['-e', 'id', identity])
    tmp = h.shell(cmd)
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def is_current_activity(h, name):
    cmd = make_cmd('testIsCurrentActivityPackage', ['-e', 'name', name])
    tmp = h.shell(cmd)
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def text_pattern_method(h, pattern, method):
    try:
        pattern = pattern.decode('utf8')
    except:
        pass
    cmd = make_cmd(method, ['-e', 'pattern', pattern])
    tmp = h.shell(cmd)
    try:
        tmp = tmp.encode('utf8')
    except:
        pass
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output: %s' % tmp)

def text_exact_visible(h, pattern):
    return text_pattern_method(h, pattern, 'testIsViewWithTextExact')

def text_regexp_visible(h, pattern):
    return text_pattern_method(h, pattern, 'testIsViewWithTextRegExp')

def click_item_with_text_exact(h, pattern):
    return text_pattern_method(h, pattern, 'testClickItemWithTextExact')

def click_item_with_text_regexp(h, pattern):
    return text_pattern_method(h, pattern, 'testClickItemWithTextRegExp')

def wait_text_exact_visible(h, pattern, timeout):
    limit = datetime.now() + timedelta(seconds=timeout)
    while True:
        if datetime.now() > limit:
            raise Timeout('timed out')
        if text_exact_visible(h, pattern):
            return



# check that invisible views are not found
def t1(h):
    pretty = '%s t1' % __file__
    print(pretty)

    if id_visible(h, 'does_not_exist'):
        print('FAIL %s: "does_not_exist" id is visible' % pretty)
        return False

    return True

# check that a predictable view is visible after pressing HOME key
def t2(h):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        press_key(h, KEYCODE_HOME)
    except Exception, e:
        print('FAIL %s: could not press HOME key: %s' % (pretty, str(e)))
        return False

    if not is_current_activity(h, 'com.sonyericsson.home'):
        print('FAIL %s: not on home screen' % pretty)
        return False

    return True

# check that a predictable view is visible after opening the status bar
def t3(h):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        open_status_bar(h)
    except Exception, e:
        print('FAIL %s: open_status_bar() failed: %s' % (pretty, str(e)))
        return False

    if h.get_sdk_version() < 21:
        if not id_visible(h, 'status_bar_latest_event_content'):
            print('FAIL %s: status bar not opened' %  pretty)
            return False
    else:
        if not id_visible(h, 'multi_user_avatar'):
            print('FAIL %s: status bar not opened' %  pretty)
            return False

    return True

# check that a predictable string is visible after opening the status bar
def t4(h):
    pretty = '%s t4' % __file__
    print(pretty)

    open_status_bar(h)
    if not status_bar_is_open(h):
        print('FAIL %s: status bar is not open' % pretty)
        return False

    return True

# check that unexpected strings are not visible on the home screen
def t5(h):
    pretty = '%s t5' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    if text_exact_visible(h, 'no way jose, this is nonsense'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that non-ascii chars in exact string search are handled correctly
def t6(h):
    pretty = '%s t6' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    if text_exact_visible(h, 'åäö finns inte'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that non-ascii chars in regexp string search are handled correctly
def t7(h):
    pretty = '%s t7' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    if text_regexp_visible(h, 'åäö.*'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that an item can be clicked based on a visible regexp string
def t8(h):
    pretty = '%s t8' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    open_status_bar(h)
    if not click_item_with_text_regexp(h, 'USB.debugging.*'):
        print('FAIL %s: could not click USB connectivity event' % pretty)
        return False
    if not text_exact_visible(h, 'Stay awake'):
        print('FAIL %s: Developer options not opened' % pretty)
        return False

    return True

# check that scroll up/down works
def t9(h):
    pretty = '%s t9' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    h.set_locale('en_us')
    h.shell('am start -n com.android.settings/.Settings')

    # this item should be first in the settings menu
    if not text_exact_visible(h, 'Bluetooth'):
        print('FAIL %s: settings not opened')
        return False

    # scroll down to hide the first settings item
    try:
        if not scroll_down(h):
            print('FAIL %s: could not scroll down' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unhandled scroll down exception: %s' % (pretty, e))
        return False

    # check that the first item is no longer visible
    if text_exact_visible(h, 'Bluetooth'):
        print('FAIL %s: first item still visible' % pretty)
        return False

    # scroll up again. do it twice to be sure that the first item becomes
    # visible again
    try:
        if not scroll_up(h):
            print('FAIL %s: could not scroll up' % pretty)
            return False
        if not scroll_up(h):
            print('FAIL %s: could not scroll up' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unhandled scroll up exception: %s' % (pretty, e))
        return False

    # check that the first item is visible again
    if not text_exact_visible(h, 'Bluetooth'):
        print('FAIL %s: first item not visible')
        return False

    return True

# check that trying to open the status bar twice does not cause a tab switch
# within the status bar. this may happen on kitkat where a second open event is
# interpreted as a click on the quick settings tab. if the events tab is still
# open, there should be an item "USB debugging connected" present in the view.
def t10(h):
    pretty = '%s t10' % __file__
    print(pretty)

    press_key(h, KEYCODE_HOME)
    open_status_bar(h)
    open_status_bar(h)

    if not text_regexp_visible(h, 'USB.*'):
        print('FAIL %s: no USB connectivity event found' % pretty)
        return False

    return True