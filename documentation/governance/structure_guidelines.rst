Structural Guidelines
=====================

All AVE packages follow a certain pattern for internal structure. This structure
is designed to meet a couple of goals:

 * The git tree is created in a way that enables enforcement of governance
   rules (such as these).
 * The package can be tested "locally" without performing a system installation.
   Used for development and debugging purposes.
 * The package can be acceptance tested against a system installation.
 * Source code, executables, OS integration files and documentation have
   separate base directories. The root directory contains no such material.
 * The module can create its own Debian package in the most straight forward
   way possible.
 * Documentation can be built with Sphinx by linking it into the build system
   inside the ave/documentation git.

In the following sections, an imaginary package ``ave-washer`` is described. It
contains equipment support, system services, OS integration support and Python
modules. It also contains the support library ``libdetergent`` written in C.

Git Tree
--------
When the git tree is requested on the SOMC CM web, its properties should follow
this pattern. Substitute "washer" for a real package name:

 * **Feature Name:** "AVE Washer"
 * **Team Name:** "AVE Governance Board"
 * **Repository List:** "semctools/ave/washer"
 * **Initial Commit:** Yes
 * **Verification:** Restricted
 * **Verification Group:** "SG-WW-AVE Committers-G"
 * **Decoupling:** No

When the tree has been created, its root directory should be populated with the
following items (again, substitute "washer" for a real package name)::

    .gitignore
    .vcsjob
    bin/
    docs/
    etc/
    jobs/tests/
    mkdeb
    packaging/DEBIAN/
    src/ave/washer/
    src/libdetergent/

Packages that do not need special OS integration, CLI tooling or native code can
skip one or more of the ``bin``, ``etc`` and ``src/lib*`` directories. The
rest are mandatory and must be given proper content.

``.gitignore``
--------------
The file ``.gitignore`` should contain at least the following lines::

    *~
    packaging/etc
    packaging/usr
    *.pyc
    *.deb

This causes git to skip editor temp files, Python byte code, the generated
Debian package and staging files generated during the Debian package creation.
Add rules as necessary to skip artifacts from the native build steps for support
libraries.

