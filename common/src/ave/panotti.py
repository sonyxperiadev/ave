import os
import sys
import json
import urllib2
import traceback

from datetime import datetime

from ave.network.process import Process
from ave.network.control import Control, RemoteControl

import ave.config

# mostly used for testing. real lab installations log to CouchDB, not an AVE
# controll process.
class PanottiControl(Control):
    _log = None

    def __init__(self, port, sock=None, home=None):
        self._log = {}
        Control.__init__(self, port, None, sock, home=home)

    @Control.rpc
    def shout(self, db, msg):
        if db not in self._log:
            self._log[db] = []
        self._log[db].append(msg)

    @Control.rpc
    def get_log(self, db):
        if db not in self._log:
            raise Exception('no such db: %s' % db)
        return self._log[db]

def get_configuration_path(home):
    return os.path.join(home, '.ave', 'config', 'panotti.json')

def load_configuration(path):
    if not os.path.exists(path):
        raise Exception('no such configuration file: %s' % path)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception, e:
        raise Exception('failed to load panotti configuration file: %s' %str(e))

# helper function to get uniform problem reports
def complain_format(attribute, format, current):
    raise Exception(
        'panotti attribute in config "%s" must be on the form %s. '
        'current value=%s (type=%s)'
        % (attribute, format, current, str(type(current)))
    )

# validate and parse the database url from config
def get_database_url(config):
    if not isinstance(config['host'], basestring):
        complain_format('host', '{"host":<string>}', config['host'])
    if not isinstance(config['port'], int):
        complain_format('port', '{"port":<integer>}', config['port'])
    if not isinstance(config['db'], basestring):
        complain_format('db', '{"db":<string>}', config['db'])
    if not isinstance(config['enabled'], bool):
        complain_format('enabled', '{"enabled":<bool>}', config['enabled'])

    return 'http://%(host)s:%(port)d/%(db)s' % config

# send json_str to the counchdb database at the given url
def call_db(url, json_str):
    try:
        req = urllib2.Request(url, json_str)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        response = urllib2.urlopen(req)
    except Exception, e:
        raise Exception('failed to send to panotti (%s): %s' % (url, e))

# used by test cases to log to a PanottiControl process instead of a CouchDB.
# otherwise used exactly as call_db() would be called in real lab installations.
def call_ave(addr, db, json_data):
    r = RemoteControl(addr, None, 5)
    r.shout(db, json_data, __async__=True)

class Shouter(Process):

    def __init__(self, guid, json_data, home, logging):
        Process.__init__(
            self, self.run, (guid, json_data, home), logging,
            'ave-panotti-shouter'
        )

    def run(self, guid, json_data, home):
        # load and validate the panotti client configuration
        home = home if home else ave.config.load_etc()['home']
        path = get_configuration_path(home)
        try:
            config = load_configuration(path)
        except Exception, e:
            self.log(e)
            os._exit(1)
        if not ('enabled' in config and config['enabled']):
            os._exit(1)
        if 'rpc' not in config:
            config['rpc'] = 'http'
        if config['rpc'] not in ['http','ave']:
            raise Exception(
                'RPC model "%s" not supported. invalid configuration: %s' % path
            )

        # validate the message to be shouted
        if not isinstance(guid, basestring) or len(guid) < 10:
            raise Exception('"guid" must be a string of 10 or more characters, '
                            'current value: "%s" (type: %s)' %(guid,type(guid)))
        if not isinstance(json_data, dict):
            raise Exception('"json_data" must be a dictionary, current value: '
                            '"%s" (type: %s)' % (json_data, type(json_data)))

        # patch the message with guid and time stamp
        json_data['guid'] = guid
        json_data['time_stamp'] = str(datetime.now())
        try:
            json_str = json.dumps(json_data)
        except Exception, e:
            raise Exception('invalid json data: %s' % e)

        if config['rpc'] == 'http':
            url = get_database_url(config)
            call_db(url, json_str)
        elif config ['rpc'] == 'ave':
            addr = (config['host'], config['port'])
            call_ave(addr, config['db'], json_data)

def shout(guid, json_data, home=None, print_errors=False):
    if not guid:
        return
    shouter = Shouter(guid, json_data, home, logging=print_errors)
    shouter.start(daemonize=True, synchronize=False)
