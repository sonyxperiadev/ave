Create Code Coverage Report
===========================

Overview
--------
Code coverage is an important measurement of testing case quality, this document
will guide you how to create coverage report for your apk package testing.

Steps to Create report
----------------------

1. Jenkins Build Job Setup
++++++++++++++++++++++++++
In this phase, we need to get instrumented APK and class coverage metadata
files.

a) Compile the APK with semc-build.

 * Build using *Execute SEMC build-script* jenkins plugin, There is an input
   field in this plugin *Additional semc-build parameters*, if it not shown,
   click the button *Advanced...* to show it, then input the text
   `-Demma-coverage-on=true` into it.
 * Build using *Execute shell* jenkins plugin, it should execute *semc-build*
   command like this::

       semc-build ... -Demma-coverage-on=true ...

b) Archive the APK and coverage metadata files.

   Add the *Archive the artifacts* post-build action, in the *Files to archive*
   field, input something like this::

       reports/coverage/coverage.em, semc-build-output/Foobar/bin/Foobar.apk

2. Run test cases to get runtime coverage data
++++++++++++++++++++++++++++++++++++++++++++++
In this phase, we will get runtime coverage data by running the test cases.

a) Download APK from Jenkins job and install it to handset::

    path = workspace.download_jenkins(..., artifacts=['Foobar.apk'], ...)

b) Install the APK and run the tests with coverage turned on, this produces
   the coverage.ec file in the handset file system::

    handset.reinstall(os.path.join(path, 'Foobar.apk'))
    handset.run_junit(..., test_options={'coverage':'true'}, ...)

3. Make coverage report
+++++++++++++++++++++++
In this phase, we already have coverage metadata and runtime data, we can make
the report file in HTML format.

a) Download the coverage metadata from Jenkins job::

    em_path = workspace.download_jenkins(..., artifacts=['coverage.em'], ...)

b) Pull the coverage runtime data from handset. The path to ``coverage.ec`` is
   predictable. It will be based on the APK's package name. E.g::

    handset.pull('/data/data/com.sonymobile.foobar/files/coverage.ec', ec_path)

c) To produce a report that also contains line by line analysis (not just
   overall coverage stats), the source code to build APK is needed. If you
   do not need the line by line analysis, you can skip this step (set
   ``src_tree=None``)::

    src_tree = workspace.download_git(...)

d) Make the report::

    report = workspace.make_coverage_report(em_path, ec_path, src_tree)

e) Push the report to flocker for later analysis::

    workspace.flocker_push_file(report, coverage.tar)