.. Note:: AVE packages do not ship settings files for IDE's. The ``.vcsjob``
    file should contain rules to skip such files if they cannot easily be kept
    in a different location (e.g. under the user's home directory).

``.vcsjob``
-----------
The file ``.vcsjob`` should contain references to executable files found in the
``jobs/`` directory. Acceptance tests must be tagged ``"ACCEPTANCE"``. Other
tags should be written in lower case. Example::

    {
      "executables": [
        { "path": "jobs/washer_accept",    "tags":["washer", "ACCEPTANCE"] },
        { "path": "jobs/detergent_accept", "tags":["detergent", "ACCEPTANCE"] },
        { "path": "jobs/debug_something",  "tags":["foo", "bar", "debug"] }
      ]
    }

``bin/``
--------
Put executable code in this directory. Typically these are CLI tools that go
with the package and are used by lab owners to manage the lab. The directory
may also contain external dependencies that are not found in the Ubuntu Linux
repository. E.g. ``ave-handset`` needs the Android development tool ``aapt``
which is not available through ``apt-get``.

Homegrown tools written in Python should be as small as possible and import as
much functionality as possible from the package. For the washer example::

    #! /usr/bin/python2

    import ave.washer

    # do command line option parsing, then call functions in the ave.washer
    # package.

.. Note:: The version of the Python interpreter is important. The hashbang in
    all AVE Python executables must specify the version 2 series to avoid
    accidental use of Python 3.

The tool itself must be named after the package. If the package implements a
service (as in this example), the tool must accept at least four standard
arguments, one option, and be able to print a simple CLI syntax helper::

    Syntax: ave-washer <action> [options]

    Actions:
        --help      Display this message
        --start     Start the washer
        --restart   Restart the washer
        --stop      Stop the washer

    Options:
        --force     Combine with --start to ignore existing PID file

The ``--force`` option is used for integration with Upstart and other
``init`` systems.

PID and Log Files
-----------------
Packages that implement services that can be started on the command line must
store PID and log files in world readable files under ``/var/tmp``:

 * ``/var/tmp/ave-washer.pid``: Content must be parsable with this Python code:
    ``with open('/var/tmp/ave-washer.pid') as f: pid = int(f.read())``
 * ``/var/tmp/ave-washer.log``: Plain text logs produced by the service. The
    content does *not* have to be easy to parse. (Use Panotti for structured
    logging.)

``etc/``
--------
Some OS integration files go here. The package is not allowed to store its own
configuration files under ``/etc`` on the host (use ``.ave/config`` for that)
but may need to ship files that are read by Upstart or udev:

    * ``etc/init/ave-washer.conf``: Config file for Upstart integration.
    * ``etc/udev/rules.d/10-washer.rules``: Config file for udev handling.

The Upstart configuration should look like this unless there are special
circumstances that require different handling::

    description "ave-washer"

    start on (filesystem and net-device-up IFACE!=lo)

    console output
    expect daemon

    exec /usr/bin/ave-washer --start --force

The udev configuration should at least set permissions so that the user
does not need special privileges to open device nodes. These examples are taken
from Android and the Devantech relay.

Tell udev that USB equipment with vendor ID 0bb4 can be read and written
to by anyone::

    SUBSYSTEM=="usb", ATTR{idVendor}=="0bb4", MODE="0666"

Tell udev that 8 virtual serial ports are world readable and writable::

    KERNEL=="ttyACM[0-7]*" MODE="0666"

``jobs/``
---------
This directory must contain all executables referenced from ``.vcsjob``. It must
also contain ``runners.py`` that imports test cases found in ``jobs/tests``.

A test job that supports development and debugging should normally follow the
pattern below. The example causes python to prefer the source code found in the
git over the source code found in the system installation. It then runs the
tests against the Washer's configuration handling::

    #! /usr/bin/python2

    import os
    import sys

    if __name__ == '__main__':
        path = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(path, 'src')
        sys.path.insert(0, path)

        import runners
        runners.all_config(debug=True, report=False)

.. Note:: It is important to perform path manipulation before importing the
    ``runners`` module. A bug in Python makes path manipulation unreliable
    within the module that performed the path manipulation. Always perform path
    manipulation before importing a module that relies on manipulated paths
    (like in this example).

A test job that implements acceptance tests must use the system installation of
the package::

    #! /usr/bin/python2

    if __name__ == '__main__':
        import runners
        runners.all_config(debug=False, report=True)



The ``jobs/runners.py`` file should look something like this:

.. code-block:: python

    # Copyright (C) 2014 Sony Mobile Communications AB.
    # All rights, including trade secret rights, reserved.

    import sys
    import traceback
    import vcsjob

    import tests.config

    def all_config(debug, report):
        args = ()
        try:
            result = run_suite([(tests.config, args)], report)
            if result = True:
                code = vcsjob.OK
            else:
                code = vcsjob.FAILURES
        except Exception, e:
            traceback.print_exc()
            code = vcsjob.ERRORS
        sys.exit(code)

The ``run_suite`` function is boiler plate code that can be found in e.g. the
``ave/workspace`` git.

``jobs/tests/``
---------------
This directory must contain all test cases for the package. For a package that
implements a service, the tests should at a minimum cover

 * Configuration
 * Service start/stop/restart
 * Broker integration (if the module implements an equipment class)
 * Functional tests against user exposed API's
 * Lister tests (if the module implements an equipment lister)

Tests against command line tools found under ``bin/`` are not needed if that
code has been minimized properly so that API tests are sufficient.

Test cases must print the full path of the file they are implemented in together
with the name of the test case. The full path combined with the test name is
called the "pretty" identity in all AVE self tests::

    /home/CORPUSERS/23060224/ave/washer/jobs/tests/config.py t01
    /home/CORPUSERS/23060224/ave/washer/jobs/tests/config.py t02
    /home/CORPUSERS/23060224/ave/washer/jobs/tests/config.py t03
    /home/CORPUSERS/23060224/ave/washer/jobs/tests/config.py t04
                                                             ...

Failing tests must print ``pretty`` together with an explanation::

    message = 'something fairly specific went wrong'
    print('FAIL %s: %s' % (pretty, message))
    return False

Test cases that pass should avoid printing any messages unless the execution is
so long that the test may otherwise appear to be stalled. Test cases that pass
must return ``True``.

.. Note:: Test cases should be as short as possible and prefer various forms of
    duplication between test cases over having fewer tests with less overhead.
    It is important that the test's source code is easy to follow. Test cases
    provide example usage of AVE and should be thought of as documentation.

``packaging/``
--------------
The packagin directory is used as a staging are to create the package's Debian
package. ``mkdeb`` will populate it with directory structures that match the
system installation. E.g. content created in ``packaging/usr`` will be installed
to ``/usr`` when the Debian package is installed.

This structure is chosen because it is required to make the OS tool ``dpkg-deb``
handle package creation correctly. ``dpkg-deb`` takes a directory as argument
(the ``packaging/`` directory in all AVE packages) and expects to find the
subdirectory ``DEBIAN/`` with configuration files in it. All other content in
the directory will be copied into the Debian package by ``dpkg-deb``.

.. Note:: Make sure all content under ``packaging/`` *except* the
    ``packaging/DEBIAN/`` directory and its contents are lister in
    ``.gitignore``.

``packaging/DEBIAN/control``
----------------------------
This file contains Debian configuration management meta data for the package.
The ``ave-washer`` package contains native code (``Architecture: amd64``) and
uses ``udev`` for device discovery. It also needs Python (because the package
is mostly implemented in Python) and ``ave-common`` (to be able to read from
``.ave/config``).

It should look something like this::

    Package:      ave-washer
    Version:      1
    Architecture: amd64
    Depends:      udev (>=151)
    Pre-Depends:  python (>=2.6.5), ave-common (>=73)
    Maintainer:   Klas Lindberg <klas.lindberg@sonymobile.com>
    Description:  AVE support for the Washer equipment

Packages without native code content should set ``Archtecture`` to ``all``.

.. Note:: The ``Pre-Depends`` field forces ``apt-get`` and ``dpkg`` to
    completely install such packages before attempting to install the current
    package. This makes it possible for the current package to import e.g. the
    AVE common modules in its ``postinst`` script. Without ``Pre-Depends``
    APT is allowed to install the dependencies *and* the current package in
    parallel, which would cause the ``postinst`` script for the current package
    to fail if it needs to import modules from the dependencies. Python itself
    is pre-depended to let us write the ``postinst`` script in Python instead
    of Sh.

``packaging/DEBIAN/postinst``
-----------------------------
``dpkg`` executes ``postinst`` at the end of the installation of the package,
with some command line options to tell the script what is going on. This is
normally used to perform detailed configuration that would be difficult to do
in any other context. E.g. to set file permissions, add special entries to
system data bases and so on.

What is needed in the ``postinst`` script? Some guidelines:

 * Packages that simply contain new Python modules do not need a ``postinst``
   script at all.
 * Packages that contain services must typically restart those. Otherwise the
   service continues to execute with the old content (already loaded in RAM by
   Python).
 * Packages that contain native code content *may* choose to build this during
   installation. This is not recommended but is necessary if the OS dependencies
   are "too different" between different versions of Ubuntu. Dependencies are
   "too different" if the package cannot be built one version of Ubuntu and then
   used on the other. Fortunately this is rare.
 * Packages that contain kernel drivers must build these. Kernel drivers cannot
   be built once and for all and then shipped in the package because the kernel
   does not provide a stable internal API.

.. Note:: Packages that depend on non-standard kernel drivers are no longer
    accepted into the default AVE distribution due to the difficulties with
    building the drivers during package installation. If you experiment with
    equipment that needs such drivers, contact the AVE governance board for
    assistance.

.. Note:: Packages that must build native code content during installation must
    look for source code and build systems under ``/usr/share/ave/<package>``,
    and also add a pass in the package's ``mkdeb`` to copy the needed material
    to this location.

The ``ave-washer`` package implements a service but has no native code content
that must be built during installation. Its ``postinst`` would look like this:

.. code-block:: python

    #! /usr/bin/python2

    # Copyright (C) 2014 Sony Mobile Communications AB.
    # All rights, including trade secret rights, reserved.

    import os
    import sys
    import errno
    import shutil

    import ave.cmd

    def is_running():
        from ave.washer.daemon import PID_PATH
        return os.path.exists(PID_PATH)

    def main():
        if len(sys.argv) > 1:
            if sys.argv[1] in ['configure']:

                # start or restart the service
                if is_running():
                    ave.cmd.run('/usr/bin/ave-washer --restart')
                else:
                    ave.cmd.run('/usr/bin/ave-washer --start')

        return 0

    if __name__ == '__main__':
        sys.exit(main())

To see an example of a most complicated package, download the
``semctools/ave/quancom`` git tree.

``src/ave/__init__.py``
-----------------------
The ``src/ave/`` directory should contain a single ``__init__.py`` file with
specially crafted content. All other content should be stored in a subdirectory
called after the package. Here is the content of ``__init__.py``:

.. code-block:: python

    import pkg_resources
    import modulefinder

    # Copyright (C) 2014 Sony Mobile Communications AB.
    # All rights, including trade secret rights, reserved.

    pkg_resources.declare_namespace(__name__)
    for p in __path__:
         modulefinder.AddPackagePath(__name__, p)

.. Note:: Make sure this file is *not* copied to the ``packaging/`` staging
    area by ``mkdeb``. It is only useful to have in the git tree.

What is going on here? The ``ave`` Python package is implemented in several
git trees that are installed to a common directory structure in ``/usr``. At
runtime, as soon as the imported package ``ave.`` is found, Python will stop
looking for this name space in other locations. So all content has to be found
under ``/usr``, or all content has to be found in the user's local directory
structure. To be able to mix, Python has to be told to handle name spaces a bit
different: Add the locally declared namespace but with all known paths attached
so that not only the local path will be searched for *all* ``ave.`` content.

Consider again the "local" test jobs do for development and debugging purposes
from the ``jobs/`` section above:

.. code-block:: python

    path = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(path, 'src')
    sys.path.insert(0, path)
    import runners
    runners.all_config(debug=True, report=False)

If the local ``src/ave/`` directory contains an ordinary (empty) ``__init__.py``
file, then after ``sys.path.insert(0, path)``, Python will no longer look for
content under ``/usr/lib/`` in the system installation. This makes it impossible
to import other AVE modules in the local test job.

.. Note:: Because all AVE packages follow this convention, a debugging test job
    can import the source tree for any AVE package that the user has a local
    copy of. Just add more calls to ``sys.path.insert()`` before importing the
    ``runners`` module.

``src/ave/washer/``
-------------------
This directory contains an empty ``__init__.py`` file and the implementation of
all ``ave.washer`` modules.

``src/libdetergent/``
---------------------
Native code libraries should be buildable in isolation, using only a private
build system that can be called without changing the current working directory::

    make -C src/libdetergent clean
    make -C src/libdetergent libdetergent.so

The resulting object file must be callable by the Python ``ctypes`` module.
There are two choices for libraries that do not implement the C ABI of the host
platform:

 * Do not use it.
 * Write a tool that uses it and distribute it separately through SWEREPO. Then
   set a Debian dependency from AVE to that package and use the ``ave.cmd``
   module to interface with the tool.

For instance, the second rule applies to re-use of most libraries written in
Java. There is no clean and simple way to call Java functions from Python. (The
library owner may of course make the extra effort to implement a C ABI through
JNI to make it callable from any C program, including Python.)

Use ``gmake`` as build system for native code libraries if you have a choice.
The build system must not use OS features that require the use of ``sudo``.

Let's assume that ``libdetergent`` implements a single function with the
following C prototype:

.. code-block:: c

    /* mix an array with 'size' integers and log a message */
    int detergent_mix(int size, int * array, char * message);

To call this from ``ave.washer.detergent``, use ``ctypes``:

.. code-block:: python

    # Copyright (C) 2014 Sony Mobile Communications AB.
    # All rights, including trade secret rights, reserved.

    from ctypes import * # CDLL(), c_int, c_char_p, POINTER(), etc

    class Detergent(object):
        c_library = None

        def __init__(self, so_path=None):
            # default to the system installation unless the caller selected
            # another version (used from test jobs for the Detergent class).
            if not so_path:
                so_path = 'libdetergent.so'
            self.c_library = self.load_so(so_path)

        def load_so(self, so_path):
            c_library = CDLL(so_path, use_errno=True)
            # declare the function prototype of mix() so that Python can take
            # care of most of the value conversions for us.
            self.mix             = c_library.detergent_mix
            self.mix.argtypes    = [c_int, POINTER(c_int), c_char_p]
            self.mix.restype     = c_int
            return c_library

        def do_something(self, integers*, message):
            Cls = c_int * len(integers) # create a class for the integer array
            buf = Cls(*integers)        # create a C compatible array
            err = self.mix(len(integers), buf, message)
            if err != 0:
                raise Exception('could not mix: %d' % get_errno)

``mkdeb``
---------
The job of ``mkdeb`` is to collect material for inclusion in a Debian package
that makes the AVE module installable. Each AVE package is a bit different but
most implement at least some of the following steps:

 * Clean out old staging material in ``packaging/``.
 * Copy Upstart integration files to ``packaging/etc/init/``.
 * Copy udev rules to ``packaging/etc/udev/rules.d/``.
 * Copy executables to ``packaging/usr/bin/``.
 * Copy Python modules to ``packaging/usr/lib/pymodules/python2.6/ave/``
 * Copy Python modules to ``packaging/usr/lib/pymodules/python2.7/ave/``
 * Build native code libraries.
 * Copy native code libraries to ``packaging/usr/lib/``.
 * Copy sources for kernel drivers to ``packaging/usr/share/ave/``.
 * Extract the package version from ``packaging/DEBIAN/control``.
 * Generate the Debian package and name it after the AVE package and the version
   number.

Because this all this is just boiler plate code that can be found in any AVE git
tree, no full example is given here. The ``semctools/ave/quancom`` git uses all
of the steps.

.. Note:: ``mkdeb`` must take care to replace the "specially crafted"
    ``__init__.py`` files with empty ones. See ``src/ave/__init__.py`` above.

.. Note:: Unlike all other Python code in AVE, the ``mkdeb`` scripts are not
    allowed to import AVE modules. (One should not have to install AVE to be
    able to build it's Debian packages.) Because of this, ``mkdeb`` executes
    external programs with ``subprocess.Popen()`` instead of ``ave.cmd.run()``.

``docs/``
---------
The contents of this directory is not included in the Debian package. Instead
it is made to integrate with the User's Guide project in the
``semctools/ave/documentation`` git. The guide is published separately on
http://ave.sonyericsson.net.

Documentation is written in reStructuredText (http://sphinx-doc.org/rest.html).
AVE packages must at least contain an API guide for users of AVE. Preferably it
should also include a technical overview and some examples of correct usage.

Although it is possible to extract Python documentation strings from souce code,
it is recommended to *not* do so. Automatically generated API documentation has
a number of drawbacks:

 * It is not possible to mix discussion with strict API documentation.
 * Decorators used on the API "take over" the generated document.
 * The writer cannot hide function parameters that users should not use.
 * The writer has no control over the layout. Functions will be sorted after
   their names instead of what may be best from a presentation standpoint.

Instead the writer should put all API documentation in ``docs/api.rst`` (or a
collection of files if the material is big enough to warrant a split). To build
the documentation, follow these steps:

 * Download the ``semctools/ave/documentation`` git so that ``documentation``
   and ``washer`` are found in the same directory.
 * Create a symbolic link from ``documentation/users_guide/washer`` to
   ``../../washer``.
 * Edit the ``html`` target of ``documentation/users_guide/Makefile`` to target
   ``washer``. E.g:

    .. code-block:: make

        html:
        	sphinx-apidoc -f -o source washer
        	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
        	@echo
        	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

 * Edit ``documentation/users_guide/index.rst``: Include ``washer/docs/api.rst``
   in the Contents listing.
 * Build: ``make -C documentation/users_guide html``.
 * Open ``documentation/users_guide/_build/html/index.html`` in a web browser
   and check that the new material is included and looks alright.

.. Note:: Consider it a **TODO** item to improve on the user's guide build
    system to require fewer of the steps listed above.
