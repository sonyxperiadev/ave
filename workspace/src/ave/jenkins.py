# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os.path
import json
import urllib2
import errno
import base64

from datetime import datetime, timedelta
from urllib2 import URLError, HTTPError

from ave.config import load_etc, load


def handle_urllib2_error(url, e):
    if e.errno == errno.EINPROGRESS or '[Errno 115]' in str(e):
        raise Exception(
            'could not access: %s: operation timed out before completion '
            '(raise the timeout value?)' % url
        )
    elif isinstance(e, HTTPError):
        if e.getcode() == 403:
            raise Exception(
                "Host '%s' \n"
                "requires authentication, please add to jenkins.json\n"
                "format example:\n"
                "'auth' : {\n"
                "\t 'http://hostname' : {\n"
                "\t\t'method' : 'basic',\n"
                "\t\t'user' : 'username',\n"
                "\t\t'password' : 'pass'},\n"
                "\t 'http://hostname2...' : {'method' : None}\n"
                "}"
                % e.geturl()
            )
        elif e.getcode() == 401:
            raise Exception(
                "Invalid authentication to '%s', please update jenkins.json.\n"
                "Note that this will happen with invalid credentials "
                "even if the host doesn't require authentication for access."
                % e.geturl()
            )
    raise Exception('could not access %s: %s' % (url, e))


class JenkinsJob(object):
    base        = None # Jenkins base URL
    job         = None
    _attributes = None

    def __init__(self, base, job, home=None):
        self.base = base
        self.job  = job
        self.home = home

    def __str__(self):
        return json.dumps(self.attributes, indent=4)

    def load(self, timeout=30):
        url = '%s/job/%s/api/json' % (self.base, self.job)
        try:
            if timeout > 0:
                f = jenkins_auth(url, timeout=timeout, home=self.home)
            else:
                f = jenkins_auth(url, home=self.home)
            self._attributes = json.load(f)
            f.close()
        except URLError, e:
            handle_urllib2_error(url, e)

    @property
    def attributes(self):
        if not self._attributes:
            self.load()
        return self._attributes

    def last_completed(self, timeout=30):
        if not self._attributes:
            self.load(timeout)
        if not 'lastCompletedBuild' in self.attributes:
            raise Exception('job has no complete build')
        build = JenkinsBuild(
            self.base, self.job,
            self.attributes['lastCompletedBuild']['number'],
            home=self.home
        )
        return build

    def last_successful(self, timeout=30):
        if not self._attributes:
            self.load(timeout)
        if not 'lastSuccessfulBuild' in self.attributes:
            raise Exception('job has no successful build')
        build = JenkinsBuild(
            self.base, self.job,
            self.attributes['lastSuccessfulBuild']['number'],
            home=self.home
        )
        return build

    def all_builds(self, timeout=30):
        if not self._attributes:
            self.load(timeout)
        builds = []
        if not 'builds' in self.attributes:
            raise Exception('job has no builds')
        for b in self.attributes['builds']:
            builds.append(JenkinsBuild(self.base, self.job, b['number'],
                                       home=self.home))
        return builds


