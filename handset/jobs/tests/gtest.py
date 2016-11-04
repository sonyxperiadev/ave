import os
import stat
import time

from decorators import smoke

# negative test of run_gtest(): parameter types
def t01(w,h):
    pretty = '%s t1' % __file__
    print(pretty)

    def verify_err(error, params):
        try:
            h.run_gtest(*params)
            print('FAIL %s: expected error on run_gtest: %s' % (pretty, params))
            return False
        except Exception as e:
            if not str(e).startswith(error):
                print(
                    'FAIL %s: wrong error message: %s, expected: %s'
                    % (pretty, str(e), error)
                )
                return False
        return True

    # target
    if not verify_err('target must be a non-empty string', (None, 'res path')):
        return False
    if not verify_err('target must be a non-empty string', ('', 'res path')):
        return False
    if not verify_err('target must be a non-empty string', (123, 'res path')):
        return False
    # result_path
    if not verify_err('result_path must be a non-empty string',('targ',['bu'])):
        return False
    path = os.path.join(w.get_path(), '_does_not_exist_')
    if not verify_err('result_path does not exist:', ('targ', path)):
        return False
    path = w.make_tempfile()
    if not verify_err('result_path not a writable directory:', ('targ', path)):
        os.remove(path)
        return False
    os.remove(path)
    # args
    args_error = 'args must be a list of strings'
    if not verify_err(args_error, ('targ', w.get_path(), None)):
        return False
    if not verify_err(args_error, ('targ', w.get_path(), 123)):
        return False
    if not verify_err(args_error, ('targ', w.get_path(), [123])):
        return False
    # timeout
    timeout_error = 'timeout must be an integer'
    if not verify_err(timeout_error, ('targ', w.get_path(),[], None)):
        return False
    if not verify_err(timeout_error, ('targ', w.get_path(),[], '0')):
        return False
    return True

# negative test of run_gtest(): target does not exist
def t03(w,h):
    pretty = '%s t3' % __file__
    print(pretty)

    target = ('/qwertyuiopasdfg123456')
    try:
        h.run_gtest(target, w.get_path())
        print(
            'FAIL %s: expected error (target does not exist): %s'
            % (pretty, target)
        )
        return False
    except Exception as e:
        if e.message != 'target does not exist: %s' % target:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# negative test of run_gtest(): target is not an executable file
def t04(w,h):
    pretty = '%s t4' % __file__
    print(pretty)

    def verify_target(target):
        try:
            h.run_gtest(target, w.get_path())
            print(
                'FAIL %s: expected error (not executable file): %s'
                % (pretty, target)
            )
            return False
        except Exception as e:
            if e.message != 'target is not an executable file: %s' % target:
                print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
                return False
        return True

    # file but not executable
    if not verify_target('/ueventd.rc'):
        return False
    # directory
    if not verify_target('/data'):
        return False
    # symlink
    if not verify_target('/sdcard'):
        return False
    return True

# negative test of run_gtest(): result_path not writable
def t05(w,h):
    pretty = '%s t5' % __file__
    print(pretty)

    result_path = w.make_tempdir()
    os.chmod(result_path, stat.S_IRUSR) # user read permission only
    try:
        h.run_gtest('some_target', result_path)
        print(
            'FAIL %s: expected error (not writable result directory): %s'
            % (pretty, temp_dir)
        )
        return False
    except Exception as e:
        if e.message != 'result_path not a writable directory: %s' % result_path:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    finally:
        os.removedirs(result_path)
    return True

# successful execution of run_gtest(): check files on host, verfiy their
#   content and that traces from run removed from handset
@smoke
def t06(w,h):
    pretty = '%s t6' % __file__
    print(pretty)

    if h.get_sdk_version() < 16:
        print('NO_RUN: gtest binary not compatible, skipping test.')
        return False

    def validate_xml_string(xml_string):
        import xml.sax.handler
        from   xml.sax.handler    import ContentHandler
        from   xml.sax            import parseString
        # A unicode string is not a well-formed XML by default, according to XML
        # 1.0 specification. Therefore the string may need to be encoded.
        try:
            uft8_xml = xml_string.encode('utf-8')
            xml.sax.parseString(uft8_xml, ContentHandler())
        except Exception, e1:
            # XML data when no encoding was needed.
            try:
                xml.sax.parseString(xml_string, ContentHandler())
            except Exception, e2:
                raise Exception('invalid XML format: %s' % e2)

    push_from = os.path.join(
        os.path.dirname(__file__), 'testdata', 'gtestAVESelfTest')
    if h.get_sdk_version() <= 22:
        push_from = os.path.join(push_from, 'bin', 'gtestAVESelfTest')
    else:
        push_from = os.path.join(push_from, '6.0', 'bin', 'gtestAVESelfTest')

    target = '/data/local/tmp/gtestAVESelfTest'
    res_path = w.make_tempdir()
    try:
        if not h.path_exists(target):
            h.push(push_from, target)
        (output,out_path,xml_path) = h.run_gtest(
            target, result_path=res_path, timeout=15
        )
        if not output:
            print('FAIL %s: no output returned from run_gtest()' % pretty)
            return False
        # verify output file exists...
        if not os.path.exists(out_path):
            print(
                'FAIL %s: returned path of output file does not exist: %s'
                % (pretty, out_path)
            )
            return False
        else: # ...and validate its content
            with open(out_path) as f:
                out_content = f.read()
            if not '[==========]' in out_content or not 'RUN' in out_content:
                print(
                    'FAIL %s: missing part(s) of the output file: %s'
                    % (pretty, out_path)
                )
                return False
        # verify XML file exists...
        if not os.path.exists(xml_path):
            print(
                'FAIL %s: returned path of XML file does not exist: %s'
                % (pretty, out_path)
            )
            return False
        else: # ...validate XML format
            with open(xml_path) as f:
                xml_content = f.read()
            validate_xml_string(xml_content)
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# check timeout on run_gtest(): verify gtest process is killed on timeout
def t07(w,h):
    pretty = '%s t7' % __file__
    print(pretty)

    if h.get_sdk_version() < 16:
        print('NO_RUN: gtest binary not compatible, skipping test.')
        return False

    push_from = os.path.join(
        os.path.dirname(__file__), 'testdata', 'gtestAVESelfTest', 'bin')
    if h.get_sdk_version() <= 22:
        push_from = os.path.join(push_from, 'bin', 'gtestAVESelfTest')
    else:
        push_from = os.path.join(push_from, '6.0', 'bin', 'gtestAVESelfTest')

    target = '/data/local/tmp/gtestAVESelfTest'
    res_path = w.make_tempdir()
    try:
        if not h.path_exists(target):
            h.push(push_from, target)
        # gtest that is expected to execute for much longer time
        (output,out_path,xml_path) = h.run_gtest(
            target, result_path=res_path, timeout=1
        )
    except Exception as e:
        if not 'command timed out' in str(e):
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    try:
        time.sleep(1) # give it a second to stop
        # verify process did not continue execution upon time out
        procs = h.get_processes(name=os.path.basename(target))
        if procs != []:
            print(
                'FAIL %s: expected no process for %s: %s'
                % (pretty, os.path.basename(target), procs)
            )
            return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# test list_gtest_tests() expect OK
