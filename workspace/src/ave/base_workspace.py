# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import hashlib
import os
import random
import errno
import shutil

import json
import copy
import re
import tempfile
import glob
import urllib2
import sys
import zipfile


import ave.apk
import ave.cmd
import ave.git
import ave.ftpclient      as ftpclient
import ave.config

from ave.jenkins            import JenkinsJob, JenkinsBuild
from ave.profile            import Profile



class BaseWorkspaceProfile(Profile):

    def __init__(self, values):
        Profile.__init__(self, values)
        self['type'] = 'workspace'

    def __hash__(self):
        return hash(self['uid'])

    def __eq__(self, other):
        if not ('uid' in self and 'uid' in other):
            return False
        return self['uid'] == other['uid']

    def __ne__(self, other):
        return not self.__eq__(other)

    def match(self, other):
        if other['type'] != 'workspace':
            return False
        if 'uid' in other and self['uid'] != other['uid']:
            return False
        if 'tools' in other:
            if 'tools' not in self:
                return False
            for tool in other['tools']:
                if not tool in self['tools']:
                    return False
        if 'pretty' in other:
            if 'pretty' not in self:
                return False
            if self['pretty'] != other['pretty']:
                return False
        if 'wifi-capable' in other:
            if 'wifi-capable' not in self:
                return False
            if self['wifi-capable'] != other['wifi-capable']:
                return False
        return True

    def minimize(self, profile=None):
        r = {
            'type' : 'workspace',
            'root' : self['root'],
            'tools': {}
        }
        if 'uid' in self:
            r['uid'] = self['uid']
        if profile:
            for p in profile:
                if p == 'tools':
                    for tool in profile['tools']:
                        r['tools'][tool] = self['tools'][tool]
                else:
                    r[p] = self[p]
                if p == 'pretty' and 'pretty' in self:
                    r[p] = self[p]
        return BaseWorkspaceProfile(r)


def validate_flocker_configuration(config):
    '''
    Check if the 'config' is a valid ftp configuration.
    '''
    # helper function to get uniform problem reports
    def complain_format(attribute, format, current):
        raise Exception(
            'ftp attribute "%s" must be on the form %s. '
            'current value=%s (type=%s)'
            % (attribute, format, current, str(type(current)))
        )

    if 'enable' not in config:
        raise Exception('the "enable" attribute is not configured')
    if 'host' not in config:
        raise Exception('the "host" attribute is not configured')
    if 'ftp' not in config:
        raise Exception('the "ftp" attribute is not configured')
    if 'http' not in config:
        raise Exception('the "http" attribute is not configured')
    if 'port' not in config['ftp']:
        raise Exception('the ftp "port" attribute is not configured')
    if 'user' not in config['ftp']:
        raise Exception('the ftp "user" attribute is not configured')
    if 'password' not in config['ftp']:
        raise Exception('the ftp "password" attribute is not configured')
    if 'timeout' not in config['ftp']:
        config['timeout'] = 10
    if 'store' not in config['ftp']:
        raise Exception('the ftp "store" attribute is not configured')

    if 'port' not in config['http']:
        raise Exception('the http "port" attribute is not configured')
    if 'doc-root' not in config['http']:
        raise Exception('the http "doc-root" attribute is not configured')


    if not type(config['enable']) == bool:
        complain_format('enable', '{"enable":<bool>}', config['enable'])
    if config['enable'] == True:
        if not type(config['host']) in [str, unicode]:
            complain_format('host', '{"server":<string>}', config['server'])
        if not type(config['ftp']['port']) == int:
            complain_format('port', '{"port":<integer>}', config['ftp']['port'])
        if not type(config['http']['port']) == int:
            complain_format('port', '{"port":<integer>}', config['http']['port'])

