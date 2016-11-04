# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import StringIO
import tempfile
import shutil
import traceback

from ave.workspace import Workspace

from decorators import smoke

def setup(fn):
    def decorated_fn():
        w = Workspace()
        result = fn(w)
        w.delete()
        return result
    return decorated_fn

# Test of ls() and that files can be found when expected.
@setup
def t01(w):
    pretty = '%s t01' % __file__
    print(pretty)

    # First get some files
    w.copy(os.getcwd()+"/jobs/tests", w.path)
    path = w.path+"/tests/testdata"
    try:
        nothing = w.ls(path, '*.py')

    except Exception, e:
        print('FAIL %s: ls failed: %s' % (pretty, str(e)))
        return False

    if len(nothing) != 0:
        print('FAIL %s: found files not expected: %s' % (pretty, nothing))
        return False

    try:
        nothing = w.ls(path, '*.apk')
    except Exception, e:
        print('FAIL %s: ls failed: %s' % (pretty, str(e)))
        return False

    if len(nothing) != 1:
        print('FAIL %s: found no files as expected: %s' % (pretty, nothing))
        return False

    return True

# Test of path_exists() and that it works when folders exists (and not)
# but also that the correct file_type is respected.
@setup
def t02(w):
    pretty = '%s t02' % __file__
    print(pretty)
	
    w.copy(os.getcwd()+"/jobs/tests/", w.path)
    path = w.path+"/tests"

    try:
        dir_name = os.path.join(path, 'testdata/white.png')
        is_dir = w.path_exists(dir_name, 'directory')
    except Exception, e:
        print('FAIL %s: path_exists failed: %s' % (pretty, str(e)))
        return False
    if is_dir == True:
        print('FAIL %s: found directory not expected: %s' % (pretty, dir_name))
        return False

    try:
        dir_name = os.path.join(path, 'testdata')
        is_dir = w.path_exists(dir_name, 'directory')
    except Exception, e:
        print('FAIL %s: path_exists failed: %s' % (pretty, str(e)))
        return False
    if is_dir == False:
        print('FAIL %s: found directory expected: %s' % (pretty, dir_name))
        return False

    try:
        dir_name = os.path.join(path, 'testdata')
        is_file = w.path_exists(dir_name, 'file')
    except Exception, e:
        print('FAIL %s: path_exists failed: %s' % (pretty, str(e)))
        return False
    if is_file == True:
        print('FAIL %s: found file not expected: %s' % (pretty, dir_name))
        return False

    return True

# Test of get_checksum() and that it raise a exception when path doesn't exists.
@setup
def t03(w):
    pretty = '%s t03' % __file__
    print(pretty)

    path = os.path.join(w.get_path(), 'non-existing')
    try:
        w.get_checksum(path)
    except Exception, e:
        if 'non-existing does not exist' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of get_checksum() and that it raise a exception when path isn't a file.
@setup
def t04(w):
    pretty = '%s t04' % __file__
    print(pretty)

    path = w.get_path()
    try:
        w.get_checksum(path)
    except Exception, e:
        if 'is not a file' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of get_checksum() and that it raise a exception when path is outside workspace.
@setup
def t05(w):
    pretty = '%s t05' % __file__
    print(pretty)

    path = '/outside-workspace'
    try:
        w.get_checksum(path)
    except Exception, e:
        if 'path cannot be outside workspace' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of get_checksum() and that it returns the checksum of a file.
@setup
def t06(w):
    pretty = '%s t06' % __file__
    print(pretty)

    try:
        filename = 'test4getchecksum.tmp'
        # Create a tmp file about 1 M size.
        path = os.path.join(w.get_path(), filename)
        with open(path, 'w') as f:
            test_string = 'a' * 1023
            for i in range(1023):
                f.write(test_string)

        checksum = w.get_checksum(filename)
        if checksum != '0407997675518ca322a9c131355965db':
            print('FAIL %s: unexpected checksum value: %s' % (pretty, checksum))
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False
    return True

# Test of cat() and that it raise a exception when path doesn't exists.
@setup
def t07(w):
    pretty = '%s t07' % __file__
    print(pretty)

    path = os.path.join(w.get_path(), 'non-existing')
    try:
        w.cat(path)
    except Exception, e:
        if 'non-existing does not exist' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of cat() and that it raise a exception when path isn't a file.
@setup
def t08(w):
    pretty = '%s t08' % __file__
    print(pretty)

    path = w.get_path()
    try:
        w.cat(path)
    except Exception, e:
        if 'is not a file' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of cat() and that it raise a exception when path is outside workspace.
