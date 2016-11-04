# coding: utf-8

import os
import ave.handset.galatea

from decorators import smoke
import time

KEYCODE_HOME = 3
KEYCODE_BACK = 4

# check that invisible views are not found
def t01(h):
    pretty = '%s t1' % __file__
    print(pretty)

    if h.id_visible('does_not_exist'):
        print('FAIL %s: "does_not_exist" id is visible' % pretty)
        return False

    return True

# check that a predictable view is visible after pressing HOME key
@smoke
def t02(h):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        h.press_key(KEYCODE_HOME)
    except Exception, e:
        print('FAIL %s: could not press HOME key: %s' % (pretty, str(e)))
        return False

    if not ave.handset.galatea.is_current_activity(h, 'com.sonyericsson.home'):
        print('FAIL %s: not on home screen' % pretty)
        return False

    return True

# check that a predictable view is visible after opening the status bar
@smoke
def t03(h):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        h.open_status_bar()
    except Exception, e:
        print('FAIL %s: open_status_bar() failed: %s' % (pretty, str(e)))
        return False

    if h.get_sdk_version() < 21:
        if not h.id_visible('status_bar_latest_event_content'):
            print('FAIL %s: status bar not opened' %  pretty)
            return False
    else:
        if not h.id_visible('multi_user_avatar'):
            print('FAIL %s: status bar not opened' %  pretty)
            return False

    return True

# check that a predictable string is visible after opening the status bar
def t04(h):
    pretty = '%s t4' % __file__
    print(pretty)

    h.open_status_bar()
    if not ave.handset.galatea.status_bar_is_open(h):
        print('FAIL %s: status bar is not open' % pretty)
        return False

    return True

