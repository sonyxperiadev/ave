import os

import ave.cmd
import ave.config
import ave.gerrit.config

from ave.exceptions import RunError

def quote_message(message):
    result = message
    result = result.replace('\\', '\\\\')
    result = result.replace('"', '\\"')
    return '"' + result + '"'

def indent_message(message, indent=1):
    message = [m for m in message.splitlines()]
    message = [(' '*indent)+m for m in message]
    message = '\n'.join(message)
    return message

def set_labels(project, change, patchset, labels, message=None):
    home   = ave.config.load_etc()['home']
    config = ave.gerrit.config.load(home)
    host   = config['host']
    port   = config['port']
    user   = config['user']

    if type(project) not in [str, unicode]:
        raise Exception('project must be a string')
    if type(change) not in [str, unicode]:
        raise Exception('change must be a string')
    if type(patchset) not in [str, unicode]:
        raise Exception('patchset must be a string')
    if not labels:
        raise Exception('labels must be specified')
    if not isinstance(labels, dict):
        raise Exception('labels must be a dictionary')
    if message and (type(message) not in [str, unicode]):
        raise Exception('message must be a string')
    if message and (message[0] != message[-1] != '"'):
        raise Exception('message must start and end with a \'"\'')

    cmd = [
        'ssh', '-p', str(port), '-l', user, host, 'gerrit', 'review',
        '--project', project, '%s,%s' % (change, patchset)
    ]

    for label in labels:
        if type(label) not in [str, unicode]:
            raise Exception('label must be a string')
        score = labels[label]
        if not isinstance(score, int):
            raise Exception('score must be an integer')
        cmd.extend(['--label', '%s=%d' % (label, score)])

    if message:
        cmd.extend(['--message', message])

    # make sure ssh finds its configuration files
    os.environ['HOME'] = home
    # make sure ssh always reads its private key from $HOME/.ssh
    if 'SSH_AUTH_SOCK' in os.environ:
        del(os.environ['SSH_AUTH_SOCK'])

    s,o,_ = ave.cmd.run(cmd)
    if s != 0:
        raise RunError(cmd, o, 'Could not perform gerrit review')

def set_label(project, change, patchset, label, score, message=None):
    set_labels(project, change, patchset, {label: score}, message)

def set_verified(project, change, patchset, value, message=None):
    if value not in [-1, 0, 1]:
        raise Exception('value must be an integer in range -1 to 1')
    set_label(project, change, patchset, 'verified', value, message)

def set_code_review(project, change, patchset, value, message=None):
    if value not in [-2, -1, 0, 1, 2]:
        raise Exception('value must be an integer in range -2 to 2')
    set_label(project, change, patchset, 'code-review', value, message)

def set_qualified(project, change, patchset, value, message=None):
    if value not in [-1, 0, 1]:
        raise Exception('value must be an integer in range -1 to 1')
    set_label(project, change, patchset, 'qualified', value, message)

def set_comment(project, change, patchset, message):
    home   = ave.config.load_etc()['home']
    config = ave.gerrit.config.load(home)
    host   = config['host']
    port   = config['port']
    user   = config['user']

    if type(project) not in [str, unicode]:
        raise Exception('project must be a string')
    if type(change) not in [str, unicode]:
        raise Exception('change must be a string')
    if type(patchset) not in [str, unicode]:
        raise Exception('patchset must be a string')
    if type(message) not in [str, unicode]:
        raise Exception('message must be a string')
    if message[0] != message[-1] != '"':
        raise Exception('message must start and end with a \'"\'')

    # make sure ssh finds its configuration files
    os.environ['HOME'] = home
    # make sure ssh always reads its private key from $HOME/.ssh
    if 'SSH_AUTH_SOCK' in os.environ:
        del(os.environ['SSH_AUTH_SOCK'])

    cmd = [
        'ssh', '-p', str(port), '-l', user, host, 'gerrit', 'review',
        '--project', project, '%s,%s' % (change, patchset),
        '--message', message
    ]
    s,o,_ = ave.cmd.run(cmd)
    if s != 0:
        raise RunError(cmd, o, 'Could not perform gerrit review')
