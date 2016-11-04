Common Subsystems
=================

:module: ``ave-common``

Modules and packages that are used by several other AVE components. It may also
be useful in

 * Scheduler implementations
 * Service implementations
 * Handling of OS specific configuration details

Regular test jobs would not use this package much, but AVE's own test jobs use
them extensively.

ave.cmd
-------

Run external commands through a forked pseudoterminal. This is done by using
``pty.fork()`` to create new processes. This affects the behavior of the new
process:

 * Output written to ``stdout`` and ``stderr`` are mixed into a single stream.
 * The process and its children are guaranteed to die when the pseudoterminal
   is destroyed. This means that the caller does not have to check that the
   external program is fully terminated afterwards.
 * Programs that daemonize survive the destruction of the pseudoterminal, but
   they have to daemonize *correctly* to achieve this. I.e. do the double fork
   and make sure the final child is a new session leader before returning.
 * There is no buffering of the program's output. If the caller is a program
   that is attached to a pseudoterminal, then the called program's output will
   be written immediately on the caller's pseudoterminal.

.. warning:: ``adb`` does not daemonize correctly and it is not possible to
   start an ADB server using the ``ave.cmd`` functions. Also note that ADB
   will start a server automatically when executing regular commands if none
   was running already. This leads to a cascading failure condition where
   every attemp to run an ADB command results in a new server that is killed
   as soon as the command returns.


.. method:: ave.cmd.run(cmd, timeout=0, debug=False, cwd='', output_file=None)

    Run a command in a separate process.

    :arg cmd: A string or a list of strings where ``index=0`` is the executable
        to run. If *cmd* is a string, then it will be split on whitespace before
        being passed to the sub-process.
    :type cmd: [string, ...] or string
    :arg output_file: A file object which is ready to be written to.
    :type output_file: file

    :returns: An *(integer, string)* tuple: The exit code from the process and
        all its output (``stdout`` and ``stderr`` are mixed in the order they
        are written to, like in a terminal).

    :raises RunError: If creation of the sub-process failed.

    :raises Exception: If any unhandled OS error was encountered during the
        execution. Caller should check the exact type of exception.

.. method:: ave.cmd.run_bg(cmd)

    Works the same as ``ave.cmd.run()``, except that it is non-blocking.

    :returns: A *(PID, file descriptor)* tuple. The file descriptor is attached
        to the new process' pseudoterminal and will carry all messages written
        to ``stdout`` and ``stderr``.

    .. note:: The caller *must* eventually use ``os.wait()`` or one of its
        variations on the PID and ``os.close()`` on the file descriptor. Failing
        to perform these cleanups will lead to defunct processes and/or running
        out of pseudoterminals.

ave.config
----------

Functions to read and write system wide configuration details. Used by servers
to find all of AVE's domain specific configuration files. Also used by Debian
package installation scripts to create default configuration files.

.. method:: ave.config.create_default(home)

    Create default configuration files under ``<home>/.ave/config``. Will also
    create the directories if they do not exist. Configuration files that
    already exist will not be touched.

    :arg home: A string containing a path to a directory. Would normally be a
        user's home directory, but can be anything where the caller has write
        and exec permissions.

    :returns: A tuple of two lists. The first contains the paths of the created
        files. The second contains skipped files.

.. method:: ave.config.load_authkeys(home)

    Load and return the administrative authentication keys from
    ``<home>/ave/config/authkeys.json``. The object can be passed as the
    ``ault_keys`` parameter when creating ``Control`` instances. Functions
    marked with the ``@Control.preauth()`` decorator can refer to account names
    found in the file.

    :arg home: The base directory to search for AVE configuration files.
    :returns:  A dictionary containing account/password pairs in plain text.

    .. Warning:: The use of authentication keys to limit access on API level
        does *not* constitute a security system. It is intended to prevent
        accidental use of features from contexts where they do not make sense
        to use and could potentially affect system performance severely.

.. method:: ave.config.create_etc(path='/etc/ave/user', user=None)

    Creates ``/etc/ave/user`` -- A JSON encoded dictionary. This is done by
    reading a string on ``stdin`` and checking that the value is an existing OS
    user account. It will write the account name and the path to the account's
    home directory to the created file.

    .. Note:: The contents of ``/etc/ave/user`` is used as a switch board to
        find all of AVE's other configuration files. It also determines which
        user account should be used to run the system when it is started from
        the ``init`` process.

    .. Note:: The function will block until it encounters *EOF* on ``stdin``.

