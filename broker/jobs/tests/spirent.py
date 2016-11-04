import os
import json

from ave.broker.profile      import *
from ave.workspace           import Workspace
from ave.broker._broker      import Broker, RemoteBroker
from ave.network.connection  import find_free_port

import setup

cfg = {
    'testdrive': {
        'uid'    : 'spirent1',
        'host'   : 'testdrive-host',
        'winhome':  'C:\Program Files\Spirent Communications\TestDrive ULTS'
    }
}

# check that no testdrive shows up in the equipment list if there is a no valid
# configuration file for it
@setup.factory()
def t1(factory):
    pretty = '%s t1' % __file__
    print(pretty)

    b = factory.make_master('master')

    result = b.list_equipment({'type':'testdrive'})
    if result != []:
        print('FAIL %s: wrong equipment list: %s' % (pretty, result))
        return False

    return True

# check that testdrive shows up in the equipment list if there is a valid
# configuration file for it
@setup.factory()
def t2(factory):
    pretty = '%s t2' % __file__
    print(pretty)

    # add testdrive equipment to a broker by writing a config file for it
    factory.write_config('spirent.json', json.dumps(cfg, indent=4))
    b = factory.make_master('master')

    result = b.list_equipment({'type':'testdrive'})
    if not result:
        print('FAIL %s: wrong equipment list: %s' % (pretty, result))
        return False

    return True

# check that testdrive shows up in stacks that include it
@setup.factory()
def t3(factory):
    pretty = '%s t3' % __file__
    print(pretty)

    # add testdrive and stack configurations to a broker
    factory.write_config('spirent.json', json.dumps(cfg, indent=4))
    b = factory.make_master('master')
    h = b.list_equipment({'type':'handset'})[0]
    t = b.list_equipment({'type':'testdrive'})[0]
    s = RemoteBroker(b.address, 3, 'share_key')
    s.set_stacks('local', [[h,t]])

    # check that the stack exists
    stacks = b.list_stacks()
    if [h,t] not in stacks:
        print('FAIL %s: wrong stacks: %s' % (pretty, stacks))
        return False

    return True

# check that handsets and testdrives can be allocated together
@setup.factory()
def t4(factory):
    pretty = '%s t4' % __file__
    print(pretty)

    # add testdrive and stack configurations to a broker
    factory.write_config('spirent.json', json.dumps(cfg, indent=4))
    b = factory.make_master('master')
    handsets   = b.list_equipment({'type':'handset'})
    testdrives = b.list_equipment({'type':'testdrive'})
    s = RemoteBroker(b.address, 3, 'share_key')
    s.set_stacks('local', [[handsets[0],testdrives[0]]])

    # allocate a stack
    try:
        h,t = b.get_resource({'type':'handset'},{'type':'testdrive'})
    except Exception, e:
        print('FAIL %s: could not allocate: %s' % (pretty, str(e)))
        return False

    if HandsetProfile(h.get_profile()) not in handsets:
        print('FAIL %s: unknown handset: %s' % (pretty, h.get_profile()))
        return False

    if TestDriveProfile(t.get_profile()) not in testdrives:
        print('FAIL %s: unknown testdrive: %s' % (pretty, t.get_profile()))
        return False

    return True
