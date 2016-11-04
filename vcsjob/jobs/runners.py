# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import tests.fetch
import tests.execute
import tests.cli
import tests.list_jobs
import tests.logging
import tests.profiles
import tests.guid
import tests.duration

def all_fetch():
    tests.fetch.t1()
    tests.fetch.t2()
    tests.fetch.t3()
    tests.fetch.t4()
    tests.fetch.t5()
    tests.fetch.t6()
    tests.fetch.t7()
    tests.fetch.t8()
    tests.fetch.t9()
    tests.fetch.t10()
    tests.fetch.t11()
    tests.fetch.t12()
    tests.fetch.t13()
    tests.fetch.t14()
    tests.fetch.t15()
    tests.fetch.t16()
    tests.fetch.t17()
    tests.fetch.t18()
    tests.fetch.t19()
    tests.fetch.t20()

def all_execute():
    tests.execute.t1()
    tests.execute.t2()
    tests.execute.t3()
    tests.execute.t4()
    tests.execute.t5()
    tests.execute.t6()
    tests.execute.t7()
    tests.execute.t8()
    tests.execute.t9()
    tests.execute.t10()
    tests.execute.t11()
    tests.execute.t12()
    tests.execute.t13()
    tests.execute.t14()
    tests.execute.t15()
    tests.execute.t16()
    tests.execute.t17()
    tests.execute.t18()
    tests.execute.t19()
    tests.execute.t20()
    tests.execute.t21()
    tests.execute.t22()
    tests.execute.t23()
    tests.execute.t24()
    tests.execute.t25()

def all_cli(executable, sources):
    tests.cli.t1(executable, sources)
    tests.cli.t2(executable, sources)
    tests.cli.t3(executable, sources)
    tests.cli.t4(executable, sources)
    tests.cli.t5(executable, sources)
    tests.cli.t6(executable, sources)
    tests.cli.t7(executable, sources)
    tests.cli.t8(executable, sources)
    tests.cli.t9(executable, sources)
    tests.cli.t10(executable, sources)
    tests.cli.t11(executable, sources)
    tests.cli.t12(executable, sources)
    tests.cli.t13(executable, sources)
    tests.cli.t14(executable, sources)
    tests.cli.t15(executable, sources)
    tests.cli.t16(executable, sources)
    tests.cli.t17(executable, sources)
    tests.cli.t18(executable, sources)

def all_list_jobs():
    tests.list_jobs.t1()
    tests.list_jobs.t2()
    tests.list_jobs.t3()
    tests.list_jobs.t4()
    tests.list_jobs.t5()
    tests.list_jobs.t6()
    tests.list_jobs.t7()
    tests.list_jobs.t8()

def all_logging():
    tests.logging.t1()
    tests.logging.t2()
    tests.logging.t3()
    tests.logging.t4()
    tests.logging.t5()
    tests.logging.t6()
    tests.logging.t7()
    tests.logging.t8()
    tests.logging.t9()

def all_profiles():
    tests.profiles.t1()
    tests.profiles.t2()
    tests.profiles.t3()
    tests.profiles.t4()
    tests.profiles.t5()
    tests.profiles.t6()
    tests.profiles.t7()
    tests.profiles.t8()
    tests.profiles.t9()
    tests.profiles.t10()
    tests.profiles.t11()
    tests.profiles.t12()
    tests.profiles.t13()

def all_guid():
    tests.guid.t1()
    tests.guid.t2()
    tests.guid.t3()
    tests.guid.t4()
    tests.guid.t5()

def all_duration():
    tests.duration.t01()
    tests.duration.t02()