.. method:: ave.config.load_etc()

    Loads the contents of ``/etc/ave/user`` and returns it as a dictionary with
    the following entries:

        * *name*: The user name or OS account used to run AVE.
        * *home*: The directory under which ``.ave/config`` must be found.

ave.persona
-----------

The functions in this module are UNIX specific and would need alternative
implementations on other OS'es.

.. method:: ave.persona.become_user(name)

    Change the current process' effective UID to that of the given user name.
    Can only be called by super user 0. This function is only intended for use
    from the ``init`` process during system boot.

    :arg name: An OS user name. Must be found in the ``password`` database, or
        a replacement authentication system.
    :returns: The user's home directory.

ave.profile
-----------

.. class:: ave.profile.Profile(values)

    :arg values: A dictionary where all keys are strings.

    Profiles are essentially ``dict`` instances that implement ``__hash__()``,
    so that they can be used as indices into other dictionaries. AVE uses
    profiles to communicate information about allocatable resources.

    .. method:: match(profile)

        Match this profile against another profile or a dictionary: Iterate
        over the keys in *profile* and check that *self* contains the same key
        with the same value.

        :arg profile: A *dict* or *Profile* instance.
        :returns: *True* if the matching succeeded, *False* otherwise.

    .. method:: minimize(profile=None)

        Return a copy of 'self' that contains the properties that are mandatory
        for the Profile subclass, plus the properties specified by *profile*.

ave.netwok.process
------------------

.. class:: ave.network.process.Process(target=None, args=None, logging=False,\
    proc_name=None)

    This is the base classs for all AVE processes. It supports daemonization.
    It also supports synchronized creation so that children can be guaranteed
    to be fully initialized before the parent's call to .start() returns. This
    is sometimes critical to avoid race conditions when the child must install
    its own signal handlers instead of inheriting those of the parent.

    :arg target: A callable or function pointer. If not set it defaults to
        ``self.run`` which must then be implemented on a subclass. (No default
        implementation is provided.)
    :arg args: A tuple of arguments to be passed to *target*. It defaults to
        ``()``, i.e. no arguments.
    :arg logging: Print activities of the new process to ``stderr``. Defaults
        to ``False``. Daemonized processes should redirect ``stderr`` to a file
        and set this to ``True``.
    :arg proc_name: A string of at most 16 characters. This is the process name
        that is shown by some process inspection tools such as ``ps``. E.g. the
        command ``ps -ejH | grep ave-`` will list processes tree with only the
        processes that were named something starting with "ave-".

    .. method:: start(daemonize=False, synchronize=False)

        Called by the parent process to start the new process.

        :arg daemonize: Perform two forks instead of one to get the new process
            re-parented to ``init``. Defaults to ``False``.
        :arg synchronize: Do not return until the new process has completed all
            initialization steps: ``self.redirect()`` and ``self.initialize()``.
            Useful if the parent will terminate itself immediately after the
            start of the new process and needs to be sure that signal handlers
            and other OS level initialization details of the child are in place.
            Defaults to ``False``.

    .. method:: close_fds(exclude)

        Must be implemented by subclasses that accept open file descriptors in
        their constructors. Append descriptors that should remain open in the
        new process to the *exclude* list before passing it to ``close_fds()``
        on the superclass.

        ``Process.close_fds()`` is called after the process has forked but
        before its target function is called.

        If no implementation is provided, the default implementation will close
        all file descriptors except 0, 1 and 2.

        :arg exclude: List of integers (file descriptors).

    .. method:: terminate()

        Send SIGTERM to the process. May be called from the parent process. May
        also be used on daemonized processes if started with *synchonize=True*.

    .. method:: join(timeout=None)

        Wait for the process to terminate. May only be called by the parent of
        the process. *Must* eventually be called by the parent process unless
        the new process was started with *daemonize=True* in which case ``init``
        will wait for the new process. See zombie control in UNIX litterature.

        :arg timeout: An integer or float. Raise a ``Timeout`` exception if the
            process does not terminate within *timeout* seconds.
        :returns: The exit value of the terminated process.

    .. method:: is_alive()

        Check if the child process is still running. Can only be called from
        the parent process. The parent should call ``join()`` on processes that
        are no longer alive.

        :returns: Boolean.

    .. note::

        The following methods are only available to the new process as methods
        on ``self`` and cannot be called by the parent.

    .. method:: log(message)

        Print a time stamped message to ``stderr`` if the process was created
        with *logging=True* (see constructor).

        :arg message: A string. A timestamp will be added before it is printed.

    .. method:: redirect()

        Default implementation is empty. Subclasses may implement it to redirect
        file descriptors that were inherited by the process. Normally used to
        redirect ``stderr`` to log files.

        Note: ``Process.redirect()`` is called *after* ``Process.close_fds()``.

    .. method:: perform_prctl(death_signal=0)

        Set OS specific process controls. Will be called by default during the
        child's initialization.

        :arg death_signal: An integer matching a valid POSIX signal number.
            Defaults to ``0``. If set, the process will receive this signal when
            its parent process dies.

    .. method:: handle_SIGTERM(signum, frame)

        Default handler for the SIGTERM signal. Exit the process immediately,
        without calling Python exit handlers. Should normally not be implemented
        by subclasses.

    .. method:: handle_SIGUSR1(signum, frame)

        Default handler for the SIGUSR1 signal. Creates a trace file for the
        process in ``.ave/hickup`` and sends SIGUSR1 to all children whose
        process names start with "ave-" (see *proc_name* parameter on the
        constructor). This has debugging purposes. Should not be implemented
        by subclasses.

