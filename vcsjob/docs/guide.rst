``vcsjob``: Version Controlled Test Jobs
========================================

:module: vcsjob

Terminology
-----------

 * **Test case:** A single test. E.g. a ``JUnit`` or ``gtest`` test case.
 * **Test instruction:** A program that drives the execution of test cases.
 * **Test job:** The execution of a test instruction, normally initiated by
   some kind of scheduler.
 * **Job scheduler:** Anyone or anything that can trigger a test job. E.g.
   DUST or Jenkins. Or a human running commands in a terminal.

Introduction
------------
**First rule of testing:** *Know what you test.*

To make the execution of a test job reproducible without magic knowledge about
previous runs, developers and testers must follow a few simple rules:

 * Keep test instructions under version control.
 * Eliminate global side effects that may affect a test job.
 * Prevent the introduction of dynamically created configuration data.

To help you follow these rules, ``vcsjob`` acts as a gate keeper between you
and your test instructions. Also, centralized schedulers such as DUST ignores
your test instructions if they are not executable by ``vcsjob``.

Implementors of advanced schedulers must work hard to break these rules as
little as possible. ``vcsjob`` provides carefully designed loop holes for this
purpose. Other users should not break the rules.

.. Warning:: The whole point of ``vcsjob`` is to force the user to provide test
    instructions on a strict format. Don't create ways to circumvent this. It's
    a feature. It's *the* feature.

Features
--------
 1. Fetch test instructions from controlled sources (i.e. Git repositories).
 2. Clear all environment variables before starting a test job. A scheduler
    must use explicit white listing of variables that should be seen by the
    test job.
 3. Stop the user from parameterizing a test job "on the fly" by adding runtime
    arguments.
 4. Use a declarative file format to act as the primary interface between jobs
    and schedulers.
 5. Select jobs to execute based on tag filtering.
 6. Separate fetching from execution so that the scheduler is not *forced* to
    fetch the instructions to execute.
 7. Provide both command line and Python interfaces.

**Rationale**

 1. Explained in the introduction.
 2. Explained in the introduction.
 3. Explained in the introduction.
 4. Is meant to let an advanced scheduler figure out if a test instruction is
    worth executing at all, and help it select maintenance jobs to run before
    and/or after the test job.
 5. Allows a scheduler to build a global test scope by looking for the same
    tags in multiple repositories. High level test planners should keep a list
    of tags that mean something specific. E.g. setting ``PERFORMANCE`` on all
    test instructions that report official performance figures.
 6. Acknowledges that developers must be able to work with interim versions of
    source trees and execute test instructions found in them without having to
    commit a new version first.
 7. Humans and Jenkins use the command line interface. Advanced schedulers use
    the Python API's.

