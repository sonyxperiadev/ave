import os
import json
import traceback

import ave.cmd

from ave.gerrit.events import GerritEventStream
from ave.workspace     import Workspace
from ave.network.pipe  import Pipe

EVENT = json.dumps({
    u'patchSet': {
        u'createdOn': 1361206997,
        u'number': u'8',
        u'parents': [u'7593eb025126bcd8561f4cdd2fe872022e3f5fee'],
        u'uploader': {
            u'username': u'klas.lindberg',
            u'name': u'Lindberg, Klas',
            u'email': u'klas.lindberg@sonymobile.com'
        },
        u'ref': u'refs/changes/39/435839/8',
        u'revision': u'7e67dba40602d838c3bdf58f2e345cbaa12b787a'
    },
    u'type': u'patchset-created',
    u'change': {
        u'url': u'http://review.sonyericsson.net/435839',
        u'number': u'435839',
        u'project': u'semctools/ave/gerrit',
        u'branch': u'master',
        u'owner': {
            u'username': u'klas.lindberg',
            u'name': u'Lindberg, Klas',
            u'email': u'klas.lindberg@sonymobile.com'
        },
        u'id': u'I995e2b8227959fdf8f24528350829a9d35115d5b',
        u'subject': u'Listen for stream events'
    },
    u'uploader': {
        u'username': u'klas.lindberg',
        u'name': u'Lindberg, Klas',
        u'email': u'klas.lindberg@sonymobile.com'
    }
})

class MockedGerritEventStream(GerritEventStream):

    def _begin(self):
        self.ssh_pid, self.ssh_fd = ave.cmd.run_bg(['echo', EVENT])

class setup(object):

    def __init__(self):
        pass

    def __call__(self, fn):
        def decorated_fn():
            HOME = Workspace()
            os.makedirs(os.path.join(HOME.path, '.ave', 'config'))
            content = {
                'host': 'foo',
                'port': 1,
                'user': 'bar'
            }
            path = os.path.join(HOME.path,'.ave','config','gerrit.json')
            with open(path, 'w') as f:
                f.write(json.dumps(content))

            pipe = Pipe()
            ges = MockedGerritEventStream(pipe=pipe, home=HOME.path)
            ges.start()
            result = fn(pipe)
            ges.terminate()
            ges.join()
            HOME.delete()

            return result
        return decorated_fn

# load mocked configuration file without crashing
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    HOME = Workspace()
    os.makedirs(os.path.join(HOME.path, '.ave', 'config'))

    content = {
        'host': 'foo',
        'port': 1,
        'user': 'bar'
    }

    with open(os.path.join(HOME.path,'.ave','config','gerrit.json'), 'w') as f:
        f.write(json.dumps(content))

    try:
        ges = GerritEventStream(pipe=Pipe(), home=HOME.path)
    except Exception, e:
        print('FAIL %s: could not initialize: %s' % (pretty, e))
        traceback.print_exc()
        HOME.delete()
        return False

    if ges.config != content:
        print('FAIL %s: loaded wrong configuration: %s' % (pretty, ges.config))
        HOME.delete()
        return False

    HOME.delete()
    return True

@setup()
def t2(pipe):
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        event = pipe.get(timeout=3)
    except Exception, e:
        print('FAIL %s: could not read from pipe: %s' % (pretty, e))
        return False

    if type(event) != dict:
        print('FAIL %s: event has wrong type: %s' % event)
        return False

    return True
