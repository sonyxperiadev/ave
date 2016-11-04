# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

from datetime import datetime, timedelta

TIMEOUT=30

def make_cmd(function, extras=None):
    package = 'com.sonymobile.galatea'
    runner  = '%s/.TestRunner' % package
    test    = '%s.Galatea#%s' % (package, function)
    cmd     = ['am', 'instrument', '-r', '-e', 'class', test]
    if extras:
        cmd.extend(extras)
    cmd.extend(['-w', runner])
    return cmd

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

def open_status_bar(h):
    if status_bar_is_open(h):
        return True
    tmp = h.shell(make_cmd('testOpenStatusBar'), timeout=TIMEOUT)
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
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
    tmp = h.shell(cmd, timeout=TIMEOUT)
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
    if type(pattern) == unicode:
        pattern = '"%s"' % pattern.encode('utf8')
    else:
        pattern = '"%s"' % pattern
    cmd = make_cmd(method, ['-e', 'pattern', pattern])
    cmd = ' '.join(cmd)
    cmd = [cmd]
    tmp = h.shell(cmd, timeout=TIMEOUT)
    try:
        tmp = tmp.encode('utf8')
    except:
        pass
    if 'FAILURES!!!' in tmp:
        return False
    if 'OK (1 test)' in tmp:
        return True
    raise Exception('unhandled output for %s: %s' % (cmd, tmp))
