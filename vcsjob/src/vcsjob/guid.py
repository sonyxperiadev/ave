# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import json
import random
import string

def set_guid(guid):
    # Will delete whatever guid was already set, with no warning
    if not guid:
        try:
            del os.environ['VCSJOB_GUID']
        except KeyError:
            pass
        return
    if type(guid) not in [str, unicode]:
        raise Exception('guid is not a string: %s' % guid)
    if type(guid) != unicode:
        guid = unicode(guid.decode('utf-8'))
    os.environ['VCSJOB_GUID'] = guid.encode('utf-8')

def get_guid():
    # Loads a previously set guid
    if not 'VCSJOB_GUID' in os.environ:
        raise Exception('guid not set')

    if not os.environ['VCSJOB_GUID']:
        raise Exception('guid not set')
    try:
        guid = os.environ['VCSJOB_GUID'].decode('utf-8')
    except Exception as e:
        raise Exception ('Wrong format of guid (%s): %s' %(guid, e))

    return guid
