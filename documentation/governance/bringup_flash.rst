Flashing
--------
Git trees to work with:

 * ``semctools/ave/flash``
 * ``semctools/ave/handset``

The handset test runner (``semctools/ave/handset/jobs/runners.py``) may need
changes to allocate the appropriate model of the prototypes you will use for
the testing.

Tests to run::

    #!/bin/sh

    # Make sure the fg3 daemon is running and if not:
    # fg3console -dm &
    vcsjob execute -j semctools/ave/handset -t FLASH

The flash tests check the following:

 * Can a flashable image be built from C2D packages?
 * Can FlashGordon flash the built image to the handset?
 * Can the handset return to full Android mode after flashing?
 * Can a handset with the newly flashed system reboot to service mode?
 * Can FlashGordon find the newly flashed handset in service mode?
 * Can FlashGordon flash a Trim Area file to the newly flashed handset?
 * Can the handset return fo full Android mode again?

If the flash tests fail, it will normally be due to one of these:

 * No official build is available in C2D. No flashable image can be created.
 * FlashGordon does not flash the handset correctly.

Contact the C2D and/or Flash Tools teams depending on what went wrong. Email:
SWDtoolsSemc@sonymobile.com

Occationally, AVE will need to be updated too. This might happen if the command
line switches to ``fg3console`` have changed. If so, make the necessary changes
to ``semctools/ave/flash/src/ave/flash/fg3.py``, re-install and re-test::

    #!/bin/sh

    semctools/ave/flash/mkdeb
    sudo dpkg -i semctools/ave/flash/ave-flash-<Debian version>.deb
    ave-broker --restart
    vcsjob execute -j semctools/ave/handset -t FLASH
