AVE Bring-up Exit Criteria
==========================

Each development project that wishes to use AVE for automated testing must
follow a couple of steps to prove that the product is ready for automated
testing. By doing so the project secures that test results generated with AVE
are credible:


* http://dmweb.sonyericsson.net/pages/fba/edit-fba.html?id=569 
  This is FBA page which SW project will request AVE team to bring up AVE 
  on the new SW platform in a project. This is maintained by AVE product owner. 
* Set up official builds to produce and store test packages in C2D and Jenkins.
* Make sure AVE can flash the new handset models.
* Make necessary changes to AVE's Handset components.
* Keep track of system dialogs that cannot be disabled or pre-configured in
  the product.
* Check that all AVE's self tests pass.
* Enable AVE's smoke tests in DUST to catch future changes in the product that
  break the verification environment.

Process Overview
----------------
AVE supports official test schedulers (e.g. DUST) which support verification
of selected feature scopes. This maps to existing project checkpoints:

.. figure:: ave-bring-up.jpg
    :align: center

.. Note::
   * It is recommended to start AVE bring-up already before `CP Basic` but the
     hard requirement is to finish before `CP Open`. It is not possible to fully
     complete the AVE bring-up before `CP Open` because of dependencies toward
     official build systems and CM labeling which are not available until that
     time.                                                                                                                                                                                                                                                                                                                    
    
   * FBA dependency: Telephony, Positioning, Android System Thermal.

**Before CP Open**

An AVE bring-up is an entirely technical affair guided by test cases, most of
which are automated. The automated tests verify that a product supports various
API's that are required to make the product testable. They also verify that
delivery systems are correctly set up for use in continuous integration with
DUST. The manual tests verify that no popup dialogs can block test execution.

PM's are recommended to use a mix of personnel with competencies in tooling and
certain domains of product functionality to secure an AVE bring-up:

* SWD Tools (primary, with support from System Verification)
* Telephony (if needed for problems with calling and messaging functions)
* Positioning (if needed for problems with GPS related functions)
* Local connectivity (if needed for problems with USB stability)
* Android System (if needed for problems with suppression of dialogs and other
  system configuration issues)

Passing the bring-up tests may require changes to AVE and/or the product itself.
It is not always the case that the product offers the needed testability out of
the box.

**A Minimal Bring-Up**

As suggested, it is often not possible to pass `all` AVE self tests during the
early bring-up activities. The reason is simple: The product does not yet have
all legacy features, many of which are exposed through AVE.

However, a small set of AVE features are so essential that almost no tests can
run without them. In reality, these are `product` features:

* A unique handset serial number is visible in the USB device descriptor.
* ADB over USB works.
* The command ``adb -s <serial number> reboot oem-53`` reboots the handset to
  soft service mode.
* The handset can be flashed in soft service mode.
* The handset automatically reboots to Android mode after a successful flash.
* The handset automatically sets the property ``sys.boot_completed`` `after`
  the home and lock screens are fully loaded. It is not possible to allocate
  the handset to a test job before this works. If the property is set too
  early, many test jobs will fail because the handset is not ready for remote
  control.
* Ability to force-wake the handset.
* Ability to disable the handset keyguard.

**After CP Open**

Once the minimal bring-up has been completed, it should be possible to execute
a wide variety of AVE-based test jobs in DUST. This is handled by System
Verification (owner of DUST).

At this point the PM can start tracking an initial test scope, and expand it
with the goal of having the full scope in place for `CP Feature Complete`. It
is normal that many tests do not initially pass and many test jobs will not be
meaningful to enable before missing features have been integrated. This should
be business as usual for the PM and System teams.

**A Complete Bring-Up**

As the platform and legacy bring-up nears completion, more and more of AVE's
self tests should pass. SWD Tools tracks this progress and helps the development
project prioritize product issues that block test automation. If the new product
is significantly different from an old one in some way that affects AVE API's,
SWD Tools also implements support for these changes in AVE.

.. Note::
    The rest of this document is concerned with the combined set of AVE bring-up
    activities that must be completed before `CP Legacy Complete`

Detailed Task Lists
-------------------
The linked documents below contain the technical details about how to pass all
AVE bring-up exit criteria:

.. toctree::

    bringup_official_build.rst
    bringup_flash.rst
    bringup_handset.rst
    bringup_dialogs.rst

Wrapping Up
-----------
So you think you are done? Please bump the version numbers of the components you
had to change:

* Bump Gort's version number by increasing the value of ``Version:`` in the
  file ``semctools/ave/gort/packaging/DEBIAN/control``.
* Bump Galatea's version number by increasing the value of ``Version:`` in the
  file ``semctools/ave/galatea/packaging/DEBIAN/control``.
* Bump flash's version number by increasing the value of ``Version:`` in the
  file ``semctools/ave/flash/packaging/DEBIAN/control``.
* Set the handset's Debian package to require the new versions of ``ave-gort``,
  ``ave-galatea`` and ``ave-flash``.
* Bump handset's version number by increasing the value of ``Version:`` in the
  file ``semctools/ave/handset/packaging/DEBIAN/control``.

Then make system installations of everything and run the acceptance tests::

    #!/bin/sh

    semctools/ave/handset/mkdeb
    semctools/ave/gort/mkdeb
    semctools/ave/galatea/mkdeb
    semctools/ave/flash/mkdeb

    sudo dpkg -i semctools/ave/handset/ave-handset-<Debian version>.deb
    sudo dpkg -i semctools/ave/gort/ave-gort-<Debian version>.deb
    sudo dpkg -i semctools/ave/galatea/ave-galatea-<Debian version>.deb
    sudo dpkg -i semctools/ave/flash/ave-flash-<Debian version>.deb

    ave-broker --restart

    vcsjob execute -j semctools/ave/handset -t ACCEPTANCE

If everything passes and no dialogs are known to cause any problems, then you
are probably ready to go into code review.

Finale
------
These last steps will be done in code review, but you can prepare by checking
them yourself:

* To avoid breaking AVE, run the acceptance tests again against older products
  that are known to pass AVE's handset tests.
* To avoid breaking AVE, run positioning reference tests (found in this git:
  ``semctools/ave/positioning``). You need a GPS simulator from Spirent to do
  this. Contact the Positioning team for more information.
