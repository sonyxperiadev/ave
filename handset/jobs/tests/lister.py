import time
from ave.broker import Broker
from ave.handset.lister     import HandsetLister
from ave.network.control    import Control
from ave.network.pipe       import Pipe
from ave.network.connection import find_free_port
from ave.network.exceptions import ConnectionTimeout
from ave.workspace import  Workspace
import ave.config
import os
import ave.cmd
import re

# Verify time out is working
def t1(h1,h2):
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        # can't be enumeration _and_ offline, will raise time out exception
        h1.wait_power_state('enumeration', timeout=1)
        h1.wait_power_state('offline', timeout=1)
        print('FAIL %s: expected time out exception' % (pretty))
        return False
    except Exception, e:
        if not 'wait power state timed out' in str(e):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Verify that exception is raised when unreachable state is given
def t2(h1,h2):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        h1.wait_power_state('this_state_doesnt_exist')
        print('FAIL %s: expected unreachable state exception' % (pretty))
        return False
    except Exception, e:
        if not str(e).startswith('no such state:'):
            print('FAIL %s: wrong exception: %s' % (pretty, str(e)))
            return False
    return True

# Verify wait_power_state() with time out (expect ok - no time out)
def t3(h1,h2):
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        h1.reboot()
        # verify all these states are reached during reboot (with time out)
        h1.wait_power_state('offline',             timeout=10)
        h1.wait_power_state(['enumeration','adb'], timeout=120)
        h1.wait_power_state('boot_completed',      timeout=120)
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# Verify that handset is in one of the valid states, using a list
def t4(h1,h2):
    pretty = '%s t4' % __file__
    print(pretty)

    states = [
        'boot_completed', 'adb', 'enumeration', 'offline', 'service_mode',
        'package_manager'
    ]
    try:
        state = h1.get_power_state()
        if not state in states:
            print('FAIL %s: unexpected state: %s' % (pretty, state))
            return False
    except Exception, e:
        print('FAIL %s: %s' % (pretty, str(e)))
        return False
    return True

# Verify exception on wrong type of states
def t5(h1,h2):
    pretty = '%s t5' % __file__
    print(pretty)

    try:
        h1.wait_power_state(1234, timeout=30)
        print('FAIL %s: expected invalid type of states exception' % (pretty))
        return False
    except Exception, e:
        if e.message != 'state must be a string or a list of strings':
            print('FAIL %s: wrong exception %s' % (pretty, str(e)))
            return False
    return True

class MockBroker(Control):
    pipe = None

    def __init__(self, port, socket, pipe):
        Control.__init__(self, port, None, socket)
        self.pipe = pipe

    def close_fds(self, exclude):
        exclude.append(self.pipe.w)
        Control.close_fds(self, exclude)

    @Control.rpc
    def add_equipment(self, address, profiles):
        for p in profiles:
            if self.pipe:
                self.pipe.put(p)

# check that filtering on sysfs paths works. positive test
def t6(h1,h2):
    pretty = '%s t6' % __file__
    print(pretty)

    p1 = h1.get_profile()['sysfs_path']
    p2 = h2.get_profile()['sysfs_path']

    # start a mocked broker to receive updates from the lister
    pipe = Pipe()
    sock,port = find_free_port()
    broker = MockBroker(port, sock, pipe)
    lister = HandsetLister(port, None, [p1,p2], False)
    broker.start()
    lister.start()

    def stop():
        broker.terminate()
        lister.terminate()
        broker.join()
        lister.join()

    seen = []
    try:
        seen.append(pipe.get(timeout=3))
    except ConnectionTimeout:
        print('FAIL %s: filtered profile not seen' % pretty)
        stop()
        return False

    for s in seen:
        if s['sysfs_path'] not in [p1,p2]:
            print('FAIL %s: wrong path: %s' % (pretty, s['sysfs_path']))
            stop()
            return False

    stop()
    return True

# check that filtering on sysfs paths works. negative test
def t7(h1,h2):
    pretty = '%s t7' % __file__
    print(pretty)

    # start a mocked broker to receive updates from the lister
    pipe = Pipe()
    sock,port = find_free_port()
    broker = MockBroker(port, sock, pipe)
    lister = HandsetLister(port, None, [], False) # filter out all paths
    broker.start()
    lister.start()

    def stop():
        broker.terminate()
        lister.terminate()
        broker.join()
        lister.join()

    try:
        profile = pipe.get(timeout=3)
        print('FAIL %s: unfiltered profile seen: %s' % (pretty, profile))
        stop()
        return False
    except ConnectionTimeout:
        pass # good

    stop()
    return True

