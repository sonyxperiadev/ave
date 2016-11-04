# Copyright (C) 2013-2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import ave.cmd


HAS_AAPT = None


def which_aapt():
    global HAS_AAPT
    from ave.base_workspace import BaseWorkspace
    if HAS_AAPT is None:
        home = ave.config.load_etc()['home']
        cfg_path = BaseWorkspace.default_cfg_path(home)
        config = BaseWorkspace.load_config(cfg_path, home)
        if 'aapt' in config['tools']:
            HAS_AAPT = config['tools']['aapt']
            return HAS_AAPT
        else:
            cmd = ['which', 'aapt']
            a, out, s = ave.cmd.run(cmd)
            if out:
                HAS_AAPT = out.strip()
                return HAS_AAPT
            else:
                raise Exception('Error:You need to set aapt path to the environment variable '
                                'or config aapt path in %s tools node like ("tools":{"aapt":"/usr/bin/aapt"})' % cfg_path)
    else:
        return HAS_AAPT


def get_aapt_path():
    return which_aapt()


def get_version(apk_path, aapt_path=None):
    if not aapt_path:
        aapt_path = get_aapt_path()
    cmd = []
    cmd.append(aapt_path)
    cmd.extend(['d', 'badging'])
    cmd.append(apk_path)
    _, package_info, _ = ave.cmd.run(cmd, 1)

    version_line = None
    version_prefix = 'package: name='
    version_field = 'versionCode='
    for line in package_info.splitlines():
        line = line.strip()
        if line.startswith(version_prefix) and version_field in line:
            version_line = line
            break
    if not version_line:
       raise Exception('Can not find versionCode from "%s".' %
                            package_info)
    # version line is something like
    # "package: name='xxx' versionCode='1' versionName='1.1'"
    version_code = line.split('versionCode=', 1)[1].split(' ', 1)[0]
    return int(version_code.strip("'"))
