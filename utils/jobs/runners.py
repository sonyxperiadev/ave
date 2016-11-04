# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import vcsjob

import tests.testjob
import tests.logger
from tests.common import StdOutRedirector
import sys
import traceback


def all_testjob():
    redirector = StdOutRedirector()
    redirector.redirect()

    res = True
    res &= tests.testjob.t1()
    res &= tests.testjob.t2()
    res &= tests.testjob.t3()
    res &= tests.testjob.t4()
    res &= tests.testjob.t5()
    res &= tests.testjob.t6()
    res &= tests.testjob.t7()

    redirector.reset()

    return res


def all_testjob_android():
    redirector = StdOutRedirector()
    redirector.redirect()

    res = True
    try:
        res &= tests.testjob_android.t01(redirector)
        res &= tests.testjob_android.t02()
        res &= tests.testjob_android.t03()
        res &= tests.testjob_android.t04()
        res &= tests.testjob_android.t05()
        res &= tests.testjob_android.t06()
        res &= tests.testjob_android.t07()
        res &= tests.testjob_android.t08()
        res &= tests.testjob_android.t09()
        res &= tests.testjob_android.t10(redirector)
        res &= tests.testjob_android.t11(redirector)
        res &= tests.testjob_android.t12()
        res &= tests.testjob_android.t13(redirector)
        res &= tests.testjob_android.t14(redirector)
        res &= tests.testjob_android.t15(redirector)
        res &= tests.testjob_android.t16(redirector)
        res &= tests.testjob_android.t17()
        res &= tests.testjob_android.t18(redirector)
        res &= tests.testjob_android.t19(redirector)
    except Exception, e:
        sys.stderr.writelines("%s\n" % str(e))

        _, _, _tb = sys.exc_info()
        stack_trace = traceback.extract_tb(_tb)
        print('Stack trace')
        for stack_item in stack_trace:
            print('   %s' % str(stack_item))

        std_out=redirector.get_content()
        sys.stderr.writelines("Final std out:\n%s\n" % std_out)
        res = False
    finally:
        redirector.reset()

    return res


def all_logger():
    redirector = StdOutRedirector()
    redirector.redirect()
    res = True
    res &= tests.logger.t1()
    res &= tests.logger.t2()
    res &= tests.logger.t3()
    res &= tests.logger.t4()
    redirector.reset()
    return res