# check that unexpected strings are not visible on the home screen
def t05(h):
    pretty = '%s t5' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    if h.text_exact_visible('no way jose, this is nonsense'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that non-ascii chars in exact string search are handled correctly
@smoke
def t06(h):
    pretty = '%s t6' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    if h.text_exact_visible('åäö finns inte'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that non-ascii chars in regexp string search are handled correctly
def t07(h):
    pretty = '%s t7' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    if h.text_regexp_visible('åäö.*'):
        print('FAIL %s: unexpected string found in view' % pretty)
        return False

    return True

# check that an item can be clicked based on a visible regexp string
def t08(h):
    pretty = '%s t8' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    h.open_status_bar()
    if not h.click_item_with_text_regexp('USB.debugging.*'):
        print('FAIL %s: could not click USB connectivity event' % pretty)
        return False
    if not h.text_exact_visible('Stay awake'):
        print('FAIL %s: Developer options not opened' % pretty)
        return False

    return True

# check that waiting for text to appear works
@smoke
def t09(h):
    pretty = '%s t9' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    h.open_status_bar()
    try:
        h.wait_text_regexp_visible('USB.*', 5)
        return True
    except Exception, e:
        print('FAIL %s: preference menu not opened: %s' % (pretty, e))
        return False

    return True

# check that scroll up/down works
@smoke
def t10(h):
    pretty = '%s t10' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    #h.set_locale('en_us')
    h.shell('am start -n com.android.settings/.Settings')
    time.sleep(2)

    # this item should be first in the settings menu
    if not h.text_exact_visible('Bluetooth'):
        print('FAIL %s: settings not opened' % pretty)
        return False

    # scroll down to hide the first settings item
    try:
        if not h.scroll_down():
            print('FAIL %s: could not scroll down' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unhandled scroll down exception: %s' % (pretty, e))
        return False

    # check that the first item is no longer visible
    if h.text_exact_visible('Bluetooth'):
        print('FAIL %s: first item still visible' % pretty)
        return False

    # scroll up again. do it twice to be sure that the first item becomes
    # visible again
    try:
        if not h.scroll_up():
            print('FAIL %s: could not scroll up' % pretty)
            return False
        if not h.scroll_up():
            print('FAIL %s: could not scroll up' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unhandled scroll up exception: %s' % (pretty, e))
        return False

    # check that the first item is visible again
    if not h.text_exact_visible('Bluetooth'):
        print('FAIL %s: first item not visible' % pretty)
        return False

    return True

# check that trying to open the status bar twice does not cause a tab switch
# within the status bar. this may happen on kitkat where a second open event is
# interpreted as a click on the quick settings tab. if the events tab is still
# open, there should be an item "USB debugging connected" present in the view.
def t11(h):
    pretty = '%s t11' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    h.open_status_bar()
    h.open_status_bar()

    if not h.text_regexp_visible('USB.*'):
        print('FAIL %s: no USB connectivity event found' % pretty)
        return False

    return True

# check the status of checkbox
def t12(h):
    pretty = '%s t12' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    h.shell('am start -n com.android.settings/.Settings')
    time.sleep(2)

    # To make sure that Bluetooth is visible
    h.scroll_up()
    h.scroll_up()
    h.scroll_up()
    if not h.click_item_with_text_exact('Bluetooth'):
        print('FAIL %s: could not click Bluetooth' % pretty)
        return False

    if h.is_checkbox_checked('switch_widget'):
        # Click On to switch off Bluetooth
        h.click_item_with_text_exact('On')
        if h.is_checkbox_checked('switch_widget'):
            print('FAIL %s: it should be unchecked after clicking a checked'
            ' checkbox' % pretty)
            # Restore the status of checkbox
            h.click_item_with_text_exact('On')
            return False
    else:
        # click Off to switch on Bluetooth
        h.click_item_with_text_exact('Off')
        if not h.is_checkbox_checked('switch_widget'):
            print('FAIL %s: it should be checked after clicking an unchecked'
            ' checkbox' % pretty)
            # Restore the status of checkbox
            h.click_item_with_text_exact('Off')
            return False

    # Restore the status of checkbox
    h.click_item_with_id('switch_widget')

    return True

# try to look for and press an item that contains an ampersand
def t13(h):
    pretty = '%s t13' % __file__
    print(pretty)

    h.press_key(KEYCODE_HOME)
    #h.set_locale('en_us')
    h.shell('am start -n com.android.settings/.Settings')
    h.scroll_down()
    h.scroll_down()
    h.scroll_down()
    h.scroll_down()
    h.scroll_down()

    # "Date & time" should be visible now
    try:
        if not h.text_exact_visible('Date & time'):
            print('FAIL %s: "Date & time" item not visible' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not look for "Date & time": %s' % (pretty, e))
        return False

    try:
        if not h.click_item_with_text_exact('Date & time'):
            print('FAIL %s: "Date & time" item not clickable' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not click "Date & time": %s' % (pretty, e))
        return False

    try:
        if not h.text_regexp_visible('.*&.*'):
            print('FAIL %s: "Automatic date & time" not visible' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not look for ".*&.*": %s' % (pretty, e))
        return False

    return True

# check that an item can be long clicked based on a id
def t14(h):
    pretty = '%s t14' % __file__
    print(pretty)

    apkpath = os.path.join(os.path.dirname(__file__), 'testdata', 'testapp-release.apk')
    h.install(apkpath, args='-r')

    h.press_key(KEYCODE_HOME)
    h.shell('am start -n com.android.uiautomator.tests.cts.testapp/.MainActivity')

    try:
        h.scroll_up()
        h.scroll_up()
        h.scroll_up()
        if not h.click_item_with_text_exact('Test 2'):
            print('FAIL %s: could not click Test 2' % pretty)
            return False
        if not h.long_click_item_with_id('test2button1'):
            print('FAIL %s: "Button 1" item not longclickable' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not long click "Button 1": %s' % (pretty, e))
        return False

    try:
        if not h.text_exact_visible('Longclick Button 1'):
            print('FAIL %s: "Longclick Button 1" item not visible' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not look for "Longclick Button 1": %s' % (pretty, e))
        return False

    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    return True

# check that an item can be long clicked based on a visible exact string
def t15(h):
    pretty = '%s t15' % __file__
    print(pretty)

    apkpath = os.path.join(os.path.dirname(__file__), 'testdata', 'testapp-release.apk')
    h.install(apkpath, args='-r')

    h.press_key(KEYCODE_HOME)
    h.shell('am start -n com.android.uiautomator.tests.cts.testapp/.MainActivity')

    try:
        h.scroll_up()
        h.scroll_up()
        h.scroll_up()
        if not h.click_item_with_text_exact('Test 2'):
            print('FAIL %s: could not click Test 2' % pretty)
            return False
        if not h.long_click_item_with_text_exact('Button 1'):
            print('FAIL %s: "Button 1" item not longclickable' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not long click "Button 1": %s' % (pretty, e))
        return False

    try:
        if not h.text_exact_visible('Longclick Button 1'):
            print('FAIL %s: "Longclick Button 1" item not visible' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not look for "Longclick Button 1": %s' % (pretty, e))
        return False

    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    return True

# check that an item can be long clicked based on a visible regexp string
def t16(h):
    pretty = '%s t16' % __file__
    print(pretty)

    apkpath = os.path.join(os.path.dirname(__file__), 'testdata', 'testapp-release.apk')
    h.install(apkpath, args='-r')

    h.press_key(KEYCODE_HOME)
    h.shell('am start -n com.android.uiautomator.tests.cts.testapp/.MainActivity')

    try:
        h.scroll_up()
        h.scroll_up()
        h.scroll_up()
        if not h.click_item_with_text_exact('Test 2'):
            print('FAIL %s: could not click Test 2' % pretty)
            return False
        if not h.long_click_item_with_text_regexp('Butt.*1'):
            print('FAIL %s: "Button 1" item not longclickable' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not long click "Button 1": %s' % (pretty, e))
        return False

    try:
        if not h.text_exact_visible('Longclick Button 1'):
            print('FAIL %s: "Longclick Button 1" item not visible' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: could not look for "Longclick Button 1": %s' % (pretty, e))
        return False

    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    h.press_key(KEYCODE_BACK)
    return True
