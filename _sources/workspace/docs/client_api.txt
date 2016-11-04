.. _workspace-client-api:

Client API
==========

Allocate workspaces through the broker, possibly with more attributes set in
the allocation profile. Note that any wanted external tool must be requested in
the allocation profile::

    from ave.broker import Broker

    broker = Broker()
    workspace = broker.get({'type':'workspace'})

The profile details are used by the broker to find a lab machine that supports
various lab features that may not be globally available. E.g. access to a WLAN
that implements a specific encryption standard. This is currently not used much
but the functionality is there. Contact the AVE governance board if you want to
make use of the feature.

Git
---

    .. method:: download_git(src, refspec, dst=None, timeout=0, depth=1)

        Synchronize a destination tree with a source tree, then check out the
        commit designated by 'refspec'. It is safe to use this method to
        repeatedly synchronize a source into the same destination, using
        different reference specifications each time.

        Execution details:
         * If *dst* is *None* or an empty directory: Clone the git, fetch (if
           needed) and check out the commit.
         * If 'dst' is a non-empty git tree: Fetch or pull the refspec (if
           needed), then check out the commit.

        :arg src: The source git. May be a local git tree or a remote git URL.
        :arg refspec: The refspec to check out. Must be a branch name or an SHA1
            commit id.
        :arg dst: The destination directory. May be an None, an empty or
            non-existing directory or a non-dirty git tree. If *None*,
            destination is ``git/<basename of src`` under the workspace base
            directory.
        :arg timeout: Seconds before time out.
        :depth: Create a shallow clone with a history truncated to the specified
            number of revisions.
        :returns: The destination path.
        :raises Timeout: If the call took longer than 'timeout' seconds.
        :raises Exception: If the destination tree is dirty or another error
            occured.

    .. method:: has_git(path, refspec)

        Check if the directory on 'path' is a git tree that has the commit
        specified by 'refspec'.

        .. Note:: The identity of the tree itself is not checked in any way
            (unless *refspec* is unique enough to establish the identity of the
            tree).

        :arg path: The path of the directory to check.
        :arg refspec: The refspec of interest.
        :returns: *True* or *False*.

    .. method:: delete_git(path)

        Delete a git tree.

        :arg path: The path to the git tree. Must be below the root directory
            of the workspace. May be relative or absolute.
        :raises Exception: If an error occured.

    .. method:: make_git(path)

        Create an empty git tree on 'path'. The directory will be created
        as needed. The directory must be located below the base directory
        of the workspace.

        :arg path: The path where the git is created.
        :returns: Full path to the created git.
        :raises Exception: If an error occured.


Jenkins
-------

    .. method:: download_jenkins(job_id, build_id=None, artifacts=None, \
         dst=None, timeout=0, base=None)

        Download artifacts from a Jenkins job into the workspace.

        :arg job_id: The Jenkins job ID to download from.
        :arg build_id: May be used to select a specific build. If None, the last
            successful build will be downloaded.
        :arg artifacts: May be used to select specific artifacts to download.
            If *None*, all found artifacts will be downloaded. Must be a list
            of strings or *None*.
        :arg dst: The download destination directory. If *None*, destination is
            <workspace path>/jenkins/<job_id>/<build_id>.
        :arg timeout: Seconds before time out.
        :arg base: May be used to specify the Jenkins URL. If None, the URL will
            be loaded from the workspace configuration file.
        :returns: The full destination path.
        :raises Timeout: If such occured.
        :raises Exception: On other errors.


Zip File
-------

    .. method:: validate_zip_file(filename,crc_check=False)

        Validates if zip file is corrupt or not.

        :arg filename: The zip file name.
        :crc_check:    Switch whether crc check shall be performed, Default to ``False``.

        :returns: True or False.

    .. method:: zip(path, dst=None)

        Creat a zip archive.

        :arg path: The dir or file used for zip. It can be a string path or a list of string path.
        :arg dst:  If set, zip archive name is dst, else creat a default automatically.

        :returns: Zip archive name path.

    .. method:: unzip(self, zip_file, path=None, pwd=None)

        Unzip a zipfile  to a dirrectory.

        :arg zip_file:  The name of zip file for unzip.
        :arg path: Path specifies a different directory to extract to.
        :arg pwd: Pwd is the password used for encrypted files.
        :returns: Unzip directory path.



