Configuration Files
===================

This document is intended only for lab owners. Broker clients cannot change the
settings of allocated workspaces.

All settings are controlled by the file ``.ave/config/workspace.json``. It
contains a JSON dictionary with various entries and sub-sections.

A broker restart is required for changes to take effect.

Root Directory
--------------
Work spaces are created in a common root directory. This directory can be set
to any path where the broker has full file system permissions. Default value::

    "root": "~/.ave"

I.e. if ``/etc/ave/user`` specifies the home directory ``/var/tmp``, then all
workspaces will be created under ``/var/tmp/.ave``.

Lab Identity
------------
Like handsets, workspaces have "pretty" values. These may be used by lab owners
to group several hosts into logical units. E.g. all hosts in the same lab may
have the same "pretty" value in their workspace configurations. This may then
be used by test jobs that must be allocated to a specific lab. Example::

    "pretty": "type-approval-japan"

The default value is the hostname of the machine and is set during installation
of AVE. E.g. "seldlx12345.corpusers.net".

.. Note:: It is not recommended for test jobs to set the "pretty" entry in
    workspace allocations. This will cause the job to fail if executed in an
    environment where the lab is not available, or if the lab is not shared to
    the allocating broker.

Flocker
-------
The hostname and port the global Flocker service. Clients will not be able to
use the Flocker API's if this entry is not set to correct values. The default
entry::

    "flocker": {
        "host": "ave.sonyericsson.net",
        "port": 4003
    }

External Tools
--------------
Clients can use workspaces to call external tools that have been white-listed
in the "tools" entry. Example::

    "tools": {
        "aapt": "/opt/ave/bin/aapt",
        "adb": "/usr/bin/adb",
        "hprof-conv": "/opt/ave/bin/hprof-conv"
    }

Jenkins
-------
The default Jenkins host used by ``Workspace.download_jenkins()`` is set by the
"jenkins" entry. If the *base* parameter is not set in the call, then its value
is taken from this entry. This the default setting::

    "jenkins": "http://"

.. Note:: This setting is legacy functionality and has limited practical value.
    Test jobs should use the *base* parameter to pass on configuration data that
    was provided by a scheduler.
