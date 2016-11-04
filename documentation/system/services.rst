Services
========

All AVE services support starting, restarting and stopping. In most cases a
restart cannot be detected by currently executing test jobs. (The exception is
the ADB server which will tear down any TCP port forwarding rules when it is
restarted.)

All services implement a common CLI to support these operations::

    ave-<service> --start [--force]
    ave-<service> --restart
    ave-<service> --stop

The ``--force`` flag should only be used from *Upstart* integration as it will
delete any found PID file for the service without checking for actual processes.

Starting
^^^^^^^^
Typical steps performed by the executable:

 * Use ``ave.config.load_etc()`` to find the ID and home directory of the user
   selected to run AVE services.
 * Use ``ave.persona.become_user()`` to demote the effective user ID to that of
   the selected user. Services should normally not run as ``root``.
 * Create an instance of the service's main Python class and daemonize it.
 * Create the PID file ``/var/tmp/ave-<service>.pid``.
 * The service uses ``ave.config.load_authkeys()`` to read the ``admin`` key
   from ``.ave/config/authkeys.json`` and requires that calls to administrative
   functions are made by clients that know this value.

.. Note::

    The use of authentication keys for administration is *not* a security
    feature. It is only meant to avoid accidental use of admin functionality
    from regular test jobs.

Restarting
^^^^^^^^^^
Currently executing test jobs must not be affected by restarts, which makes this
a complex operation. The general idea is to

 * Use ``ave.config.load_authkeys()`` to load the ``admin`` authentication key
   from ``.ave/config/authkeys.json``.
 * Find the currently executing instance and connect to it with the ``admin``
   authentication key.
 * Tell the running instance to dump its internal state and to stop accepting
   new clients.
 * Create a new instance of the service and feed the internal state to it.
 * Tell the running service that it may quit as soon as all of its regular
   clients have disconnected.
 * Daemonize the new instance.
 * Replace the PID file.

This means that two instances will be executing until the old instance has lost
all of its clients. New clients can only connect to the new instance because the
old instance no longer has a listening socket.

Rationale
~~~~~~~~~
The restart behavior is not typical for UNIX daemons and is not supported with
convenience features in any of the major ``init`` implementations. Some AVE
services are very complicated to restart seamlessly. Why bother?

 * The lab owner should be able to update an AVE installation without having to
   plan for maintenance downtime.
 * Some tests can conceivably run for days or even weeks (power measurements
   and aging tests come to mind) and would be costly to evict.
 * Scheduler complexity would increase a lot if it was necessary to handle job
   errors that stem from service restarts (and this assumes that all jobs report
   this error correctly). There may be many schedulers but only one framework
   so it is cheapest and most robust to solve problem in the framework.

Stopping
^^^^^^^^
 * Use ``ave.config.load_authkeys()`` to load the ``admin`` authentication key
   from ``.ave/config/authkeys.json``.
 * Find the currently executing instance and connect to it with the ``admin``
   authentication key.
 * Tell the service to evict all clients and terminate itself.
 * Delete the PID file.

Systemic Uses
^^^^^^^^^^^^^

 * *Upstart* scripts use ``ave-<service> --start --force`` to start services
   when the PC boots.
 * Debian package ``postinst`` scripts use the (re)start functionality when
   packages are configured after installation. So, installing a new version of
   an AVE component automatically restarts it (or starts it if it wasn't already
   running).
 * Programmatic use from lab supervision tools.
 * Manual use by the lab owner.

Notes
^^^^^

 * The ADB server is never restarted automatically by AVE because it is not
   possible to hide this event from currently executing test jobs. The lab owner
   has to do this manually in the event that it is needed.
 * There is no AVE service to manage the life cycle of FG3. The lab owner has to
   start and stop ``fg3console`` as needed.
