# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os

import ave.apk


from ave.workspace import Workspace

from decorators import smoke

class AaptWorkspace(Workspace):

    def get_aapt_path(self):
        '''
        This method is mainly for changing aapt in unit test, in
        this case, aapt may not exist in user file system, for acceptance
        test, aapt file will be installed with ave.
        '''
        project_root = __file__
        for i in range(3):
            project_root = os.path.dirname(project_root)
        aapt_install_path = os.path.join(project_root, 'bin/ave-aapt')
        return aapt_install_path

def setup(fn):
    def decorated_fn(local):
        if local:
            w = AaptWorkspace()
        else:
            w = Workspace()
        result = fn(w)
        if result:
            w.delete()
        return result
    return decorated_fn


# check that package names can be extraced
@smoke
@setup
def t1(w):
    pretty = '%s t1' % __file__
    print(pretty)
    root_path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    rel_path = os.path.join(root_path, "handset/jobs/tests/testdata/galatea-v-1.apk")
    apk_path = os.path.abspath(rel_path)
    if not apk_path:
        print('FAIL %s: could not download apk' % pretty)
        return False

    try:
        package_name = w.get_package_name(apk_path) # apk
        if not package_name:
            print(
                'FAIL %s: Could not get package name of apk: %s'
                % (pretty, apk_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    return True

# check that get_aapt_path return an existing path
@setup
def t2(w):
    pretty = '%s t2' % __file__
    print(pretty)

    path = w.get_aapt_path()
    if not os.path.isfile(path):
        print('FAIL %s: file "%s" does not exist.' % (pretty, path))
        return False
    return True

# check that get_apk_version can get the version of the apk
@setup
def t3(w):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        apk_path = os.path.join(os.path.dirname(__file__), 'testdata',
                                'gort-v-1.apk')
        version = w.get_apk_version(apk_path)
    except Exception, e:
        print('FAIL %s: failed: %s' % (pretty, str(e)))
        return False
    if version != 1:
        print('FAIL %s: failed to get the version of the apk: %s.' % (pretty,
                                                                apk_path))
        return False
    return True

# check that get_apk_version raise Exception if the apk doesn't exist
@setup
def t4(w):
    pretty = '%s t4' % __file__
    print(pretty)

    expected_exception = 'ERROR: dump failed because assets could not be loaded'
    try:
        w.get_apk_version('apk.non-existing')
    except Exception, e:
        if expected_exception not in e.message:
            print('FAIL %s: unexpected exception: %s.' % (pretty, str(e)))
            return False
        return True
    print('FAIL %s: missing exception: %s.' % (pretty, expected_exception))
    return False
