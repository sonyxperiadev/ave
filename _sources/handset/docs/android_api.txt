Android Handset
===============

Inherits from ``AdbHandset``. Refer to separate document for a list of inherited
functions.

Although handset objects can be created explicitly, you should always allocate
handsets through the broker instead (possibly with more attributes set in the
allocation profile)::

    from ave.broker import Broker

    broker = Broker()
    handset = broker.get({'type':'handset', 'platform':'android'})

The returned handset implements the API that is documented here.

.. Warning:: Many functions require super user privileges and will not work
    before a ``root()`` call has been made.

.. class:: ave.handset.android_handset.AndroidHandset(profile)

    :arg profile: A ``HandsetProfile`` instance that must contain at least
        the following members::

            {
                'type'    : 'handset',
                'platform': 'android',
                'serial'  : 'xxx' # the serial number of the handset
            }

Power States
------------

Android handsets can be in any of the following power states::

    'offline',         # the handset is turned off or not connected
    'service',         # the handset is in service mode
    'enumeration',     # the handset's USB is set up and ready
    'adb',             # the handset is available via adb
    'package_manager', # the Android package manager is ready
    'boot_completed'   # the sys.boot_completed property is set to "1"

.. function:: get_power_state()

    :returns: A string denoting the current power state.
    :raises Exception: If an error occured.

.. function:: wait_power_state(states, timeout=0)

    Wait for the handset to reach a desired power state. The function returns
    when the first matching power state has been reached.

    :arg states: A string or a list of strings denoting power states to wait
        for.
    :arg timeout: Number of seconds, as an integer, until a time out. Default
        is 0, meaning no time out is set.
    :returns: The reached power state.
    :raises Exception: If a state is invalid, an error or time out occurs.

    On a normal boot of a handset it will go through the power states in
    the following order::

        offline > enumeration > adb > package_manager > boot_completed

.. function:: reboot(service=False, timeout=30)

    Reboot the handset. The function returns when the handset enters the
    *offline* power state. Use e.g. ``wait_power_state('boot_completed')`` to
    wait for the handset to return to a fully booted state.

    :arg service: If *True* enter service mode on reboot, else reboot normally.
    :arg timeout: Number of seconds to wait for the handset to go offline.
    :raises Timeout: If the handset did not enter the ``offline`` power state
        in time.
    :raises Exception: On other errors.

SIM Card Handling
-----------------

.. function:: get_phone_number()

    Get the phone number from SIM card.

    :returns: The phone number, formatted as a string.

Networking
----------

.. function:: get_gsm_operator()

    :returns: The name of the GSM operator, if any. Note that handsets in flight
        mode have no GSM operator even if they have a valid SIM card inserted.

Positioning
-----------


UI Manipulation
---------------

.. function:: press_key(keycode)

    Press key with the given keycode. These are the same codes as appear in
    Android SDK documentation. E.g. ``3`` is the go-to-home-screen key.

    :arg keycode: The keycode of the key to press, an integer.
    :raises Exception: If the keypress failed.

.. function:: open_status_bar()

    Open the status bar.

    :returns: *True* if successfully opened status bar, otherwise *False*.

.. function:: id_visible(identity)

    Check whether a view with the given identity is visible. View ID's can be
    found by inspecting a running application with ``hierarchyviewer``, which
    is included in the Android SDK.

    :arg identity: A string. The identity of the view.
    :returns: *True* if visible, else *False*.

.. function:: is_checkbox_checked(pattern)

    Check whether a checkbox with an ID that matches the given pattern is
    visible.

    :arg pattern: A string holding the ID to look for.
    :returns: *True* if visible, else *False*.

.. function:: text_exact_visible(pattern)

    Search for a visible view with text that is an exact match of the given
    pattern.

    :arg pattern: The exact match of the text in the view.
    :returns: *True* if visible, else *False*.

