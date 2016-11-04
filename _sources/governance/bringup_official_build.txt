Official Builds
---------------

Label Builds
^^^^^^^^^^^^
Official builds must be configured to use the function that builds both e.g.
the ``userdebug`` variant of each component and the extra content that is used
during testing. I.e. the build job should produce a Debian package for the
component itself *and* a Debian package for any extra test content.

There are three passes in the build job that produce artifacts that must be
packaged this way:

 * ``Android.mk`` based components in the platform.
 * ``semc-build`` based components (platform and/or apps).
 * ``semc-build`` based decoupled applications.

To test that the build job is set up correctly, run the following test for each
kind of component::

    #!/usr/bin/python2

    from ave.workspace import Workspace
    from ave.label     import get_latest

    # set these to appropriate values
    branch  = 'THE BRANCH TO BE TESTED'
    package = 'THE NAME OF THE PACKAGE WITH TEST CONTENT'
    pc      = 'testcontent' # None for regular packages

    w = Workspace()
    try:
        label = get_latest(branch)
        path  = w.download_c2d(package, label=label, pc=pc)
    except Exception, e:
        print('FAIL: could not download package: %s' % e)
        return False

    try:
        path = w.unpack_c2d(path)
    except Exception, e:
        print('FAIL: could not unpack package: %s' % e)
        return False

    # check that contents in the returned path matches what is expected for the
    # package that was downloaded.

    return True

Commit Builds
^^^^^^^^^^^^^
This works like the label build jobs, but the test selects the content directly
from Jenkins. The build steps to secure are the same (platform, coupled and
decoupled components) but the test is a little bit different::

    #!/usr/bin/python2

    from ave.workspace import Workspace

    # set these to appropriate values
    job       = 'THE ID OF THE OFFICIAL JENKINS BUILD JOB'
    artifacts = ['artifact1', 'artifact2', ...] # as found in jenkins
    host      = None # defaults to 'http://android-ci.sonyericsson.net'

    w = Workspace()
    try:
        path = w.download_jenkins(job, artifacts=artifacts, base=host)
    except Exception, e:
        print('FAIL: could not download artifacts: %s' % e)
        return False

    # check that contents in the returned path matches the expected artifacts

    return True
