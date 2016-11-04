import os

import ave.config

def load(home):
    path = os.path.join(home, '.ave', 'config', 'gerrit.json')
    return ave.config.load(path)

def validate(config):
    for key in ['host', 'port', 'user']:
        if key not in config:
            raise Exception('missing gerrit configuration key: %s' % key)
    if type(config['host']) not in [str, unicode]:
        raise Exception('host must be a string')
    if type(config['port']) != int:
        raise Exception('port must be an integer')
    if type(config['user']) not in [str, unicode]:
        raise Exception('user must a string')
    if config['user'].startswith('REPLACE THIS'):
        raise Exception(
            'user must be the name part of the email address that has been '
            'registered as a gerrit user. i.e. the "jane.doe" part from the '
            'jane.doe@sonymobile.com email address. PLEASE EDIT your gerrit '
            'configuration file (normally $HOME/.ave/config/gerrit.json)'
        )
    return config
