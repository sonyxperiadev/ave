Test Job Base Classes
=====================

Base classes for implementing test jobs that is compliant with test schedulers.

``TestJob``
-----------

.. class:: ave.utils.testjob.TestJob( )

    May be used as a base class when implementing test jobs to be executed.
    Implement a class inheriting from this class and at least override the
    ``main()`` function. It is recommended to set the instance
    variable branch to the CM branch that the test is running on.

    Call ``execute()`` on the class instance in the test job. This will pick up
    parameters including the globally unique ID, or "GUID", used
    to track the job's execution.

    .. Note:: When executing on a development machine, the GUID is randomized
        by ``TestJob``. If test results are reported to *Decibel*, this GUID
        may be used to find those results in that database.

    :raises Exception: If the scheduler issued an invalid GUID.

Flocker Support
+++++++++++++++

    .. attribute:: flocker_session_key

        Use this attribute in calls to ``Workspace.flocker_push_*()`` functions
        to get all logs collected in the same Flocker session.

State Machine
+++++++++++++

    The different states of the state machine are::

        'Setup'
        'Pre'
        'Main'
        'Post'
        'Teardown'

    .. function:: execute(nr_of_iterations)

        Drives the whole test job execution state machine. Will run
        setup-pre-main-post-teardown looping over pre-main-post the specified
        number of times.

        Each call to the functions are contained in a try statement that catches
        exceptions, logs it to file and exits the execution flow in an ordered
        way if an exception is caught.

        :arg nr_of_iterations: A number that states how many times pre-main-post
            should be iterated in the state machine

    .. function:: setup()

        *Setup* state in execution state machine, should be used for general
        setup for the test job. Regardless of *nr_of_iterations* parameter in
        execute it will be executed once.

    .. function:: pre()

        *Pre* state in execution state machine, should be used for setup that is
        closely connected to the test performed in the following main function.
        If execute is called with parameter *nr_of_iterations* > 1, ``pre()``
        will be executed that number of times.

    .. function:: main()

        The *Main* state in the state machine. Must be overridden in a subclass.
        Will be executed *nr_of_iteration* times.

    .. function:: post()

        *Post* state in execution state machine, should be used for cleanup that
        is closely connected to the test performed in the previous main
        function. If ``execute()`` is called with parameter *nr_of_iterations*
        > 1, ``post()`` will be executed that number of times.

    .. function:: teardown(self)

        *Teardown* state in execution state machine, should be used for general
        cleanup for the test job. Regardless of *nr_of_iterations* parameter in
        ``execute()`` it will be executed once.

Convenience Methods
+++++++++++++++++++
.. function:: allocate_equipment(self)

    .. function:: allocate_equipment()

        Retrieves the profiles from ``vcsjob`` and assigns equipment with the
        ``equipment_assignment()`` function.

    .. function:: equipment_assignment(profiles)

        Must be overridden in subclass.

        Subclass function should assign all the equipment with a single call
        to ``Broker.get()``.

        :arg profiles: List of profiles that should be assigned.

    .. function:: evaluate_results()

        Must be overridden in subclass.

        Should evaluate results and set a verdict of the test job to one of
        ``vcsjob.OK``, ``vcsjob.FAILURES`` or ``vcsjob.ERROR``.

    .. function:: find_suitable_label()

        Gets the build label from the allocated handset. If it is set to
        ``"private"``, then the latest official build label on the current
        branch is used instead.

        :returns: A string with the found label

    .. function:: print_handset_info()

        Prints all info in the handset profile plus build label and SIM
        information to log.

    .. function:: update_status(test_job_status)

        Setter of *self.test_job_status*. Use this method to avoid overwriting
        values with higher priority, to get logging, and to not set invalid
        status values.

        :arg test_job_status: the status to be set.

Multiple Handset Handling
+++++++++++++

    .. function:: register_handset_workspace(handset, workspace)

        Use to register handset and workspace. Create an HandsetWorkspaceData
        object and put it into *self.handset_workspace_data_dict* which is a
        dict, handset's serial as key, HandsetWorkspaceData object as value.

        :arg handset: the handset allocated
        :arg workspace: the workspace allocated with handset together

    .. function:: get_handset_workspace_data(handset)

        Get the HandsetWorkspaceData object linked with given handset

        :arg handset: the handset allocated
        :returns: A HandsetWorkspaceData object

``AndroidTestJob``
------------------

.. class:: ave.utils.testjob_android.AndroidTestJob(logcat_active=True)

    Inherits from ``TestJob``.

    Base class for test jobs that are written for Android handsets.

    :arg logcat_active: Run ``logcat`` for the duration of the test job?

State Machine
+++++++++++++

    .. function:: setup()

        * Calls the ``TestJob.setup()`` function.
        * Removes crashes from handset by calling
          ``remove_crashes_from_handset()``.
        * Initiates logcat if variable *logcat_active* is set to *True*.

    .. function:: teardown()

        * Get all logcat data and pushes it to flocker if *logcat_active* is
          set to *True*.
        * Handles crash dumps.
        * Calls the ``TestJob.teardown()`` function.

