Upstart Integration
===================

*Upstart* is the current ``init`` implementation in Ubuntu. It is slated for
migration to *systemd* sometime in the future as Debian has recently opted to
make it the default ``init`` implementation on Linux. *Upstart* is used by AVE
to start various services, such as the broker, when the PC boots.

The current volatile situation with ``init`` implementations on Linux prompted
a solution that does not actually make any use of "extra" features found in
*Upstart*, compared to the classic *SysV* implementation. Such use would make
future migration to another implementation difficult. *Upstart* is only used to
*start* AVE services at boot. The lab owner must interact directly with the
various services to start, restart and stop them after the PC is fully booted.

Model
-----
All AVE services must implement this command line interface::

    ave-<service> --start --force

which will be used from a corresponding *Upstart* rule in::

    /etc/init/ave-<service>.conf

The CLI arguments must be handled like so:

 * Delete any existing PID file found in ``/var/tmp/ave-<service>.pid``.
 * Start the service daemonized.
 * Create ``/var/tmp/ave-<service>.pid``.

The *Upstart* configuration file should normally not start the service until
the local file system and full networking is available. AVE services demote
their effective user ID to whatever is found in ``/etc/ave/user``, so the file
system and networking are needed to interact with the networked authentication
system used at SoMC. *Broker* example::

    # /etc/init/ave-broker.conf
    description "ave-broker"

    start on (filesystem and net-device-up IFACE!=lo)

    console output
    expect daemon

    exec /usr/bin/ave-broker --start --force

Notes
-----
 * The lab owner can disable automatic start of a service at boot by commenting
   out the ``exec`` line in the corresponding ``/etc/init/ave-<service>.conf``
   file.
 * The default *Upstart* file for *Flocker* has the ``exec`` commented out. Most
   hosts should not run this service. (Note that Flocker's configuration file
   ``.ave/config/flocker.json`` is also not created by default for the same
   reason, and because its contents depends very much on the local configuration
   of *lighttpd*, which AVE does not try to parse.)
 * The service that starts the ADB server runs as root. (This is needed to
   guarantee that ADB will have sufficient permissions to claim the equipment
   on USB level. It also makes ADB a bit more reliable in general.) Users who
   want to control the life cycle of the ADB server manually should create
   ``.ave/config/adb_server.json`` with this content::

        { "demote":true, "persist":false }

   This still starts the ADB server on PC boot, but not as ``root`` and the ADB
   server will not be restarted automatically when it is killed.
