# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

class DeviceOffline(Exception):
    def __init__(self):
        Exception.__init__(self, 'device is offline')