.. function:: text_regexp_visible(pattern)

    Search for a visible view with text that is a match of the given regexp
    pattern.

    :arg pattern: The regexp pattern to search for. Note that this must be a
        *plain* regular expression, not a PCRE styled one.
    :returns: *True* if visible, else *False*.

.. function:: click_item_with_id(identity)

    Click on an item with an ID that matches the given pattern.

    :arg identity: A string holding the ID to look for.
    :returns: *True* if succeeded, else *False*.

.. function:: click_item_with_text_exact(pattern)

    Click on the item with text that is an exact match of the given pattern.

    :arg pattern: The exact pattern of the text in the item.
    :returns: *True* if succeeded, else *False*.

.. function:: click_item_with_text_regexp(pattern)

    Click on the item with text that is a match of the given regexp pattern.

    :arg pattern: The regexp pattern of the text in the view.
    :returns: *True* if succeeded, else *False*.

.. function:: wait_id_visible(identity, timeout=20)

    Wait until a view with the given identity is visible.

    :arg identity: The identity of the view.
    :arg timeout: Seconds before time out.

.. function:: wait_text_exact_visible(pattern, timeout=20)

    Wait until a view with text that is an exact match of the given pattern
    is visible.

    :arg pattern: The exact match of the text in the view.
    :arg timeout: Seconds before time out.
    :arg Timeout: If such occured.

.. function:: wait_text_regexp_visible(pattern, timeout=20)

    Wait until a view with text that is a match of the given regexp pattern
    is visible.

    :arg pattern: The exact match of the text in the view.
    :arg timeout: Seconds before time out.
    :raises Timeout: If such occured.

.. function:: get_display_bound()

    Get handset display bound for current display orientation.

    :raises Exception:
        * If unable to determine handset display bound.

    :returns: Bound dictionary representing device display bound.

    :Example:

        >>> # Get handset display size
        >>> bound = handset.get_display_bound()
        >>> width = bound['width']
        >>> height = bound['height']

        >>> # Get center point of display
        >>> bound = handset.get_display_bound()
        >>> x = bound['center_x']
        >>> y = bound.['center_y']

        Following keys can be used on returned bound dictionary to fetch information

        ============== =====================================================================
        KEY            DESCRIPTION
        ============== =====================================================================
        x1             Get Top-left X coordinate of display
        y1             Get Top-left Y coordinate of display
        x2             Get Bottom-right X coordinate of display
        y2             Get Bottom-right Y coordinate of display
        width          Get width of display
        height         Get height of display
        center_x       Get Center X coordinate of display
        center_y       Get Center Y coordinate of display
        ============== =====================================================================

.. function:: get_application_content_area_bound()

    Get handset application content area bound. Application content area bound
    represents viewing area on the handset display except status bar and
    navigation bar.

    :raises Exception:
        * If content area bound can not be determined.

    :returns: Bound dictionary representing application content area bound.

    :Example:

        >>> # Get application content area rectangle
        >>> bound = handset.get_application_content_area_bound()
        >>> top_left_x = bound['x1']
        >>> top_left_y = bound['y1']
        >>> width = bound['width']
        >>> height = bound['height']

        Following keys can be used on returned bound dictionary to fetch information

        ============== =====================================================================
        KEY            DESCRIPTION
        ============== =====================================================================
        x1             Get Top-left X coordinate of content area
        y1             Get Top-left Y coordinate of content area
        x2             Get Bottom-right X coordinate of content area
        y2             Get Bottom-right Y coordinate of content area
        width          Get width of content area
        height         Get height of content area
        center_x       Get Center X coordinate of content area
        center_y       Get Center Y coordinate of content area
        ============== =====================================================================

