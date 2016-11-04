import pkg_resources
import modulefinder

# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

# the ave Python package is implemented in several Debian packages (git trees
# really). this causes problems when importing different ave modules from
# different source paths. consider the following template which is used in many
# unit test jobs for various ave modules:
#
#     path = os.path.dirname(os.path.dirname(__file__))
#     path = os.path.join(path, 'src')
#     sys.path.insert(0, path)
#     import runners
#     runnsers.all_git()
#
# after "sys.path.insert(0, path)", the interpreter won't be able to find any
# ave modules which are not implemented in the current tree. the following two
# lines work around that by adding the tree-local modules to another name space
# with the same name as the system-installed modules.

pkg_resources.declare_namespace(__name__)
for p in __path__:
     modulefinder.AddPackagePath(__name__, p)

# make sure that this __init__.py is NOT INSTALLED TO THE SYSTEM! the "common"
# package owns that file.

