Resource Brokering
==================

:module: ``ave-broker``

The broker is used to allocate resources: Handsets, workspaces, GPS simulators,
programmable relays and more. It uses some simple rules for how to treat the
client that performs the allocations, depending on what it tries to do. Knowing
how the rules work is essential when working with AVE.

Basic Rules of Correct Usage
----------------------------

 * If the allocation attempt raises an exception, check its type. If the type
   is ``Busy``, that means the wanted equipment exists but is allocated to
   someone else. Exit your program with status ``vcsjob.BUSY`` and let the
   scheduler that ran your program decide when to try it again::

    import sys
    import vcsjob

    from ave.broker            import Broker
    from ave.broker.exceptions import Busy

    broker = Broker()
    try:
        handset = broker.get({'type':'handset', 'pretty':'yuga'})
    except Busy:
        # tell the scheduler that the job should be retried sometime later:
        sys.exit(vcsjob.BUSY)

 * Client can allocate multiple resources in one call, and if the client
   needs some resources configured to work together, in a 'stack', the
   client should enclose these resources in a parentheses when invoking the
   'get' method::

    # ensure workspace is allocated on the same host as the equipment,
    # no need configure workspace in the stack, for workspace, this is a
    # default behavior.
    from ave.broker import Broker
    broker = Broker()
    h, w = broker.get(({'type':'handset'}, {'type':'workspace'}))

    # in this case, the client intends to allocate a handset and a relay which
    # were configured to work together in a 'stack'.
    from ave.broker import Broker
    broker = Broker()
    h, r, w = broker.get(({'type':'handset'}, {'type':'relay'},{'type':'workspace'}))

    #client allocates two handsets, but these two handsets may be located in different
    #Host PC,
    from ave.broker import Broker
    broker = Broker()
    h1, h2 = broker.get(({'type':'handset'},), ({'type':'handset'},))
    #client allocate  two handsets, and these two handsets were configured
    #to work together in  a 'stack'
    from ave.broker import Broker
    broker = Broker()
    h1, h2 = broker.get({'type':'handset'}, {'type':'handset'})
    # or
    h1, h2 = broker.get(({'type':'handset'}, {'type':'handset'}))

    # in this case, client intends to allocate two handsets and one relay, and
    # one of the handsets should work together with the relay.
    from ave.broker import Broker
    broker = Broker()
    h1, r, h2 = broker.get(({'type':'handset'}, {'type':'relay'}), {'type':'handset'})

 * If the client disconnects from the broker, the broker will free all of the
   client's resources, terminate its session and make the equipment available
   again. This means that the client does not need to yield resources. Simply
   terminate the program.

Examples of Incorrect Usage
---------------------------

 * Allocating a handset and a workspace separately can cause them to end up on
   different hosts. Interaction between them will then not work::

    # handset.push() may raise an exception about the source file not existing
    # in the file system, because the workspace downloaded it on a different
    # host:

    broker = Broker()
    handset = broker.get({'type':'handset'})
    workspace = broker.get({'type':'workspace'})

    path = workspace.download_git(...)
    handset.push(path+'/some_file', '/system/data')

 * The broker disconnects your client if an allocation fails for *any* reason.
   The rationale is that a misbehaving client should not be able to loop on the
   allocation request because that may lead to deadlocks between two clients
   that fight for the same set of resources::

    import time

    from ave.broker            import Broker
    from ave.broker.exceptions import Busy

    broker = Broker()

    # THE FOLLOWING WILL NOT WORK. the broker disconnects the client on the
    # first failed allocation attempt, after which broker.get() will raise a
    # different exception, telling you that the client's session has been
    # terminated.
    while True:
        try:
            h1 = broker.get({'type':'handset', 'pretty':'yuga'})
            h2 = broker.get({'type':'handset', 'pretty':'togari'})
            break
        except Busy:
            time.sleep(1) # retry

 * The client must keep a reference to its ``Broker`` instance to prevent the
   broker from disconnecting the client. Here is a common pitfall that will not
   work::

    from ave.broker import Broker

    def allocate():
        broker = Broker()
        return broker.get({'type':'handset', 'pretty':'yuga'})
        # broker object is garbage collected here

    handset = allocate()
    handset.ls('/') # will raise ConnectionRefused

API for Regular Clients
-----------------------

.. class:: ave.broker.Broker()

    .. function:: get(*profiles)

        Allocate one or more resources based on profiles.

        :arg profiles: One or more ``dict`` objects that encode resource
            profiles. All profiles must have the ``"type"`` field set.
        :returns: The same number of resource objects as there were profiles
            in the request.
        :raises Busy: If the request could not be satisfied because all matching
            equipment is currently allocated to some other client.
        :raises NoSuch: If the request could not be satisfied because no match
            is possible at all. I.e. the broker knows of no such equipment, busy
            or not.
        :raises Restarting: If the broker has restarted since the client
            connected to it. When restarting, the old broker instance remains
            running to keep track of all sessions it created, but is forbidden
            to allocate more equipment (because the replacement broker now has
            that privilege). A client that makes all of its allocation in the
            close succession is extremely unlikely to ever see this exception.
        :raises AveException: The parameters could not be validated. E.g. if a
            profile is malformed.

        Example allocations::

            b = Broker()

            # any android handset on the GTE network together with a workspace:
            h,w = b.get(
                {'type':'handset', 'platform':'android', 'gsm.operator':'GTE'},
                {'type':'workspace'}
            )

            # a Hayabusa handset running FirefoxOS of a specific label, together
            # with a programmable relay that has been wired to cut the USB and
            # battery connections of the handset, plus a workspace:
            h,r,w = b.get(
                {
                    'type':'handset',
                    'platform':'firefox',
                    'sw.label':'ICS-BLUE-FF-130516-1131'
                },
                {'type':'relay', 'circuits':['usb.pc.vcc', 'handset.battery']},
                {'type':'workspace'}
            )

        If the broker cannot satisfy the request and a forwarding rule is set
        to point to another broker on the network, then the request will be
        passed on and tried there instead. This chain can be arbitrarily long.

