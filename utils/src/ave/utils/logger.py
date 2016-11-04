# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys
import traceback

import ave.panotti

from datetime import datetime


class LogLevel(object):
    log_level_map = {'d': {'name': 'DEBUG  ',  # WHITE
                           'numeric': 10,
                           'color': '\033[0m'},
                     'i': {'name': 'INFO   ',  # BLUE
                           'numeric': 20,
                           'color': '\033[94m'},
                     'o': {'name': 'OK     ',  # GREEN
                           'numeric': 30,
                           'color': '\033[92m'},
                     'w': {'name': 'WARNING',  # YELLOW
                           'numeric': 40,
                           'color': '\033[93m'},
                     'e': {'name': 'ERROR  ',  # RED
                           'numeric': 50,
                           'color': '\033[91m'},
                     'x': {'name': 'NONE   ',  # PURPLE
                           'numeric':  0,
                           'color': '\033[95m'}
                     }

    @classmethod
    def get_level_name(cls, level):
        return cls.log_level_map[cls.verify_level(level)]['name']

    @classmethod
    def get_level_numeric(cls, level):
        return cls.log_level_map[cls.verify_level(level)]['numeric']

    @classmethod
    def colorize_string(cls, level, string):
        return '%s%s%s' % (cls.log_level_map[cls.verify_level(level)]
                           ['color'], string, '\033[0m')

    @classmethod
    def verify_level(cls, level):
        lvl = str(level).lower()
        if lvl in cls.log_level_map:
            return lvl
        else:
            raise Exception('Log level "%s" not an accepted level, accepted '
                            'levels:%s' % (lvl, cls.log_level_map.keys()))


class Logger(object):
    def __init__(self, workspace, guid, file_path='test_job_log.txt',
                 lowest_level='x'):
        self.workspace = workspace
        self.guid = guid
        self.file_path = file_path
        self.pending_flocker_strings = ''
        self.log_shouted = False
        self.flocker_session_key = None
        self.flocker_enabled = True
        self.lowest_level = LogLevel.get_level_numeric(lowest_level)

        self.log_it('i', 'Initiating Test Job Log in flocker')

    def set_lowest_log_level(self, lvl):
        self.lowest_level = LogLevel.get_level_numeric(lvl)

    def log_traceback(self, lvl):
        _, _, _tb = sys.exc_info()
        stack_trace = traceback.extract_tb(_tb)
        self._print_message(lvl, 'Stack trace')
        for stack_item in stack_trace:
            self._print_message(lvl, '   %s' % str(stack_item))

    def log_it(self, lvl, message, handset=None):
        if LogLevel.get_level_numeric(lvl) < self.lowest_level:
            return
        if handset is not None:
            serial = handset.get_profile()['serial']
            message = 'Handset[%s] - %s' % (serial, message)
        result = self._print_message(lvl, message)

        if not self.log_shouted and result:
            self.shout_log_to_panotti_if_result(result)

        #If log level is error (or higher) print traceback
        if LogLevel.get_level_numeric(lvl) >= LogLevel.get_level_numeric('e'):
            self.log_traceback(lvl)
        return result

    def shout_log_to_panotti_if_result(self, result):
        self.flocker_url, self.flocker_session_key = \
            self.parse_flocker_data(result)
        if self.flocker_url:
            info = {'title': 'Test Job Log', 'url': '%s/%s' % (self.flocker_url,
                                                               self.file_path)}
            self.log_shouted = True
        else:
            info = {'title': 'Test Job Log', 'url': 'Failed to log to flocker'}
        try:
            if self.guid:
                ave.panotti.shout(self.guid, info)
        except:
            self.log_shouted = False
        self.log_it('d', '%s: %s' % (info['title'], info['url']))

    def _push_message(self, message):
        """
        Encapsulating flocker_push_string to be able to test exceptions from
        function in self tests
        """
        return self.workspace.flocker_push_string(message,
                                                  self.file_path)

    def _print_message(self, lvl, message):
        message = '%s - %s - %s' % (datetime.now().strftime
                  ("%Y-%m-%d %H:%M:%S"), LogLevel.get_level_name(lvl), message)
        print '%s' % (LogLevel.colorize_string(lvl, message))
        result = None
        if self.workspace and self.flocker_enabled:
            message += '\n'
            try:
                if self.pending_flocker_strings:
                    self._push_message(self.pending_flocker_strings)
                    self.pending_flocker_strings = ''
                result = self._push_message(message)
            except Exception, e:
                if 'the flocker is disable' in str(e):
                    self.flocker_enabled = False
                    return result
                self.pending_flocker_strings += message
                # store message for later if we get an exception from
                # flocker_push_string
        return result

    @staticmethod
    def parse_flocker_data(flocker_return):
        # parse the flocker return data, from which we cook the url
        try:
            flocker_url = ('http://' + flocker_return['url']['host']
                           + ':' + str(flocker_return['url']['port'])
                           + '/' + flocker_return['url']['path'])
            return flocker_url, flocker_return['key']
        except:  # If any error return None, None
            return None, None