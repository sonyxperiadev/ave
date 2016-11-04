Adding New API's
================

.. Note::

    This document does not cover smaller improvements on existing features.
    That kind of change can normally be handled with ordinary code review in
    Gerrit and some consultation with members of the `DL-WW-AVE-GB
    <email:dl-ww-ave-gb@sonymobile.com>`_ mailing list.

Changes to public AVE API's are handled by a governance process. Especially if
the changes are large or involve entirely new functionality. The process is as
follows:

 1. Contact the governance board and check if you need to follow this process.

 2. Describe the new API. Do not add too much detail. Focus
    on the primary use cases and provide pseudo code examples of how the feature
    would be used in real test jobs. A template is available `here
    <https://wiki.sonyericsson.net/androiki/ave/template>`_.

 3. The governance board considers the proposal and either rejects it or gives
    it a tentative approval. In case of approval, the board will also

     * Put formal requirements on a full solution.
     * Ensure that a PM is assigned to handle the development. The PM is then
       responsible to present a time plan, secure resources and the long term
       maintenance of the new feature.

    *Note that this is a neither a formal approval of the API nor a commitment
    to offer it as an AVE component. It is simply a statement of interest and
    acknowledgement that the feature would be valuable.*

 4. The assigned team gets to work to create a working example.

 5. The team presents the demo and a fuller API description to the board. The
    implementation and documentation must follow AVE's `structural guidelines
    <structure_guidelines.html>`_ and `source code style rules
    <source_code_style_rules.html>`_.

 6. The board either approves or rejects. If rejected, iterate from (3) or (4),
    depending on the severity of identified issues.

 7. SWD Tools prepares a beta release and makes it available for wider testing.
    If problems are found during testing, iterate from (3) or (4), depending on
    the severity of the problems.

 8. The board updates any impacted process documents.

 9. SWD Tools includes the new feature in a stable release.

 10. The feature is delivered according to the handshaked maintenance plan (3).

.. Note::

    Sometimes conceptual errors cannot be not seen until actual code can be
    tried out or at least reviewed. It is better to fail many "small" times at
    (5) than to fail once but big.
