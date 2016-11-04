System API
==========

These API's are only usable by system implementations that use the AVE class
library directly (instead of going through the broker), such as schedulers or
tools that supervise labs.

Workspace
---------
This is the resource class allocated to sessions by the broker. The complete
system API consitst of the following, plus all methods exposed in the
:ref:`client API <workspace-client-api>`. I.e. all client exposed methods can
also be called directly on the actual workspace object.

.. class:: ave.workspace.Workspace(uid=None, cfg_path=None, config=None,\
     home=None)

     :arg uid: If *uid* is set and a workspace with the same unique ID exists
        in the file system, then that workspace will be reused. Otherwise a new
        workspace is created.
     :arg cfg_path: Only used by AVE's own test cases. If used, *cfg_path* must
        be an absolute path pointing at a valid workspace configuration file.
        If not used, the path defaults to ``.ave/config/workspace.json``.
     :arg config: Only used by AVE's own test cases. If used, 'config' overrides
        all values found in the configuration file.
     :arg home: Only used by AVE's own test cases. If used and 'config' is not
        used, all configuration data will be read from .ave/config under <home>.
     :raises Exception: If an error occured.

.. class:: ave.workspace.WorkspaceProfile(values)

    Primarily used by networked brokers to communicate about currently existing
    workspaces.

    :arg values: A dictionary that contains profile data. All keys must be
        strings.

    .. method:: match(other)

        Check if this WorkspaceProfile is a match to the given profile, *other*.

        :arg other: The profile to match against.
        :returns: *True* if it is a match, otherwise *False*.

    .. method:: minimize(profile=None)

        Reduces *self* to whatever is in *profile*, plus the fields that are
        mandatory for the broker to set::

            'type', 'root', 'tools'

        :raises Exception: If *self* is not complete enough to be minimized.

        .. Note:: This function is used by the broker to ensure that profiles
            that are thrown around the system contain enough information to
            let the system maintain a fully usable state (other profiles are
            caught as error indications during testing).
