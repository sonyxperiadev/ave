Relay
=====

:module: ``ave-relay``

Relays may be used to control the electrical connectivity of many types of
equipment, including handsets. The relays are allocated by symbolic name, such
as ``"usb.pc.vcc"`` or ``"handset.battery"`` to control USB voltage supply and
the battery of a handset, respectively.

Symbolic Circuit Names
----------------------
The following symbolic circuit names are currently defined. In all cases, the
lab owner is responsible for setting up actual wiring of the equipment and to
create configuration files that match the wiring. See the *Configuration Files*
section for details on lab maintenance.

Handset Circuits
^^^^^^^^^^^^^^^^
The following circuits can be used if the lab owner has augmented corresponding
physical handset buttons or connectors with electrical cords.

 * ``handset.battery``: The connection between a handset and its battery. Open
   the circuit to disconnect the battery.
 * ``handset.power``: The power button on a handset. Close the circuit to press
   the button.
 * ``handset.volume.up``: The volume up button on a handset. Close the circuit
   to press the button.
 * ``handset.volume.down``: The volume down button on a handset. Close the
   circuit to press the button.

USB Circuits
^^^^^^^^^^^^
Note that opening and closing USB circuits should be done in a specific order.
Always open ``usb.pc.vcc`` before opening other circuits. Always close
``usb.pc.vcc`` before closing other circuits.

PC connector
++++++++++++
 * ``usb.pc.vcc``: PC 5V supply. Open the circuit to disconnect the PC from
   whatever is connected at the device end. Power may still leak through the
   remaining four circuits, but opening this circuit causes a full protocol
   level disconnect.
 * ``usb.pc.d+``: PC D+ data pin.
 * ``usb.pc.d-``: PC D- data pin.
 * ``usb.pc.gnd``: PC ground.
 * ``usb.pc.id``: PC ID pin.

Wall Charger
++++++++++++
 * ``usb.wall.vcc``: Wall charger 5V supply.
 * ``usb.wall.d+``: Wall charger D+ data pin.
 * ``usb.wall.d-``: Wall charger D- data pin.
 * ``usb.wall.gnd``: Wall charger ground.
 * ``usb.wall.id``: Wall charger ID pin.

Client API
----------
Relays are allocated through a broker. The client must specify which symbolic
circuit names it wishes to manipulate. In this example, the client asks for a
relay that can manipulate the battery and general USB connectivity of a handset:

.. code-block:: python

    import time
    from ave.broker import Broker

    b = Broker()
    r,h = b.get(
        {'type':'relay','circuits':['handset.battery','usb.pc.vcc']},
        {'type':'handset'}
    )
    r.set_circuit('usb.pc.vcc', False)
    assert h.get_power_state() == 'offline'

    # force a cold boot of the handset
    r.set_circuit('handset.battery', False)
    time.sleep(1)
    r.set_circuit('handset.battery', True)
    r.set_circuit('usb.pc.vcc', True)
    h.wait_power_state('boot_completed')

Relay
^^^^^

    .. function:: set_circuit(circuit, closed)

        Open or close the named circuit. The allocation of the relay must have
        specified the named circuit.

        :arg closed: *True* closes the circuit. *False* opens the circuit.
        :returns: UTC time stamp to tell the client when the relay was actually
            manipulated by the server.
        :raises Exception: If the client did not allocate a relay that includes
            the named circuit.

    .. function:: reset()

        Reset all circuits in the relay to their default states.

Server API
----------
This API is intended for administrative clients and require a valid ``admin``
authentication key.