Flocker
-------

    .. method:: flocker_push_file(src, dst=None, key=None)

        Upload a file to Flocker. An existing session may be targeted by setting
        `key`. This should only be used when uploading from multiple workspaces
        that are used from the same job.

        :arg src: Path to the file to upload. The path must point inside the
            root directory of the workspace.
        :arg dst: Path to use on the remote server. It may include forward
            slashes to create a directory hiearchy. If `dst` is not set, the
            basename of the uploaded file will be used.
        :arg key: A valid session key (a string). If not set, the key will be
            either generated automatically (to start a new session) or set to
            the key for a session that is already created for this workspace.
            Normally `key` is never set, unless the user has created multiple
            workspaces from the same job.
        :returns: A dictionary containing some metadata about the server-side
            session.

        .. Note:: The `key` field in the returned metadata may be used as the
            value of `key` in calls to *flocker_push_file()* and
            *flocker_push_string()*.

    .. method:: flocker_initial(existing_key=None, custom_key=None)

        :arg existing_key: A valid session key to reuse the session.
        :arg custom_key: A friendly name (a string). If this parameter is set,
            the session will hold the session key in the form of
            `<friendly-name>_<hash id>`.

        .. Note:: Users cannot set `existing_key` and `custom_key` at the
            same time.

    .. method:: flocker_push_string(string, dst, key=None)

        Upload a string to Flocker and store it in a file. An existing session
        may be targeted by setting `key`.

        :arg string: A message to store on the server.
        :arg dst: Path to use on the remote server. It may include forward
            slashes to create a directory hiearchy.
        :arg key: A valid session key (a string). If not set, the key will be
            either generated automatically (to start a new session) or set to
            the key for a session that is already created for this workspace.
            Normally `key` is never set, unless the user has created multiple
            workspaces from the same job.
        :returns: A dictionary containing some metadata about the server-side
            session.

        .. Note:: The `key` field in the returned metadata may be used as the
            value of `key` in calls to *flocker_push_file()* and
            *flocker_push_string()*.

    .. method:: flocker_set_metadata(key=None, contact=None, asset=None, \
        comment=None)

        Set extended metadata attributes on the server session.

        :arg key: A valid session key (a string). If not set, the key will be
            either generated automatically (to start a new session) or set to
            the key for a session that is already created for this workspace.
            Normally `key` is never set, unless the user has created multiple
            workspaces from the same job.
        :arg contact: A string containing contact information. E.g. an email
            address.
        :arg asset: A string containing a resource locator. E.g. a tag with
            context dependent semantics, a URL, or some other globally unique
            identifier.
        :arg comment: A free form message string.
        :returns: The updated session metadata.

        .. Note:: The `key` field in the returned metadata may be used as the
            value of `key` in calls to *flocker_push_file()* and
            *flocker_push_string()*.


Profiling
---------

    .. method:: convert_hprof(infile, outfile)

        Convert a HPROF file generated with Handset.dumpheap( native=False ) to
        a standard format so the file can viewed in a common profiling tool.
        This method uses hprof-conv.

        .. Note:: This is NOT applicable on native heaps.

        :arg infile: Full path to the file to convert.
        :arg outfile: Full path where the converted file will be saved.
        :raises Excpetion: If an error occured.


Temporary Files
---------------

    .. method:: make_tempdir()

        Create a directory with a randomized name within the workspace.

        :returns: The path to the created directory.

    .. method:: make_tempfile(path=None)

        Create a tempfile.

        :arg path: If path is set the tempfile will be created at path, else it
            will be created in the workspace root directory.
        :returns: The path to the created file.

    .. method:: write_tempfile(sequence, encoding='uft-8')

        Create a temp file in workspace and write a sequence of strings to it.
        The sequence can be any iterable object producing strings, typically a
        list of strings.

        :arg sequence: an iterable sequence of strings.
        :arg encoding: default encoding is utf-8

        :returns: The path to the created file.
        :raises Exception: If it was not possible to write the file.

    .. method:: promote(source_path, target, server='flocker')

        Promotes a file by making it traceable, this needs to be done
        to tmp-files that are generated by workspace.makefile() as they
        are not pushable to the handset. Traceability is secured by
        pushing the file to flocker and returning the metadata as well as
        making a symlink to the promoted file named as the target

        :arg source_path: full path to the source file.
        :arg target: path inside the ws to the target file.
        :arg server: server, optional, defaults to flocker.

        :returns: the result of the file storage operation.