class JenkinsBuild(object):
    base              = None
    job               = None
    build             = None
    _attributes       = None
    _build_parameters = None

    def __init__(self, base, job, build, home=None):
        self.base  = base
        self.job   = job
        self.build = build
        self.home  = home

    def __str__(self):
        return json.dumps(self.attributes, indent=4)

    def __eq__(self, other):
        return (
            self.base  == other.base
        and self.job   == other.job
        and self.build == other.build
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def load(self, timeout=30):
        url = '%s/job/%s/%s/api/json' % (self.base, self.job, self.build)
        try:
            if timeout > 0:
                f = jenkins_auth(url, timeout=timeout, home=self.home)
            else:
                f = jenkins_auth(url, home=self.home)
            self._attributes = json.load(f)
            f.close()
        except URLError, e:
            handle_urllib2_error(url, e)

    def load_build_parameters(self, timeout=30):
        url = '%s/job/%s/%s/artifact/build_parameters.json' \
              % (self.base, self.job, self.build)
        try:
            if timeout > 0:
                f = jenkins_auth(url, timeout=timeout, home=self.home)
            else:
                f = jenkins_auth(url, home=self.home)
            self._build_parameters = json.load(f)
            f.close()
        except URLError, e:
            handle_urllib2_error(url, e)

    @property
    def attributes(self):
        if not self._attributes:
            self.load()
        return self._attributes

    @property
    def build_parameters(self):
        if not self._build_parameters:
            self.load_build_parameters()
        return self._build_parameters

    def download(self, path, artifacts=None, timeout=0):
        if timeout > 0:
            time_limit = datetime.now() + timedelta(seconds=timeout)
        else:
            time_limit = None
        if not self._attributes:
            self.load(timeout)

        if artifacts:
            artifacts = [
                a for a in self.attributes['artifacts']
                if a['relativePath'] in artifacts
            ]
        else:
            artifacts = self.attributes['artifacts']

        if not artifacts:
            url = '%s/job/%s/%s' % (self.base, self.job, self.build)
            raise Exception('job has no artifacts: %s' % url)

        for a in artifacts:
            # set up source
            src = (
                '%s/job/%s/%s/artifact/%s'
                % (self.base, self.job, self.build, a['relativePath'])
            )
            # set up destination
            dst = os.path.join(path, a['relativePath'])
            try: # create the target directory
                os.makedirs(os.path.dirname(dst))
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise Exception(
                        'could not create directory at %s: %s' % (path, str(e))
                    )
            # open the endpoints
            try:
                if time_limit:
                    time_left = time_limit - datetime.now()
                    remote = jenkins_auth(src,
                                          timeout=max(time_left.seconds,0),
                                          home=self.home)
                else:
                    remote = jenkins_auth(src, home=self.home)
            except URLError, e:
                handle_urllib2_error(src, e)
            local = open(dst, 'wb')
            while True:
                buf = remote.read(8192)
                if not buf:
                    break
                local.write(buf)
            remote.close()
            local.close()

def load_jenkins(home):
    path = os.path.join(home, '.ave', 'config', 'jenkins.json')
    try:
        config = load(path)
    except Exception as e:
        if "no such configuration file:" in e.message:
            return {}  # don't interfere with systems that don't use auth at all
        else:
            raise
    for key, value in config.iteritems():
        if type(key) not in [str, unicode]:
            raise Exception(
                'invalid config file %s: key "%s" is not a string: %s'
                % (path, key, type(key))
            )
        if key == 'auth':
            if type(value) is not dict:
                raise Exception(
                    'invalid config file %s: value of "%s" is not a dict: %s'
                    % (path, key, type(value))
                )
            for host, credentials in value.iteritems():
                if type(host) not in [str, unicode]:
                        raise Exception(
                            'invalid config file %s: Jenkins host "%s" '
                            'is not a string: %s'
                            % (path, host, type(host))
                        )
                if type(credentials) is not dict:
                    raise Exception(
                        'invalid config file %s: value of "%s" '
                        'is not a dict: %s'
                        % (path, host, type(credentials))
                    )
                if 'method' not in credentials:
                    raise Exception(
                        'invalid config file %s: Jenkins host "%s" '
                        'have no "method" defined: %s'
                        % (path, host, credentials)
                    )
            continue
    return config

def jenkins_auth(url, timeout=None, home=None):
    '''Common function for contacting the Jenkins server.

    Purpose of this function is to handle authentication when needed.
    Authentication information is stored in the key "auth" in the jenkins
    config file.

    "auth" : { <hostname> : {"method" : <string>,
                                <credentials based on method> } }

    Example methods:
    No authentication: {'method' : None}
    Basic: {'method' : 'Basic',
            'user' : <username>,
            'password' : <password or API token> }
    '''
    if not home:
        home = load_etc()['home']
    authkeys = load_jenkins(home)
    proto = ''
    if url.find('http://') == 0:
        proto = 'http://'
    elif url.find('https://') == 0:
        proto = 'https://'
    host = url.replace(proto, '')
    host = host.split('/')[0]
    method = None
    if not proto:
        proto = 'http://'

    hostkey = proto+host
    try:
        if hostkey in authkeys['auth']:
            method = authkeys['auth'][hostkey]['method'].upper()
        elif host in authkeys['auth']:  # support skipping http:// in config
            hostkey = host
            method = authkeys['auth'][hostkey]['method'].upper()
    except Exception:
        pass  # skipping both if auth doesn't exist and upper on NoneType

    # There are ways to use urllib2 to automatically handle auth based on
    # reply code, but we still need to read the authkey file every time, so
    # might as well define the method there and skip the failed
    # connection attempt.
    if not method:  # attempt to access host without authentication
        request = urllib2.Request(url, headers={'Bypass-Kerberos': 'Yes'})
        if timeout is None:
            reply = urllib2.urlopen(request)
        else:
            reply = urllib2.urlopen(request, timeout=timeout)

    elif method == 'BASIC':  # Basic access authentication for HTTP
        user = authkeys['auth'][hostkey]['user']
        password = authkeys['auth'][hostkey]['password']
        login = base64.encodestring("%s:%s" % (user, password)).strip()
        headers = {'Authorization': 'Basic %s' % login,
                   'Bypass-Kerberos': 'Yes'}
        request = urllib2.Request(url, headers=headers)
        if timeout is None:
            reply = urllib2.urlopen(request)
        else:
            reply = urllib2.urlopen(request, timeout=timeout)
    else:
        raise Exception("Unknown authorization method '%s' for Jenkins host %s"
                        % (method, hostkey))
    return reply