ave.network.control
-------------------

.. class:: ave.network.control.Control(port, authkey=None, socket=None,\
   alt_keys=None, interval=None, home=None, proc_name=None, logging=False)

   This is the base class for all RPC capable AVE services. It accepts new
   connections on a listening TCP socket and polls the resulting sockets for
   traffic. Incoming JSON encoded messages are treated as remote procedure
   calls.

   ``Control`` implements a very limited cookie based authentication mechanism
   to secure that clients and their sessions are not accidentally mixed up,
   and a similar system based on persistent cookies to limit and/or expand
   client capabilities.

   :arg port: The port number to listen on.
   :arg authkey: If set, clients who do not provide the same key will not be
       allowed to connect.
   :arg socket: Must be a socket object that is listening on the same port as
       was specified with the *port* parameter.
   :arg alt_keys: A dictionary of alternative authentication keys that may be
       used to implement persistent cookies. Keys that appear in this dict may
       be used with the ``@Control.preauth()`` decorator. Functions that are
       marked this way can only be called by clients that authenticated with
       the right key when connecting.
   :arg interval: The interval in seconds at which the ``Control.idle()``
       method is called.

   .. Note:: None of the ``Control`` methods are directly accessible by RPC.
       Subclasses are expected to expose functions that should be accessible
       over RPC.

   .. Warning:: The use of persistent cookies to limit or expand a client's
       access rights does *not* constitute a security system. It is intended
       to prevent accidental use of features from contexts where they do not
       make sense.

   .. method:: shutdown(details=None)

       Exit the main loop and write a last exit message on all connections
       before closing them. The exit message will be serialized as an ``Exit``
       exception.

   .. method:: join_later(proc)

       Defer joining of the process to the control process' main loop. When
       the process is joined, ``Control.joined_process()`` will be called.
       Deferred joins are made non-blocking. Any object whose class inherits
       from ``ave.network.process.Process`` may be joined in this way. Errors
       encountered in the actual attempt to join the process will be printed
       with ``Process.log()``.

   .. method:: joined_process(pid, exit)

       May be implemented by classes that inherit from Control. The function
       will be called whenever a process terminates with a deferred join. See
       ``Control.join_later()`` for more information.

   .. method:: add_connection(connection, authkey)

       May be used by a subclass to add new open ``Connection`` objects to the
       main event loop.

   .. method:: remove_connection(connection)

       May be used by a subclass to remove a ``Connection`` objects from the
       main event loop.

   .. method:: new_connection(connection, authkey)

       May be implemented by classes that inherit directly from ``Control``.
       The function will be called whenever a new connection is accepted by
       the ``Control`` object.

   .. method:: lost_connection(connection, authkey)

       May be implemented by classes that inherit directly from ``Control``.
       The function will be called whenever a previously accepted connection,
       or one added with ``add_connection()``, is lost. The function is called
       regardless of which peer caused the connection to be lost.

   .. method:: idle()

       Called periodically as long as there is no other activity in the main
       loop.

   .. method:: stop_listening()

       Stop accepting new clients. Close the listening socket.

   .. function:: @rpc

      Use this decorator on a subclass method to make it callable over the
      network. Clients can only call functions that have been marked this way.

   .. function:: @auth

      Use this decorator on a subclass RPC method to signal that only clients
      that have authenticated with the primary authentication key may use the
      method.

   .. function:: @preauth(*accounts)

      Use this decorator on a subclass RPC method to signal that only clients
      that have authenticated with an alternate authentication key may use the
      method.