File Interface
--------------
When pointed to a source tree, ``vcsjob`` expects to find a special file called
``.vcsjob`` in the root of the tree. This file is JSON formatted and contains
a dictionary. The dictionary must contain the key ``"executables"``, which in
turn must be a list of instruction meta data::

    {
        "executables": [
            { "path":     "jobs/demo_job.py",
              "tags":     ["demo"] },

            { "path":     "other/path/job_x",
              "tags":     ["SMOKE", "PERFORMANCE", "x"]
              "banner":   "Pass/fail performance test of component X on Lagan",
              "profiles": [{"type":"handset", "pretty":"yuga"}] },

            { "path":     "somewhere/job_y",
              "tags":     ["SMOKE", "PERFORMANCE", "y"]
              "banner":   "Pass/fail performance test of component Y on Lagan",
              "profiles": [{"type":"handset", "pretty":"yuga"}
                           {"type":"relay", "circuits":["usb.power","battery"]}
                           {"type":"workspace"}],
              "coverage": ["asset 1", "coverage item 2"] }


            { "path":     "broken/stuff",
              "tags":     ["joes_special_blend"]
              "banner":   "Don't run me unless you know what you're doing!",
        ]
    }

Each meta data entry is a dictionary with the following attributes:

 * **path:** *String. Mandatory.* The value must be a valid file system path,
   relative to the directory where the ``.vcsjob`` file is found. The path must
   be a regular file that is executable by the user that invokes ``vcsjob``.
 * **tags:** *List of strings. Mandatory.* The value is not checked against any
   enforced pattern. It is recommended that tags which have an official meaning
   over multiple source trees use only capital letters and that other tags do
   not.
 * **banner:** *String. Optional.* A descriptive one liner.
 * **profiles:** *List of resource profiles. Mandatory for DUST jobs.* May be
   used by test instructions to give hints to the scheduler about what resources
   will be allocated. It is considered a bug if this hint is not in accord with
   what the test job actually does at run time, but no enforcement is performed.
   The value of this field is accessible from the test job.
 * **coverage:** *List of strings. Optional.* This field may be used to state
   that the test covers one or more areas of functionality in a product. These
   "coverage items" should normally be the exact names of "assets", to use
   corporate lingo. ``vscjob`` does not check these names against a database
   with known assets, but a scheduler might do that.

Given the example above, a content crawler that looks for certain ``vcsjob``
tags in source trees might use the contents to create a global catalogue of
performance tests, their descriptions, and options to add individual jobs to a
scheduler.

Command Line Interface
----------------------

Fetching
++++++++
To fetch version controlled test instructions from Git::

    vcsjob fetch -s|--source <url>
                 -d|--destination <path>
                 -r|--refspec <version>
                 -t|--timeout <seconds>

source, destination and refspec must be used:

 * **source:** The Git tree to fetch from. May be a local file system path, a
   ``git://`` URL or an ``ssh://`` URL.
 * **destination:** The local file system path where the tree will be stored.
   You may use the same destination again and again as long as the tree remains
   clean (as reported by ``git status``).
 * **refspec:** The version to check out in the destination tree. You can
   specify branch names and SHA1 ID's. (Tags probably work too.) You may switch
   back and forth between different versions in the same tree as long as the
   tree is clean (as reported by `git status`).
 * **timeout:** The timeout for fetching source code, unit is seconds.


.. Note:: The implementation of the ``fetch`` operation allows a scheduler to
   keep a tree around between job executions. ``vcsjob`` will automatically
   choose ``git clone`` or ``git fetch`` as needed. This typically reduces the
   time needed to perform subsequent fetches. For some source trees it will be
   a significant difference.

.. Warning:: The behavior of ``vcsjob fetch`` is undefined if multiple instances
   fetch concurrently to the same destination.

Executing
+++++++++
To execute test instructions from a file system directory::

    vcsjob execute -j|--jobs <path>
                  [-t|--tags <tags>]
                  [-e|--env <env vars>]

Only the **jobs** option is mandatory:

 * **jobs:** A file system directory where a ``.vcsjob`` file can be found. The
    contents of the file will be checked for basic correctness. Especially the
    **path** attributes will be checked that they exist and are executable.
 * **tags:** A comma separated list of strings. If no tags are set, then all
    jobs listed by the ``.vcsjob`` file will be executed. White space is not
    allowed in the list of tags.
 * **env:** A comma separated list of strings. Each string is the name of an
    environment variable to white list. White listed variables are passed to
    each job. Other environment variables are not. The values of the white
    listed variables are reset between each executed job.

For instance, the following line executes jobs that have both the ``SMOKE`` and
``PERFORMANCE`` tags set::

    vcsjob execute -j some_path -t SMOKE,PERFORMANCE

Python Interface
----------------

Job API
+++++++

.. module:: vcsjob

.. function:: get_profiles()

    Returns the contents of the job's **profile** field as a dictionary.
    Raises an exception if no profiles have been set.

.. function:: get_log_path()

    Returns the path to a log file created by ``vcsjob`` on the job's behalf by
    redirecting prints from ``stdout`` and ``stderr``. See ``set_log_path()``.
    Raises an exception if no log path has been set.

.. data:: OK

    Test jobs should use exit codes defined in the ``vscjob`` module to tell
    their scheduler how the job faired. For instance::

        sys.exit(vcsjob.OK) # tell the scheduler that all test cases passed

    The following exit statuses are available to job writers:

    ========  ===================================================
    Code      Meaning
    ========  ===================================================
    OK        Everything went well. I.e. all tests passed.
    FAILURES  The job identified problems or test failures.
    ERROR     The job itself or the test cases it drives crashed.
    BUSY      The job failed to allocate necessary resources.
    BLOCKED   The job could not satisify other pre-conditions.
    ========  ===================================================

Scheduler API
+++++++++++++

.. module:: vcsjob

.. function:: fetch(src, dst, refspec, depth=1, timeout=600)

    All arguments mean exactly the same as their corresponding
    command line arguments, as documented for ``vcsjob fetch``.

    :depth: Create a shallow clone with a history truncated to the specified
            number of revisions.
    :timeout: timeout for fetching source code

.. function:: execute_tags(jobs_dir, job_tags, env_vars=None, log_path=None)

    Execute all jobs that match a set of tags. Jobs that do not have all tags
    will not be selected.

    :arg jobs_dir: The file system directory where a ``.vcsjob`` file can be
        found.

    :arg job_tags: A list of strings. A value of ``[]`` or ``None`` matches any
        tag.

    :arg env_vars: A list of strings. Each string is the name of an environment
        variable to white list. White listed variables are passed to each job.
        Other environment variables are not. The values of the white listed
        variables are reset between each executed job.

    :arg log_path: Treated as a file system path if set. Otherwise it will be
        set to ``stderr`` by ``vcsjob`` before starting a job. All terminal
        output created by the job will be written to the selected file.

.. function:: execute_job(jobs_dir, job_dict, env_vars=None, log_path=None, \
    guid=None)

    Execute a single job described by a dictionary of meta data.

    :arg jobs_dir: The file system directory where a ``.vcsjob`` file can be
        found.

    :arg job_dict: A dictionary with job meta data, containing at least the
        **path** and **tags** fields. There is no requirement that the job meta
        data matches any entry in the ``.vcsjob`` file, but the **path** field
        must point to an executable file within the same directory tree.

    :arg env_vars: A list of strings. Each string is the name of an environment
        variable to white list. White listed variables are passed to each job.
        Other environment variables are not. The values of the white listed
        variables are reset between each executed job.

    :arg log_path: Treated as a file system path if set. Otherwise it will be
        set to ``stderr`` by ``vcsjob`` before starting a job. All terminal
        output created by the job will be written to the selected file.

    :arg guid: A string that will be passed on by AVE to various external
        reporting systems so that entries in such systems can be correlated.
        It is the caller's responsibility to ensure that the value is unique
        within the global context that is relevant to the caller. Passing
        ``None`` disables propagation of the GUID.

.. function:: load_jobs(jobs_dir, job_tags)

    Load all jobs that match a set of tags. Jobs that do not have all tags will
    not be selected.

    :arg jobs_dir: The file system directory where a ``.vcsjob`` file can be
        found.

    :arg job_tags: A list of strings. A value of ``[]`` or ``None`` matches any
        tag.

    :returns: A list of dictionaries containing job meta data. The values are
        taken exactly as found in the ``.vcsjob`` file.

.. function:: exit_to_str(exit)

    Translate job exit codes into strings.

.. function:: set_log_path(path)

    ``vcsjob`` monitors everything a job writes to ``stdout`` and ``stderr``.
    When a log path is set by the scheduler, this content is redirected to a
    file. The job may access the contents of the file. See ``get_log_path()``.
