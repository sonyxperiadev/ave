# Copyright (C) 2016 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys

from ave.workspace import Workspace

def setup(fn):
    def decorated_fn():
        w = Workspace()
        result = fn(w)
        w.delete()
        return result
    return decorated_fn


@setup
def t01(w):
    '''
        Template.
    '''
    pretty = '%s t01' % __file__
    print(pretty)
    try:
        return True
    except Exception, e:
        print('FAIL %s: wrong exception type: %s' % (pretty, type(e)))
        return False
    return True

#test zip works
@setup
def t02(w):
    pretty = '%s t02' % __file__
    print(pretty)

    work_dir = w.get_path()
    file = w.make_tempfile()
    f = open(file, 'w')
    f.write('hello, a file will be zip')
    f.close()

    dir1 = w.make_tempdir()
    file1 = w.make_tempfile(path=dir1)
    f1 =open(file1, 'w')
    f1.write('hello, a dir will be zip')
    f1.close()
    try:
        z = w.zip(file)
        if z != os.path.join(work_dir, '%s.zip' % os.path.basename(file)):
            print('FAIL %s: zip file return a wrong zip name' % pretty)
            return False

        z = w.zip(file, dst='file.zip')
        if z != os.path.join(work_dir, 'file.zip'):
            print('FAIL %s: zip file not return a specified zip name' % pretty)
            return False

        z = w.zip(dir1)
        if z != os.path.join(work_dir, '%s.zip' % os.path.basename(dir1)):
            print('FAIL %s: zip dir return a wrong zip name' % pretty)
            return False

        z = w.zip(dir1, dst='dir1.zip')
        if z != os.path.join(work_dir, 'dir1.zip'):
            print('FAIL %s: zip dir not return a specified zip name' % pretty)
            return False

        # a file list will be zip
        z = w.zip([file, dir1])
        if z != os.path.join(work_dir, '%s.zip' % os.path.basename(work_dir)):
            print('FAIL %s: zip file list return a wrong zip name' % pretty)
            return False

        z = w.zip([file, dir1], dst='list.zip')
        if z != os.path.join(work_dir, 'list.zip'):
            print('FAIL %s: zip file list not return a specified zip name' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: zip occurs an error:%s' % (pretty, str(e)))
        return False

    return True

#test unzip works
@setup
def t03(w):
    pretty = '%s t03' % __file__
    print(pretty)

    work_dir = w.get_path()
    file = w.make_tempfile()
    f =open(file, 'w')
    f.write('hello, zip zip')
    f.close()
    w.zip(file, dst='dest.zip')
    if not os.path.exists(os.path.join(work_dir, 'dest.zip')):
        print('FAIL %s: not existing an zip file' % pretty)
        return False
    try:
        path = w.unzip('dest.zip')
        if path != os.path.join(work_dir, 'dest'):
            print('FAIL %s: unzip a zip file return a wrong path' % pretty)
            return False
        if not os.path.exists(os.path.join(path, os.path.basename(file))):
            print('FAIL %s: unzip a zip file not success' % pretty)
            return False

        path = w.unzip('dest.zip', path='unpack_dir')
        if path != os.path.join(work_dir, 'unpack_dir'):
            print('FAIL %s: unzip a zip file not return a specified path' % pretty)
            return False
    except Exception, e:
        print('FAIL %s: unzip occurs an error:%s' % (pretty, str(e)))
        return False

    return True