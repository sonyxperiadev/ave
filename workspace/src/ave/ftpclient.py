import os
import random
import string
import hashlib
import json
import ave.config
import re
import time
from datetime        import datetime, timedelta

from ftplib             import FTP
from ave.exceptions     import AveException, Timeout


DIRNAME_LENGTH = 32

def rand_dirname():
    result = []
    for i in range(DIRNAME_LENGTH):
        result.append(random.choice(string.ascii_lowercase + string.digits))
    return ''.join(['%s' % i for i in result])

class FtpClient(object):
    tmp_file = None
    ftp = None
    home      = None
    store     = None
    dirname   = None
    comment   = None
    asset     = None
    contact   = None
    key       = None

    def __init__(self, ws, config, key=None):
        if key:
            self.dirname = key
            self.key = key
        elif not self.dirname:
            self.dirname = rand_dirname()

        self.store = config['ftp']['store']
        self.config = config
        self.ws = ws
        self.login()

    @property
    def root(self):
        if not (self.store and self.dirname):
            return None
        return os.path.join(self.store, self.dirname)

    def _connect(self):
        try:
            if not self.ftp:
                self.ftp = FTP()
            self.ftp.connect(self.config['host'], self.config['ftp']['port'], self.config['ftp']['timeout'])
            self.ftp.login(self.config['ftp']['user'], self.config['ftp']['password'])
        except Exception, e:
            raise AveException({'message': 'Could not login FTP server: %s' % (str(e))})

    def login(self):
        self._connect()
        try:
            self.ftp.cwd(self.dirname)
        except Exception, e:
            if not self.key:
                self.ftp.mkd(self.dirname)
            else:
                details = {'message':'Could not access %s: %s' % (self.dirname, str(e))}
                raise AveException(details)

    def relogin(self):
        self._connect()

    def is_alive(self):
        try:
            self.ftp.sendcmd('NOOP')
        except:
            return False

        return True

    def keep_ftp_connect(fn):
        def decorated_fn(self, *vargs, **kwargs):
            try:
                self.ftp.sendcmd('NOOP')
            except:
                self.relogin()
            return fn(self, *vargs, **kwargs)
        return decorated_fn

    def switch_dirname(self, existing_key=None, custom_key=None):
        if existing_key:
            self.key=existing_key
            self.dirname=existing_key
            self.login()
        if custom_key:
            self.dirname='%s_%s' % (custom_key, rand_dirname())
            self._connect()
            try:
                self.ftp.cwd(self.dirname)
            except Exception, e:
                self.ftp.mkd(self.dirname)
            self.key=self.dirname
            self.login()

    def _push_file(self, path, filename):
        try:
            os.path.getsize(path)
        except Exception, e:
            details = {'message':'could not push file %s: %s' % (path, str(e))}
            raise AveException(details)

        filename = filename.split('/')
        count = len(filename)
        if count > 1:
            for i in range(count-1):
                try:
                    self.ftp.cwd(filename[i])
                except:
                    self.ftp.mkd(filename[i])
                    self.ftp.cwd(filename[i])

        self.ftp.storbinary("STOR " + filename[count-1], open(path,'rb'))

    @keep_ftp_connect
    def get_file(self, remote, local, root=True):
        try:
            if root:
                self.ftp.cwd(self.root)
            else:
                self.ftp.cwd(self.store)

            fhandle = open(local,'wb')
            self.ftp.retrbinary("RETR " + remote, fhandle.write)
        except Exception, e:
            details = {'message':'could not get file %s: %s' % (remote, str(e))}
            raise AveException(details)

    @keep_ftp_connect
    def push_file(self, path, filename):
        self.ftp.cwd(self.root)
        self._push_file(path,filename)
        self.update_metadata_file()

    @keep_ftp_connect
    def push_metadata(self, path, filename):
        self.ftp.cwd(self.store)
        self._push_file(path,filename)

    def list_remote_files(self):
        lines = []
        def list_name(line):
            lines.append(line)

        self.ftp.retrlines('NLST', list_name)
        return lines

    @keep_ftp_connect
    def is_file_exist(self, filename):
        filename = filename.split('/')
        count = len(filename)
        if count > 1:
            for i in range(count -1):
                try:
                    self.ftp.cwd(filename[i])
                except:
                    return False
        try:
            self.ftp.size(filename[count-1])
        except:
            return False

        return True

    @keep_ftp_connect
    def push_string(self, content, filename, timeout= 30):
        self.ftp.cwd(self.root)
        full_path_filename = filename
        #check file whether exist or not
        exist = self.is_file_exist(filename)
        if not exist:
            tmp_file = self.ws.make_tempfile()
            self.ftp.cwd(self.root)
            self._push_file(tmp_file, filename)

        filename = filename.split('/')
        filename = filename[len(filename)-1]
        if timeout > 0:
            limit = datetime.now() + timedelta(seconds=timeout)
        else:
            limit = None

        while True:
            if limit and datetime.now() > limit:
                raise Timeout('push string timed out')
            try:
                rsize = self.ftp.size(filename)
                datasock, esize = self.ftp.ntransfercmd("STOR " + filename, rsize)
            except Exception, e:
                time.sleep(1)
                self.relogin()
                self.ftp.cwd(self.root)
                self.is_file_exist(full_path_filename)
                continue

            datasock.sendall(content)
            datasock.close()
            self.ftp.voidcmd('NOOP')
            self.ftp.voidresp()
            self.update_metadata_file()
            break


    def get_metadata(self):
        metadata = {
            'url'    : None,
            'contact': self.contact,
            'asset'  : self.asset,
            'comment': self.comment
        }
        root = self.config['http']['doc-root']
        if not self.root:
            return metadata
        host = self.config['host']
        port = self.config['http']['port']
        path = self.root[len(root)+1:]
        metadata['url'] = {'host':host, 'port':port, 'path':path}
        return metadata

    def update_metadata_file(self):
        if not self.tmp_file:
            self.tmp_file = self.ws.make_tempfile()
        with open(self.tmp_file, 'w') as f:
            f.write(json.dumps(self.get_metadata(), indent=4))
        self.push_metadata(self.tmp_file, self.dirname + ".json")

    def set_metadata(self, contact=None, asset=None, comment=None):
        if contact and type(contact) not in [str,unicode]:
            raise Exception('contact is not a string: %s' % type(contact))
        if asset and type(asset) not in [str,unicode]:
            raise Exception('asset is not a string: %s' % type(asset))
        if comment and type(comment) not in [str,unicode]:
            raise Exception('comment is not a string: %s' % type(comment))

        if contact != None:
            self.contact = contact
        if asset != None:
            self.asset = asset
        if comment != None:
            self.comment = comment

        self.update_metadata_file()

        return self.dirname + '.json'
