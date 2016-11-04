/*
 * Copyright (C) 2013 Sony Mobile Communications AB.
 * All rights, including trade secret rights, reserved.
 */

package com.sonymobile.galatea;

import android.graphics.Rect;
import android.support.test.uiautomator.Configurator;
import android.support.test.uiautomator.UiAutomatorTestCase;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.os.Bundle;


public class Galatea extends UiAutomatorTestCase {
    private static final String TAG = "galatea";
    private static final int GET_VIEW_TIMEOUT = 1000;
    private static final int SPEED_REDUCTION  = 100;
    private static final String ID_PREFIX = "\\S+:id/";


    public Galatea() {
        super();
        Configurator.getInstance().setWaitForSelectorTimeout(GET_VIEW_TIMEOUT);
    }

    private Bundle getArguments() {
        return ((TestRunner)getInstrumentation()).getArguments();
    }

    private String getIdRegex(String id) {
        return ID_PREFIX + id;
    }

    private boolean hasUiObject(UiSelector selector) {
        return getUiDevice().findObject(selector).waitForExists(GET_VIEW_TIMEOUT);
    }

    private void clickUiObject(UiSelector selector) {
        try {
            getUiDevice().findObject(selector).click();
        } catch (UiObjectNotFoundException e) {
            fail("UiObject with selector: " + selector.toString() + " not found.");
        }
    }

    private void longClickUiObject(UiSelector selector) {
        try {
            UiObject uiObject = getUiDevice().findObject(selector);
            Rect rect = uiObject.getBounds();
            getUiDevice().swipe(rect.centerX(), rect.centerY(),  rect.centerX(), rect.centerY(), 40);
        } catch (UiObjectNotFoundException e) {
            fail("UiObject with selector: " + selector.toString() + " not found.");
        }
    }

    private static boolean isRegex(String text) {
        String pattern = "[a-zA-Z_0-9-& .,@]+";
        if (text.matches(pattern)) {
            return false;
        } else {
            return true;
        }
    }

    public void testOpenStatusBar() {
        Log.d(TAG, "openStatusBar");
        getUiDevice().openNotification();
    }

    public void testIsViewWithIdPresent() {
        String id = getArguments().getString("id");
        Log.v(TAG, "isViewWithIdPresent id="+id);
        if (! hasUiObject(new UiSelector().resourceIdMatches(getIdRegex(id)))) {
            fail("isViewWithIdPresent id="+id);
        }
    }

    public void testIsViewWithTextExact() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "isViewWithTextExact pattern="+pattern);
        if (! hasUiObject(new UiSelector().text(pattern))) {
            fail("isViewWithTextExact pattern="+pattern);
        }
    }

    public void testIsCheckboxChecked() {
        String pattern = getArguments().getString("pattern");
        UiObject uiObject = getUiDevice().findObject(new UiSelector().resourceIdMatches(getIdRegex(pattern)));
        try {
            Log.v(TAG, "isCheckboxChecked pattern=" + pattern);
            if (!uiObject.isChecked()) {
                fail("isCheckboxChecked pattern=" + pattern);
            }
        } catch (UiObjectNotFoundException e){
            fail("UiObject with id: " + pattern + " not found.");
        }
    }

    public void testIsViewWithTextRegExp() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "isViewWithTextRegExp pattern="+pattern);
        UiSelector uiSelector;
        if(isRegex(pattern)) {
            uiSelector = new UiSelector().textMatches(pattern);
        } else {
            uiSelector = new UiSelector().textContains(pattern);
        }
        if (! hasUiObject(uiSelector)) {
            fail("isViewWithTextRegExp pattern="+pattern);
        }
    }

    public void testIsViewWithTypePresent() {
        String type = getArguments().getString("type");
        Log.v(TAG, "isViewWithTypePresent="+type);
        if (! hasUiObject(new UiSelector().className(type))) {
            fail("isViewWithTypePresent type="+type);
        }
    }

    public void testClickItemWithTextExact() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "clickItemWithTextExact pattern="+pattern);
        clickUiObject(new UiSelector().text(pattern));
    }

    public void testLongClickItemWithTextExact() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "longClickItemWithTextExact pattern="+pattern);
        longClickUiObject(new UiSelector().text(pattern));
    }

    public void testClickItemWithTextRegExp() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "clickItemWithTextRegExp pattern="+pattern);
        UiSelector uiSelector;
        if(isRegex(pattern)) {
            uiSelector = new UiSelector().textMatches(pattern);
        } else {
            uiSelector = new UiSelector().textContains(pattern);
        }
        clickUiObject(uiSelector);
    }

    public void testLongClickItemWithTextRegExp() {
        String pattern = getArguments().getString("pattern");
        Log.v(TAG, "longClickItemWithTextRegExp pattern="+pattern);
        UiSelector uiSelector;
        if(isRegex(pattern)) {
            uiSelector = new UiSelector().textMatches(pattern);
        } else {
            uiSelector = new UiSelector().textContains(pattern);
        }
        longClickUiObject(uiSelector);
    }

    public void testClickItemWithId() {
        String id = getArguments().getString("pattern");
        Log.v(TAG, "clickItemWithId id=" + id);
        clickUiObject(new UiSelector().resourceIdMatches(getIdRegex(id)));
    }

    public void testLongClickItemWithId() {
        String id = getArguments().getString("pattern");
        Log.v(TAG, "longClickItemWithId id=" + id);
        longClickUiObject(new UiSelector().resourceIdMatches(getIdRegex(id)));
    }

    public void testScrollDown() {
        Log.v(TAG, "scrollDown");
        UiScrollable uiObject = new UiScrollable(new UiSelector().scrollable(true).enabled(true));
        try {
            uiObject.scrollForward();
        } catch (UiObjectNotFoundException e) {
            fail("No scrollable UiObject exists.");
        }
    }

    public void testScrollUp() {
        Log.v(TAG, "scrollUp");
        UiScrollable uiObject = new UiScrollable(new UiSelector().scrollable(true).enabled(true));
        try {
            uiObject.scrollBackward();
        } catch (UiObjectNotFoundException e) {
            fail("No scrollable UiObject exists.");
        }
    }

    public void testIsCurrentActivityPackage() {
        String name = getArguments().getString("name");
        Log.v(TAG, "isCurrentActivityPackage name=" + name);
        String pkg = getUiDevice().getCurrentPackageName();
        if (!pkg.equalsIgnoreCase(name)) {
            fail("isCurrentActivityPackage name=" + name + "!=" + pkg);
        }
    }
}