def validate_configuration(config, home):
    # helper function to get uniform problem reports
    def complain_format(attribute, format, current):
        raise Exception(
            'workspace attribute "%s" must be on the form %s. '
            'current value=%s (type=%s)'
            % (attribute, format, current, str(type(current)))
        )

    # check that mandatory configuration attributes are present
    if 'root' not in config:
        raise Exception('workspace root directory is not configured')
    if 'tools' not in config:
        raise Exception('workspace tools are not configured')

    # check that governed attributes have correct types
    if type(config['root']) not in [str, unicode]:
        complain_format('root', '{"root":<string>}', config['root'])
    if 'jenkins' in config:
        if type(config['jenkins']) not in [str, unicode]:
            complain_format('jenkins','{"jenkins":<string>}',config['jenkins'])
    if 'wlan' in config:
        if (type(config['wlan']) != dict
        or  'ssid' not in config['wlan']
        or  'auth' not in config['wlan']
        or  type(config['wlan']['ssid']) not in [str, unicode]
        or  type(config['wlan']['auth']) not in [str, unicode]):
            complain_format(
                'wlan', '{"wlan":{"ssid":<string>, "auth":<string>}}',
                config['wlan']
            )
    if 'wifi-capable' in config:
        if type(config['wifi-capable']) != bool:
            complain_format(
                'wifi-capable', '{"wifi-capable": <bool>}',
                config['wifi-capable']
            )
    if 'pretty' in config:
        if type(config['pretty']) not in [str, unicode]:
            complain_format('pretty', '{"pretty":<string>}', config['pretty'])

    if 'flocker' in config:
        validate_flocker_configuration(config['flocker'])


    # interpret shorthands in attributes that hold file system paths
    if not home:
        raise Exception('home must be set')
    while '~' in config['root']:
        i = config['root'].index('~')
        config['root'] = config['root'][:i] + home + config['root'][i+1:]
    while '$HOME' in config['root']:
        i = config['root'].index('$HOME')
        config['root'] = config['root'][:i] + home + config['root'][i+5:]

    return config

