# Check exception when forcing a dump during the test run.
# UNIT TEST ONLY
def t45(w,h,branch):
    pretty = '%s t45' % __file__
    print(pretty)

    # Get and install apks
    package_name = prepare_apk(pretty,w,h,branch)
    if not package_name:
        return False
    runner = 'com.sonyericsson.organizer.test/com.sonyericsson.organizer.ru' \
        'nners.SystemTestRunner'
    # Where the test execution output should be written to
    output_path = w.make_tempfile()
    try:
        h.root()
    except Exception, e:
        print('FAIL %s: root failed: %s' % (pretty, str(e)))
        return False

    def force_dump(h):
        time.sleep(5)
        h.force_dump()

    p = Process(target=force_dump, args=(h,))
    p.start()
    try:
        # Run all test cases on instrumentation apk
        output = h.run_junit(output_path, runner=runner)
        print('FAIL %s: expected exception (incomplete run)' % (pretty))
        return False
    except (RunError) as e:
        if e.details['message'] != 'instrumentation test run incomplete':
            print('FAIL %s: wrong message %s' % (pretty,e.details['message']))
            # if there another exception, the other process will still force a
            # dump which must be taken care of to avoid subsequent tests fail
            time.sleep(7)
            h.wait_power_state('boot_completed', timeout=300)
            return False
    except Exception, e:
        print('FAIL %s: expected RunError got Exception: %s' % (pretty,str(e)))
        # if there another exception, the other process will still force a
        # dump which must be taken care of to avoid subsequent tests fail
        time.sleep(7)
        h.wait_power_state('boot_completed', timeout=300)
        return False
    p.join()
    try:
        # Make sure the device gets ready
        h.wait_power_state('boot_completed', timeout=300)
        h.root()
        # Remove crash dump
        # TODO: use Handset.remove_crashes() when it's available
        h.rm('/sdcard/CrashDump/*', recursive=True)
        # Give it some extra time before moving on to next test
        time.sleep(10)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# kill com.sonyericsson.organizer.test and expect:
# INSTRUMENTATION_RESULT: shortMsg=Process crashed in RunError output
# UNIT TEST ONLY
def t2(w,h,branch):
    pretty = '%s t56' % __file__
    print(pretty)

    output = None
    # Get and install apks
    package_name = prepare_apk(pretty,w,h,branch)
    if not package_name:
        return False

    tr = 'com.sonyericsson.organizer.test/' \
          'com.sonyericsson.organizer.runners.SystemTestRunner'

    def stop_test(package):
        time.sleep(10)
        h.kill_junit_test(package)

    p = Process(target=stop_test, args=('com.sonyericsson.organizer.test',))
    p.start()

    output_path = w.make_tempfile()
    try:
        output = h.run_junit(
            output_path, runner=tr, timeout=20
        )
        print('FAIL %s: expected RunError' % (pretty))
        return False
    except RunError as e:
        if e.details['message'] != 'instrumentation test run crash':
            print('FAIL %s: wrong RunError: %s' %(pretty,e.details['message']))
            return False
        if not 'ptyout' in e.details:
            print('FAIL %s: expected ptyout in RunError.details' % (pretty))
            return False
        if e.details['ptyout'] == '':
            print('FAIL %s: ptyout empty string in RunError.details' %(pretty))
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    p.join()
    if h.get_processes(package_name, exact=True) != []:
        print('FAIL %s: process not killed: %s' % (pretty, package_name))
        return False
    return True

