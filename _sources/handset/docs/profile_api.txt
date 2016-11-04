Handset Profile
===============

.. class:: ave.handset.profile.HandsetProfile(values)

    Inherits from ``ave.profile.Profile``.

    :arg values: A dictionary that contains profile data. All keys must be
        strings.

    .. method:: minimize(profile=None)

        Reduces *self* to whatever is in *profile*, plus the fields that are
        mandatory::

            'type', 'platform', 'serial', 'sysfs_path', 'pretty', 'power_state'

        :raises Exception: If the profile is not complete enough to be
            minimized.

        .. Note:: This function is used by the broker to ensure that profiles
            contain enough information to be used in all parts of AVE.
