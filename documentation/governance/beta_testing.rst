.. _beta-testing:

Beta Testing
============

To participate in beta testing you need to add a special ``apt-get`` repository.
To do this, you need administrator privileges on the target machine.

Administrator Privileges
------------------------
First try to become owner and admin according to the normal IT process. Run::

    makemeowner

and type ``ADMIN`` when prompted.

If this does not work because someone else already owns the machine, you can
still become administrator with some help from the current administrator. *That*
person should run::

    sudo usermod -a -G admin <your user name>

Adding the ``apt-get`` Repository
---------------------------------
Run::

    sudo sh -c "echo 'deb http://linuxmirror.global.sonyericsson.net/swerepo test semc' > /etc/apt/sources.list.d/ave-beta.list"

This adds the beta repository but in such a way that it will always have lower
priority than the regular repsitories. This makes sure you cannot accidentally
install a beta whenever you perform regular updates of the machine.

Installing the Beta
-------------------
To install from the beta repository, run::

    sudo apt-get update
    sudo apt-get install -t 'n=test,c=semc' ave

Alternatively, you can open ``synaptic`` or another Debian package manager to
check what the latest available version is before actually installing anything.

When the next official version of AVE is published, ``apt-get`` will prefer that
version (because it is higher than that of the beta you installed) when you run
a regular update::

    sudo apt-get update
    sudo apt-get install ave

Reverting a Beta Installation
-----------------------------
Regrettably, this can be tricky if the beta was really broken. The most reliable
way is probably to open ``synaptic``, search all "ave-" packages and uninstall
them all. Then install the regular version normally.
