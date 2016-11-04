# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import re
import getopt

import ave.git

import vcsjob # to get constant definitions

usage = '''
Syntax:
    vcsjob fetch -s|--source <url> -d|--destination <path> -r|--refspec <version> -t|--timeout <timeout>
'''

def parse_url(url, debug=False):
    m = re.match('(?P<scheme>.+?)://(?P<path>.*)', url)
    if m:
        scheme = m.group('scheme')
        path   = m.group('path')
    else:
        scheme = 'file'
        path   = url
    return (scheme, path)

def get_opt(argv):
    (opts, args) = getopt.gnu_getopt(
        argv, 's:r:d:t:', ['source=', 'refspec=', 'destination=', 'timeout=']
    )

    if args:
        args = ','.join(args)
        raise Exception('non-dashed options "%s" not recognized' % args)

    src     = None
    dst     = None
    refspec = None
    timeout = 600

    for (opt, arg) in opts:
        if   opt in ['-s', '--source']:
            src = arg
        elif opt in ['-r', '--refspec']:
            refspec = arg
        elif opt in ['-d', '--destination']:
            dst = arg
        elif opt in ['-t', '--timeout']:
            timeout = int(arg)

    return (src, dst, refspec, timeout)

def fetch(src, dst, refspec, depth=1, timeout=600):
    if not (src and dst and refspec):
        raise Exception('source, refspec and destination must be specified')

    # parse the source URL. it should specify a scheme. if none is given, it
    # defaults to "file".
    (src_scheme, src_path) = parse_url(src)
    if src_scheme == 'file':
        src_path = os.path.realpath(src_path)
        if not ave.git.is_git(src_path):
            raise Exception('supported protocols: git')

    # parse the destination URL. it should not specify a scheme. if it does,
    # then it has to be "file". no other schemes are supported as destinations.
    (dst_scheme, dst_path) = parse_url(dst)
    if dst_scheme != 'file':
        raise Exception('destination must be on a locally mounted file system')
    dst_path = os.path.realpath(dst_path)
    if src_scheme == 'file':
        if not ave.git.sync(src_path, dst_path, refspec, timeout=timeout, depth=depth):
            return vcsjob.NOFETCH
        return vcsjob.OK

    if src_scheme in ['git', 'ssh']:
        if not ave.git.sync(src, dst_path, refspec, timeout=timeout, depth=depth):
            return vcsjob.NOFETCH
        return vcsjob.OK

def main(argv):
    try:
        (src, dst, refspec, timeout) = get_opt(argv)
    except Exception, e:
        print('ERROR: %s' % str(e))
        return vcsjob.NOFETCH

    try:
        return fetch(src, dst, refspec, timeout=timeout)
    except Exception, e:
        print('ERROR: %s' % str(e))
        return vcsjob.NOFETCH
