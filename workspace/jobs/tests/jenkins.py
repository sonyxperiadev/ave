# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import json

import ave.jenkins

from ave.jenkins   import JenkinsJob, load_jenkins
from ave.workspace import Workspace
from ave.config    import create_default

from decorators import smoke, with_workspace

JOB_ID = 'Tools_AVE_Jenkins_Test_Artifact_Producer'
JOB_ID_WITH_BUILD_PARAMETERS = 'Gerrit_l-shinano_android_fullbuild'
JENKINS_WITH_AUTH = 'http://android-ci-protected.sonyericsson.net'
JENKINS = 'http://android-ci.cnbj.sonyericsson.net'
JENKINS_WITH_BUILD_PARAMETERS = 'http://android-ci-cm.sonyericsson.net'

# check that downloading all artifacts work
def t01():
    pretty = '%s t1' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    try:
        path = w.download_jenkins(JOB_ID)
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        w.delete()
        return

    expected = [
        os.path.join(os.path.dirname(path), 'last_successful'),
        os.path.join(path, 'testArtifact.apk')
    ]
    for e in expected:
        if not os.path.exists(e):
            print(
                'FAIL %s: expected path "%s" does not exist after download'
                % (pretty, e)
            )
            w.delete()
            return

    w.delete()
    return True

# check that downloading a selection of artifacts from a named build works
def t02():
    pretty = '%s t2' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    # find a build id, not the latest
    job = ave.jenkins.JenkinsJob(w.config['jenkins'], JOB_ID)
    all_builds = job.all_builds()
    if len(all_builds) < 2:
        print(
            'BLOCKED %s: no enough builds available to support the test: %d'
            % (pretty, len(all_builds))
        )
        w.delete()
        return

    build_id = None
    artifacts = None
    for b in all_builds:
        if (b.attributes['result'] == 'SUCCESS'
        and len(b.attributes['artifacts']) > 1):
            build_id = str(b.build)
            artifacts = [a['relativePath'] for a in b.attributes['artifacts']]
            break

    if not build_id:
        print('BLOCKED %s: no usable build to support the test' % pretty)
        w.delete()
        return

    # download the id'd build
    try:
        path = w.download_jenkins(JOB_ID, build_id, artifacts)
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        w.delete()
        return

    expected = [os.path.join(path, a) for a in artifacts]
    for e in expected:
        if not os.path.exists(e):
            print(
                'FAIL %s: expected path "%s" does not exist after download'
                % (pretty, str(e))
            )
            w.delete()
            return

    unexpected = [os.path.join(os.path.dirname(path), 'last_completed')]
    for u in unexpected:
        if os.path.exists(u):
            print(
                'FAIL %s: unexpected path "%s" exists after filtered download'
                % (pretty, u)
            )

    w.delete()
    return True

# check that downloading with timeout works
@smoke
def t03():
    pretty = '%s t3' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    exc = None
    try:
        path = w.download_jenkins(JOB_ID, timeout=1)
        print('FAIL %s: download did not time out' % pretty)
        w.delete()
        return
    except Exception, e:
        exc = e
        pass

    # check the error message
    if 'timed out' not in str(e):
        print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
        w.delete()
        return

    w.delete()
    return True

# check that downloading to specific destination works
def t04():
    pretty = '%s t4' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    try:
        path = w.download_jenkins(JOB_ID, dst='foo')
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        w.delete()
        return

    if path != os.path.join(w.path, 'foo'):
        print('FAIL %s: unexpected destination directory: %s' % (pretty, path))
        w.delete()
        return

    w.delete()
    return True

# check that downloading to destination outside workspace fails
@smoke
def t05():
    pretty = '%s t5' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    try:
        path = w.download_jenkins(JOB_ID, dst='foo')
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        return

    if path != os.path.join(w.path, 'foo'):
        print('FAIL %s: unexpected destination directory: %s' % (pretty, path))
        w.delete()
        return

    w.delete()
    return True

# check that the proper exception is thrown if JenkinsJob.load() times out
def t06():
    pretty = '%s t6' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;

    exc = None
    try:
        job = JenkinsJob(w.config['jenkins'], JOB_ID)
        job.load(timeout=0.000001) # let's hope this is small enough to fail
        print('FAIL %s: JenkinsJob.load() did not time out' % pretty)
        w.delete()
        return
    except Exception, e:
        exc = e
    if 'timed out' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
        w.delete()
        return

    w.delete()
    return True