File Manipulation
-----------------
Generic file manipulation and AVE's golden cage model do not mix easily. The
methods listed here are designed to satisfy specific needs that many test jobs
do have and that do not break the model. To request new methods, please send an
email to the AVE governance board or to SWD Tools SEMC.

    .. method:: get_checksum(path)

        Get checksum of the file.

        :arg path: The file to check.

        :returns: Checksum value of the file.
        :raises Exception: If it was not possible to get the checksum.

    .. method:: cat(path, encoding=None, errors=None)

        Get the content of the file.

        :arg path: The file to read.
        :arg encoding: name of unicode encoding,
            see python __builtin__.unicode for further information.
        :arg errors: specify encoding error handling for invalid characters,
            see python __builtin__.unicode for further information.
            Valid values::

                'strict', 'ignore', 'replace'

        :returns: the content of the file.
        :raises Exception: If it was not possible to read the file.

    .. method:: ls(path, globstr='*')

        Return a list of paths matching a pathname pattern.

        :arg path: String containing a path specification.
        :arg globstr: String containing a pattern with shell-style wildcards.
        :raises Excpetion: If an error occured.

    .. method:: path_exists(path, file_type=None)

        Check if path exists in workspace. Optional: check file type of path.

        :arg path: Path on handset to check.
        :arg file_type: If given, verify that the file type of path is
            file_type. Valid values::

                'symlink', 'directory', 'file'

        :returns: *True* if path exists (and file type is file_type, if that
            parameter was given), else False.
        :raises Exception: If an error occurs.


APK Inspection
--------------

    .. method:: get_package_name(path)

        Get the package name from the apk (using aapt).

        :arg path: The path to the apk.
        :returns: The package name.
        :raises Exception: If failed to get package name or an error occured.

    .. method:: get_apk_version(apk_path)

        Get the version code of the apk file.

        :arg apk_path: The apk file to check.

        :returns: Version code of the apk file.
        :raises Exception: If it was not possible to get the version code.


Miscellaneous
-------------

    .. method:: get_profile()

        Get the profile of the workspace. This dictionary should be used
        by test jobs to look up properties of the workspace.

    .. method:: get_path()

        Get the base directory of this workspace.

    .. method:: get_wifi_ssid()

        Get wifi ssid from workspace profile.

    .. method:: get_wifi_pw()

        Get wifi password from workspace profile.

    .. method:: delete()

        Delete the directory that holds the workspace's persistent storage.
        The workspace is no longer usable afterwards.

        :raises Exception: If an error occured.

External Tools
--------------
Workspaces can be used to call external tools. The list of tools that can be
called is controlled by a white-list which is configured by the lab owner.

The support for external tools is an explicit loophole to escapce AVE's golden
cage model. This is sometimes needed in special lab environments. Jobs that use
such exceptions will not run in DUST which does not white-list any extra tools.

    .. method:: has_tool(tool)

        Check whether the given tool is listed in the workspace's configuration.

        :arg tool: The tool of interest.
        :returns: *True* or *False*.

    .. method:: run(cmd, timeout=0)

        Run a command line tool on the host of the workspace.

        .. Note:: The tool must be listed in the workspace's configuration
            file (.ave/config/workspace.json).

        :arg cmd: The command line to execute. May be a string or a list of
            strings.
        :arg timeout: Seconds before a time out.
        :returns: A 3-tuple with: (exit code, output, '')

            .. Note:: error messages will end up in "output".

        :raises Timeout: If such occured.
        :raises Exception: If the tool is not available in this workspace,
            execution failed or another error occured.
