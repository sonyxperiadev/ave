# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os

import ave.cmd
from ave.workspace import Workspace

class EmmaWorkspace(Workspace):
    def _get_emma_jar_path(self):
        '''
        This method is mainly for changing emma jar package in unit test, in
        this case, emma jar may not exist in user file system, for acceptance
        test, emma jar file will be installed with ave.
        '''
        original_emma_path = Workspace._get_emma_jar_path(self)
        project_root = __file__
        for i in range(3):
            project_root = os.path.dirname(project_root)
        emma_install_path = os.path.join(project_root, original_emma_path[1:])
        return emma_install_path

def setup(fn):
    def decorated_fn(local):
        if local:
            w = EmmaWorkspace()
        else:
            w = Workspace()
        result = fn(local, w)
        if result:
            w.delete()
        return result
    return decorated_fn

# check generating html coverage report file succeeded.
@setup
def t1(local, w):
    pretty = '%s t1' % __file__
    print(pretty)

    em_path = os.path.join(
        os.path.dirname(__file__),'testdata','coverage.em')
    ec_path = os.path.join(
        os.path.dirname(__file__),'testdata','coverage.ec')
    try:
        report_path = w.make_coverage_report(em_path, ec_path)
        if not w.path_exists(report_path, 'file'):
            print(
                'FAIL %s: Could not create coverage report: %s'
                % (pretty, report_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    return True

# check generating html coverage report file succeeded with code source line.
@setup
def t2(local, w):
    pretty = '%s t2' % __file__
    print(pretty)

    em_path = os.path.join(
        os.path.dirname(__file__),'testdata','coverage.em')
    ec_path = os.path.join(
        os.path.dirname(__file__),'testdata','coverage.ec')
    src_tar = os.path.join(
        os.path.dirname(__file__),'testdata','coverage-src.tar')

    src_copied_path = w.make_tempdir()
    cmd = ['tar', '-x', '-C', src_copied_path, '-f', src_tar]
    (s, o, e) = ave.cmd.run(cmd)
    if s != 0:
        print('FAIL %s: Could not extract testing package source: %s'
              % (pretty, o))
        return False
    src_path = os.path.join(src_copied_path, 'sim-detection', 'src')

    try:
        report_path = w.make_coverage_report(em_path, ec_path, src_path)
        if not w.path_exists(report_path, 'file'):
            print(
                'FAIL %s: Could not create coverage report: %s'
                % (pretty, report_path)
            )
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False

    return True

# check that targetted emma.jar is tree-local or system installation depending
# on value of local (i.e. if test is executing as UNIT or ACCEPTANCE).
@setup
def t3(local, w):
    pretty = '%s t3' % __file__
    print(pretty)

    path = w._get_emma_jar_path()
    if local:
        tree_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if not path.startswith(tree_path):
            print('FAIL %s: not using tree-local emma.jar: %s' % (pretty, path))
            return False
    else:
        if not path.startswith('/usr/share/ave/workspace'):
            print('FAIL %s: not using system emma.jar: %s' % (pretty, path))
            return False

    return True