@smoke
def t08(w,h):
    pretty = '%s t8' % __file__
    print(pretty)

    if h.get_sdk_version() < 16:
        print('NO_RUN: gtest binary not compatible, skipping test.')
        return False

    push_from = os.path.join(
        os.path.dirname(__file__), 'testdata', 'gtestAVESelfTest', 'bin')
    if h.get_sdk_version() <= 22:
        push_from = os.path.join(push_from, 'bin', 'gtestAVESelfTest')
    else:
        push_from = os.path.join(push_from, '6.0', 'bin', 'gtestAVESelfTest')

    target = '/data/local/tmp/gtestAVESelfTest'
    res_path = w.make_tempdir()

    try:
        if not h.path_exists(target):
            h.push(push_from, target)
        gtests = h.list_gtest_tests(target)
        if not gtests:
            print('FAIL %s: expected non-empty list of tests' % pretty)
            return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# negative test of list_gtest_tests(): target does not exist
def t09(w,h):
    pretty = '%s t9' % __file__
    print(pretty)

    target = ('/qwertyuiopasdfg123456')
    try:
        h.list_gtest_tests(target)
        print(
            'FAIL %s: expected error (target does not exist): %s'
            % (pretty, target)
        )
        return False
    except Exception as e:
        if e.message != 'target does not exist: %s' % target:
            print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
            return False
    return True

# negative test of list_gtest_tests(target): target is not an executable file
def t10(w,h):
    pretty = '%s t10' % __file__
    print(pretty)

    def verify_target(target):
        try:
            h.list_gtest_tests(target)
            print(
                'FAIL %s: expected error (not executable file): %s'
                % (pretty, target)
            )
            return False
        except Exception as e:
            if e.message != 'target is not an executable file: %s' % target:
                print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
                return False
        return True

    # file but not executable
    if not verify_target('/ueventd.rc'):
        return False
    # directory
    if not verify_target('/data'):
        return False
    # symlink
    if not verify_target('/sdcard'):
        return False
    return True

# check output, None, None is returned if no result_path was given
def t11(w,h):
    pretty = '%s t11' % __file__
    print(pretty)

    if h.get_sdk_version() < 16:
        print('NO_RUN: gtest binary not compatible, skipping test.')
        return False

    push_from = os.path.join(
        os.path.dirname(__file__), 'testdata', 'gtestAVESelfTest', 'bin')
    if h.get_sdk_version() <= 22:
        push_from = os.path.join(push_from, 'bin', 'gtestAVESelfTest')
    else:
        push_from = os.path.join(push_from, '6.0', 'bin', 'gtestAVESelfTest')

    target = '/data/local/tmp/gtestAVESelfTest'
    try:
        if not h.path_exists(target):
            h.push(push_from, target)
        (output,out_path,xml_path) = h.run_gtest(target, timeout=15)
        if not output:
            print('FAIL %s: no output returned from run_gtest()' % pretty)
            return False
        if out_path:
            print(
                'FAIL %s: expected no output file path from run_gtest() but got'
                ' %s' % (pretty, out_path)
            )
            return False
        if xml_path:
            print(
                'FAIL %s: expected no xml result file path from run_gtest() but'
                ' got %s' % (pretty, xml_path)
            )
            return False
    except Exception as e:
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False
    return True

# test run_gtest() raises "invalid executable" exception
def t12(w,h):
    pretty = '%s t12' % __file__
    print(pretty)

    if h.get_sdk_version() < 16:
        print('NO_RUN: gtest binary not compatible, skipping test.')
        return False

    push_from = os.path.join(
        os.path.dirname(__file__), 'testdata', 'gtest-invalid'
    )
    target = '/data/local/tmp/gtest-invalid'
    res_path = w.make_tempdir()

    try:
        h.push(push_from, target)
        h.run_gtest(target)
        print('FAIL %s: expected "invalid executable" exception.' % pretty)
        return False
    except Exception as e:
        if 'invalid executable' not in str(e):
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False
    return True
