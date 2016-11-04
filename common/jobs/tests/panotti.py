import json
import traceback
import couchdb
import os
import sys
import time
import random

import vcsjob
import ave.panotti

from ave.broker             import Broker
from ave.network.connection import find_free_port
from ave.network.control    import RemoteControl
from ave.exceptions         import *

import setup

def _rand_string():
    result = []
    for i in range(10):
        result.append(random.randint(0,9))
    return ''.join(['%d' % i for i in result])

def get_database_config(db_name=None):
    if not db_name:
        db_name = 'panotti_test_%s' % _rand_string()
    return {
        'host'    : 'localhost',
        'port'    : 5984,
        'db'      : db_name,
        'enabled' : True
    }

def make_config(w, db_config):
    config_path = os.path.join(w.get_path(), '.ave', 'config')
    try:
        os.makedirs(config_path)
    except Exception as e:
        pass
    with open(os.path.join(config_path,'panotti.json'), 'w') as f:
        f.write(json.dumps(db_config))

def mock_database(w, db_config):
    make_config(w, db_config)
    return get_database(db_config)

def get_database(db_config):
    url = 'http://%s:%s' %(db_config['host'], str(db_config['port']))
    db_name = db_config['db']
    try:
        server = couchdb.Server(url)
        try:
            return server[db_name]
        except Exception:
            return server.create(db_name)
    except Exception as e:
        raise Exception('failed to get %s database at %s: %s'
                        % (db_name, url, str(e)))

def delete_database(db_config):
    db_name = db_config['db']
    url     = 'http://%s:%d' %(db_config['host'], db_config['port'])
    server  = couchdb.Server(url)
    try:
        server.delete(db_name)
    except Exception as e:
        raise Exception('failed to delete database %s at %s: %s'
                        % (db_name, url, str(e)))

def get_guid_and_json():
    json_data = {'title':'title-mock', 'url':'http://link'}
    guid = 'http://localhost:5984/job_queue/refs/changes/93/600593/1@git://re' \
           'view.sonyericsson.net/platform/vendor/semc/verification/dust@jobs' \
           '/example/smoke-dustpy@SMOKE'
    return guid, json_data

def failed(message, db_name):
    print('FAIL: %s' % message)
    try:
        delete_database(get_database_config(db_name))
    except Exception:
        pass
    return False

def query(db):
    map_fun = '''
        function(doc) {
            if (doc.title)
              emit(doc.title, doc);
        }'''
    return db.query(map_fun)

def verify_single_entry(db, json_data):
    results = query(db)
    if len(results) != 1:
        return failed(
            'Wrong number of rows in result: %d, expected: 1' % len(results),
            db.name
        )
    # TODO: remove loop... verify single... [0]
    for r in results:
        if not r.key == json_data['title']:
            return failed(
                'Expected (%s) to match %s' %(r.key, json_data['title']),
                db.name
            )
        if not r.value['url'] == json_data['url']:
            return failed(
                'Expected (%s) to match %s' % (r.value['url'],json_data['url']),
                db.name
            )
        if len(results) != 1:
            return failed(
                'Wrong number of rows in result: %d, expected: 1' %len(results),
                db.name
            )
    return True

#positive test, shout once and verify the entry
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    broker = Broker()
    w = broker.get({'type':'workspace'})
    config = get_database_config()
    db = mock_database(w, config)
    guid, json_data = get_guid_and_json()

    ave.panotti.shout(guid, json_data, w.get_path())
    time.sleep(1) # give it a moment
    if not verify_single_entry(db, json_data):
        return False
    delete_database(config)
    return True

# Stress, run 1000 requests in series
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    broker = Broker()
    w = broker.get({'type':'workspace'})
    config = get_database_config()
    db = mock_database(w, config)
    guid, json_data = get_guid_and_json()

    expected = 100
    try:
        for i in range(0, expected):
            ave.panotti.shout(guid, json_data, w.get_path())
    except Exception as e:
        return failed('Exception in shout %s' % e, db.name)

    res = None
    for r in range(3):
        time.sleep(1) # give it a moment
        res = len(query(db))
        if res == expected:
            break

    if res != expected:
        return failed(
            'Wrong nr of records: %d, expected: %d' % (res, expected), db.name
        )

    delete_database(config)
    return True

