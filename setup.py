"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from setuptools.command.install import install
# To use a consistent encoding
from codecs import open
from os import path
import subprocess
import sys
import os
import shutil
import psutil
import json

BROKER_PID_PATH = '/var/tmp/ave-broker.pid'
RELAY_PID_PATH = '/var/tmp/ave-relay.pid'
ADB_SERVER_PID_PATH = '/var/tmp/ave-adb-server.pid'

here = path.abspath(path.dirname(__file__))


def run(cmd):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode:
        print(err)
        sys.exit(1)
    else:
        return out


def is_running(pid_path):
    if os.path.exists(pid_path):
        return True
    else:
        return False

def initial_ave():
    # create /etc/ave/user if it doesn't exist
    import ave.config
    try:
        user = ave.config.create_etc()
    except Exception, e:
        print('ERROR: Installation failed: %s' % e)
        return 1

    # become the run-as user before checking/generating config files
    try:
        import ave.persona
        home = ave.persona.become_user(user)
    except Exception, e:
        print('ERROR: Could not become user %s' % user)
        return 2

    # create the default AVE configuration
    try:
        ave.config.create_default(home)
    except Exception, e:
        print(
            'ERROR: Could not create configuration files for %s: %s'
            % (user, str(e))
        )
        return 3


def post_install():
    initial_ave()

    import ave.config
    import ave.cmd
    import ave.relay.config

    try:
        etc = ave.config.load_etc()
        try:
            path = ave.relay.config.write_devantech_config(etc['home'])
        except Exception, e:
            if 'will not overwrite' in str(e):
                pass
            raise
        os.chown(path, etc['uid'], -1)
    except Exception, e:
        print('WARNING: could not write default config file: %s' % e)

    # Start adb server
    etc = ave.config.load_etc()
    home = etc['home']
    path = os.path.join(home, '.ave', 'config', 'adb_server.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            config = {'demote': False, 'persist': True}
            json.dump(config, f)
        os.chown(path, etc['uid'], -1)  # let user own the file

    # start the service if it wasn't already running. other do nothing
    # as a restart of the ADB server would interfere with all running
    # test jobs that communicate with handsets. the user has to do a
    # restart manually if this is neccessary.
    if not is_running(ADB_SERVER_PID_PATH):
        ave.cmd.run(['/usr/bin/ave-adb-server', '--start'])

    # Start/Restart broker
    if is_running(BROKER_PID_PATH):
        ave.cmd.run(['/usr/bin/ave-broker', '--restart'])
    else:
        ave.cmd.run(['/usr/bin/ave-broker', '--start', '--force'])

    # Start/Restart relay
    if is_running(RELAY_PID_PATH):
        ave.cmd.run(['/usr/bin/ave-relay', '--restart'])
    else:
        ave.cmd.run(['/usr/bin/ave-relay', '--start', '--force'])

class custom_install(install):
    def run(self):
        install.run(self)
        self.execute(post_install, [], msg="Running post install task")


# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


# Build libfdtx in common
def build_libfdtx():
    root = here + '/common/src/libfdtx'
    run(['make', '-C', root, 'clean'])
    run(['make', '-C', root, 'libfdtx.so'])
    return 'common/src/libfdtx/libfdtx.so'


# Build Galatea
galatea_src = here + '/galatea/galatea-main/build/outputs/apk/galatea-main-release.apk'
galatea_dst = here + '/galatea/latest/galatea.apk'
if os.path.exists(galatea_src):
    shutil.copy(galatea_src, galatea_dst)

libfdtx = build_libfdtx()

# Copy workspace/src/ave to common/src/ave
src = here + '/workspace/src/ave'
dst = here + '/common/src/ave'
for fname in os.listdir(src):
    shutil.copy(src + '/' + fname, dst)

# Clean __init__.py
for root, dirs, files in os.walk(here):
    for fname in files:
        if 'ave/broker' in root or 'vcsjob' in root:
            continue
        if fname == '__init__.py':
            f = open(os.path.join(root, fname), 'w')
            f.close()

setup(
    name='ave',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.0.1',

    description='AVE Python project',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/sonyxperiadev/ave',

    # Author details
    author='The Python Packaging Authority',
    author_email='junji.shimagaki@sonymobile.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='Automated Verification Environment',
    packages=['ave', 'ave.broker', 'ave.broker.tools', 'ave.gerrit', 'ave.handset',
              'ave.adb', 'ave.relay', 'vcsjob', 'ave.network', 'ave.utils'],
    package_dir={'ave': 'common/src/ave',
                 'ave.network': 'common/src/ave/network',
                 'ave.utils': 'utils/src/ave/utils',
                 'ave.broker': 'broker/src/ave/broker',
                 'ave.broker.tools': 'broker/src/ave/broker/tools',
                 'ave.gerrit': 'gerrit/src/ave/gerrit',
                 'ave.handset': 'handset/src/ave/handset',
                 'ave.adb': 'handset/src/ave/adb',
                 'ave.relay': 'relay/src/ave/relay',
                 'vcsjob': 'vcsjob/src/vcsjob'
                 },

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['oursql', 'psutil', 'coverage', 'pyserial'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
    #     'dev': ['oursql'],
    #     'test': ['coverage'],
    # },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #     'sample': ['package_data.dat'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=[('/usr/bin', ['common/bin/ave-config', 'broker/bin/ave-broker',
                              'handset/bin/ave-adb-server', 'relay/bin/ave-relay',
                              'vcsjob/bin/vcsjob']),
                ('/usr/lib', [libfdtx]),
                ('/etc/init', ['broker/etc/init/ave-broker.conf',
                               'handset/etc/init/ave-adb-server.conf',
                               'relay/etc/init/ave-relay.conf']),
                ('/usr/share/ave/handset', ['handset/usr/share/ave/handset/handset.json']),
                ('/etc/udev/rules.d', ['relay/etc/udev/rules.d/10-devantech.rules']),
                ('/usr/share/ave/workspace', ['workspace/usr/share/ave/workspace/emma.jar']),
                ('/usr/share/ave/galatea', ['galatea/latest/galatea.apk'])],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # entry_points={
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
    cmdclass={'install': custom_install}
)
