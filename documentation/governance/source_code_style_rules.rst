Source Code Style Rules
=======================
There are just a few rules for source code style. Follow them.

Python
------
 * Must run on versions 2.6 and 2.7 of CPython.
 * Max 80 chars per line.
 * Avoid deep class hierarchies.
 * Prefer a procedural programming style. Mimic C, not Java.
 * It is forbidden to pass ``self`` references into an object held by ``self``,
   or otherwise create circular references.
 * It is forbidden to declare variables with global scope. Only constants,
   classes and functions may have global scope.
 * User visible functions must only take parameters that are JSON serializable.
 * User visible functions must only return values that are JSON serializable.
 * Avoid function declarations inside other functions. All functions should be
   callable from tests.
 * Functions must raise exceptions to signal error conditions. The caller must
   not be forced to inspect the regular return value to look for an error
   condition.
 * Prefix user invisible function names with "_".
 * Classes must not be implemented as singletons.
 * Base classes must inherit from ``object`` or ``Exception``.
 * Use the ``ctypes`` module to interface with native code libraries.
 * Use the ``ave.cmd`` module to interface with external programs.
 * Default values for function parameters must be of type ``None``, ``int``,
   ``float``, ``str`` or ``unicode``.

An example to illustrate the importance of the last rule. The default values
have non-simple types (a dictionary and a list). Python treats these as globals
that are not created fresh on each call to the function. Instead a single object
is used over and over. Needless to say this can give you very strange results.

.. code-block:: python

    #! /usr/bin/python2

    # structured types for default parameters are not ok. behavior depends on
    # how many times the function was called before.
    def f(a={'a':1,'b':2}, b=[1,2,3]):
        print a, b
        a['b'] += 1
        b.append(4)

    f() # prints "{'a': 1, 'b': 2} [1, 2, 3]"
    f() # prints "{'a': 1, 'b': 3} [1, 2, 3, 4]"

What about ``ave.cmd``? Why not use the ``subprocess`` module?  Programs started
with ``subprocess`` can be very hard to kill completely if they started their
own sub-processes. A user of ``ave.cmd`` can simply terminate itself to also
terminate the external programs it started.

Java
----
Gort and Galatea. Coding style rules are **TODO** items.

JavaScript
----------
Marionette is used to implement helper functions in Firefox OS products. Coding
style rules are **TODO** items.

C
-
Mostly **TODO**. However:

 * If the program is for the handset (and not for the host), then it cannot be
   part of AVE. It must instead be part of the product and built by the product
   build system. This is necessary because different products run on different
   CPU architectures. Cross compilation of C is out of scope for AVE.
