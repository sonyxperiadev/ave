Gerrit
======

Functions and classes to manipulate Gerrit changes and subscribe to events.

**Configuration files**

 * ``<home>/.ave/config/gerrit.json``: A dictionary with site specific
   config details. Example::

        {
            "host": "review.sonyericsson.net",
            "port":  29418,
            "user": "john.doe"
        }

 * ``<home>/.ssh``: SSH configuration files, where ``<home>`` is read
   from ``/etc/ave/user``. Used to implement password-free login.

The value of ``<home>`` is read from ``/etc/ave/user``.

ave.gerrit.review
-----------------

.. method:: ave.gerrit.review.quote_message(message)

    Escape any ``"`` and ``\`` characters in *message*. Unescaped strings
    interfere with SSH command line parameter handling (Gerrit API's are only
    accessible over SSH). Also put quotes around the contents in *message*
    before returning the modified string.

    :arg message: A free form, human readable message.
    :returns: The quoted version of *message*.


.. method:: ave.gerrit.review.indent_message(message, indent=1)

    Split *message* into lines and add *indent* whitespace characters at the
    head of each line. This will cause Gerrit to render the paragraph in code
    listing style.

    :arg message: A free form, human readable message.
    :arg indent: The number of whitespace characters to add at the start of each
        line of *message*.
    :returns: The indented version of *message*.

.. method:: ave.gerrit.review.set_labels(project, change, patchset, labels,\
     message=None)

    Set scores on one or more labels for a change in Gerrit.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg labels: A dictionary representing the labels to be scored, in the
        form ``{"label-name": value }`` where ``"label-name"`` is a string
        and ``value`` is an integer.
    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

.. method:: ave.gerrit.review.set_label(project, change, patchset, label,\
     score, message=None)

    Set the score on a label for a change in Gerrit.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg label: A string representing the label to be scored.
    :arg score: An integer in the range expected by Gerrit for ``label``.
    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

.. method:: ave.gerrit.review.set_verified(project, change, patchset, value,\
     message=None)

    Set the verified status for a change in Gerrit.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg value: An integer in the range [-1..1].

        * -1 : Verification failed.
        * 0 : No score.
        * 1 : Verification OK.

    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

.. method:: ave.gerrit.review.set_code_review(project, change, patchset, value,\
     message=None)

    Set the code review status for a change in Gerrit.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg value: An integer in the range [-2..2].

        * -2 : Do not submit.
        * -1 : I would prefer that you did not submit this.
        * 0 : No score.
        * 1 : Looks good to me, but someone else must approve.
        * 2 : Approved.

    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

.. method:: ave.gerrit.review.set_qualified(project, change, patchset, value,\
     message=None)

    Set the qualified status for a change in Gerrit.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg value: An integer in the range [-2..2].

        * -1 : Qualification failed.
        * 0 : No score.
        * 1 : Qualified.

    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

.. method:: ave.gerrit.review.set_comment(project, change, patchset, message)

    Make a comment in a Gerrit project.

    :arg project: A string holding the project identity. E.g.
        ``"ave/gerrit"``.
    :arg change: A character string holding the change number. I.e.
        the ``"456785"`` part of the following git refspec:
        ``"refs/changes/85/456785/2"``.
    :arg patchset: A string holding the patchset number. I.e. the final ``"2"``
        part of the following git refspec: ``"refs/changes/85/456785/2"``.
    :arg message: A free form text message. Gerrit comment formatting rules
        apply.

        Use ``ave.gerrit.review.quote_message()`` before ``set_comment()`` to
        secure that the comment does not contain unescaped ``"`` characters.

        Use ``ave.gerrit.review.indent_message()`` before ``set_comment()`` to
        make sure Gerrit formats the message in fixed width style. E.g. as code
        listing.
    :raises Exception: If validation of parameters failed.
    :raises RunError: If communication with Gerrit failed.

ave.gerrit.config
-----------------

.. method:: ave.gerrit.config.load(home)

    Load the configuration file that contains Gerrit access details.

    :arg home: Path to a directory that contains the ``.ave/config/gerrit.json``
        file.
    :returns: A JSON compatible dictionary.
    :raises Exception: If there is a problem with loading or parsing the file.

.. method:: ave.gerrit.config.validate(config)

    Validate the contents of a configuration dictionary. E.g. the return value
    from ``ave.gerrit.config.load()``.

    :arg config: A dictionary that is expected to contain *host*, *port* and
        *user* fields.
    :raises Exception: If the configuration does not validate.

ave.gerrit.events
-----------------

.. class:: ave.gerrit.events.GerritEventStream(host=None, port=0, user=None,\
     pipe=None, mailbox=None, home=None)

    This class implements a separate process that listens to Gerrit events and
    reposts them on an ave.network.pipe.Pipe or an ave.network.Control mailbox.

    :arg host: A valid host name where Gerrit is running.
    :arg port: The port number SSH is listening on, on the Gerrit host.
    :arg user: The user name to use when negotiating the SSH connection to
        Gerrit.
    :arg pipe: An ave.network.pipe.Pipe. If supplied, Gerrit events will be
        reposted in the pipe. Intended for use in applications that want to
        handle inputs as pipe messages.
    :arg mailbox: A *(host,port)* tuple that will be used as the address
        parameter when creating an ``ave.network.control.RemoteControl`` object.
        If a mailbox is used, the receiving object must implement this method::

           @Control.rpc
           def put_gerrit_event(event): ...

    :arg home: Override value of *home* read from ``/etc/ave/user``.
    :raises Exception: If validation of parameters or the ``gerrit.json``
        configuration file fails.