.. function:: get_status_bar_bound()

    Get handset status bar bound. Status bar bound represents area in display except application
    content area and navigation bar area.

    :raises Exception:
        * If display bound can not be determined.
        * If content area bound can not be determined.
        * If display orientation can not be determined.

    :returns: Bound dictionary representing status bar area bound.

    :Example:

        >>> # Get status bar area rectangle
        >>> bound = handset.get_status_bar_bound()
        >>> top_left_x = bound['x1']
        >>> top_left_y = bound['y1']
        >>> width = bound['width']
        >>> height = bound['height']

        Following keys can be used on returned bound dictionary to fetch information

        ============== =====================================================================
        KEY            DESCRIPTION
        ============== =====================================================================
        x1             Get Top-left X coordinate of status bar
        y1             Get Top-left Y coordinate of status bar
        x2             Get Bottom-right X coordinate of status bar
        y2             Get Bottom-right Y coordinate of status bar
        width          Get width of status bar
        height         Get height of status bar
        center_x       Get Center X coordinate of status bar
        center_y       Get Center Y coordinate of status bar
        ============== =====================================================================

.. function:: get_navigation_bar_bound()

    Get handset navigation bar bound. Navigation bar represents area in display except application
    content area and status bar area.

    :raises Exception:
        * If display bound can not be determined.
        * If content area bound can not be determined.
        * If display orientation can not be determined.

    :returns: Bound dictionary representing navigation bar area bound.

    :Example:

        >>> # Get navigation bar area rectangle
        >>> bound = handset.get_navigation_bar_bound()
        >>> top_left_x = bound['x1']
        >>> top_left_y = bound['y1']
        >>> width = bound['width']
        >>> height = bound['height']

        Following keys can be used on returned bound dictionary to fetch information

        ============== =====================================================================
        KEY            DESCRIPTION
        ============== =====================================================================
        x1             Get Top-left X coordinate of navigation bar
        y1             Get Top-left Y coordinate of navigation bar
        x2             Get Bottom-right X coordinate of navigation bar
        y2             Get Bottom-right Y coordinate of navigation bar
        width          Get width of navigation bar
        height         Get height of navigation bar
        center_x       Get Center X coordinate of navigation bar
        center_y       Get Center Y coordinate of navigation bar
        ============== =====================================================================

.. function:: get_display_orientation()

    Get handset display orientation.

    :raises Exception:
        * If display orientation can not be determined.

    :returns: String representing handset display orientation. Possible return values are:

        ====================== =====================================================================
        VALUE                  MEANING
        ====================== =====================================================================
        0                      ORIENTATION_PORTRAIT_0_DEGREE
        1                      ORIENTATION_LANDSCAPE_90_DEGREE
        2                      ORIENTATION_PORTRAIT_180_DEGREE
        3                      ORIENTATION_LANDSCAPE_270_DEGREE
        ====================== =====================================================================

    :Example:

        >>> # Check if display is in 180 degree rotation
        >>> rotation = handset.get_display_orientation()
        >>> is_180_degree = rotation == '2'

.. function:: is_orientation_portrait()

    Check if handset display orientation is in portrait mode. Display is in portrait mode if display
    orientation is either 0 degree or 180 degree.

    :raises Exception:
        * If display orientation can not be determined.

    :returns: Boolean value ``True`` if display orientation is in portrait mode else ``False``.

    :Example:

        >>> # Check if handset display is in portrait mode
        >>> if handset.is_orientation_portrait():
        >>>     print "Display is in Portrait mode"

.. function:: is_orientation_landscape()

    Check if handset display orientation is in landscape mode. Display is in landscape mode if
    display orientation is either 90 degree or 270 degree.

    :raises Exception:
        * If display orientation can not be determined.

    :returns: Boolean value ``True`` if display orientation is in landscape mode else ``False``.

    :Example:

        >>> # Check if handset display is in landscape mode
        >>> if handset.is_orientation_landscape():
        >>>     print "Display is in Landscape mode"