.. _broker-admin-api:

API for Administrative Clients
------------------------------

Connecting as administrator gives the client new capabilities and removes some.
The administrator role is supposed to be used by web frontends and the like, not
by regular programs.

.. class:: ave.broker.Broker(authkey)

    :arg authkey: An authentication string that must match the value of the
        ``"admin"`` field in ``.ave/config/authkeys.json``.

    .. function:: get(*profiles)

    :raises ConnectionClosed: The client is not allowed to allocate resources
        while logged in as administrator.

    .. function:: list_allocations_all()

        :returns: A list of profiles representing the combined allocations of
            all clients.

    .. function:: list_collateral_all()

        :returns: A list of profiles representing the collateral of the combined
            allocations of all clients.

        Collateral is any equipment that is part of a stack that the client has
        taken some other resource from, but not the equipment itself. It is an
        internal book keeping mechanism that secures that different clients
        cannot accidentally get resources that will interfere with each other
        when manipulated.

    .. function:: start_sharing()

        If the broker has a sharing rule, this call will force it to start
        sharing its equipment over the network.

    .. function:: stop_sharing()

        Stop sharing equipment with another broker.

    .. function:: list_shares()

        List all brokers that share equipment with this broker.

    .. function:: drop_share(address)

        :arg address: A *(host, port)* tuple.

        Causes the broker to disconnect another broker that shares equipment
        with it. The call has no effect if no such broker is connected. Note
        that sharing brokers are by default configured to try to reconnect when
        they loose the connection. This call is only useful for diagnostics.

    .. function:: drop_all_shares()

        Causes the broker to disconnect all brokers that share equipment with
        it. Note that sharing brokers are by default configured to try to
        reconnect when they loose the connection. This call is only useful for
        diagnostics.

    .. function:: list_equipment(profile=None)

        Returns a list of equipment that matches the profile. The equipment does
        not have to be available for allocation.

    .. function:: list_available(profile=None)

        Returns a list of equipment that matches the profile and is available
        for allocation.

    .. function:: list_stacks()

        Returns a list of the broker's configured equipment stacks. Stacking
        determines what equipment can be allocated together. (Workspaces can
        always be allocated together with equipment and is not listed in the
        stacks.)

Starting and Stopping the Broker
--------------------------------

On systems that use ``Upstart``, the broker and other AVE services will be
started by ``init`` on system boot. On other systems, the user has to start
the broker manually::

    ave-broker --start

The broker can be restarted without affecting clients and their sessions::

    ave-broker --restart

Stopping the broker terminates all open sessions and disconnects all clients::

    ave-broker --stop

Configuration Files
-------------------

The files are located under ``$home/.ave/config``, where the value of ``$home``
is read from ``/etc/ave/user``.

Changes to the files take effect when the broker is restarted::

    # change the config files
    ave-broker --restart

.. Note:: Some changes require a full stop and start of the broker: Port numbers
    and changes to authentication keys::

        ave-broker --stop
        # change the config files
        ave-broker --start

``broker.json``
+++++++++++++++

The smallest valid configuration is just the empty dictionary::

    {}

A broker that is configured to forward failed allocations to another broker
uses the *remote* rule (always use port 4000 unless you know what you are
doing)::

    {
        "remote": {
            "host"  : "hostname",
            "port"  : 4000,
            "policy": "forward"
        }
    }

A broker that is configured to share its equipment with another broker also
uses the *remote* rule, but with slightly different settings. The *authkey*
field must match the *share* value of the remote broker's ``authkeys.json``
file::

    {
        "remote": {
            "host"   : "hostname",
            "port"   : 4000,
            "policy" : "share",
            "authkey": "sharing key of the other broker"
        }
    }

A broker that is configured to handle stacked equipment can add the *stacks*
field. Each entry must be a list of profiles that contain the *type* field and
a field that uniquely identifies an instance of that kind of equipment. In the
following example, handsets (identified by serial number) are stacked against
relays (identified by symbolic ID's)::

    {
        "stacks":[
            [{"type":"relay","uid":"a"}, {"type":"handset","serial":"CB5A1JYXRQ"}],
            [{"type":"relay","uid":"b"}, {"type":"handset","serial":"CB511VD8AF"}],
            [{"type":"relay","uid":"c"}, {"type":"handset","serial":"CB5A1M7CTP"}]
        ]
    }

A broker configuration can contain both *remote* and *stacks* rules.

.. Note:: Although JSON is great for comfortable configuration handling, it is
    a format with some limitations:

    * It is not possible to put comments in the files. Hopefully this document
      is so smashingly fantastic that this is not a problem...
    * If the same field occurs more than once, the Python JSON parser simply
      keeps the last entry and silently overwrites whatever was already there.
      E.g. it is not possible to use the *remote* rule twice, but the broker
      will not complain about it because the JSON parser doesn't.

``authkeys.json``
+++++++++++++++++

Certain adiministrative functions in the broker are protected by authentication
keys to prevent accidental usage of functionality that are not meant to be used
by regular clients. These are keys are generated automatically when AVE is
installed but can be changed to more memorable values::

    {
        "admin": "Some random stuff... 1234!",
        "share": "please stick to printable characters, ok?"
    }

In the API documentation above, functions that require use of the *admin* key
have been put under their own section.