# check that JenkinsJob.last_successful() works
@smoke
def t07():
    pretty = '%s t7' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;
    job = JenkinsJob(w.config['jenkins'], JOB_ID)

    try:
        job.load()
        build = job.last_successful()
    except Exception, e:
        print('FAIL %s: got exception: %s' % (pretty, str(e)))
        w.delete()
        return

    if build.job != JOB_ID:
        print('FAIL %s: wrong return value: %s' % (pretty, str(build)))
        w.delete()
        return

    w.delete()
    return True

# check that JenkinsJob.all_builds() works
@smoke
def t08():
    pretty = '%s t8' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;
    job = JenkinsJob(w.config['jenkins'], JOB_ID)

    try:
        job.load()
        all_builds = job.all_builds()
    except Exception, e:
        print('FAIL %s: got exception: %s' % (pretty, str(e)))
        w.delete()
        return

    # look for a particular job in all_builds
    last = job.last_completed()
    if last not in all_builds:
        print(
            'FAIL %s: last complete build not in all builds: %s'
            % (pretty, str(all_builds))
        )
        w.delete()
        return

    w.delete()
    return True

# check that JenkinsJob.last_completed() works
def t09():
    pretty = '%s t9' % __file__
    print(pretty)

    w = Workspace()
    w.config['jenkins'] = JENKINS;
    job = JenkinsJob(w.config['jenkins'], JOB_ID)

    try:
        job.load()
        build = job.last_completed()
    except Exception, e:
        print('FAIL %s: got exception: %s' % (pretty, str(e)))
        w.delete()
        return

    if build.job != JOB_ID:
        print('FAIL %s: wrong return value: %s' % (pretty, str(build)))
        w.delete()
        return

    w.delete()
    return True

# check that base parameter works, ie overrides jenkinshost in config file
# use the same base as in config file
def t10():
    pretty = '%s t10' % __file__
    print(pretty)

    w   = Workspace()
    w.config['jenkins'] = JENKINS;
    dst = 'downloads'

    sameBase = w.config['jenkins']

    try:
        path = w.download_jenkins(JOB_ID, base=sameBase,  dst=dst)
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        return

    expected = [
        os.path.join(os.path.dirname(path), dst),
        os.path.join(path, 'testArtifact.apk'),
        os.path.join(path, 'testArtifact.apk.1')
    ]
    for e in expected:
        if not os.path.exists(e):
            print(
                'FAIL %s: expected path "%s" does not exist after download'
                % (pretty, e)
            )
            w.delete()
            return

    w.delete()
    return True

# check that base parameter works, ie overrides jenkinshost in config file
# use other base as in config file
@smoke
def t11():
    pretty = '%s t11' % __file__
    print(pretty)

    w   = Workspace()
    dst = 'downloads'

    # The same job is available in both regular and platform cluster
    regularBase = 'http://android-ci.cnbj.sonyericsson.net'
    platformBase = 'http://android-ci-platform.cnbj.sonyericsson.net'

    if w.config['jenkins'] == regularBase:
        otherBase = platformBase
    else:
        otherBase = regularBase

    try:
        path = w.download_jenkins(JOB_ID, base=otherBase, dst=dst)
    except Exception, e:
        print('FAIL %s: download failed: %s' % (pretty, str(e)))
        return

    expected = [
        os.path.join(os.path.dirname(path), dst),
        os.path.join(path, 'testArtifact.apk'),
        os.path.join(path, 'testArtifact.apk.1')
    ]
    for e in expected:
        if not os.path.exists(e):
            print(
                'FAIL %s: expected path "%s" does not exist after download'
                % (pretty, e)
            )
            w.delete()
            return

    w.delete()
    return True

# check that a faulty base parameter is handled correctly
def t12():
    pretty = '%s t12' % __file__
    print(pretty)

    w   = Workspace()
    dst = 'downloads'

    # Faulty base
    bananaBase = 'http://android-ci.bananas.net'
    nap = 5

    exc = None
    try:
        path = w.download_jenkins(JOB_ID, base=bananaBase, dst=dst, timeout=nap)
    except Exception, e:
        exc = e
    if 'timed out' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(exc)))
        w.delete()
        return

    w.delete()
    return True

# check that an empty artifacts list raises exception
def t13():
    pretty = '%s t13' % __file__
    print(pretty)

    base = 'http://android-ci.cnbj.sonyericsson.net'
    build = '7' # no artifacts in this build, for sure

    w = Workspace()
    try:
        w.download_jenkins(JOB_ID, build, timeout=300, base=base)
        print('FAIL %s: did not raise exception' % pretty)
        w.delete()
        return False
    except Exception, e:
        if not str(e).startswith('job has no artifacts'):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            w.delete()
            return False

    if os.listdir(w.path):
        print('FAIL %s: directory left after failure: %s' % (pretty, w.path))
        w.delete()
        return False

    w.delete()
    return True

