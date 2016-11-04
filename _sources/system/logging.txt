Logging
=======

Overview
--------

A few different kinds of logging are used to serve different purposes:

 * Prints to ``stdout`` by test jobs. Used to provide progress indication with
   lots of semantics. Intended for post-mortem analysis by humans. Not intended
   for automated analysis.
 * Prints to ``stderr`` by AVE daemons. Used to provide debugging information.
   Intended for post-mortem analysis by humans.
 * Consolidation of log files and other test job artifacts. Used to store logs
   in a way that can be tied to a single run of a test job. Intended for
   post-mortem analysis by humans.
 * Automatic emission of structured entries to a centralized store. Used to log
   resource utilization and system malfunctions and unexpected events in AVE
   itself. Intended for automated business intelligence analysis.
 * Explicit emission of test results from test jobs. Used to store the pass/fail
   status of individual test cases. Intended for manual as well as automated
   analysis.
 * Explicit emission of domain specific measurements from test jobs. Used to
   store e.g. performance data collected by test jobs. Intended for manual as
   well as automated analysis.

``stdout`` Prints by Test Jobs
------------------------------
Test jobs are executed by ``vcsjob``, which is able to intercept all prints to
``stdout`` and ``stderr``. A scheduler may redirect this output to a file. See
``vcsjob.execute_job(..., log_path=None, ...)``.

The job itself has access to this file so that it may upload its own log to
Flocker: ``vcsjob.get_log_path()`` returns the path that was selected by the
scheduler, or raises an exception if not set.

``stderr`` Prints by Daemons
----------------------------
Daemons are initialized with writable file handles that replace ``stdout`` and
``stderr`` (the handles may point to the same file). Consequently all prints by
the daemon, the Python interpreter and functions called by the daemon will end
up in the log file(s).

Left to do:
 * Log files are currently created under ``/var/tmp`` and should move to
   ``.ave/logs`` in AVE's home directory.
 * Implement log file rotation or garbage collection against a maximum disk
   usage.

Consolidation of Job Logs
-------------------------
API's on the ``Workspace`` class may be used to push files and log entries to
Flocker. Test jobs should use this to store artifacts that may be needed in
post-mortem analysis.

Flocker itself implements parallel uploads from multiple clients, configurable
garbage collection and log rotation. The logs will eventually be purged as they
are not considered business critical in the long term. It is enough if they are
available for a "reasonable" amount of time after the test job has finished.

Structured Logging to Panotti
-----------------------------
.. figure:: panotti.jpg
    :align: right

Panotti is a mythical creature of antiquity with very large ears. Presumably it
has excellent hearing and will faithfully record everything it hears.

Schedulers may use ``vcsjob`` to set a globally unique ID on job executions:
``vcsjob.execute_job(..., guid=None, ...)``. If set, this GUID is picked up by
the RPC marshalling mechanism (see ``ave.network.control.RemoteControl``) and
used to created JSON compatible log entries of all remote procedure calls that
generate an exception.

The GUID may also be read by the job, using ``vcsjob.get_guid()``.

The function ``ave.panotti.shout()`` is used to post a message to CouchDB. It
will do nothing if no GUID is provided or the file ``.ave/config/panotti.json``
does not contain the configuration data needed to connect to the database.

Left to do:
 * Log daemon ``stderr`` prints to Panotti on hosts that enable this behavior.
 * Trace *all* calls from test jobs to AVE  on hosts that enable this behavior.

Test Results
------------
Test results that fit the pass/fail/error model may be uploaded to deciBel with
``Workspace.report()`` if the result was generated with ``Handset.run_junit()``
or Handset.run_gtest()``. In other cases, the result may be built using calls
to ``ave.report.decibel`` function and then posted directly to deciBel.

Left to do:
 * Document the ``ave.report.decibel`` module.

Performance Results
-------------------
Test results that fit a tabulated data model may be uploaded to MySQL.

Left to do:
 * Document the ``oursql`` module or refer the reader to existing documentation
   on the Internet.

Scheduler Work Performed on a Job’s Behalf
------------------------------------------
Schedulers are expected to use GUID's (as outlined above) to connect the logs
of test jobs with the logs of preparatory work performed by the scheduler. E.g.
if a scheduler has flashed a handset before the job allocates it, then the log
from the flashing should be possible to find through the log for the test job.