.. class:: ave.relay.server.RemoteRelayServer(address=None, authkey=None)

    :arg address: A (string,integer) tuple denoting the hostname and port number
        where the relay server is running. If *None*, the address will be read
        from ``.ave/config/relay.json``. (Also see the *Configuration Files*
        section below.)
    :arg authkey: A string. Must be set to the ``admin`` key used on the host
        where the relay server is running. (Also see the *Configuration Files*
        section below.)

    .. function:: ping()

        :returns: The string "ave-relay pong" if a working RPC connection has
            been establised.

    .. function:: stop():

        Stops the relay server.

    .. function:: list_equipment()

        List all physical relay boards, including manufacturer, device model id,
        etc.

        :returns: A list of board profile dictionaries, describing the model,
            manufacturer and hardware specific details of each physical board
            handled by the server.

    .. function:: list_virtual()

        List all virtual relay boards provided by the server. I.e. the relays
        that can be allocated through a broker.

        :returns: A list of relay profile dictionaries, listing the named
            circuits that each relay can manipulate.

    .. function:: set_board_circuit(profile, circuit, closed)

        Open or close a named circuit in a virtual relay.

        :arg profile: A virtual relay profile as returned by ``list_virtual()``.
        :arg circuit: A named circuit.
        :arg closed: *True* to close the circuit. *False* to open the circuit.
        :returns: A UTC time stamp as a list of integers: [year, month, day,
            hour, minute, second, microsecond]

    .. function:: reset_board_group(profile)

        Reset all circuits in a virtual relay.

        :arg profile: A virtual relay profile as returned by ``list_virtual()``.
        :returns: A UTC time stamp as a list of integers: [year, month, day,
            hour, minute, second, microsecond]

Starting and Stopping the Server
--------------------------------
On systems that use Upstart, the relay server will be started by init on system
boot. On other systems, the user has to start the relay server manually::

    ave-relay --start

The relay server can be restarted without affecting clients and their sessions::

    ave-relay --restart

Stopping the server terminates all open sessions and disconnects all clients::

    ave-relay --stop

.. _relay-config-files:

Configuration Files
-------------------
All configuration files are located in ``<home>/.ave/config/``, where the value
of ``<home>`` is read from ``/etc/ave/user``.

The relay server uses three kinds of configuration files:

 * Files for the relay server itself.
 * Files for each supported board manufacturer.
 * The equipment stacking configuration of the broker.

Changes to configuration files require a full stop and start of the server. Not
doing so will either make the server unreachable (in case of``relay.json`` and
``authkeys.json``) or affect connected clients (for board specific files)::

    ave-relay --stop
    # change the config file
    ave-relay --start

``relay.json``
^^^^^^^^^^^^^^
The smallest valid configuration is to not have the configuration file at all.
In such cases, the server runs with default values::

    {
        "port": 4006
    }

``authkeys.json``
^^^^^^^^^^^^^^^^^
Adiministrative functions in the relay server are protected by an authentication
key to prevent accidental usage of functionality that is not meant for regular
clients. The key is generated automatically when AVE is installed but can be
changed to more memorable values::

    {
        "admin": "please stick to printable characters, ok?"
    }

``devantech.json``
^^^^^^^^^^^^^^^^^^
If this file does not exist, then the server will not be able to use boards from
Devantech.

In this example there are two sections. The first is a wild card that matches
the serial number of all Devantech boards. The second matches a specific board
with serial number "123abc", which overrides the wild card section:

.. code-block:: javascript

    {
        "*":{
            "groups": {
                "a": {"handset.power":1, "usb.pc.vcc":2},
                "b": {"handset.power":3, "usb.pc.vcc":4}
            },
            "defaults":[1,1,1,1, 1,1,1,1]
        }

        "123abc": {
            "groups": {
                "a": {"handset.power":1, "handset.battery":2}
                "b": {"handset.power":3, "handset.battery":4}
            },
            "defaults":[0,1,0,1, 0,0,0,0]
        }
    }

The file will be loaded each time a Devantech board is plugged in. The default
values values for each board determine if circuits will be (re)set to open or
closed by a call to ``Relay.reset()`` or by a unplug/plug of the USB connector.

The "groups" sub-section for each board determines the symbolic circuit names
associated with each physical port on the board. Port numbering starts with 1.
The same port number cannot appear more than once in one board configuration.

``broker.json``
^^^^^^^^^^^^^^^
Refer to the broker documentation for generic equipment stacking information.
In the stack declarations, use virtual relay profiles that contain the "type"
and "uid" fields. Example profiles::

    { "type": "relay", "uid": "00014007.b" }

The virtual relay UID's can be found by using the administrative server function
``RemoteRelayServer.list_virtual()``. See the *Server API* section for details.

Supported Hardware
------------------
 * `Devantech USB-RLY16`_. This is the recommended board to use for all 5 volt
   applications, such as USB connections and handset batteries.

.. _Devantech USB-RLY16: http://www.robot-electronics.co.uk/htm/usb_rly16ltech.htm