@setup
def t09(w):
    pretty = '%s t09' % __file__
    print(pretty)

    path = '/outside-file'
    try:
        w.cat(path)
    except Exception, e:
        if 'path cannot be outside workspace' not in e.message:
            print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
            return False
    return True

# Test of cat() and that it returns the binary content of a file.
@setup
def t10(w):
    pretty = '%s t10' % __file__
    print(pretty)

    try:
        # Create a tmp file about 1 M size.
        filename = 'test4cat.tmp'
        path = os.path.join(w.get_path(), filename)
        origin_content = '\xa7\xb8\xc7'
        with open(path, 'wb') as f:
            f.write(origin_content)

        content = w.cat(filename)
        if content != origin_content:
            print('FAIL %s: unexpected content value: %s' % (pretty, content))
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False
    return True

def _verify_content(actual, expected, pretty):

    if len(actual) != len(expected):
        print('FAIL %s: unexpected content size: %s' % (pretty, len(actual)))
        return False

    for i in range(len(expected)):

        if actual[i] != expected[i]:
            print('FAIL %s: unexpected content: %s expected %s at position %d' %
                (pretty, actual[i], expected[i], i))
            return False

    return True

# Test of cat() and that it returns the content of a file as unicode.
@setup
def t11(w):
    pretty = '%s t11' % __file__
    print(pretty)

    try:
        origional = '\xa7a\xc7bc'

        filename = 'test4cat.tmp'
        path = os.path.join(w.get_path(), filename)
        with open(path, 'wb') as f:
            f.write(origional)

        actual   = w.cat(filename, encoding='ascii')
        expected = u'\uFFFDa\uFFFDbc'
        return _verify_content(actual, expected, pretty)
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False

# Test of cat() and that it returns the content of a file as unicode.
@setup
def t12(w):
    pretty = '%s t12' % __file__
    print(pretty)

    try:
        origional = '\xa7a\xc7bc'

        filename = 'test4cat.tmp'
        path = os.path.join(w.get_path(), filename)
        with open(path, 'wb') as f:
            f.write(origional)

        actual   = w.cat(filename, encoding='ascii', errors='ignore')
        expected = u'abc'
        return _verify_content(actual, expected, pretty)
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False

# Test of cat() and that it returns the content of a file as unicode.
@setup
def t13(w):
    pretty = '%s t13' % __file__
    print(pretty)

    try:
        origional = str(bytearray(range(255)))

        filename = 'test4cat.tmp'
        path = os.path.join(w.get_path(), filename)
        with open(path, 'wb') as f:
            f.write(origional)

        actual   = w.cat(filename, encoding='latin-1').encode('latin-1')
        expected = origional
        return _verify_content(actual, expected, pretty)
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False

# Test of write_tempfile().
@setup
def t14(w):
    pretty = '%s t14' % __file__
    print(pretty)

    try:
        a = []
        s = ''
        for i in range(0, 10):
            tmp = '\xa7\xb8\xc7'
            tmp_unicode = u'\u4f60\u597d'
            s += tmp
            s += tmp_unicode.encode('utf-8')
            a.append(tmp)
            a.append(tmp_unicode)
        path = w.write_tempfile(a, encoding='utf-8')
        tmpfile = os.path.basename(path)
        if not tmpfile.startswith('tmp'):
            print('FAIL %s: not writing a temp file: %s' % (pretty, path))
            return False
        content = w.cat(path)
        if content != s:
            print('FAIL %s: unexpected content value: %s' % (pretty, content))
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False
    return True


# Test of promote(). Create a tempfile, promote it to a targetfile
# make sure the file is created and pushed to flocker, verify return
# values
@setup
def t15(w):
    pretty = '%s t15' % __file__
    print(pretty)

    temp_file = w.make_tempfile()
    target = 'application.txt'

    result = w.promote(temp_file, target)

    if len(w.ls(w.get_path(), temp_file)) != 1:
        print('FAIL %s: temp file was destroyed: %s' %
                (pretty, temp_file))
        return False

    if len(w.ls(w.get_path(), target)) != 1:
        print('FAIL %s: promoted target file was can not be found: %s' %
                (pretty, target))
        return False
    return True

# Test of promote() when target is an tmp-file (not allowed)
@setup
def t16(w):
    pretty = '%s t16' % __file__
    print(pretty)

    temp_file = w.make_tempfile()
    target = os.path.basename(w.make_tempfile())

    try:
        result = w.promote(temp_file, target)
    except Exception as e:
        if 'tmpfile can not be target' in str(e):
            return True
        print('FAIL %s: unexpected exception: %s' %
                (pretty, e))
        return False
    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of promote() when target already exists