# check that filtering on sysfs paths works. positive test
def t8(h1,h2):
    pretty = '%s t8' % __file__
    print(pretty)

    p1 = h1.get_profile()['sysfs_path']
    p2 = h2.get_profile()['sysfs_path']

    # start a mocked broker to receive updates from the lister
    pipe = Pipe()
    sock,port = find_free_port()
    broker = MockBroker(port, sock, pipe)
    lister = HandsetLister(port, None, None, False) # filter in all paths
    broker.start()
    lister.start()

    def stop():
        broker.terminate()
        lister.terminate()
        broker.join()
        lister.join()

    found = False
    seen  = []
    while True:
        try:
            seen.append(pipe.get(timeout=3)['sysfs_path'])
            if p1 in seen and p2 in seen:
                found = True
                break
        except ConnectionTimeout:
            break

    if not found:
        print('FAIL %s: filtered profile not seen' % pretty)
        stop()
        return False

    stop()
    return True

# check that filtering on sysfs paths works. mixed test
def t9(h1,h2):
    pretty = '%s t9' % __file__
    print(pretty)

    p1 = h1.get_profile()['sysfs_path']
    p2 = h2.get_profile()['sysfs_path']

    # start a mocked broker to receive updates from the lister
    pipe = Pipe()
    sock,port = find_free_port()
    broker = MockBroker(port, sock, pipe)
    lister = HandsetLister(port, None, [p1], False) # only filter one handset
    broker.start()
    lister.start()

    def stop():
        broker.terminate()
        lister.terminate()
        broker.join()
        lister.join()

    # reboot the handsets
    h1.reboot()
    h2.reboot()
    h1.wait_power_state('boot_completed', timeout=120)
    h2.wait_power_state('boot_completed', timeout=120)
    # give the lister a couple of seconds to report to the broker (the handset
    # makes a call by itself to the lister class, not waiting for the lister to
    # report state which may cause a situation where the handset's "wait power
    # state" is done but the broker has not yet been notified)
    time.sleep(3)

    # check that various power states were reported by the lister for the
    # filtered handset
    seen = []
    while True:
        try:
            profile = pipe.get(False)
            if profile['sysfs_path'] != p1:
                print('FAIL %s: wrong profile added: %s' % (pretty, profile))
                stop()
                return False
            seen.append(profile['power_state'])
        except ConnectionTimeout:
            break
    if 'offline' not in seen:
        print('FAIL %s: offline state not reported: %s' % (pretty, seen))
        stop()
        return False
    if 'boot_completed' not in seen:
        print('FAIL %s: boot_completed state not reported: %s' % (pretty,seen))
        stop()
        return False

    stop()
    return True

#check the handset.conf format
def t10(h1, h2):
    pretty = '%s t10' % __file__
    print(pretty)

    handsets= '{ "handsets":[{"model":"ds001", "pretty":"kat", "shutdown":3, ' \
              '"boot_to_service":"oem-53", "magic":[]}]}'
    home = ave.config.load_etc()['home']
    w = Workspace(home=home)
    path = os.path.join(w.path, 'correct.json')
    with open(path, 'w') as f:
        f.write(handsets)

    try:
        from ave.handset.lister import load_handset_config
        load_handset_config(path)
    except Exception, e:
        print("FAIL %s : could not load json file: %s" % (pretty, str(e)))
        return False

    handsets= '{ "handsets":[{"model":"ds001", "pretty":"kat", "illegal":"wrong"}]}'
    path = os.path.join(w.path, 'wrong.json')
    with open(path, 'w') as f:
        f.write(handsets)

    try:
        load_handset_config(path)
    except Exception, e:
        if "invalid config file" in str(e):
            pass
        else:
            print("FAIL %s : could not load json file: %s" % (pretty, str(e)))
            return False

    handsets = '{ "handsets":[{"pretty":"kat", "variant":"good", "shutdown":3}]}'
    path = os.path.join(w.path, 'model.json')
    with open(path, 'w') as f:
        f.write(handsets)

    try:
        load_handset_config(path)
    except Exception, e:
        if 'no "model" entry' in str(e):
            pass
        else:
            print("FAIL %s : could not load json file: %s" % (pretty, str(e)))
            return False

    handsets = '{ "handsets":[{"model":"dd00","variant":"good", "shutdown":3}]}'
    path = os.path.join(w.path, 'pretty.json')
    with open(path, 'w') as f:
        f.write(handsets)

    try:
        load_handset_config(path)
    except Exception, e:
        if 'no "pretty" entry' in str(e):
            pass
        else:
            print("FAIL %s : could not load json file: %s" % (pretty, str(e)))
            return False
    w.delete()
    return True