.. function:: get_view_bound(key, value, index=0, matching=True)

    Get bound for a view present in the device display.

    :raises Exception:
        * If key is not supported.
        * If view is not located for specified key-value-index match.
        * if view bound can not be determined.
        * If handset ui hierarchy XML can not be obtained.

    :arg key: It specifies the search type in device UI hierarchy.
        Following are acceptable key which represents an attribute for a view element of a running
        application. This can be inspected by ``uiautomatorviewer``, which is included in the
        Android SDK.

        ====================== =====================================================================
        KEY                    MEANING
        ====================== =====================================================================
        text                   Search device ui hierarchy by 'text' attribute
        type                   Search device ui hierarchy by 'class' attribute
        id                     Search device ui hierarchy by 'resource-id' attribute
        desc                   Search device ui hierarchy by 'content-desc' attribute
        ====================== =====================================================================

    :arg value: It specifies what value to be searched for specified key. This can be inspected by
        ``uiautomatorviewer``, which is included in the Android SDK.

    :arg index: It specifies N'th occurrence of view need to be searched for specified key/value
        pair. It is a zero based indexing system, that is, index of first view is zero.

    :arg matching: Boolean value ``True`` if specified ``value`` need to be matched in case
        insensitive way and a match will be positive if specified ``value`` is a substring
        of the original ``value`` with same ``key``. Boolean value ``False`` if case sensitive
        exact match is required for the specified ``value``.

    :returns: Bound dictionary for the matched view.

    :Example:

        >>> # Get rectangle for a view with id "Album-Image" and second occurrence in screen.
        >>> bound = handset.get_view_bound("id", "album-image", index=1)
        >>> top_left_x = bound['x1']
        >>> top_left_y = bound['y1']
        >>> width = bound['width']
        >>> height = bound['height']

        >>> # Get center coordinate of the first view with type "android.widget.ImageView"
        >>> bound = handset.get_view_bound("type", "imageview")
        >>> x = bound['center_x']
        >>> y = bound['center_y']

        >>> # Get bottom right coordinate for first view with exact text "Hello World"
        >>> bound = handset.get_view_bound("text", "Hello World", matching=False)
        >>> x = bound['x2']
        >>> y = bound['y2']

        >>> # Get width and height of 5'th view with description "item_image"
        >>> bound = handset.get_view_bound("desc", "item_image", index=4)
        >>> width = bound['width']
        >>> height = bound['height']

        Following keys can be used on returned bound dictionary to fetch information

        ============== =====================================================================
        KEY            DESCRIPTION
        ============== =====================================================================
        x1             Get Top-left X coordinate of view
        y1             Get Top-left Y coordinate of view
        x2             Get Bottom-right X coordinate of view
        y2             Get Bottom-right Y coordinate of view
        width          Get width of view
        height         Get height of view
        center_x       Get Center X coordinate of view
        center_y       Get Center Y coordinate of view
        ============== =====================================================================

Popup Handling
--------------

.. function:: disable_usb_mode_chooser()

    Removes a dialog that asks the user to choose the usb mode.
    Caller must have called ``.root()`` beforehand.

.. function:: enable_usb_mode_chooser()

    Enables a dialog that asks the user to choose the usb mode.
    Caller must have called ``.root()`` beforehand.

.. function:: disable_package_verifier()

    Disables the following security check that was introduced in Jelly
    Bean: A dialog appears when the user installs an APK from an unknown
    source (e.g. one installed with ADB). The user must accept or reject
    the installation to remove the dialog.

.. function:: enable_package_verifier()

    Enables the following security check that was introduced in Jelly
    Bean: A dialog appears when the user installs an APK from an unknown
    source (e.g. one installed with ADB). The user must accept or reject
    the installation to remove the dialog.

Application Management
----------------------

.. function:: list_packages()

    List all installed packages on the handset.

    :returns: A list with all installed packages.
    :raises Exception: If it was not possible to list packages.

.. function:: is_installed(package)

    Check if the given package is installed on the handset.

    :arg package: The package to check.
    :returns: *True* if the package is installed, *False* otherwise.

