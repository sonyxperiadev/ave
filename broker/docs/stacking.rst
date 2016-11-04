.. _broker-equipment-stacking:

Equipment Stacking
==================

Overview
--------

There must be some way to tell the broker that a certain handset is connected
to a certain relay (to make up a common example) so that it does not allocate
some *other* combination where the relay affects some other piece of equipment
(that may already be allocated to some other test job).

It is typically not possible for one piece of equipment to discover that it is
connected to some other piece of equipment, so the generic solution has to be
based on explicit configuration. This configuration is recorded by the lab owner
in ``.ave/config/broker.json``.

Terminology
-----------

* **Stack:** A stack is a configuration that describes the entanglement of
  multiple pieces of equipment.

* **Entanglement:** Entanglement is a static relationship between two or more
  pieces of equipment such that concurrent allocation of the equipment to
  different clients results in unusable configurations.

  Entanglement does not simply mean that manipulation of one resource may have
  side effects on another resource. E.g. it does not cover the relationship
  that is produced by telling one handset to call another.

* **Collateral:** A client may allocate equipment that is referenced from a
  stack and not claim the other equipment in the stack. The broker cannot
  allocate the extra equipment to other clients because of the assumption of
  entanglement. The broker is also not allowed to return references to equipment
  that the client did not explicitly request. This status of implicit allocation
  is called "collateral". The broker tracks it for each explicit allocation to
  be able to free the related collateral when the allocated equipment is
  reclaimed from the client.

Equipment Detection
-------------------
The stacking mechanism is not involved in equipment detection. It merely works
with the identities provided to the broker by various equipment listers.

Configuration
-------------

The broker reads a list of equipment stacks on startup. A restart is needed
after changes to the list.

Because some equipment may be combined in more than one way, it is OK to have
the same equipment in multiple stacks. For instance, a WLAN dongle may work
with more than one handset, but the dongle can only interact with one handset
at a time. Consequently the dongle would show up in several stacks; one for
each handset that may connected to it.

.. rubric:: Format

The file ``.ave/config/broker.json`` may contain a section called "stacks" which
must be a list of lists of unique equipment profiles::

    "stacks": [
        [{"type":"handset","serial":"CB5A1QH2K2"},
         {"type":"relay","uid":"00014007.a"}],
        [{"type":"handset","serial":"CB5121X6KM"},
         {"type":"relay","uid":"00014007.b"}]
    ]

Any number of profiles can be included in a single stack. Each profile must
contain the ``type`` field and whatever field that uniquely identifies a single
piece of equipment (``serial`` for handsets, ``uid`` for most other types of
equipment).

Client Usage
------------
See broker API documentation.

Implementation
--------------

Allocators
^^^^^^^^^^
Each allocator in the broker keeps its own list of stacks. For the local host,
the list is read from ``.ave/config/broker.json``. For remote sharing brokers,
the list has been published by each broker, using ``Broker.set_stacks()``.

Referenced equipment may not be connected to the broker at all times, so the
broker does not try to assert that stacked equipment actually exists. What *can*
be done is to check that each profile contains a property that is guaranteed to
be a unique identifier. This is done by creating a ``Profile`` instance from
each profile (using a factory function that knows about all equipment types) and
then calling ``hash(profile)`` which will raise an exception if the profile does
not contain the uniquely identifying field.

Allocations
^^^^^^^^^^^
Each allocation is tracked by mapping the full profile of a resource to the
following items:

* A session. This is mostly used to check for ownership of the allocation when
  a call is made to ``Broker.yield_resources()``.

* A list of collateral. Several allocations may share the same collateral.
  (See the discussion about multiple stacks being allowed to reference the same
  equipment, above). Without the list, the broker would not be able to reclaim
  collateral for each yielded allocation.

Rules for allocation:

* Equipment must not be allocated if it is included in a stack that contains
  equipment which has already been allocated. Two clients having control over
  different parts of a common stack is presumed to cause side effects between
  the clients.

* Equipment may be allocated even if the allocation will share collateral with
  another allocation. This should be safe because neither client will be able
  to interact with the collateral. Neither client should be able to detect if
  manipulations of their allocations have side effects on the collateral.