.. class:: ave.network.control.RemoteControl(object)

   Class used to connect to ``Control`` objects. Creates a ``Connection``
   object internally to handle socket traffic with the peer.

   :arg address: A (port, host) tuple. The host may be the empty string ''
       which is interpreted as ``localhost``.
   :arg authkey: The authentication key, if any, to use.
   :arg timeout: Maximum amount of time in seconds to try connecting to a
       ``Control`` instance.
   :arg optimist: Set to ``True`` to keep retrying a connection attempt until
       it succeeds or the timeout expires.
   :arg sock: An open socket object that has already been connected to the
       port and host given in the *address* parameter.

ave.network.connection
----------------------

.. method:: ave.network.connection.find_free_port(start=49152, stop=65536,\
    listen=True)

    Find a free IP port by random picking in the selected range. If successful,
    a bound socket is returned.

    :arg start: Start value for the search range.
    :arg stop: Stop value for the search range.
    :arg listen: Creates a listening socket.
    :returns: A (socket, port) tuple.
    :raises: *Exception* if no free port is found in 20000 attempts.

.. class:: ave.network.connection.Connection(address, socket=None)

    A non-blocking TCP/IP socket based message queue.

    :arg address: A (host,port) tuple. Represents the remote peer on outgoing
        connections. Represents the current host on listening connections.
    :arg socket: A pre-allocated socket. If not set, one will be created.

    .. method:: fileno()

        :returns: The file descriptor of the underlying socket, if any.

    .. method:: listen()

        Sets the underlying socket to a new one that is listening.

    .. method:: accept()

        Accepts a connection attempt on the underlying socket and returns a new
        connection object.

    .. method:: connect()

        Connect to the host/port provided in the constructor.

        :raises: *ConnectionInProgress* if the attempt could not complete
            immediately. The caller should poll the underlying socket for
            writing to determine when connection has been established.

    .. method:: close()

        Shuts down and closes the underlying socket.

    .. method:: write(obj)

        Write a string on the underlying socket.

        :raises: *ConnectionAgain* if the write could not complete immediately
            and should be retried. The caller should poll the underlying socket
            for writing to determine when to retry.
        :raises: *ConnectionClosed* if the connection is no longer open.

    .. method:: read(size)

        Read a string serialized object from the underlying socket.

        :arg size: The number of characters to read.
        :returns: A string.
        :raises: *ConnectionAgain* if the write could not complete immediately
            and should be retried. The caller should poll the underlying socket
            for reading to determine when to retry.
        :raises: *ConnectionClosed* if the connection is no longer open.

    .. method:: put(payload)

        Write a payload to the network, prefixed by a 32 bit network order
        integer that carries the byte size of *payload*. A reference is kept to
        the payload internally so that the call may be retried later if writing
        can not be completed in a single step.

        :arg payload: A string.
        :raises: *ConnectionAgain* if the write could not complete immediately
            and should be retried. The caller should poll the underlying socket
            for reading to determine when to retry.
        :raises: *ConnectionClosed* if the connection is no longer open.

    .. method:: get()

        Read a message from the network. The message must be composed of a 32
        bit network order integer header followed by a payload whose size is
        encoded in the header. Partially read messages are kept internally
        until they can be completed or the connection is lost.

        :returns: The payload string, or *None* if the attempt should be tried
            again later.
        :raises: *ConnectionClosed* if the connection is no longer open.

