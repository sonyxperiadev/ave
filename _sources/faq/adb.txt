.. _adb-server-behavior:

ADB Behavior
============

Problem Description
-------------------
* The ADB client kills the server and starts a new one when it detects a
  version mismatch. Usually this is not needed because ADB is backward
  compatible and does not change much between Google releases.
* Users will (without knowing it) mix ADB versions. The typical scenario is
  manual use of a private version of ADB client in the terminal while AVE is
  using the version shipped by SWD Tools. The manual use kills the ADB server
  and thus all ongoing sessions.
* Handsets cannot be claimed by ADB server after a PC reboot due to permission
  problems if the server is started "too early" (whatever that means). Having
  a proper ``udev`` rule doesn't help.
* The ADB server's ability to claim the device (on USB level) after it has
  rebooted is higher when running the server as root. This is probably a
  variation of the problem with PC reboot.
* The ADB server does not daemonize correctly. If the server was started by
  the client, then the server may die immediately when the client returns.
  This causes a persistent error condition where all uses of the ADB client
  cause a server restart. If you were trying to use ADB socket forwarding, or
  waiting for a long-running shell command to complete, then this will be very
  noticable.

All of these can be addressed by running the ADB server as root. But that has
its own problems:

*If you really have to run a private version of ADB, all uses of the client
will fail because the client can no longer kill the ADB server run by AVE.*

What AVE Does
-------------
The ADB server is controlled by AVE through the program ``ave-adb-server``.
This wrapper is started by ``init`` and runs as root. It is configured to
immediately kill off other ADB servers and start a new one if its own should
terminate.

So, the owner of an AVE installation will find it difficult to stop the AVE
controlled ADB server with ``adb kill-server``. Of course, the client will try
to do that for you if it detects a version mismatch. Then the error will look
like this::

    adb server is out of date.  killing...
    cannot bind 'tcp:5037'
    ADB server didn't ACK
    * failed to start daemon *

Solution (well, sort of...)
---------------------------
* Stop the wrapper: ``sudo ave-adb-server --stop``
* Stop the broker: ``ave-broker --stop``

Stopping the broker is necessary because it continously polls connected devices
with ``/usr/bin/adb``. If no server is running when this happens, a new one is
automatically started by the ADB client itself. This will conflict with any
attempt to run a private version of ADB.

If you stop the wrapper but not the broker, you will see a message like this
one before your command is evaluated::

    adb server is out of date.  killing...

Closing Remarks
---------------
* Unfortunately there is no way to tell the client to not start a server if
  none was running. That would have made the problem a bit smaller as it would
  have given the user more control in the first place.
* There is also no way to tell the client to ignore version differences. That
  would also have helped.
* The stability problems listed under the problem description are sort of OK
  if you only make manual use of ADB with a very limited number of handsets.
  In larger setups with automation, this just doesn't work.
* Regrettably the only currently known workaround is to run the ADB server as
  root. If there is a better way, please let us know!
