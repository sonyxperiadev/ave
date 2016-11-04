Workspaces
==========

:module: ave-workspace

This class has two main purposes:
* Provide an API used to query properties about the machine that holds
  the workspace. Such properties may include the SSID of the local WLAN
  or whether a particular tool is installed on the machine. This should
  be used whenever a test job would otherwise use hard coded values
  which may not be valid when the test job is executed on a different
  machine. Test jobs can use ``get_profile()`` to get a dictionary with
  all such properties of a workspace. Most of the properties are set in
  ``.ave/config/workspace.json``.
* Give the test job writer a convenient API to interface with official
  CM and delivery systems: Git, C2D, Jenkins, Goobug, flashable image
  creatin, etc.

.. toctree::
    :maxdepth: 2

    client_api.rst
    system_api.rst
    config.rst
