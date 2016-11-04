ADB Handset
===========

Although handset objects can be created explicitly, you should always allocate
handsets through the broker instead (possibly with more attributes set in the
allocation profile)::

    from ave.broker import Broker

    broker = Broker()
    handset = broker.get({'type':'handset', 'platform':'adb'})

The returned handset implements the API that is documented here.

.. Warning:: Many functions require super user privileges and will not work
    before a ``root()`` call has been made.

.. class:: ave.handset.adb_handset.AdbHandset(profile)

    Base class for handsets supporting the ADB protocol.

    :arg profile: A ``HandsetProfile`` instance that must contain at least
        the following members::

            {
                'type'    : 'handset',
                'platform': 'adb',
                'serial'  : 'xxx' # the serial number of the handset
            }

    :returns: An ``AndroidHandset`` instance.
    :arg profile: A dictionary containing at least the ``"type":"handset"`` and
        ``"platform":"adb"`` entries.

    .. method:: get_profile()

        Get the profile that the handset was allocated against. This method is
        intended for AVE internal usage and not recommended for regular users.
        This profile is not updated when the handset's state changes,
        e.g. rebooting does not affect this profile's power_state value.

        :returns: A dictionary.
    .. method:: get_workstation()

        Get the workstation to which the handset is connected.

        :returns: the handset's workstation name
        :raises Exception: If an error occurs.



Port Forwarding
---------------

    .. method:: open_forwarded_port(remote)

        Set up an ADB port forwarding rule.

        :arg remote: An ADB port forwarding expression. E.g. ``"tcp:2001"``
            would create a rule that forwards connections to TCP port 2001 on
            the handset. See ADB documentation for details.
        :returns: An identifying token that may be used as input to functions
            that manipulate or query the state of the forwarded port. The token
            is formatted as ``"tcp:<int>"`` where <int> is the randomized port
            number used on the PC to forward connections.

    .. method:: close_forwarded_port(entry)

        Tear down an ADB port forwarding rule.

        :arg entry: A token returned by ``open_forwarded_port()``.

    .. method:: list_forwarded_ports(all_adb=False)

        List all port forwarding rules.

        :arg all_adb: If set, return all forwarding rules for `all` handsets.
            Default behavior is to only list rules for the current handset.

Power States
------------

    .. method:: has_adb()

        Check if the handset is reachable via ``adb``.

        :returns: *True* or *False*.

    .. method:: boot_completed()

        Check if handset property sys.boot_completed has been set to "1".

        :returns: *True* or *False*.

    .. method:: get_power_state()

        Get the handset's current power state.

        Reachable power states::

            'offline',         # the handset is turned off or not connected
            'service',         # the handset is in service mode
            'enumeration',     # the handset's USB is set up and ready
            'adb',             # the handset is available via adb
            'boot_completed'   # the sys.boot_completed property is set to "1"

        :returns: The current power state.

    .. method:: wait_power_state(states, timeout=0)

        Wait for the handset to reach a desired power state.

        Reachable power states::

            'offline',         # the handset is turned off or not connected
            'service',         # the handset is in service mode
            'enumeration',     # the handset's USB is set up and ready
            'adb',             # the handset is available via adb
            'boot_completed'   # the sys.boot_completed property is set to "1"

        On a normal boot of a handset it will go through the power states in
        the following order::

            offline > enumeration > adb > boot_completed

        :arg states: A string or a list of strings, where the string(s) can be
            any of the reachable states listed above.
        :arg timeout:
            If timeout > 0, seconds before time out.
        :returns: The reached power state.
        :raises Exception: If an error occurs.

    .. method:: reboot(timeout=30)

        Reboot the handset.

        :arg timeout: Number of seconds to wait for the handset to go offline.
        :raises Timeout: If such occurs.
        :raises Exception: If an error occurs.

ADB Intrinsics
--------------

    .. method:: root()

        Restart ``adbd`` as root.

        The call will block until the device is available again.
        :raises Exception: If an error occurs.

    .. method:: remount()

        Remount the handset's system partition as writable.

        :returns: The output of the remount command.
        :raises Exception: If an error occurs.

