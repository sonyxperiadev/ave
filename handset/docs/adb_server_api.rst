.. default-domain:: py

ADB Server
==========

This package contains functionality to track the liveness of the ADB server on
the PC and starts a new one as needed. It also tries to kill any competing ADB
server to make sure it stays in control.

That probably sounds nuts. Well behaved programs should not go around killing
each other, right? Unfortunately...

* The ADB server is unstable, so its liveness needs tracking.
* There is a bug in the ADB server's daemonization code which prevents it from
  actually daemonizing under some conditions. When this happens, every client
  command causes a new ADB server to start and then immediately die when the
  result has been returned to the client. The unwanted server death causes all
  ADB connections to all handsets to be closed.
* Any client can intentionally kill the ADB server unless it was started as
  root, triggering the rolling error condition described above.

As it is, the "only" way to handle the worst effects is to start the ADB server
as ``root`` from ``init`` and then watch that server process closely. The exact
behavior can be controlled with a configuration file.

.. class:: ave.adb.server.AdbServer(home=None, config=None)

    If no parameters are passed, the ``AdbServer`` class' configuration is
    loaded from ``<home>/.ave/config/adb_server.json`` where ``<home>`` is the
    value of ``"home"`` in ``/etc/ave/user``.

    :arg home: Use an alternative value of ``<home>``.
    :arg config: Use an explicit set of configuration values (a dictionary). If
        this is passed, the default configuration file will not be loaded.

    .. classmethod:: find_server_processes(port=None)

        Return a list of PID's with server processes that listen to a selected
        TCP port *port*, or any server if *port* is omitted.

        :arg port: An integer or ``None``.
        :returns: A list of integers (PIDs).

    .. classmethod:: kill_all_servers(port=None, excepted=None)

        Kill all ADB servers that listen to the TCP port *port* and do not have
        the same PID as *excepted*. Kill all ADB servers if both parameters are
        omitted.

        :arg port: Integer. Only kill servers that listen to this TCP port.
        :arg excepted: Integer. Do not kill a server with this PID.

    .. classmethod:: load_config(home)

        Load the file ``<home>/.ave/config/adb_server.json`` and validate its
        contents.

        :arg home: String. A valid directory path.

    .. method:: kill_competition()

        Kill all ADB servers that were not created by the current instance of
        the ``AdbServer`` class.

    .. method:: start_server()

        Start a new ADB server. The call returns immediately.

    .. method:: stop_server()

        Stop an ADB server that were previously started with ``start_server()``.

    .. method:: run()

        Kill all other ADB servers, then start a new one and wait until it dies.
        Repeat forever if this ``AdbServer`` instance was configured to be
        persistent (see *Configuration Files* below).
        
Command Line Interface
----------------------

A tool called ``ave-adb-server`` wraps the functionality desribed above::

    ave-adb-server --start   # start a new instance
                   --restart # replace a running instance with a new one
                   --stop    # stop a running instance


.. _adb-server-config:

Configuration Files
-------------------

``.ave/config/adb_server.json``
+++++++++++++++++++++++++++++++

If this file exists, it must contain a dictionary. The dictionary may have any
of the following fields:

* ``port``: The port number the ADB server should be listening on.
* ``persist``: A boolean. If ``True``, a new ADB server is started if the
  currently executing one exits.
* ``demote``: A boolean. If ``True``, the tool ``ave-adb-server`` tries to
  demote its own effective user ID to the configured AVE user (see the
  value of ``name`` in ``/etc/ave/user``). This only works if the tool
  was executed with sufficient privileges (i.e. as root).

This is the default configuration::

    {
        "port": 5037,
        "persist": true,
        "demote": false
    }
