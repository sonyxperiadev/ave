# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import sys
import base64
import uuid

from ave.broker import Broker
from ave.workspace import Workspace

def get_test_pretty():
    call_stack = sys._getframe(1).f_code
    return '%s %s' % (call_stack.co_filename, call_stack.co_name)


def generate_id():
    return base64.urlsafe_b64encode(uuid.uuid1().bytes).replace('=', '')


class StdOutRedirector(object):
    broker = None
    workspace = None
    path = None
    file = None
    original = None
    def __init__(self):
        self.broker = Broker()
        self.workspace = self.broker.get({'type':'workspace'})
        self.path = self.workspace.make_tempdir()
        self.file = self.workspace.make_tempfile(self.path)

    def redirect(self):
        self.original = sys.stdout
        sys.stdout = open(self.file, 'r+')

    def flush(self):
        sys.stdout.flush()

    def get_content(self):
        self.flush()
        f = open(self.file)
        content = f.read()
        return content

    def clear(self):
        f = open(self.file, 'w')
        f.truncate()

    def reset(self):
        sys.stdout = self.original

    def __del__(self):
        self.reset()