File System Functionality
-------------------------

    .. method:: ls(path)

        List files in path on handset.

        :args path: The path to list files in.
        :returns: A list of files.
        :raises Exception: If an error occurs.

    .. method:: cat(target)

        Get the content of the file *target*.

        :arg target: The file to read.
        :returns: The content of the target file as a string.
        :raises Exception: If an error occurs.

    .. method:: rm(target, recursive=False)

        Remove file or directory from the handset.

        :arg target: The file or directory to remove.
        :arg recursive: If *True* files will be removed recursively, else not.
        :raises Exception: If an error occurs.

    .. method:: mv(src, dst)

        Move file(s) on the handset.

        :arg src: Source path.
        :arg dst: Destination path.
        :raises Exception: If an error occurs.

    .. method:: mkdir(target, parents=False)

        Create directory on handset.

        :arg target: The directory to create.
        :arg parents: If True create parent directories as needed and don't
            raise an exception if target already exists.
        :raises Exception: If an error occurs or the directory already exists.

    .. method:: chmod(permissions, target)

        Change permissions of a file on the handset.

        :arg permissions: Permissions to set on the file (e.g. "777").
        :arg target: The file to change permissions on.
        :raises Exception: If an error occurs.

    .. method:: path_exists(path, file_type=None)

        Check if path exists on handset. Optional: check file type of path.

        :arg path: Path on handset to check.
        :arg file_type: If given, verify that the file type of path is
            file_type. Valid values::

                'symlink', 'directory', 'file', 'executable'

        :returns: *True* if path exists (and file type is file_type, if that
            parameter was given), else False.
        :raises Exception: If an error occurs.

    .. method:: push(src, dst, timeout=0)

        Push file to the handset via adb.if the pushed source filename starts
        with 'tmp' then the method raises an exception: temp-files generated
        by the workspace are not possible to track after the test execution
        and thus the possibility to push these files to the handset has been
        restricted. In order to push a generated file, it must first be
        secured that the file can be resurrected during post mortem analysis.
        AVE offers two ways to do this: Either during write_tempfile() or
        with the specific workspace method promote(). Please refer to the
        API description for details.

        :arg src: The path on host to the source file.
        :arg dst: The destination on the handset.
        :arg timeout: Seconds before time out.
        :returns: The execution output.
        :raises Timeout: If such occurs.
        :raises Exception: If other error occurs.

    .. method:: pull(src, dst, timeout=0)

        Pull file from the handset via adb.

        :arg src: The source file(s) on the handset (wildcards allowed).
        :arg dst: The local destination path.
        :arg timeout: Seconds before time out.
        :returns: The execution output.
        :raises Timeout: If such occurs.
        :raises Exception: On other errors.

    .. method:: take_screenshot(dst, timeout=20)

        Take screenshot of the device via adb.

        :arg dst: The destination file of screenshot.
        :arg timeout: Seconds before time out.
        :returns: The execution output.
        :raises Timeout: If such occurs.
        :raises Exception: On other errors.

    .. method:: is_mounted(mount_point)

        Check if mount_point is mounted.

        :arg mount_point: Mount point as a string.
        :returns: *True* if mount_point is mounted, else *False*.
        :raises Exception: If an error occurs.

    .. method:: wait_mounted(sdcard, ext_card, timeout=30)

        Wait until sdcard and/or ext_card is mounted.

        :arg sdcard: If *True* wait for sdcard to be mounted.
        :arg ext_card: If *True* wait for ext_card to be mounted.
        :arg timeout: Seconds before time out.
        :raises Timeout: If such occured.

    .. method:: wait_for_path(path, file_type=None, timeout=0)

        Wait until path exists on handset. Optional: check file type of path.

        :arg path: Path on handset to check.
        :arg file_type: If given, verify that the file type of path is
            file_type. Valid values::

                'symlink', 'directory', 'file', 'executable'
        :arg timeout:
            If timeout > 0, seconds before time out.

        :raises Exception: If an error occurs.

Processes
---------

    .. method:: shell(args, timeout=0, bg=False)

        Execute an adb shell command.

        :arg args: A list or a string of arguments to be executed by adb shell
        :arg timeout: Timeout for the command. No timeout is set by default.
        :arg bg: specify the running mode, if True, run the command in background
        :returns: if the cmd run in background the return values are the new process
            id and the file descriptor of the new process's pseudoterminal,
            else is the Output from execution.
        :raises Timeout: If such occured.
        :raises Exception: On other errors.

        .. Note:: Detection of failure is hard with ADB because the exit code
            for an execution is not returned to the test host. ``shell()`` only
            checks for known error indications on stdout.

    .. method:: kill_background_cmd(pid, fd)

        Kill the cmd process now is running in background

        :arg pid: The id of the background process
        :arg fd: The file descriptor of the process's pseudoterminal
        :raises OSError: If cannot close fd
        :raises Exception: On other errors

    .. method:: ps(name=None, exact=False)

        Get all current procceses' id and name.

        :arg name: If given only return processes with matching name.
        :arg exact: If *True* only return processes with exact matching name.
        :returns: A list with dicts, e.g [{'pid':123,'name':'pid_name'},..]
        :raises Exception: If an error occurs.

Properties
----------

    .. method:: set_property(key, value)

        Set property and verify value.

        :arg key: The property name.
        :arg value: The new property value as a string.
        :raises Exception: If property was not set successfully.

    .. method:: get_property(key)

        Get the value of the given property.

        :arg key: The property name.
        :returns: The property's value.
        :raises Exception: If no value was found or an error occured.

    .. method:: get_product_name()

        Get the product name of the handset.

        :returns: The product name of the handset, or empty string if product
            name wasn't found.
        :raises Exception: If an error occurs.

    .. method:: get_build_label()

        Get the build label of the software on the handset.

        :returns: The build label of the software on the handset.
        :raises Exception: If the build label was not fetched successfully.

    .. method:: clear_property(key)

        Clear the value for the given property.

        :arg key: The property name.
        :raises Exception: If failed to clear property or an error occured.


   .. method:: get_sdk_version()

       Get the SDK version of the running platform.

       :returns: An integer denoting the version. E.g. ``23`` for Android M


Crash Handling
--------------

    .. method:: run_bugreport(directory)

        Execute 'bugreport' on handset. Create a file with the bugreport output
        in the given directory on the handset and return the file's full path.

        :arg directory: An existing directory on the handset where the file will
            be written.
        :returns: The full path on the handset to the created file.
        :raises Exception: If an error occurs.

    .. method:: force_dump(timeout=0)

        Force the handset to dump.

        :arg timeout: Secods before time out.
        :raises Timeout: If such occured.
        :raises Exception: On other errors.


    .. method::: disable_dm_verity(timeout=300, reboot=False)

        disable dm-verity checking on USERDEBUG builds

        :arg timeout: seconds waits for system reboot completed
        :arg reboot: whether reboot system or not after disable dm-verity
        :raises Exception: If an error occurs.

    .. method::: enable_dm_verity(timeout=300, reboot=False)

        re-enable dm-verity checking on USERDEBUG builds

        :arg timeout: seconds waits for system reboot completed
        :arg reboot: whether reboot system or not after enable dm-verity
        :raises Exception: If an error occurs.
