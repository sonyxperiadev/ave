Dialogs
-------

Our capability to predict when dialogs appear is low. They often stop execution
of test cases until the dialog has been dismissed, so dialogs incur a high risk
against test automation. To handle this, AVE provides functions to configure, enable and disable individual dialogs.

Known dialogs must be checked that they can be enabled/disabled with AVE during
bring-up. The bring-up team also needs to make an inventory of new dialogs that
did not exist before, and handle these.

.. Warning::

    Generally it is not possible to know with absolute certainty that all
    possible dialogs receive sufficient handling in either AVE or in the test
    jobs that use AVE. Manual verification of the handling is needed.

.. Note:: Alternative Handling

    Sometimes it is important for a test that a dialog *does* pop up. For these
    situations the handset UI manipulation functions should be used to dismiss
    dialogs. The UI manipulation functions are covered by the fully automated
    AVE handset tests.

Auto Power Off
^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: SHOULD handle. SIM card should not be necessary to have
   in all lab prototypes.
 * Preferred implementation: Enable/disable the behavior (not the dialog). We
   don't want the handset to turn itself off. Disabling the behavior should
   disable the dialog.
 * How to recognize: Shown soon after boot completed on handsets without a SIM.
   Warns user that handset will be turned off automatically within 15 minutes
   of idling.

Dangerous Listening Volume
^^^^^^^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: NICE to have. Headset must be connected to trigger.
 * Preferred implementation: Let user enable/disable the dialog.
 * How to recognize: Connect headset, set volume to max. Dialog will appear with
   warning about high volume levels causing impaired hearing.

Data Disclaimer
^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. Does not seem to block tests, but likely
   we just haven't tripped over the blocked tests yet.
 * Preferred implementation: Let user enable/disable the dialog.
 * How to recognize: *"Data disclaimer. For quality purposes, your device will
   check for software updates to your preinstalled Sony applications ...
   <Accept>"*

Data Transmission Charges May Apply
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: SHOULD handle. GPS tests currently have to dismiss the
   dialog with UI traversal. This just adds execution time if the dialog does
   not appear (within a timeout).
 * Preferred implementation: Let user pre-configure the presented choice to
   disable the dialog.
 * How to recognize: *"The device will download inforation about your current
   location to improve the performance. Data transmission charges may apply.
   <checkbox> Don't ask me again <Disagree|Agree>"*

Improved Stamina Tips
^^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: SHOULD handle. Uncertain if this dialog blocks testing.
 * Preferred implementation: Let user enable/disable the dialog.
 * How to recognize: ...

Insufficient Power
^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. This information is needed by AVE to avoid
   draining prototype batteries.
 * Preferred implementation: Let user enable/disable the dialog. The condition
   itself should be exposed as a property or event that can be interfaced by a
   programmable solution.
 * How to recognize: *"The connected power source is not sufficient. The
   battery is discharging faster than it is charging. Please change to your AC
   charger."*

Key Guard
^^^^^^^^^
 * AVE implementation: ``AndroidHandset.disable_keyguard()``
 * Bring-up handling: MUST handle.
 * Preferred implementation: Let user select the exact key guard. E.g. "Swipe",
   "PIN" or "None", as seen in Android menu ``Settings / Security / Screen
   lock``.

Learning Client
^^^^^^^^^^^^^^^
 * AVE implementation: ``AndroidHandset.uninstall_learning_client()``.
 * Bring-up handling: MUST handle.
 * Preferred implementation: The dialog is currently disabled by uninstalling
   the learning client. It would be better if it could be pre-configured.

Location Consent
^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. GPS tests currently have to use UI traversal
   to dismiss the dialog.
 * Preferred implementation: Let user pre-configure the presented choice to
   disable the dialog.
 * How to recognize: *"Location consent. Allow Google's location service to
   collect anonymous location data. Some data may be stored on your device.
   Collection may occur even when no apps are running. <Disagree|Agree>"*

Package Verifier
^^^^^^^^^^^^^^^^
 * AVE implementation: ``AndroidHandset.disable_package_verifier()``
 * Bring-up handling: MUST handle.
 * Preferred implementation: Current implementation.

PC Companion
^^^^^^^^^^^^
 * AVE implementation: ``AndroidHandset.disable_pc_companion()``
 * Bring-up handling: MUST handle.
 * Preferred implementation: Current implementation.

Process X has Stopped
^^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: SHOULD handle. It seems these dialogs disappear anyway.
   The risk is that the dialog masks something in the UI that a test is looking
   for.
 * Preferred implementation: Let user enable/disable. Report should be written
   to on-device storage instead (if it isn't already).
 * How to recognize: Duh...

Regularly Check Apps
^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. Blocking on JB MR2.
 * Preferred implementation: Let user enable/disable the dialog.
 * How to recognize: *"Google may regularly check installed apps ..."*

Satelite Notification
^^^^^^^^^^^^^^^^^^^^^
 * AVE implementation: Test jobs that encounter this dialog currently uninstall
   ``/system/app/GpsSatellitesNotification.apk`` from the handset.
 * Bring-up handling: SHOULD handle.
 * Preferred implementation: Let user enable/disable without uninstalling the
   APK.
 * How to recognize: Unknown. Ask positioning team.

Setup Wizard
^^^^^^^^^^^^
 * AVE implementation: ``AndroidHandset.uninstall_setup_wizard()``
 * Bring-up handling: MUST handle.
 * Preferred implementation: The dialog is currently disabled by uninstalling
   the setup wizard. It would be better if it could be pre-configured.

This is a Prototype
^^^^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. Blocks all UI driven tests.
 * Preferred implementation: Let user enable/disable the dialog.
 * How to recognize: *"This is a prototype..."*

Upload Reminder
^^^^^^^^^^^^^^^
 * AVE implementation: ``AndroidHandset.uninstall_upload_reminder()``
 * Bring-up handling: MUST handle.
 * Preferred implementation: Current implementation.

Water Resistance
^^^^^^^^^^^^^^^^
 * AVE implementation: None
 * Bring-up handling: MUST handle. Blocks UI driven tests.
 * Preferred implementation: Let user enable/disable the dialog. Take guidance
   from the implementation in DeviceEnvironment.
 * How to recognize: Warns user that water protection flaps are being left open.