#check that two handset config file can be correctly merged.
def t11(h1, h2):
    pretty = '%s t11' % __file__
    print(pretty)

    handsets = '{"vendors":["1q2w"],'\
               '"handsets":[{"model":"ds001", "variant":"gina", "pretty":"kat"},' \
               ' {"model":"ds002", "variant":"windy", "pretty":"bird", "magic":["boot1","boot2"]}]}'

    home = ave.config.load_etc()['home']
    w = Workspace(home=home)
    lib = os.path.join(w.path, 'lib.json')
    with open(lib, 'w') as f:
        f.write(handsets)

    handsets = '{"vendors":["0fce"],'\
               '"handsets":[{"model":"ds003", "variant":"gina", "pretty":"fish"},' \
               ' {"model":"ds002", "variant":"windy", "shutdown":3, "pretty":"flower"}]}'

    local = os.path.join(w.path, 'local.json')
    with open(local, 'w') as f:
        f.write(handsets)

    expected = {
        'vendors':['1q2w', '0fce'],
        'handsets':[{'model': 'ds001', 'variant': 'gina', 'pretty': 'kat'},
        {'model': 'ds002', 'variant': 'windy', 'shutdown': 3, 'pretty': 'flower'},
        {'model': 'ds003', 'variant': 'gina', 'pretty': 'fish'}]
    }
    config = {}
    try:
        from ave.handset.lister import merge_handset_config
        config = merge_handset_config(lib, local)
    except Exception, e:
        print('FAIL %s : fail to merge two handset configs %s' % (pretty, str(e)))
    if config != expected:
        print("FAIL %s: The merged result is wrong !!!" % pretty)

# check that hands can get the correct relative customizer information
def t12(h1, h2):
    pretty = '%s t12' % __file__
    print(pretty)
    home = ave.config.load_etc()['home']
    key = ave.config.load_authkeys(home)
    b = Broker(authkey=key["admin"])
    handsets = b.list_handsets()
    serial = h1.get_profile()["serial"]
    for h in handsets:
        if h['serial'] == serial and h['power_state'] == 'boot_completed':
            # check software build type like "[ro.build.type]: [userdebug]"
            if h['sw_type'] is None or re.compile("\w").match(h['sw_type']):
                pass
            else:
                print("can't get normal profile['sw_type'] value.")
                return False
            # check phone operator code like "'sim.operator.numeric': '46000,46001'"
            if h['sim.operator.numeric'] is None or re.compile("\d{5},?(\d{5})?").match(h['sim.operator.numeric']):
                pass
            else:
                print("can't get normal profile['sim.operator.numeric'] value.")
                return False
            # check the country name of the service provider.
            if h['sim.country'] is None or re.compile('\w{1,9}').match(h['sim.country']):
                pass
            else:
                print("can't get normal profile['sim.country'] value.")
                return False
            break
    return True

#check that two handset config file with uppercase model can be correctly merged.
def t13(h1, h2):
    pretty = '%s t13' % __file__
    print(pretty)

    handsets = '{"handsets":[{"model":"ds001", "variant":"gina", "pretty":"kat"},' \
               ' {"model":"DS002", "variant":"windy", "pretty":"bird", "magic":["boot1","boot2"]},' \
               ' {"model":"ds003", "variant":"windy" ,"pretty":"bull"}]}'

    home = ave.config.load_etc()['home']
    w = Workspace(home=home)
    lib = os.path.join(w.path, 'lib.json')
    with open(lib, 'w') as f:
        f.write(handsets)

    handsets = '{"handsets":[{"model":"DS003", "variant":"gina", "pretty":"fish"},' \
               ' {"model":"DS004", "variant":"gina", "pretty":"bull"},' \
               ' {"model":"ds002", "variant":"windy", "shutdown":3, "pretty":"flower"}]}'

    local = os.path.join(w.path, 'local.json')
    with open(local, 'w') as f:
        f.write(handsets)

    expected = {
        'vendors':[],
        'handsets':[{'model': 'ds001', 'variant': 'gina', 'pretty': 'kat'},
        {'model': 'ds002', 'variant': 'windy', 'shutdown': 3, 'pretty': 'flower'},
        {'model': 'ds003', 'variant': 'gina', 'pretty': 'fish'},
        {'model': 'ds004', 'variant': 'gina', 'pretty': 'bull'}]
    }
    config = {}
    try:
        from ave.handset.lister import merge_handset_config
        config = merge_handset_config(lib, local)
    except Exception, e:
        print('FAIL %s : fail to merge two handset configs %s' % (pretty, str(e)))
    if config != expected:
        print("FAIL %s: The merged result is wrong !!!" % pretty)