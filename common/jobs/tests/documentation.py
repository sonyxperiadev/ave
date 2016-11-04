# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import pydoc

import ave.cmd

from decorators import smoke

# these tests merely check that documentation can be generated without raising
# exceptions.

# check the documentation for ave.cmd
@smoke
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    try:
        pydoc.plain(pydoc.render_doc(ave.cmd))
    except:
        print('FAIL %s: pydoc failed to process ave.cmd' % pretty)
        return False

    return True