@setup
def t17(w):
    pretty = '%s t17' % __file__
    print(pretty)

    temp_file = w.make_tempfile()
    target_file = 'application.txt'
    target_path = os.path.join(w.get_path(), target_file)
    shutil.copy(temp_file, target_path)

    try:
        result = w.promote(temp_file, target_file)
    except Exception as e:
        if 'target file exists' in str(e):
            return True
        print('FAIL %s: unexpected exception: %s' %
                (pretty, e))
        return False
    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of promote(), not allowed to promote files outside workspace
@setup
def t18(w):
    pretty = '%s t18' % __file__
    print(pretty)

    w2 = Workspace()
    temp_file2 = w2.make_tempfile()
    target_file = 'application.txt'

    try:
        result = w.promote(temp_file2, target_file)
    except Exception as e:
        if 'source file not stored inside workspace' in str(e):
            return True
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of promote(), with nested target folders
@setup
def t19(w):
    pretty = '%s t19' % __file__
    print(pretty)

    temp_file = w.make_tempfile()
    target = 'A/B/C/application.txt'

    result = w.promote(temp_file, target)

    if len(w.ls(w.get_path(), temp_file)) != 1:
        print('FAIL %s: temp file was destroyed: %s' %
                (pretty, temp_file))
        return False

    if len(w.ls(w.get_path(), target)) != 1:
        print('FAIL %s: promoted target file was can not be found: %s' %
                (pretty, target))
        return False
    return True

# Test of promote(), with folder accidentally in PC root /A
@setup
def t20(w):
    pretty = '%s t20' % __file__
    print(pretty)

    temp_file = w.make_tempfile()
    target_file = '/A/B/C/application.txt'

    try:
        result = w.promote(temp_file, target_file)
    except Exception as e:
        if 'target must be within workspace' in str(e):
            return True
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of promote(), with nonexistant file
@setup
def t21(w):
    pretty = '%s t21' % __file__
    print(pretty)

    temp_file = '%snonexistant' %w.make_tempfile()

    try:
        result = w.promote(temp_file, temp_file)
    except Exception as e:
        if 'source file does not exist:' in str(e):
            return True
        print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
        return False

    print('FAIL %s: expected exception, but none raised' % pretty)
    return False

# Test of write_tempfile() with promotion target.
@setup
def t22(w):
    pretty = '%s t22' % __file__
    print(pretty)

    promoted_target = 'pmt_target.%s' %os.path.basename(w.make_tempfile())
    try:
        a = []
        s = ''
        for i in range(0, 10):
            tmp = '\xa7\xb8\xc7'
            tmp_unicode = u'\u4f60\u597d'
            s += tmp
            s += tmp_unicode.encode('utf-8')
            a.append(tmp)
            a.append(tmp_unicode)
        path = w.write_tempfile(a,
                                encoding='utf-8',
                                promoted_target=promoted_target)
        tmpfile = os.path.basename(path)
        if not tmpfile == promoted_target:
            print('FAIL %s: wrong file returned: %s' % (pretty, path))
            return False
        content = w.cat(path)
        if content != s:
            print('FAIL %s: unexpected content value: %s' % (pretty, content))
            return False
    except Exception, e:
        print('FAIL %s: unexpected exception: %s' % (pretty, e.message))
        return False
    return True

# Test of write_tempfile() with promotion target where file exists
@setup
def t23(w):
    pretty = '%s t23' % __file__
    print(pretty)

    promoted_target = 'pmt_target.%s' %os.path.basename(w.make_tempfile())
    path = w.write_tempfile('a',
                            encoding='utf-8',
                            promoted_target=promoted_target)

    try:
        twin_path = w.write_tempfile('b',
                                encoding='utf-8',
                                promoted_target=promoted_target)
    except Exception as e:
        if 'target file exists' in str(e):
            return True
        print('FAIL %s: wrong exception raised: %s' % (pretty, str(e)))
        return False
    print('FAIL %s: no exception raised: %s' % (pretty, str(e)))
    return False

# Test of write_tempfile() with promoted target outside ws
@setup
def t24(w):
    pretty = '%s t24' % __file__
    print(pretty)

    promoted_target = '/pmt_target.%s' %os.path.basename(w.make_tempfile())
    try:
        path = w.write_tempfile('a',
                                encoding='utf-8',
                                promoted_target=promoted_target)
    except Exception as e:
        if 'target must be within workspace' in str(e):
            return True
        print('FAIL %s: wrong exception raised: %s' % (pretty, str(e)))
        return False
    print('FAIL %s: no exception raised: %s' % (pretty, str(e)))
    return False