# Verify Exceptions for badly formatted jenkins config
@with_workspace
def t14(w):
    pretty = '%s t14' % __file__
    print(pretty)

    config_key = "auth"
    config_file = "jenkins.json"

    base = os.path.join(w.path, '.ave', 'config')
    os.makedirs(base)

    # Key but invalid data type
    config = {
        config_key: 1
    }
    with open(os.path.join(base, config_file), 'w') as f:
        json.dump(config, f, indent=4)

    try:
        authkeys = load_jenkins(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'value of "%s" is not a dict' % config_key not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    # No data for host defined
    config[config_key] = {'host.sonyericsson.net': None}
    with open(os.path.join(base, config_file), 'w') as f:
        json.dump(config, f, indent=4)

    try:
        authkeys = load_jenkins(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'value of "host.sonyericsson.net" is not a dict' not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False

    # No method defined for host
    config[config_key] = {'host.sonyericsson.net': {'user':'me', 'Password':'ssh'}}
    with open(os.path.join(base, config_file), 'w') as f:
        json.dump(config, f, indent=4)

    try:
        authkeys = load_jenkins(w.path)
        print('FAIL %s: could load invalid config: %s' % (pretty, authkeys))
        return False
    except Exception, e:
        if 'have no "method" defined:' not in unicode(e):
            print('FAIL %s: wrong error: %s' % (pretty, e))
            return False


    return True

# Verify that trying to access protected jenkins without authentication throws
# the correct exception
@with_workspace
def t15(home):
    pretty = '%s t15' % __file__
    print(pretty)

    # Making sure that we don't actually use real config that might have access
    create_default(home.path)
    w = Workspace(home=home.path)
    try:
        w.download_jenkins(JOB_ID, base=JENKINS_WITH_AUTH)
    except Exception, e:
        if "requires authentication" not in str(e) \
                or "please add to jenkins.json" not in str(e):
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False
        return True
    finally:
        w.delete()

    print('FAIL %s: No Exception caught' % pretty)
    return False



# Verify that using incorrect credentials to a jenkins server throws the
# correct exception
@with_workspace
def t16(home):
    pretty = '%s t16' % __file__
    print(pretty)

    config_key = "auth"
    config_file = "jenkins.json"

    create_default(home.path)
    authkeys = load_jenkins(home.path)
    authkeys[config_key] = {JENKINS_WITH_AUTH: {'method': 'basic',
                                                'user': '<username>',
                                                'password': '<password>'}}

    path = os.path.join(home.path, '.ave', 'config', config_file)
    with open(path, 'w') as f:
        json.dump(authkeys, f, indent=4)

    w = Workspace(home=home.path)
    try:
        w.download_jenkins(JOB_ID, base=JENKINS_WITH_AUTH)
    except Exception, e:
        if "Invalid authentication to" not in str(e):
            print('FAIL %s: unexpected exception: %s' % (pretty, str(e)))
            return False
        return True
    finally:
        w.delete()


    print('FAIL %s: No Exception caught' % pretty)
    return False


# check that the proper exception is thrown if
# JenkinsJob.load_build_parameters() times out
def t17():
    pretty = '%s t17' % __file__
    print(pretty)

    w = Workspace()

    exc = None
    try:
        job = JenkinsJob(base=JENKINS_WITH_BUILD_PARAMETERS,
                         job=JOB_ID_WITH_BUILD_PARAMETERS)
        build = job.last_successful()
        build_parameters = build.load_build_parameters(timeout=0.000001)
        print('FAIL %s: JenkinsBuild.load_build_parameters() did not time '
              'out' % pretty)
        w.delete()
        return
    except Exception, e:
        exc = e
    if 'timed out' not in str(exc):
        print('FAIL %s: wrong error message: %s' % (pretty, str(e)))
        w.delete()
        return

    w.delete()
    return True


# check that JenkinsJob.build_parameters works
def t18():
    pretty = '%s t18' % __file__
    print(pretty)

    w = Workspace()
    job = JenkinsJob(base=JENKINS_WITH_BUILD_PARAMETERS,
                     job=JOB_ID_WITH_BUILD_PARAMETERS)

    try:
        job.load()
        build = job.last_successful()
        build_parameters = build.build_parameters
        product = build_parameters['PRODUCT']
    except Exception, e:
        print('FAIL %s: got exception: %s' % (pretty, str(e)))
        w.delete()
        return

    w.delete()
    return True