.. function:: install(apk_path, timeout=30, args=None)

    Install an APK on the handset.

    :arg apk_path: The path to the package to install.
    :arg timeout: Execution time out.
    :arg args: The parameters of install, defalut to ``None``,args also can be -lrtsdg,
                                 (-l: forward lock application)
                                 (-r: replace existing application)
                                 (-t: allow test packages)
                                 (-s: install application on sdcard)
                                 (-d: allow version code downgrade)
                                 (-g: grant all runtime permissions)

.. function:: uninstall(package)

    Uninstall an APK from the handset.

    :arg package: The name of the package to uninstall.

.. function:: reinstall(apk_path)

    Reinstall an APK on the handset.

    :arg apk_path: The path to the APK to reinstall.

.. function:: get_package_version(package)

    Get the version code of the package.

    :arg package: The package to check.
    :returns: Version code of the package.
    :raises Exception: If it was not possible to get the version code.

.. function:: list_permissions(args)

    Prints all known permissions. Defalut options are '-d -g'.

    :arg args:     -g: organize by group.
                   -f: print all information.
                   -s: short summary.
                   -d: only list dangerous permissions.
                   -u: list only the permissions users will see.

    :returns:  permissions list string

.. function:: grant_permission(package, permissions_name)

    Grant permissions to apps. The permissions must be declared as used
    in the app's manifest, be runtime permissions (protection level dangerous),
    and the app targeting SDK greater than Lollipop MR1.

    :arg package: app package name
    :arg permissions: The permissions name

    :returns: True
    :raises Exception: If an error occurs


.. function:: revoke_permission(package, permissions_name)

    Revoke permissions to apps. The permissions must be declared as used
    in the app's manifest, be runtime permissions (protection level dangerous),
    and the app targeting SDK greater than Lollipop MR1.

    :arg package: app package name
    :arg permissions: The permissions name

    :returns: True
    :raises Exception: If an error occurs




Properties
----------

.. function:: set_property(key, value, local=False)

    Set a property.

    .. Note:: Local properties are not supported if handset's SDK version > 15.

    .. Note:: If *local=False* and the key doesn't start with "persist." the
        property will be reset when handset is rebooted.

    .. Note:: If *local=True*, changes will only take effect upon reboot.

    .. Note:: If *local=True*, properties will be persistent through rebooting
        until ``/data/local.prop`` is cleared and the handset is rebooted again.

    :arg key: The property name (a string).
    :arg value: The property value (a string).
    :arg local: If *True* the property is set by writing *key=value* into
        ``/data/local.prop``, else the property is set with the ``setprop``
        command.
    :raises Exception: If the property was not set successfully.

.. function:: clear_local_properties()

    Clear all local properties by removing ``/data/local.prop``. The change
    does not take effect until the handset is rebooted.

    .. Note:: Local properties are not supported if handset's SDK version > 15.

Logging
-------

.. function:: clear_logcat(args='')

    Erase logcat logs from the handset.

    :arg args: Arguments to logcat; e.g. ``"-b main -b system"``.

.. function:: start_logcat(args='', log_file=None)

    Start Logcat logging.

    :arg args: Arguments to logcat; e.g. ``"-v time -b main"``.
    :arg log_file: A path where the log file will be saved on the test host
        (not on the handset). It is not necessary to provide this parameter
        to retrieve the logs later.
    :returns: A unique ID that can be used with ``get_log()``.

.. function:: stop_logcat(uid)

    Stop Logcat logging for the specified UID.

    Every call to start_logcat spawns a new Logcat logger thread which will
    remain active until the handset is deallocated. To preserve system
    resources, the caller should always call stop_logcat to free up
    system resources when the logcat associated with the specified UID
    is no longer needed.

    :arg uid: The unique id returned by ``start_logcat()``.

.. function:: get_logcat_log(uid, timeout=10)

    Get the logcat log by UID.

    :arg uid: The unique id returned by ``start_logcat()``.
    :arg timeout: Seconds before time out.
    :returns: The logcat log as a string.

Test Runners
------------

