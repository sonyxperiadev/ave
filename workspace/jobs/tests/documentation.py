# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import pydoc


import ave.git
import ave.jenkins

import ave.workspace

# these tests merely check that documentation can be generated without raising
# exceptions.


# check the documentation for ave.cmd
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    try:
        pydoc.plain(pydoc.render_doc(ave.cmd))
    except:
        print('FAIL %s: pydoc failed to process ave.cmd' % pretty)
        return
    return True

# check the documentation for ave.git
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    try:
        pydoc.plain(pydoc.render_doc(ave.git))
    except:
        print('FAIL %s: pydoc failed to process ave.git' % pretty)
        return
    return True

# check the documentation for ave.jenkins
def t4():
    pretty = '%s t4' % __file__
    print(pretty)

    try:
        pydoc.plain(pydoc.render_doc(ave.jenkins))
    except:
        print('FAIL %s: pydoc failed to process ave.jenkins' % pretty)
        return
    return True