.. class:: ave.network.connection.BlockingConnection(address, socket=None)

    A blocking TCP/IP socket based message queue. Inherits from *Connection*.

    :arg address: A (host,port) tuple. Represents the remote peer on outgoing
        connections. Represents the current host on listening connections.
    :arg socket: A pre-allocated socket. If not set, one will be created.

    .. method:: poll(mask, timeout)

        Blocks until the underlying socket satisfies a condition or the wait
        times out.

        :arg mask: See ``poll()`` semantics for POSIX.
        :arg timeout: Seconds. An integer or floating point value.
        :returns: A list of (fd, event) tuples. *None* if no event was seen
            before the timeout.

    .. method:: connect(timeout=None, optimist=False)

        Connects the underlying socket to a remote peer.

        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :arg optimist: Ignore error conditions on the socket. Useful when the
            peer has not yet started listening on its accepting socket. The
            client eventually gets a timeout instead of an immediate failure.
        :raises: *ConnectionTimeout* if the connection could not be established
            before the timeout.
        :raises: *ConnectionRefused* if there is an error condition and the
            attempt is not made optimistically.

    .. accept(timeout=None)

        Accept an incoming connection attempt.

        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :raises: *ConnectionTimeout* if the connection could not be established
            before the timeout.
        :raises: *ConnectionClosed* if an error condition is seen during the
            attempt.
        :returns: A new *BlockingConnection* object.

    .. method:: write(obj, timeout=None)

        Write a string on the underlying socket.

        :arg obj: A string.
        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :raises: *ConnectionClosed* if the connection is no longer open.
        :raises: *ConnectionTimeout* if the attempt could not be completed
            before the timeout.

    .. method:: read(size, timeout=None)

        Read a string from the underlying socket.

        :arg size: The number of characters to read.
        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :raises: *ConnectionClosed* if the connection is no longer open.
        :raises: *ConnectionTimeout* if the attempt could not be completed
            before the timeout.
        :returns: A string.

    .. method:: put(payload, timeout=None)

        Write a payload to the network, prefixed by a 32 bit network order
        integer that carries the byte size of *payload*. A reference is kept to
        the payload internally so that the call may be retried later if writing
        can not be completed in a single step.

        :arg payload: A string.
        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :raises: *ConnectionClosed* if the connection is no longer open.
        :raises: *ConnectionTimeout* if the attempt could not be completed
            before the timeout.

    .. method:: get(timeout=None)

        Read a message from the network. The message must be composed of a 32
        bit network order integer header followed by a payload whose size is
        encoded in the header. Partially read messages are kept internally
        until they can be completed or the connection is lost.

        :arg timeout: Maximum time in seconds to spend on the attempt. May be
            *None* for infinite waiting.
        :raises: *ConnectionClosed* if the connection is no longer open.
        :raises: *ConnectionTimeout* if the attempt could not be completed
            before the timeout.
        :returns: The payload string, or *None* if the attempt should be tried
            again later.

ave.exceptions
--------------

.. class:: ave.exceptions.AveException(details)

    Base class for all other AVE exception classes.

    :arg details: A *dict* where all keys are strings. One key must be the
        ``"message"`` key. A ``"type"`` key will be automatically set from the
        name of the exception class, unless provided in the *details* object.

    .. method:: format_trace()

        :returns: A pretty printed version of trace information included in the
        exception. An empty string is returned if no trace is available.

.. class:: ave.exceptions.Timeout(details)

    Indicates that an operation timed out.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.exceptions.Exit(details)

    Indicates that an operation could not be performed because the hosting
    service (e.g the broker) has terminated in a controlled manner.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.exceptions.AuthError(details)

    Used internally in the client/broker, client/session, and other ``Control``
    based handshakes.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.excetptions.RunError(cmd, out, message='')

    Indicates that an externally called tool has failed.

    :arg cmd: The command that was passed to ``ave.cmd.run()``.
    :arg out: The output that was produced by the call.
    :arg message: A free form text message.

.. class:: ave.exceptions.Restarting(details)

    Indicates that an operation could not be performed because the hosting
    service (e.g the broker) has restarted and is no longer accepting new calls
    to the old instance.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.exceptions.Terminated(details)

    Indicates that a background activity has terminated. Background activities
    are typically long running processes, such as flashing a handset or making
    a flashable image, that AVE starts in the background and lets the client
    poll for completion.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.exceptions.Offline(details)

    Indicates that an handset is offline.

    :arg details: A free form text message or a dictionary containing at least
        a ``"message"`` key.

.. class:: ave.exceptions.CompositionServerResponseNot200Exception(details)

    Indicates that the response code of composition server was not 200.

    :arg details: A free form text message.

.. class:: ave.exceptions.CompositionServerResponseHttpRetryCode(details)

    Indicates that the request was failed as composition server issue, user should
    try to request again. Retry HTTP codes:
        502,  # Bad Gateway
        503,  # Service (temporarily) unavailable
        504   # Gateway timeout

    :arg details: A free form text message.

.. class:: ave.exceptions.CompositionServerResponseOrderFailed(details)

    Indicates that the result of order composition was failed.

    :arg details: A free form text message.

.. class:: ave.exceptions.CompositionDownloadImagesFailed(details)

    Indicates that the composition was failed when downloading images

    :arg details: A free form text message.

ave.network.exceptions
----------------------

These exceptions are never propagated over the network. They are generated on
the client side in response to various network issues. They refer to conditions
that can be detected on ``ave.network.connection.Connection`` objects.

