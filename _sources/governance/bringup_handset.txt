Handset Changes
---------------
AVE's handset classes often break when the Android API level is stepped up.
They may also break when a new platform is introduced. Such breakage must be
corrected in the product, in AVE, or both. AVE provides tests that can be used
to prove that the changes have been made correctly.

There are three primary areas to look for breakage:

 * Individual functions in AVE's handset classes must be changed.
 * Individual functions in Gort must be changed.
 * Galatea may need to be rebuilt against a new version of ATF.

Git trees to work with:

 * ``semctools/ave/handset``
 * ``semctools/ave/gort``
 * ``semctools/ave/galatea``

Tests to Run
^^^^^^^^^^^^
To pass the bring-up exit criteria, a number of AVE's self-tests must pass. The
tests are found in the handset Git::

    git clone git://review.sonyericsson.net/semctools/ave/handset

The test runner (``semctools/ave/handset/jobs/runners.py``) may need changes to
allocate the appropriate model of the prototypes you will use for the testing.

To complete the preparations, connect two handsets of the new model to your
workstation. The handsets must have valid SIM cards on a network that provides
data traffic. The SIM cards must store their own phone numbers so that AVE can
read them. (New SIM cards do not have this data filled in.)

Tests to run::

    #!/bin/sh
    vcsjob execute -j handset -t GTEST,UNIT
    vcsjob execute -j handset -t JUNIT,UNIT
    vcsjob execute -j handset -t LOCALE,UNIT
    vcsjob execute -j handset -t LOGCAT,UNIT
    vcsjob execute -j handset -t ANDROID,UNIT
    vcsjob execute -j handset -t LISTER,UNIT
    vcsjob execute -j handset -t CALLS,UNIT
    vcsjob execute -j handset -t POSITIONING,UNIT

Individual Handset Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Git tree to modify: ``semctools/ave/handset``

Examples of breakage from the past:

 * ``AndroidHandset.get_phone_number()`` have a different implementations from
   API level 18 and forward. The function checks internally which API level to
   work with by asking the handset and then picks the right implementation.
 * ``AndroidHandset.install_gort()`` must call ``self.root()`` before the Gort
   APK can be intalled if API level is 17 or higher.
 * ``AndroidHandset.uninstall_setup_wizard()`` must manipulate the handset's
   settings database if API level is 17 or higher.

Steps to follow if tests fail:

 * Change handset files as needed:
   ``semctools/ave/handset/src/ave/handset/*.py``.
 * Re-run the tests (as outlined above).

Individual Gort Functions
^^^^^^^^^^^^^^^^^^^^^^^^^
Git tree to modify: ``semctools/ave/gort``

Examples of breakage from the past:

 * For JB MR2, the call engine had to follow API changes in Android telephony
   call state class.
 * For JB MR1, applications must by default be verified by the user or not be
   allowed to install. A new function was created to allow programmatic control
   over this setting.
 * Locale handling changed between ICS and JB. This caused Gort to crash when
   the locale setting function was used.

Steps to follow if tests fail:

 * Change Gort internals to use the correct Android API's depending on
   the system's API level. There is only one Gort APK and it handles all
   supported API levels, so any changes must be backward compatible.
 * Build Gort's Debian package: ``semctools/ave/gort/mkdeb``.
 * Install the package:
   ``sudo dpkg -i semctools/ave/gort/ave-gort-<Debian version>.deb`` where
   ``<Debian version>`` is the new value of ``Version:`` above.
 * Re-run the handset tests (as outlined earlier in this document).

Rebuilding Galatea
^^^^^^^^^^^^^^^^^^
Galatea is a "UI scraper" that can access and manipulate system and application
UI elements. This is done with a lot of help from a platform component called
ATF ("Application Test Framework") which inserts itself right on top of the
Android UI hierarchy. ATF is distributed as a JAR file within SONY Mobile and
may need patching when the Android API level changes.

Steps to follow if tests fail:

 * Download the new ATF JAR from its official Jenkins build job. (See further
   instructions below.)
 * Store the new JAR file in the Galatea source tree as
   ``semctools/ave/galatea/src/libs/<version>/atf.jar`` where ``<version>`` is
   something appropriate. (Currently we track ICS and JB.)
 * Modify ``semctools/ave/galatea/mkdeb`` to use the new JAR file by adding a
   line ``make_apk(root, '<version>', '<branch>')`` where ``<version>`` is the
   same value as above and ``<branch>`` is something appropriate for the new
   product that is being brought up. (Currently we track Blue and Lagan).
 * Build Galatea's Debian package: ``semctools/ave/galatea/mkdeb``.
 * Install the package:
   ``sudo dpkg -i semctools/ave/galatea/ave-galatea-<Debian version>.deb`` where
   ``<Debian version>`` is the new value of ``Version:`` above.
 * Change ``AndroidHandset.reinstall_galatea()`` to select the new APK when the
   new API level is seen in the handset.
 * Re-run the handset tests (as outlined earlier in this document).

The different versions of the ATF JAR can be taken directly from their Jenkins
builds. The currently existing versions are found here::

    http://android-ci.sonyericsson.net/job/ATF-ics/
    http://android-ci.sonyericsson.net/view/MBT/job/ATF-JB/

If ATF has been changed (it has its own bring-up process to follow), the System
Verification team in Lund can tell you which Jenkins job to go to for the new
version.