class BaseWorkspace(object):
    uid             = None
    config          = None
    home            = None
    ftpclient         = None

    def __init__(self, uid=None, cfg_path=None, config=None, home=None):
        if not home:
            home = ave.config.load_etc()['home']
        self.home = home

        # load and validate the configuration file
        if config:
            self.config = validate_configuration(config, self.home)
        else:
            if not cfg_path:
                cfg_path = BaseWorkspace.default_cfg_path(self.home)
            self.config = BaseWorkspace.load_config(cfg_path, self.home)

        if not uid:
            uid = self._rand_string()
            if 'pretty' in self.config:
                uid = '%s-%s' % (self.config['pretty'], uid)
        self.uid = uid

        # create the base directory for the workspace it is based on the root
        # directory (used for all workspaces under the active configuration)
        # and the unique identifier of the workspace itself.
        try:
            os.makedirs(self.path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Exception(
                    'could not create directory at %s: %s' % (self.path, str(e))
                )

    @staticmethod
    def _rand_string():
	    result = []
	    for i in range(10):
	        result.append(random.randint(0,9))
	    return ''.join(['%d' % i for i in result])


    def _valid_path(self, path):
        if path.startswith('/') and not path.startswith(self.path):
            raise Exception(
                'path cannot be outside workspace: %s' % path
            )
        return os.path.join(self.root, self.uid, path)

    def delete(self):
        try:
            shutil.rmtree(os.path.join(self.root, self.uid))
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass # already removed by someone else



    @property
    def root(self):
        # The workspace's parent directory in which all workspaces are
        # created (unless they have different active configurations, see
        # the discussion of <home>).
        return self.config['root']

    @property
    def path(self):
        # The base directory of this workspace
        return os.path.join(self.root, self.uid)

    @classmethod
    def default_cfg_path(cls, home=None):
        # site and node specific configuration details must be stored somewhere
        # and <home>/.ave/config seems like a reasonable default, where the
        # value of <home> is set by /etc/ave/home
        if not home:
            home = ave.config.load_etc()['home']

        return os.path.join(home,'.ave','config','workspace.json')

    @classmethod
    def load_config(cls, path, home):
        if not os.path.exists(path):
            raise Exception('no such configuration file: %s' % path)
        try:
            with open(path) as f:
                config = json.load(f)
        except Exception, e:
            raise Exception(
                'could not load workspace configuration file: %s' % str(e)
            )
        return validate_configuration(config, home)

    def has_tool(self, tool):
        return tool in self.config['tools']

    @classmethod
    def list_available(cls, cfg_path=None, config=None, home=None):
        result = []
        if not config:
            if not cfg_path:
                cfg_path = BaseWorkspace.default_cfg_path(home)
            config = BaseWorkspace.load_config(cfg_path, home)
        if not os.path.isdir(config['root']):
            return result
        for uid in os.listdir(config['root']):
            profile = BaseWorkspaceProfile(config)
            profile['uid'] = uid
            result.append(profile)
        return result

    def get_path(self):
        return self.path

    def get_profile(self):
        r = copy.deepcopy(self.config)
        r['uid'] = self.uid
        return BaseWorkspaceProfile(r)

    def get_wifi_ssid(self):
        try:
            ssid = self.get_profile()['wlan']['ssid']
            return ssid
        except Exception, e:
            raise Exception(
                'Fail to get wlan-ssid: %s' % str(e)
            )

    def get_wifi_pw(self):
        try:
            pw = self.get_profile()['wlan']['auth']
            return pw
        except Exception, e:
            raise Exception(
                'Fail to get wlan-auth: %s' % str(e)
            )

    def has_git(self, path, refspec):
        dir_path = os.path.join(self.root, self.uid, path)
        try:
            ave.git.rev_list(path, 1, refspec)
            return True
        except ave.cmd.RunError as e:
            return False

    def delete_git(self, path):
        dir_path = os.path.join(self.root, self.uid, path)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

    def make_git(self, path):
        if path.startswith('/'):
            path = os.path.normpath(path)
            if not path.startswith(self.path):
                raise Exception('can not create git outside workspace')
        path = os.path.join(self.root, self.uid, path)
        try: # create the target directory
            os.makedirs(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Exception(
                    'could not create directory at %s: %s' % (path, str(e))
                )
        ave.git.init(path)
        msg = 'Created by avi.workpace.make_git()'
        ave.git.commit(path, msg, allow_empty=True)
        return path

    def download_git(self, src, refspec, dst=None, timeout=0, depth=1):

        # check that destination is within self.path, or use a default
        if dst:
            if dst.startswith('/'):
                dst = os.path.normpath(dst)
                if not dst.startswith(self.path):
                    raise Exception('can not store git tree outside workspace')
            dst = os.path.join(self.path, dst)
        else:
            dst = os.path.join(self.path, 'git', os.path.basename(src))

        # check that destination is within self.root.uid
        dst = os.path.normpath(dst)
        if not dst.startswith(self.path):
            raise Exception('can not download to path outside workspace')
        ave.git.sync(src, dst, refspec, timeout, depth=depth)
        return dst

    def make_tempdir(self):
        path = os.path.join(self.root, self.uid, self._rand_string())
        os.makedirs(path) # will raise OSError if directory exists
        return path

    def make_tempfile(self, path=None):
        if not path:
            handle,ret_path = tempfile.mkstemp(dir=self.path)
        else:
            handle,ret_path = tempfile.mkstemp(dir=path)
        return ret_path


    def download(self, url, dst=None, timeout=0, output_file=None, proxy=False, proxy_user=None, proxy_password=None):
        if not url:
            raise Exception('url is None')

        if dst:
            path = self._valid_path(dst)
        else:
            path = os.getcwd()

        try: # create the target directory
            os.makedirs(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Exception(
                    'could not create directory at %s: %s' % (path, str(e))
                )

        try:
            proxy_flag = False
            #add environment variable and urlopen proxy
            if proxy is True:
                proxy_url = None
                if 'proxy' in self.config:
                    if 'url' in self.config['proxy'] and self.config['proxy']['url'] != '':
                        proxy_url = self.config['proxy']['url']
                    else:
                        raise Exception('proxy url is not set or provided')
                else:
                    raise Exception('proxy is not set or provided')

                if os.environ.has_key('http_proxy') and os.environ.has_key('https_proxy'):
                    proxy_flag = True
                else:
                    os.environ['http_proxy'] = proxy_url
                    os.environ['https_proxy'] = proxy_url

                if proxy_user and proxy_password:
                    proxyConfig = 'http://%s:%s@%s' % (proxy_user, proxy_password, proxy_url)
                else:
                    if 'proxy_user' in self.config['proxy'] and 'proxy_password' in self.config['proxy']:
                        if self.config['proxy']['proxy_user'] and self.config['proxy']['proxy_password']:
                            proxy_user = self.config['proxy']['proxy_user']
                            proxy_password = self.config['proxy']['proxy_password']
                            proxyConfig = 'http://%s:%s@%s' % (proxy_user, proxy_password, proxy_url)
                        else:
                            proxyConfig = 'http://%s' % proxy_url

                opener = urllib2.build_opener(urllib2.ProxyHandler({'http': proxyConfig, 'https': proxyConfig}))
                urllib2.install_opener(opener)

            request = urllib2.Request(url)
            if timeout == 0:
                remote = urllib2.urlopen(request)
            else:
                remote = urllib2.urlopen(request, timeout=timeout)
            info = remote.info()
            #get download file name
            if info.has_key('Content-Disposition'):
                tmpname = info['Content-Disposition'].partition('filename=')
                filename = tmpname[2][1:-1]
            else:
                filename = os.path.basename(url)

            download_path_name = os.path.join(path, filename)

            cmd = ['wget', '-O', download_path_name, '--content-disposition', url]
            if proxy_user:
                cmd.extend(['--proxy-user', proxy_user])
            if proxy_password:
                cmd.extend(['--proxy-password', proxy_password])

            if not output_file:
                ave.cmd.run(cmd, timeout=timeout, output_file=sys.stdout)
            else:
                try:
                    file = open(os.path.join(path, output_file), 'a+')
                    ave.cmd.run(cmd, timeout=timeout, output_file=file)
                except Exception, e:
                    raise e
                finally:
                    file.close()

        except urllib2.URLError, e:
            raise e
        except Exception, e:
            raise e
        finally:
            if proxy is True and proxy_flag is False:
                if 'http_proxy' in os.environ:
                    del os.environ['http_proxy']
                if 'https_proxy' in os.environ:
                    del os.environ['https_proxy']

        return download_path_name

    # validates if zip file is corrupt  or not
    def validate_zip_file(self, filename, crc_check=False):

        if not zipfile.is_zipfile(filename):
            return False
        if crc_check is True:
            zip_file = zipfile.ZipFile(filename)
            ret = zip_file.testzip()
            if ret is not None:
                return False
        return True

    def zip(self, path, dst=None):
        if type(path) in [str, unicode]:
            path = self._valid_path(path)
            if dst is None:
                fname_prefix = os.path.basename(path)
                dst = os.path.join(self.path, '%s.zip' % fname_prefix)
                i = 1
                while os.path.exists(dst):
                    dst = os.path.join(self.path, '%s_%d.zip' % (fname_prefix, i))
                    i += 1
            else:
                dst = self._valid_path(dst)
                if os.path.exists(dst):
                    raise Exception('A file named %s already exists. Suggest to change a new one.' % dst)
            zf = zipfile.ZipFile(dst, 'w', zipfile.zlib.DEFLATED)
            self._zip(path, zf, dst)
            zf.close()
        elif isinstance(path, list):
            if dst is None:
                fname_prefix = os.path.basename(self.path)
                dst = os.path.join(self.path, '%s.zip' % fname_prefix)
                i = 1
                while os.path.exists(dst):
                    dst = os.path.join(self.path, '%s_%d.zip' % (fname_prefix, i))
                    i += 1
            else:
                dst = self._valid_path(dst)
                if os.path.exists(dst):
                    raise Exception('A file named %s already exists. Suggest to change a new one.' % dst)
            zf = zipfile.ZipFile(dst, 'w', zipfile.zlib.DEFLATED)
            for p in path:
                p = self._valid_path(p)
                self._zip(p, zf, dst)
            zf.close()
        else:
            raise Exception("Not supported path: s%, it must be a string or a list of strings" % str(path))
        return dst

    def _zip(self, path, zfile, dst):
        file_list = []
        if os.path.isfile(path):
            file_list.append(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for name in files:
                    file_list.append(os.path.join(root, name))
        else:
            raise Exception('not an existing file or directory:%s' % path)

        for tar in file_list:
            if os.path.samefile(tar, dst):
                continue
            arcname = tar[len(os.path.dirname(path)):]
            zfile.write(tar, arcname)

    def unzip(self, zip_file, path=None, pwd=None):
        zip_file = self._valid_path(zip_file)
        if not self.validate_zip_file(zip_file):
            raise Exception('%s is not a zip file' % zip_file)
        if path:
            path = self._valid_path(path)
            if not os.path.exists(path):
                os.makedirs(path)
            else:
                raise Exception('path:%s already exists. Suggest to change a new one.' % path)
        else:
            path = os.path.splitext(zip_file)[0]
            i = 1
            while os.path.exists(path):
                path = '%s_%d' % (os.path.splitext(zip_file)[0], i)
                i += 1
            os.makedirs(path)
        zf_obj = zipfile.ZipFile(zip_file)

        for file in zf_obj.namelist():
            zf_obj.extract(file, path, pwd=pwd)
        zf_obj.close()
        return path


    def download_jenkins(self, job_id, build_id=None, artifacts=None, dst=None,
                         timeout=0, base=None):
        if not base:
            if 'jenkins' in self.config:
                base = self.config['jenkins']
            else:
                raise Exception('jenkins base URL is not set or provided')

        if build_id:
            build = JenkinsBuild(base, job_id, build_id, home=self.home)
            path  = os.path.join(self.path, 'jenkins', job_id, build_id)
        else:
            job   = JenkinsJob(base, job_id, home=self.home)
            build = job.last_successful(timeout)
            path  = os.path.join(self.path, 'jenkins', job_id, str(build.build))

        if dst:
            # check that destination is within self.root.uid
            if dst.startswith('/'):
                dst = os.path.normpath(dst)
                if not dst.startswith(self.path):
                    raise Exception('destination can not be outside workspace')
            path = os.path.join(self.path, dst) # override default path

        build.download(path, artifacts, timeout)

        if (not build_id) and (not dst):
            # only create the last_completed indicator when downloading to a
            # to default directory. where would we put it when the user has
            # made an explicit choice about the directory structure? would it
            # even be helpful to have the indicator?
            last = os.path.join(self.path, 'jenkins', job_id, 'last_successful')
            # symlink would be nicer, but this works on windows too:
            f = open(last, 'w')
            f.write(str(build.build))
            f.close()
        return path


    def get_package_name(self, path):
        aapt = ave.apk.get_aapt_path()
        # Make sure the path exists
        if not os.path.exists(path):
            raise Exception(
                'The given path does not exist: %s' % path
            )
        try:
            # Only use output from ave.cmd.run (-> [1])
            badging = ave.cmd.run([aapt, 'd', 'badging', path])
            if not badging:
                raise Exception(
                    'Nothing returned from "aapt d bagding" of apk: %s'
                    % (path)
                )
            pattern = 'name=\'[A-Za-z0-9_.]*\''
            fa_list = re.findall(pattern, badging[1])
            pattern = '[A-Za-z0-9_.]*'

            apk_name_list = re.findall(pattern, fa_list[0])
            ret = apk_name_list[3]
        except Exception, e:
            raise Exception(
                'Could not get package name from apk %s: %s'
                % (path, str(e))
            )
        return ret


    def run(self, cmd, timeout=0):
        # make sure 'cmd' is a list of strings
        if type(cmd) in [str, unicode]:
            cmd = [c for c in cmd.split() if c != '']
        if not self.has_tool(cmd[0]):
            raise Exception(
                'no such tool available in this workspace: %s' % cmd[0]
            )
        # replace the tool with its full path
        cmd[0] = self.config['tools'][cmd[0]]
        return ave.cmd.run(cmd, timeout)

    def _flocker_validate_availability(self):
        if self.config['flocker']['enable'] is False:
            raise Exception(
			    "the flocker is disable,pls set workspace.js's attribute"
            )


    def promote(self, source_path, target, server='flocker'):
        '''
        Promotes a file by making it traceable, this needs to be done
        to tmp-files that are generated by workspace.makefile() as they
        are not pushable to the handset. Traceability is secured by
        pushing the file to flocker and returning the metadata as well as
        making a symlink to the promoted file named as the target

        input : full path to the source file
        input : path inside the ws to the target file
        input : server, optional, defaults to flocker
        return: the result of the file storage operation
        '''
        self._flocker_validate_availability()
        # the following tests are done in flocker_push_ta as well...
        if not source_path.startswith('/'):
            source_path = os.path.join(self.path, source_path)
        if not os.path.exists(source_path):
            raise Exception('source file does not exist: %s' % source_path)
        if not os.path.isfile(source_path):
            raise Exception('source file is not a file: %s' % source_path)
        if not source_path.startswith(self.path):
            raise Exception('source file not stored inside workspace: %s'
                    % source_path)

        if target.startswith('/'):
            raise Exception('target must be within workspace: %s'
                    % source_path)
        if os.path.basename(target).startswith('tmp'):
            raise Exception('tmpfile can not be target: %s'
                    % source_path)

        if len(self.ls(self.path, target)) != 0:
            raise Exception('target file exists (%s)' %target)

        target_path = os.path.join(self.get_path(), target)

        # build possible folder struct
        if not os.path.basename(target) is target:
            os.makedirs(os.path.dirname(target_path))

        # make a symlink to the promoted file that can be used for pushing
        os.symlink(source_path, target_path)

        if not os.path.isfile(target_path):
            raise Exception ('failed to make a promoted copy of (%s)'
                                %source_path)
        # if flocker is down, let the show go on.
        # TODO: Add testcase for this
        metadata = None
        try:
            metadata = self.flocker_push_file(source_path, target)
        except Exception as e:
            pass
        return metadata

    def flocker_initial(self, existing_key=None, custom_key=None):
        self._flocker_validate_availability()
        if existing_key and custom_key:
            raise Exception('existing_key and custom_key cannot be set at the same time.')
        if existing_key:
            if not self.ftpclient:
                self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'],
                                                     key=existing_key)
            else:
                self.ftpclient.switch_dirname(existing_key=existing_key)
        if custom_key:
            if not self.ftpclient:
                self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'])
                self.ftpclient.switch_dirname(custom_key=custom_key)
            else:
                self.ftpclient.switch_dirname(custom_key=custom_key)

    def flocker_push_file(self, src, dst=None, key=None):
        self._flocker_validate_availability()
        # check that src is a file within the workspace
        if not src.startswith('/'):
            src = os.path.join(self.path, src)
        if not os.path.exists(src):
            raise Exception('pushed file does not exist: %s' % src)
        if not os.path.isfile(src):
            raise Exception('pushed file is not a file: %s' % src)
        if not src.startswith(self.path):
            raise Exception('pushed file not stored inside workspace: %s' % src)

        if not dst:
            dst = os.path.basename(src)
        if dst.startswith('/'):
            raise Exception('pushed file destination is absolute path: %s'% dst)

        if not self.ftpclient:
            self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'], key=key)

        self.ftpclient.push_file(src, dst)

        metadata = self.ftpclient.get_metadata()
        metadata['key'] = self.ftpclient.dirname
        return metadata

    def flocker_push_string(self, string, dst, key=None, timeout=30):
        self._flocker_validate_availability()
        if type(string) not in [str, unicode]:
            raise Exception('pushed string is not a string: %s' % type(string))

        if dst.startswith('/'):
            raise Exception('pushed file destination is absolute path: %s'% dst)

        if not self.ftpclient:
            self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'], key=key)

        self.ftpclient.push_string(string, dst, timeout)

        metadata = self.ftpclient.get_metadata()
        metadata['key'] = self.ftpclient.dirname
        return metadata

    def flocker_set_metadata(
            self, key=None, contact=None, asset=None, comment=None):
        self._flocker_validate_availability()
        if not self.ftpclient:
            self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'])

        self.ftpclient.set_metadata(contact, asset, comment)

        metadata = self.ftpclient.get_metadata()
        return metadata

    def flocker_get_file(self, remote, local):
        self._flocker_validate_availability()
        if local:
            local = self._valid_path(local)
        else:
            raise Exception('Local file should be valid path: %s'% remote)

        if remote.startswith('/'):
            raise Exception('Remote file should be relative path: %s'% remote)

        if not self.ftpclient:
            self.ftpclient = ftpclient.FtpClient(self, self.config['flocker'])

        self.ftpclient.get_file(remote, local)

    def ls(self, path, globstr='*'):
        return glob.glob(os.path.join(self._valid_path(path), globstr))

    def path_exists(self, path, file_type=None):
        path = self._valid_path(path)
        if not file_type:
            return os.path.exists(path)

        if file_type == 'symlink':
            return os.path.islink(path)
        elif file_type == 'directory':
            return os.path.isdir(path)
        elif file_type == 'file':
            return os.path.isfile(path)

        return False

    def make_coverage_report(self, em, ec, src_tree=None):
        report_root = os.path.join(self.path, 'reports', 'coverage')
        report_summary = os.path.join(report_root, 'coverage.html')

        if os.path.exists(report_summary):
            raise Exception('report file already exists: %s' % report_summary)

        try:
            os.makedirs(report_root)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Exception('could not create directory at %s: %s' %
                    (report_root, str(e)))

        cmd = ['java', '-cp', self._get_emma_jar_path(), 'emma', 'report',
            '-r', 'html', '-in', '%s,%s'%(em,ec),
            '-Dreport.html.out.file=%s'%report_summary]
        if src_tree:
            cmd.extend(['-sp', src_tree])

        try:
            (s, o, e) = ave.cmd.run(cmd)
        except Exception as e:
            raise Exception(
                'failed to execute coverage report generation command: %s'
                % str(e))
        if s != 0:
            raise ave.cmd.RunError(' '.join(cmd), o, e)

        report_tar = os.path.join(report_root, 'coverage.tar')
        report_detail = '_files'
        cmd = ['tar', '-cf', report_tar, '-C', report_root,
            os.path.basename(report_summary), report_detail]
        (s, o, e) = ave.cmd.run(cmd)
        if s != 0:
            raise ave.cmd.RunError(' '.join(cmd), o, e)
        return report_tar

    def _get_emma_jar_path(self):
        return '/usr/share/ave/workspace/emma.jar'

    def get_aapt_path(self):
        return ave.apk.get_aapt_path()

    def get_apk_version(self, apk_path):
        return ave.apk.get_version(apk_path, self.get_aapt_path())

    def _md5_for_file(self, path, block_size=4096, hr=True):
        '''
        Block size directly depends on the block size of your filesystem
        to avoid performances issues.
        '''
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                md5.update(chunk)
        if hr:
            return md5.hexdigest()
        return md5.digest()

    def get_checksum(self, path):
        path = self._valid_path(path)
        if not os.path.exists(path):
            raise Exception('Path %s does not exist' % (path, ))
        if not os.path.isfile(path):
            raise Exception('Path %s is not a file' % (path, ))
        return self._md5_for_file(path)

    def cat(self, path, encoding=None, errors=None):
        path = self._valid_path(path)
        if not os.path.exists(path):
            raise Exception('Path %s does not exist' % (path, ))
        if not os.path.isfile(path):
            raise Exception('Path %s is not a file' % (path, ))
        with open(path, 'rb') as f:
            if encoding or errors:
                encoding = encoding or sys.getdefaultencoding()
                errors   = errors   or 'replace'

                return unicode(f.read(), encoding, errors)
            else:
                return f.read()

    def write_tempfile(self, sequence, encoding='utf-8', promoted_target=None):
        path = self.make_tempfile()

        try:
            with open(path, 'w') as f:
                for string in sequence:
                    # As we cannot detect the encoding of a string, we cannot
                    # encode it to given encoding, we only handle unicode here.
                    if type(string) == unicode:
                        string = string.encode(encoding)
                    f.write(string)
        except Exception, e:
            raise Exception('could not write %s: %s %s' % (path, sequence, e))
        if not promoted_target:
            return path

        self.promote(path, promoted_target)
        return os.path.join(self.path, promoted_target)


    def copy(self, src, dst):
        if os.path.isdir(src):
            ave.cmd.run(['cp', '-r', src, dst], timeout=10)
        else:
            ave.cmd.run(['cp', src, dst], timeout=10)
