/*
 * Copyright (C) 2013 Sony Mobile Communications AB.
 * All rights, including trade secret rights, reserved.
 */

package com.sonymobile.galatea;

import android.os.Bundle;
import android.support.test.uiautomator.UiAutomatorInstrumentationTestRunner;
import android.test.InstrumentationTestSuite;
import android.util.Log;

import junit.framework.TestSuite;

public class TestRunner extends UiAutomatorInstrumentationTestRunner {
    public Bundle arguments = null;

    @Override
    public void onCreate(Bundle arguments) {
        Log.v("galatea", "onCreate");
        this.arguments = arguments;
        super.onCreate(arguments);
    }

    @Override
    public TestSuite getAllTests() {
        Log.v("galatea", "getAllTests");
        TestSuite suite = new InstrumentationTestSuite(this);
        suite.addTestSuite(Galatea.class);
        return suite;
    }

    public Bundle getArguments() {
        return this.arguments;
    }
}