# Robustness, panotti is down
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    db_name = 'panotti_test'
    port = 2929292
    host = 'nosuchhostcanbefound'
    invalid_config = {'db':db_name, 'host':host, 'port':port,'enabled':True}

    broker = Broker()
    w = broker.get({'type':'workspace'})
    guid, json_data = get_guid_and_json()
    # configure for db, but do not create
    make_config(w, invalid_config)

    try:
        ave.panotti.shout(guid, json_data, w.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (urlopen error), exception: %s' % e)
        return False
    return True

# Robustness, panotti is disabled - enabled - disabled
# use four different home directories with different shouter configurations
# so that the asynchronous execution of the shouters do not accidentally read
# wrong configurations (i.e. if all four shouts were made from the same config
# file, but with changes made to it between shouts).
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    config = get_database_config()
    broker = Broker()
    w1 = broker.get({'type':'workspace'})
    w2 = broker.get({'type':'workspace'})
    w3 = broker.get({'type':'workspace'})
    w4 = broker.get({'type':'workspace'})
    guid, json_data = get_guid_and_json()

    # must exit silently ...

    # no config
    try:
        ave.panotti.shout(guid, json_data, w1.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (no config file), exception: %s' % e)
        return False

    # empty config
    make_config(w2, {})
    try:
        ave.panotti.shout(guid, json_data, w2.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (empty config), exception: %s' % e)
        return False

    # enabled
    make_config(w3, config)
    db = mock_database(w3, config)
    try:
        ave.panotti.shout(guid, json_data, w3.get_path())
    except Exception as e:
        return failed('Unexpected exception: %s' % e, db.name)
    time.sleep(1)
    verify_single_entry(db, json_data)

    # disabled
    config['enabled'] = False
    make_config(w4, config)
    try:
        ave.panotti.shout(guid, json_data, w4.get_path())
    except Exception as e:
        return failed('Expected silent exit (disabled),exception: %s'%e,db.name)

    time.sleep(1)
    # no entry was added
    verify_single_entry(db, json_data)

    delete_database(config)
    return True

# test short guid, invalid type of guid and invalid type of data
# panotti daemonized process should never raise
def t5():
    pretty = '%s t5' % __file__
    print(pretty)

    broker = Broker()
    w = broker.get({'type':'workspace'})
    config = get_database_config()
    make_config(w, config)

    guid, json_data = get_guid_and_json()
    # must be a dictionary
    invalid_data = [{'title':'decibel-mock', 'url':'http://link'}]
    # must be a string of length >= 10
    short_guid = 'short'
    invalid_guid = ['wrong','type','of','guid']

    # must exit silently ...

    # short guid
    try:
        ave.panotti.shout(short_guid, json_data, w.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (short guid), exception: %s' % e)
        return False
    # invalid type of guid
    try:
        ave.panotti.shout(invalid_guid, json_data, w.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (invalid guid), exception: %s' % e)
        return False
    # invalid type of data
    try:
        ave.panotti.shout(guid, invalid_data, w.get_path())
    except Exception as e:
        print('FAIL: Expected silent exit (invalid json), exception: %s' % e)
        return False

    return True

# check that RemoteControl.__getattr__() logs exceptions to panotti if a job
# GUID is set (using vcsjob.get_guid()).
@setup.factory()
def t6(pretty, factory):
    # make a panotti server based on AVE RPC
    s = factory.make_panotti_server(factory.HOME.path)

    # write the client side panotti config
    port = s.address[1]
    cfg = { 'host':'', 'port':port, 'db':'foo', 'enabled':True, 'rpc':'ave' }
    factory.write_config('panotti.json', cfg)

    # make some Control based server for the client to call. then ask it to
    # raise an exception over RPC. no GUID has been set on the client side, so
    # no exception log should be posted to panotti by the client.
    c = factory.make_control(factory.HOME.path)
    try:
        c.raise_ave_exception({'message':'foo', 'extras':'bar'})
    except AveException, e:
        pass # expected
    except Exception, e:
        print('FAIL %s: could not raise RPC exception: %s' % (pretty, e))
        return False

    # set the client side GUID and make another failed call. this exception
    # should be logged to panotti.
    vcsjob.set_guid('example_guid')
    c = RemoteControl(c.address, None, 1, home=factory.HOME.path)

    exc = None
    try:
        c.raise_ave_exception({'message':'cow', 'extras':'cat'})
    except AveException, e:
        exc = e # expected
    except Exception, e:
        print('FAIL %s: could not raise RPC exception: %s' % (pretty, e))
        return False

    time.sleep(1) # give asynchronous events some time to settle

    # expect to find the same exception in the panotti server log, with the
    # guid and time stamp patched in
    log = s.get_log('foo')

    if len(log) != 1:
        print('FAIL %s: wrong number of log entries: %s' % (pretty, log))
        return False

    if 'guid' not in log[0]:
        print('FAIL %s: log entry without GUID: %s' % (pretty, log[0]))
        return False

    if log[0]['guid'] != 'example_guid':
        print('FAIL %s: wrong GUID: %s' % (pretty, log[0]))
        return False

    if 'time_stamp' not in log[0]:
        print('FAIL %s: log entry without time stamp: %s' % (pretty, log[0]))
        return False

    for detail in exc.details:
        if detail not in log[0]['exception']:
            print('FAIL %s: detail "%s" not in log: %s' % (pretty, detail, log))
            return False
        if log[0]['exception'][detail] != exc.details[detail]:
            print('FAIL %s: wrong detail in log: %s' % (pretty, log))
            return False

    return True
