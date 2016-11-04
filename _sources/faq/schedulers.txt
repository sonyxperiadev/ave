Scheduling
==========

There is no explicit job scheduler in AVE. Some reasons for this:

* Any node that runs any job is implicitly a scheduler. It would be very hard
  to enforce a scheduling policy across all nodes because they can have very
  loose relationships, yet need access to the same common resource pool.
* Jobs should be runnable even when a node is fully disconnected if enough
  equipment is available locally.
* It is anticipated that different groups will want to set up automation based
  on (very) different economic calculations, resulting in (very) different
  scheduling. It is hard to envision a centralized job scheduler that can handle
  arbitrary requirements.
* Centralized job scheduling often implies that resources will be allocated in
  advance to secure that a scheduled job will be able to run. A centralized
  mechanism would need detailed information about all jobs' resource needs.
  Adding such tags *helps* but cannot *guarantee* an allocation. The scheduler
  is not the only actor in the system, equipment might fail, etc.

The following solution seems more robust:

* Put a declarative interface on all jobs to help schedulers. AVE's interface
  is the ``.vcsjob``. This interface is kept as small as possible to keep both
  job and scheduler complexity low.
* Match jobs' needs with resources centrally but don't try to *schedule* the
  allocations. An allocation attempt must always succeed or fail immediately,
  with an option to retry the job later. DUST is implemented this way.
* Allow brokers to set conditions for allocation of specific handsets. E.g.
  deny allocation unless the request includes properties that don't matter to
  most jobs but are critical to some.
* Prevent jobs from looping on resource allocations until they succeed. This
  is done by letting the broker reclaim *all* equipment allocated to that job
  immediately if one allocation fails. Users are not able to prevent this.
* Reuse network security on IP level as much as possible. Often it is good
  enough to simply move a sensitive lab into a restricted network.

This way, the problem of finding a workable schedule is moved to the users of
the system. Then scheduling can be solved as one or several fully separated
problems. Separation of concerns is its own reward.

Jenkins
-------
How to schedule jobs from Jenkins? The typical scenario is that test results
are wanted to go together with the state of a build job. Can this be done?

The asynchronous nature of allocation in AVE makes this tricky. If the Jenkins
job is kept open for test results but there is no available equipment to run
on, the job ends with a failure. If the Jenkins job solves this by looping on
a ``vcsjob execute`` statement, it may not be possible to get a test result for
a very long time. In the meantime, the Jenkins job cannot be started again.

One solution is to enable the parallel flag on a Jenkins job, but that invites
problems with overuse of RAM and CPU as any number of expensive build jobs can
then be triggered in parallel. A cleaner solution is to fully separate building
and testing and to use a dedicated test scheduler such as DUST. So instead of
running the tests directly in the build job, push a job ticket to DUST. Help
with setting this up can be gotten from the `DUST team <mailto:DL-WW-DUST-Support@sonymobile.com>`_.
