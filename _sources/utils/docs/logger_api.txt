Logging
=======

Logger classes used to generate structured logs in Flocker

``Logger``
----------

.. class:: ave.utils.logger_api.Logger(workspace, guid,\
        file_path='test_job_log.txt', lowest_level='x')

    Handles all logging, pushes logs to Flocker and shouts Flocker links to
    Panotti, using the scheduler GUID as label.

    :arg workspace: Workspace that is used to push strings to Flocker.
    :arg guid: The global unique identifier that is used to set a label on the
        Flocker URL when it is uploaded to Panotti.
    :arg file_path: Name of the log file. Defaults to *'test_job_log.txt'*.
    :arg lowest_level: Sets the lowest level of log messages that should be
        added to log. Defaults to *'x'* - unknown.

    .. function:: set_lowest_log_level(lvl)

        Sets the lowest log level that should be added to log.

        :arg lvl: Sets the lowest level of log messages that should be added to
            the log.

    .. function:: log_traceback(lvl)

        Retrieves a stack trace and prints it to log.

        :arg lvl: Sets the level of the log entry.

    .. function:: log_it(lvl, message, handset=None)

        Logs the message with a time stamp, a level descriptor and a color code.

        :arg lvl: Sets the level of the log entry.
        :arg message: The message to log.
        :arg handset: Print the handset's serial (Optional)
        :returns: The return parameter from ``Workspace.flocker_push_string()``.

    .. function:: parse_flocker_data(flocker_return)

        Parses the flocker return value to a URL.

        :arg flocker_return: The return value from
            ``Workspace.flocker_push_string()``.
        :returns: A tuple: The Flocker URL and the Flocker session key.

``LogLevel``
------------

Used by ``Logger`` to colorize strings and retrieving name and numeric value
from a log level.

The different log levels::

    'Level'         'Name'          'Numeric value'     'Color'
    'd'             'DEBUG'         '10'                'White'
    'i'             'INFO'          '20'                'Blue'
    'w'             'WARNING'       '30'                'Yellow'
    'e'             'ERROR'         '40'                'Red'
    'x'             'UNKNOWN'       '0'                 'Purple'

.. function:: ave.utils.logger.LogLevel.colorize_string(level, string)

    :arg level: The level to set color.
    :arg string: The string to colorize.
    :returns: The colorized string.

.. function:: ave.utils.logger.LogLevel.get_level_numeric(level)

    :arg level: The level to get the numeric value for.
    :returns: The numeric value of the log level.

.. function:: ave.utils.logger.LogLevel.get_level_name(level)

    :arg level: The level to get the name for.
    :returns: The name of the log level.

.. function:: ave.utils.logger.LogLevel.verify_level(level)

    :arg level: The level to verify
    :returns: The level if it is an ok level
    :raises: Exception if the level supplied is not an ok level