.. function:: get_instrumentation_runners(package)

    Get the JUnit instrumentation runners of a package on the handset.

    :arg package: The target package.
    :returns: A list of all instrumentation runners included in the package.

.. function:: run_junit(output_path=None, test_package=None, runner=None, \
        test_options=None, raw=None, timeout=0, timeout_kill=True)

    Run JUnit tests on the handset.

    It's possible to run full test scope of the junit instrumentation test
    or just a subset of it, depending on what parameters are given.
    Exactly one of apk, runner and raw must be given, i.e. they may not be
    combined. The possible parameter combinations can be found in the table
    below and more details can be found under Args.

    ====================== =========================================
    PARAMETERS             WHAT TO EXECUTE
    ====================== =========================================
    test_package           All tests in the package (all runners)
    runner                 All tests in the given runner
    runner, test_options   All tests that matches the parameters
    raw                    All tests that matches the raw parameters
    ====================== =========================================

    :arg output_path: The execution output data will be written to target
        output_path.

    :arg test_package: The package name of the test package, as a string. The
        value of the package attribute of the manifest element in the test
        package's manifest file. If given, all tests of the given package will
        be executed. May *not* be combined with: extras, runner nor raw.

    :arg runner: The instrumentation test runner (<test_package>/<runner_class>)
       to run, as a string. If given without test_options, all tests of the
       given instrumentation test runner will be executed. May *not* be combined
       with: apk nor raw.

    :arg test_options: A dictionary containing key-value pairs that will be used
        with the -e flag on am instrumentation (-e <key> <value>). Requires
        runner to be given but may _not_ be combined with apk nor raw. Details
        about test options can be found at http://developer.android.com/tools/testing/testing_otheride.html#AMOptionsSyntax

    :arg raw: A raw string containing all parameters to forward to ADB ``shell
        am instrument`` on execution. May *not* be combined with: apk, runner
        nor test_options.

    :arg timeout: Execution time out. No time out by default.

    :arg timeout_kill: If *True* an attempt to kill the test process will be
        conducted when a *Timeout* was raised. Default is *True*.

    :raises Timeout: If the execution timed out.
    :raises RunError: If the execution of ``am instrument`` failed or detected
        any of the folling conditions:

        * Invalid runner: Unable to find instrumentation info
        * Invalid test class: No such test class
        * Invalid test case: No such test case
        * Crash during instrumentation: Instrumentation test run crash
        * Handset dumped during test: Instrumentation test run incomplete

    :raises Exception: If any of the following:

        * Missing parameter
        * Invalid combination of parameters
        * Invalid parameter given
        * No such test package
        * No runners available
        * No such runner available

    :returns: The instrumentation test output as a string.

.. function:: kill_junit_test(package, timeout=10)

    Try to kill the process of a JUit test running from a specific package.

.. function:: list_gtest_tests(target)

    Returns a list of GTest tests.

    :arg target: The path on the handset to the GTest executable.
    :returns: A list of test names.
    :raises Exception: If target is not an existing executable file on the
        handset.

.. function:: run_gtest(target, result_path=None, args=[], timeout=0)

    Execute a GTest runner on the handset. If *result_path* is given, the
    execution output file and GTest result XML file will be saved on the
    host in that directory (not on the handset).

    :arg target: The path on the handset to the GTest executable.
    :arg result_path: A directory on the host where the result files are saved.
    :arg args: A list of arguments for the GTest execution, optional. See the
        "Supported Advanced Options" box below for a list of available options.
    :arg timeout: Seconds before execution time out.
    :returns: A 3-tuple containing the following items:

        * The execution output as a string,
        * Full path on host to the execution output data file or *None*,
        * Full path on host to the GTest XML result file or *None*

    :raises Timeout: If the execution timed out.
    :raises RunError: If execution failed.
    :raises Exception: If any invalid parameter was found.

    Advanced Options::

        --gtest_filter=POSTIVE_PATTERNS[-NEGATIVE_PATTERNS]
        --gtest_also_run_disabled_tests
        --gtest_repeat=[COUNT]
        --gtest_shuffle
        --gtest_random_seed=[NUMBER]
        --gtest_color=(yes|no|auto)
        --gtest_print_time=0
        --gtest_death_test_style=(fast|threadsafe)
        --gtest_break_on_failure
        --gtest_throw_on_failure
        --gtest_catch_exceptions=0

    For more info about GTest execution options visit:
        https://code.google.com/p/googletest/wiki/AdvancedGuide#Running_Test_Programs:_Advanced_Options

