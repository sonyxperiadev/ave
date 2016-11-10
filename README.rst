

AVE
===

**AVE** is short for **Automated Verification Environment**, is a framework for test
automation and designed  by Sony Mobile. It is written for Linux Ubuntu 12+ in python 2.7
and consists of three parts:

- A set of modular APIs for efficient test automation that let test designers
  automate all sorts of tests, functional, power, performance, security and stability
  using various test equipment.
- A highly controlled test execution context to guarantee reliable test execution
  results, every time and regardless of location.
- A distributed resource management system that enables hardware sharing through
  a self-sustaining network of resource pools.


There’s extensive documentation available online at http://sonyxperiadev.github.io/ave/

The documentation can also be built locally by running `make html` from the
'documentation' directory (which does require sphinx), or read in their original
reST format.

Installation
------------
To install it one must have administrator privileges on the target machine.

.. rubric:: Installation

To install from source code, run::

    make clean
    make install-all

Alternatively, you can make a debian pakage and install it, run::

    make clean
    make debian
    sudo dpkg -i install ave-[ver].deb
    sudo apt-get install -f
    sudo dpkg -i install ave-[ver].deb (try to install again if needed)

Be prepared to enter your login user names, whatever that may be.

Acknowledgement
---------------

In 2012 Klas Lindberg, then working for Sony Mobile, designed the architecture
of AVE, building on a set of crucial principles that would enforce a way of working
with test automation that proved to be very successful. He continued to be the
projects main contributor, followed by Fredrik Åkerlund as he joined the team.
Since then, many joined in the project to maintain and help grow the project.
Although several of them have left the organization and we have development
footprint internally available but not at GitHub,we would like to express our
gratitude to them for contribution to make this project publicly available:

**Major Contributors (@GitHubAccount)**



Klas Lindberg (`@Mysingen <https://github.com/Mysingen>`_),
Fredrik Åkerblom

**Contributors**

Johan Müllern-Aspegren (`@johanaspegren <https://github.com/johanaspegren>`_),
Wang Qiang (`@WangQiang3 <https://github.com/WangQiang3>`_),
Xu Quanhao (`@xu-quanhao <https://github.com/xu-quanhao>`_),
Johan Svegne (`@sejosg <https://github.com/sejosg>`_),
Martin Berg (`@jamtse <https://github.com/jamtse>`_),
Emil Billing,
Nima Davoudi-Kia,
Fredrik Lindell,
Martin Lindblom,
Li Baojian (`@li-baojian <https://github.com/li-baojian>`_),
Zhang Xiaoming (`@zxmsony <https://github.com/zxmsony>`_),
Duan Jianjie (`@JianjieDuan <https://github.com/JianjieDuan>`_),
Wang Chuang,
Huaming Lin,
Anders Hedlund,
Snild Dolkow (`@Snild-Sony <https://github.com/Snild-Sony>`_),
David Pursehouse (`@dpursehouse <https://github.com/dpursehouse>`_),
Toshiaki Tanaka,
Junji Shimagaki (`@yiu31802 <https://github.com/yiu31802>`_),
Ma Lina (`@LinaMAS <https://github.com/LinaMAS>`_) and
many other minor contributors