.. class:: ave.network.exceptions.ConnectionClosed(msg='connection closed')

    The connection was closed.

    :arg msg: A string.

.. class:: ave.network.exceptions.ConnectionTimeout(msg='timed out')

    The connection timed out. I.e. no traffic could be read from, or written
    to, the conncetion within the time limit that had been set to govern all
    functions on the connection.

    :arg msg: A string.

.. class:: ave.network.exceptions.ConnectionRefused(msg='connection refused')

    A connection could not be established because the other end refused it.

    :arg msg: A string.

.. class:: ave.network.exceptions.ConnectionInProgress(msg='connection in\
     progress')

    A non-blocking connection attempt is in progress and needs to be monitored
    with POSIX ``poll()`` to check for completeness.

    :arg msg: A string.

.. class:: ave.network.exceptions.ConnectionAgain(msg='connection again')

    A non-blocking read or write operation could not be completed and must be
    continued later. Use POSIX ``poll()`` to determine when the connection is
    ready for reading or writing.

    :arg msg: A string.

.. class:: ave.network.exceptions.ConnectionReset(msg='connection reset')

    The connection was reset.

    :arg msg: A string.

ave.network.fdtx
----------------

FdTx is short for File Descriptor Transfer. It is used when restarting brokers
in a way that is invisible to clients.

All functionality in this module is UNIX specific. It seems unlikely that a
matching feature can be implemented on WIN32, which might mean that service
restart on that platform would have to be implemented with some limitations.

The motivation to use file descriptor transfer is based on the following
dilemma:

 * A session to be transfered may be temporarily unresponsive because it is
   busy evaluating a lengthy call.
 * A broker can not tell if a session is alive and healthy without either
   actively polling it or at least checking if its TCP connection to the broker
   is open.
 * A broker that is told to take over sessions started by someone else will not
   be able to reconnect immediately with sessions that are severely busy, and
   so will not be able to tell by either polling or connection openness if the
   session is alive.
 * If the broker should wait for a busy session to become responsive, how long
   should it wait?

Instead of trying to solve the dilemma, ``FdTx`` allows two processes to pass
open file descriptors between each other and so it doesn't become necessary for
the receiver to reconnect with sessions to check their health. The receiver can
poll for error conditions on the file descriptor just like the original owner
did.

Alternate solutions:

 * Drop the requirement on WIN32 that service restarts should be invisible to
   the clients. I.e. disconnect clients when an AVE service is restarted on a
   WIN32 host.
 * Use at least two processes per broker session: One for communication with
   resources and one for communication with the broker and client. This might
   anyway be needed in the long run to support asynchronous manipulation of
   resources from a threaded or muliprocessed client (if that really is what
   is wanted).

.. class:: ave.network.fdtx.FdTx(so_path)

    Implements file descriptor transfer between processes using a special
    feature of UNIX domain sockets. This feature is not wrapped by Python 2's
    standard library, so the implementation resides in a separate C library
    which is interfaced with the ``ctypes`` module.

    :arg so_path: *None* or a file system path to the underlying C library that
        implements file descriptor transfer.

    .. method:: listen(dirname, filename=None)

        Create a UNIX domain socket in the file system and start listening on
        it for connections.

        :arg dirname: The file system directory where the socket file will be
            created.
        :arg filename: The file name of the created socket. Will be randomized
            if not set.
        :returns: The full socket path.
        :raises: *Exception* if the file already exists.

    .. method:: accept(timeout=None)

        Accept a connection. The caller must have called ``listen()`` first.

        ``FdTx`` only keeps track of one open socket internally. Calling this
        function more than once has undefined behavior.

        :arg timeout: The maximum amount of time to wait, in seconds, for a
            connection attempt.
        :raises: A *Timeout* exception if the timeout expires.

    .. method:: connect(path, timeout)

        Connect to an accepting peer. The attempt will be retried until it is
        successful or *timeout* expires.

        :arg path: File system path to a UNIX domain socket that is accepting
            connections.
        :arg timeout: The maximum amount of time to wait, in seconds, for the
            connection attempt to be successful.
        :raises: A *Timeout* exception if the timeout expires.

    .. method:: close()

        Close the underlying domain socket.

    .. method:: put(message, *fds)

        Send a message containing a free form text message and an array of file
        descriptors.

        .. Note:: The receiver must have been told beforehand, in a separate
            message or by convention, how many file descriptors it will receive.

    .. method:: get(max_msg_len, max_fds)

        Receive a message containing a free form text message and an array of
        file descriptors.

        :returns: A tuple containing the message and a list of file descriptors.