Miscelaneous
------------

.. function:: is_mounted(mount_point)

    Check if mount_point is mounted.

    :args mount_point: Mount point.
    :returns: *True* if *mount_point* is mounted, else *False*.

.. function:: sdcard_mounted()

    :returns: *True* if internal SD Card is mounted, else *False*.

.. function:: extcard_mounted()

    :returns: *True* if the external SD Card is mounted, else *False*.


.. function:: set_libc_debug_malloc(on, package, timeout=45)

    Convenience method to set/unset property *libc.debug.malloc* and execute
    'stop' and 'start' on the handset (stop/start must be executed for the
    change to take effect). The property *libc.debug.malloc* must be set to be
    able to dump native heap with ``dump_heap(native=True)``.

    .. Note:: Application processes will be restarted and get new PIDs.

    .. Note:: The *libc.debug.malloc* property is reset on reboot.

    :arg on: If *True* the property will be set to '1' otherwise it will be
        cleared.
    :arg package: The method waits for a process with name *package* to be
        started again after stop/start, before returning. (Preferably the same
        as the package provided to ``dump_heap()`` or a package that is known
        to be automatically started by the system.)
    :arg timeout: If > 0, seconds before timing out when waiting for package's
        process to be up and running.
    :returns: *True* if the property was set before execution of this method,
        else *False*.
    :raises Timeout: If such occured.
    :raises Exception: On other errors.

.. function:: dump_heap(directory, package, native=False, timeout=30)

    Dump heap for processes with name 'package' (using ``am dumpheap``) and
    save the resulting hprof-files to the *directory* on the host (not on the
    handset).

    .. Note:: The property *libc.debug.malloc* must already be set if
        *native=True*. See ``set_libc_debug_malloc()``.

    :arg directory: A directory on the host where the hprof files will be saved.
    :arg package: Dump heap for all processes with a name that matches exactly.
    :arg native: If *True*, dump native heap instead of managed heap.
    :arg timeout: If timeout > 0, seconds before time out.
    :returns: A list with each generated hprof file's full path on the host.
    :raises Timeout: If such occured.
    :raises Exception: On other errors.

Thermal
------------

Doze and App Standby
--------------------

.. function:: set_inactive(package, value)

    set the App Standby mode

    :arg package: the app package name
    :arg value: a string of true or false.
                true: force the app into idle;
                false: recover app from idle

.. function:: get_inactive(package)

    get the App Standby mode

    :arg package: the app package name
    :returns: the app mode

.. function:: dumpsys_battery(operate='unplug')

    set Battery Service state

    :arg operate: default is unplug, pretend device not to be charged

.. function:: dumpsys_deviceidle(command, para=None)

    Transition to Doze (Idle) mode

    :arg command: step: Immediately step to next state, without waiting for alarm.
                  force-idle: Force directly into idle mode, regardless of other device state.Use "step" to get out.
                  disable: Completely disable device idle mode.
                  enable: Re-enable device idle mode after it had previously been disabled.
                  enabled: Print 1 if device idle mode is currently enabled, else 0.
                  whitelist: Print currently whitelisted apps.
                  whitelist [package ...]: Add (prefix with +) or remove (prefix with -) packages.
                  tempwhitelist [package ..]: Temporarily place packages in whitelist for 10 seconds
    :arg para: default is None. If the command is whiltelist or tempwhitelist,
               the para should be a package name.