Packages Installation
+++++++++++++++++++++

    .. function:: download_binary(pkg, app, label=None, version=None,\
            package_component=None, handset=None)

        Downloads the specified application from C2D or Jenkins depending on
        how *self.build_url* is set.

        :arg pkg: The package to fetch from.
        :arg app: The application to fetch.
        :arg label: The label to fetch from. *Not used if downloading from
            Jenkins.*
        :arg package_component: Package component to download from, will not be
            used if label is set. *Not used if downloading from Jenkins.*
        :arg version: Version to download, will not be used if label is set.
            *Not used if downloading from Jenkins.*
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*
        :returns: The path to the downloaded files. *Not used if downloading
            from Jenkins.*

    .. function:: download_binary_from_jenkins(pkg, app, build_url=None,\
            pkg_path=None, handset=None)

        Downloads the specified application from Jenkins.

        :arg pkg: The package to fetch from.
        :arg app: The application to fetch.
        :arg build_url: The path to the Jenkins build.
        :arg pkg_path: The path to the artifacts created by the Jenkins build.
            Not necessary to set unless a special Jenkins job is used that does
            not follow standard BOC setup.
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*
        :returns: The path to the downloaded files.

    .. function:: fetch_binary(label, pkg, app, handset=None)

        Deprecated. Use ``download_binary()``.

    .. function:: install_binary(path, timeout=30, handset=None)

        Wrapper function for ``AndroidHandset.install()``

        :arg path: Path to the place to find files that should be installed.
        :arg timeout: Timeout in seconds (defaults to 30 seconds).
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

    .. function:: reinstall_binary(path, timeout=30, handset=None)

        Wrapper function for ``AndroidHandset.reinstall()``

        :arg path: Path to the place to find files that should be reinstalled.
        :arg timeout: Timeout in seconds (defaults to 30 seconds).
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

    .. function:: uninstall_binary(pkg, handset=None)

        Checks if a package is installed and if it is it is uninstalled.

        :arg pkg: The name of the package to uninstall.
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

Crash Handling
++++++++++++++

    .. function:: remove_crashes_from_handset()

        Removes all found crashes on the allocated handset.

    .. function:: handle_crash_dumps()

        If the allocated handset has an official build label, then all crashes
        are pulled and reported to Goobug.

        Removes all crashes from the handset.

``AndroidInstrumentationTestJob``
---------------------------------

.. class:: ave.utils.testjob_android.AndroidInstrumentationTestJob(\
        logcat_active=True)

    Inherits from ``AndroidTestJob``.

    Base class for test jobs that are written for Android handsets, that run
    instrumentation tests.

Instrumentation
+++++++++++++++

    .. function:: execute_instrumentation_tests(runner, test_name,\
        test_options, timeout=600, handset=None)

        Executes an instrumentation test. Stores the JUnit result file in the
        local results directory and pushes it to flocker, then shouts it to
        Panotti.

        :arg runner: The runner to run.
        :arg test_name: The Name of the test.
        :arg test_options: Test options that are passed on to ``run_junit()``.
            Defaults to *None*.
        :arg timeout: Timeout in seconds, defaults to 600.
        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

    .. function:: evaluate_results()

        Reports the test by using ``report_instrumentation_tests()``. If the
        reporting succeeds, then the report is evaluated with the function
        ``evaluate_instrumentation_report()``.

    .. function:: report_instrumentation_tests(handset=None)

        Reports the Instrumentation test to decibel

        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

        :returns: *True* if the reporting is successful.

    .. function:: evaluate_instrumentation_report(handset=None)

        Evaluates the instrumentation test report and sets the test job status
        to ``vcsjob.ERROR``, ``vcsjob.FAILURES`` or ``vcsjob.OK`` depending on
        the result of the tests.

        :arg handset: the handset used, must be set. For backwards compatibility,
            Defaults to *None*

State Machine
+++++++++++++

    .. function:: setup()

        Calls ``AndroidInstrumentationTestJob.setup()``.

State Machine
+++++++++++++

    .. function:: setup()

        Calls ``AndroidTestJob.setup()``.

``HandsetWorkspaceData``
------------------

.. class:: ave.utils.testjob.HandsetWorkspaceData(handset, workspace)

    Data structure for the shared variables linked to a handset.

    List of variables set::
        HandsetWorkspaceData.handset
        HandsetWorkspaceData.workspace
        HandsetWorkspaceData.results_directory
        HandsetWorkspaceData.sw
        HandsetWorkspaceData.hw
        HandsetWorkspaceData.serial
        HandsetWorkspaceData.imei
        HandsetWorkspaceData.instrumentation_report
        HandsetWorkspaceData.build_handler
        HandsetWorkspaceData.logcat_handler
        HandsetWorkspaceData.crash_handler
        HandsetWorkspaceData.run
        HandsetWorkspaceData.junit_test_completed

    .. function:: set(name, value):

        The function assigns the value to the attribute.

        :arg name: A string may name an existing attribute or a new attribute
        :arg value: an arbitrary value

