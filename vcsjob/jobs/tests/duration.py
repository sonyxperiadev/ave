import vcsjob
import os

#check that if job's running time is longer than the allowed time, job will be kileed
#job's running time is 12 seconds
def t01():
    pretty = '%s t01' % __file__
    print(pretty)

    pwd = os.path.dirname(__file__)
    job_dir = os.path.dirname(os.path.dirname(pwd))
    job = {"path":"jobs/duration_test","duration":10}

    status = vcsjob.execute_job(job_dir, job, None, None, None)
    if status == vcsjob.TIMEOUT:
        return  True
    else:
        return  False
#check that if the allowed time is longer than job's running time, job will execute and exit normally
#job's running time is 12 seconds
def t02():
    pretty = '%s t02' % __file__
    print(pretty)

    pwd = os.path.dirname(__file__)
    job_dir = os.path.dirname(os.path.dirname(pwd))
    job = {"path":"jobs/duration_test","duration":14}

    status = vcsjob.execute_job(job_dir, job, None, None, None)
    if status == 0:
        return  True
    else:
        return  False