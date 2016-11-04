# Copyright (C) 2016 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import apt

def get_package_version(package='ave'):
    cache = apt.cache.Cache()
    pkg = cache[package]
    instver = pkg.installed
    if instver is None:
        raise Exception('The package "%s" was not installed' % package)
    return instver.version
