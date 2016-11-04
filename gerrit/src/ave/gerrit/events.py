import os
import json
import errno
import signal

import ave.cmd
import ave.config
import ave.gerrit.config

from ave.network.exceptions import ConnectionClosed
from ave.network.control    import RemoteControl
from ave.network.process    import Process
from ave.network.pipe       import Pipe


class GerritEventStream(Process):
    home     = None # home directory where AVE and SSH config files are stored
    pipe     = None # ave.network.pipe.Pipe
    mailbox  = None # a (host,port) tuple to reach a Control process
    config   = None
    procname = None
    ssh_pid  = -1
    ssh_fd   = -1

    def __init__(self, host=None, port=0, user=None, pipe=None, mailbox=None,
        home=None):
        if not home:
            self.home = ave.config.load_etc()['home']
        else:
            self.home = home
        # load the default configuration file
        config = ave.gerrit.config.load(self.home)
        # override configuration file entries
        if host is not None:
            config['host'] = host
        if port != 0:
            config['port'] = port
        if user is not None:
            config['user'] = user
        if pipe and type(pipe) != Pipe:
            raise Exception('pipe must be an ave.networking.pipe.Pipe')
        if mailbox and (type(mailbox) != tuple or len(mailbox) != 2):
            raise Exception('mailbox must be a (host,port) tuple')
        # validate the final configuration
        ave.gerrit.config.validate(config)
        self.config = config
        self.pipe   = pipe
        if mailbox:
            self.mailbox = RemoteControl(mailbox, None, None)
        # superclass initialization
        Process.__init__(
            self, target=self._run, proc_name='ave-gerrit-event-stream'
        )

    def close_fds(self, exclude):
        if self.pipe:
            exclude.append(self.pipe.w)
        Process.close_fds(self, exclude)

    def handle_SIGTERM(self, signum, frame):
        if os.getpid() != self.pid:
            # someone else is running "our" signal handler. impossible to make
            # sure this never happens because there is a race condition between
            # creating a process and setting its signal handler, and the signal
            # handler will automatically get inherited by all children of a
            # process. if such a child is terminated before it sets its own
            # handler, then the parent's handler will be run (with parameters
            # that may be private to the parent. e.g. 'self' will not point to
            # the child).
            os._exit(os.EX_OK) # best we can do  :-(
        self._shutdown()

    def _shutdown(self):
        self._kill_ssh()
        os._exit(os.EX_OK)

    def _kill_ssh(self):
        if self.ssh_pid > 1:
            try:
                os.kill(self.ssh_pid, signal.SIGTERM)
                os.waitpid(self.ssh_pid, 0)
            except OSError, e:
                if e.errno not in [errno.ECHILD, errno.ESRCH]:
                    raise Exception('unhandled errno: %d' % e.errno)
            self.self_pid = -1
            try:
                os.close(self.ssh_fd)
            except OSError, e:
                if e.errno == errno.EBADF:
                    pass # already closed
                else:
                    print 'WHAT?', e
                    raise e

    def _begin(self):
        cmd = ['ssh']
        cmd.extend(['-p',str(self.config['port'])])
        cmd.extend(['-l',self.config['user']])
        cmd.append(self.config['host'])
        cmd.extend(['gerrit','stream-events'])

        # make sure ssh finds its configuration files
        os.environ['HOME'] = self.home
        # make sure ssh always reads its private key from $HOME/.ssh
        if 'SSH_AUTH_SOCK' in os.environ:
            del(os.environ['SSH_AUTH_SOCK'])

        self.ssh_pid, self.ssh_fd = ave.cmd.run_bg(cmd)

    def _pop(self):
        # look for the line break that delimits a complete JSON encoded message
        msg = ''
        while True:
            c = os.read(self.ssh_fd, 1)
            if not c:
                raise ConnectionClosed('gerrit closed the connection')
            if c == '\n':
                return msg.strip()
            msg += c

    def _run(self):
        self._begin()
        while True:
            event = None
            try:
                event = self._pop()
            except OSError, e:
                if e.errno == errno.EIO: # dropped SSH connection? start over
                    self._kill_ssh()
                    self._begin()
                    continue
            except ConnectionClosed:  # dropped SSH connection? start over
                self._kill_ssh()
                self._begin()
                continue
            try:
                event = json.loads(event)
            except Exception, e:
                print 'GES WARNING: %s' % e
                continue
            if self.pipe:
                self.pipe.put(event)
            if self.mailbox:
                try:
                    self.mailbox.put_gerrit_event(event)
                except Exception, e:
                    if str(e).startswith('project not tracked by heimdall'):
                        pass
                    elif str(e).startswith('ignoring'):
                        pass
                    else:
                        print 'GES WARNING:', e
