# Copyright (C) 2014 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import os
import sys
import vcsjob
import base64
import uuid
import time

import ave.config
import ave.panotti
from ave.broker.exceptions import Busy
from ave.broker.exceptions import NoSuch
from ave.exceptions import AveException

from datetime import datetime
from ave.broker import Broker
from ave.utils.logger import Logger

MAX_RETRY = 10

class TestJob(object):
    SETUP = 'SETUP'
    PRE = 'PRE'
    MAIN = 'MAIN'
    POST = 'POST'
    TEARDOWN = 'TEARDOWN'

    LOCAL_GUID_PREFIX = 'LOCAL_GUID_'

    def __init__(self):
        try:
            self.guid = vcsjob.get_guid()
        except Exception, e:
            if e.message != 'guid not set':
                raise e
            random_string = str(base64.urlsafe_b64encode(uuid.uuid1().bytes))\
                .rstrip('=').lstrip('_')
            self.guid = '%s%s' % (self.LOCAL_GUID_PREFIX, random_string)

        retry = 0
        while True:
            try:
                self.broker = Broker()
                self.logger_broker = Broker()
                self.logger_workspace = self.logger_broker.get(
                    {'type': 'workspace'}
                )
                self.logger = Logger(self.logger_workspace, self.guid)
                self.flocker_session_key = self.logger.flocker_session_key
                break
            except Exception, e:
                retry += 1
                if retry <= MAX_RETRY:
                    print('Exception while initiating Test Job No Logger active: %s'
                          ' Will try again.' % e)
                    time.sleep(retry / 2.0 + 1)
                    continue
                else:
                    print('Exception while initiating Test Job No Logger active: %s'
                          % e)
                    sys.exit(vcsjob.ERROR)

        try:
            self.logger.log_it('i', 'GUID is set to: %s' % self.guid)
            panotti_status = self.panotti_enabled()
            log_level = 'i' if panotti_status else 'w'
            self.logger.log_it(
                log_level,
                'Shout to Panotti is set to: {status} in config'.format(
                    status='Enabled' if panotti_status else 'Disabled'))
            if not panotti_status:
                self.logger.log_it('w', 'It will not be able to locate log '
                                        'files in Panotti')
            self.test_job_status = None
            self.broker = Broker()
            self.start_time = datetime.now()
            self.update_status(vcsjob.OK)
            # check if build_url is set from outside
            if 'BUILD_URL' in os.environ:
                self.build_url = os.environ['BUILD_URL']
            else:
                self.build_url = None
            # check if team set from outside
            if 'TEAM' in os.environ:
                self.team = os.environ['TEAM']
            else:
                self.team = 'no team'
            # check if banner set from outside
            if 'BANNER' in os.environ:
                self.banner = os.environ['BANNER']
            else:
                self.banner = 'no banner'
            self.iteration = None
            self.logger.log_it('d', 'Banner: %s' % self.banner)
            self.branch = None
            self.compatible_mode = False
            # serial as key, HandsetWorkspaceData object as value
            self.handset_workspace_data_dict = {}

        except Exception, e:
            self.logger.log_it('e', 'Exception while initiating Test Job: %s'
                                    % e)
            sys.exit(vcsjob.ERROR)

    def panotti_enabled(self):
        home = ave.config.load_etc()['home']
        try:
            panotti_config = ave.panotti.load_configuration(
                ave.panotti.get_configuration_path(home=home))
        except Exception as e:
            self.logger.log_it('w', 'Could not locate panotti config,'
                                    'exception caught: {e}'.format(e=str(e)))
            return False
        if not ('enabled' in panotti_config and panotti_config['enabled']):
            return False
        return True

    def update_status(self, test_job_status):
        if self.test_job_status == vcsjob.BUSY:
            self.logger.log_it('i', 'No update of test job status BUSY '
                                    'already set, trying to set %s' %
                                    vcsjob.exit_to_str(test_job_status))
        elif self.test_job_status == vcsjob.ERROR:
            self.logger.log_it('i', 'No update of test job status ERROR '
                                    'already set, trying to set %s' %
                                    vcsjob.exit_to_str(test_job_status))
        elif (self.test_job_status == vcsjob.FAILURES and
                test_job_status in [vcsjob.OK, vcsjob.FAILURES]):
            self.logger.log_it('i', 'No update of test job status FAILURES '
                                    'already set, trying to set %s' %
                                    vcsjob.exit_to_str(test_job_status))
        elif (self.test_job_status == vcsjob.OK and
                test_job_status == vcsjob.OK):
            self.logger.log_it('d', 'No update of test job status OK '
                                    'already set, trying to set %s' %
                                    vcsjob.exit_to_str(test_job_status))
        elif test_job_status in [vcsjob.OK, vcsjob.FAILURES,
                                 vcsjob.ERROR, vcsjob.BUSY]:
            self.test_job_status = test_job_status
            self.logger.log_it('i', 'test job status updated to %s' %
                                    vcsjob.exit_to_str(test_job_status))
        else:
            raise Exception('Setting status %s is not allowed in test '
                            'jobs' % vcsjob.exit_to_str(test_job_status))

    def equipment_assignment(self, profiles):
        msg = '''
        Equipment_assignment function must be overridden in child class. The
        function should only contain one line where all equipment is assigned
        in one call to broker.get.

        If only one handset is allocated, for example:
        self.h1, self.w1 = self.broker.get(*profiles)
        self.register_handset_workspace(h1,w1)

        If two or more handsets are allocated, for example:
        self.h1, self.w1, self.h2, self.w2 = self.broker.get(*profiles)
        self.register_handset_workspace(h1,w1)
        self.register_handset_workspace(h2,w2)
        '''
        raise Exception(msg)


    def allocate_equipment(self):
        profiles = vcsjob.get_profiles()
        self.logger.log_it('d', 'Try to allocate based on profiles: %s'
                                % profiles)
        self.equipment_assignment(profiles)

    def register_handset_workspace(self, handset, workspace):
        try:
            workspace.flocker_initial(existing_key=self.flocker_session_key)
        except Exception, e:
            if '550 Failed to change directory' in str(e):
                # The failure only happens if master and slave are located in
                # different site. In this situation, we create a new key:
                # [self.flocker_session_key]_[random string]
                workspace.flocker_initial(custom_key=self.flocker_session_key)
            else:
                raise

        key = handset.get_profile()['serial']
        self.handset_workspace_data_dict[key] = HandsetWorkspaceData(handset, workspace)

    def get_handset_workspace_data(self, handset):
        if handset is None and self.compatible_mode:
            # For backwards compatibility
            handset = self.handset
        elif handset is None and not self.compatible_mode:
            raise Exception('Parameter "handset" must be set when multiple '
                            'handset were registered.')

        return self.handset_workspace_data_dict[handset.get_profile()['serial']]

    def setup(self):
        self.allocate_equipment()

        # For backwards compatibility
        if not self.handset_workspace_data_dict:
            self.register_handset_workspace(self.handset, self.workspace)
            self.compatible_mode = True

        self.print_handset_info()

        for jd in self.handset_workspace_data_dict.values():
            jd.sw = jd.handset.get_build_label()
            if jd.sw == 'private':
                try:
                    jd.sw = jd.handset.get_property('persist.private_sw_id')
                except Exception as e:
                    self.logger.log_it('w',
                                       'Failed to fetch persist.private_sw_id '
                                       'as property (%s)' % e,
                                       jd.handset)

        self.sw = self.handset_workspace_data_dict.values()[0].sw
        self.logger.log_it('d', 'Build label: %s' % self.sw)
        # For backwards compatibility, keep those variable
        if self.compatible_mode is True:
            hwd = self.handset_workspace_data_dict.values()[0]
            self.hw = hwd.hw
            self.serial = hwd.serial
            self.results_directory = hwd.results_directory

    def pre(self):
        self.logger.log_it('d', 'Running pre iteration %d' % self.iteration)
        for jd in self.handset_workspace_data_dict.values():
            jd.handset.wait_power_state('boot_completed', 600)
            self.logger.log_it('d', 'Handset in power state "boot_completed"', jd.handset)

    def main(self):
        raise Exception('main function must be overridden in child class')

    def post(self):
        self.logger.log_it('d', 'Running post iteration %d' % self.iteration)
        for jd in self.handset_workspace_data_dict.values():
            jd.handset.wait_power_state('boot_completed', 600)
            self.logger.log_it('d', 'Handset in power state "boot_completed"', jd.handset)

    def teardown(self):
        self.evaluate_results()

    def evaluate_results(self):
        raise Exception('evaluate_results function must be overridden in child '
                        'class')

    def _execute(self, nr_of_iterations=1):
        finished = False
        next_state = TestJob.SETUP
        self.iteration = 1
        while not finished:
            if next_state == TestJob.SETUP:
                try:
                    # set next state to TEARDOWN, if setup does not fail it
                    # will be set to PRE instead
                    next_state = TestJob.TEARDOWN
                    self.setup()
                    next_state = TestJob.PRE
                except Busy, e:
                    self.update_status(vcsjob.BUSY)
                    self.logger.log_it('w', '%s' % str(e))
                except NoSuch, e:
                    self.update_status(vcsjob.BUSY)
                    self.logger.log_it('w', '%s' % str(e))
                except AveException, e:
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run setup. '
                                            'Ave Exception: %s\n%s'
                                            % (str(e), e.format_trace()))
                except Exception, e:
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run setup: %s' % e)

            elif next_state == TestJob.PRE:
                try:
                    self.pre()
                    next_state = TestJob.MAIN
                except AveException, e:
                    next_state = TestJob.POST
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run pre in iteration '
                                            '%d. Ave Exception: %s\n%s'
                                            % (self.iteration, str(e),
                                               e.format_trace()))
                except Exception, e:
                    next_state = TestJob.POST
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run pre in iteration '
                                            '%d: %s' % (self.iteration, e))
            elif next_state == TestJob.MAIN:
                try:
                    self.main()
                    next_state = TestJob.POST
                except AveException, e:
                    next_state = TestJob.POST
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run main in iteration '
                                            '%d. Ave Exception: %s\n%s'
                                            % (self.iteration, str(e),
                                               e.format_trace()))
                except Exception, e:
                    next_state = TestJob.POST
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run main in iteration '
                                            '%d: %s' % (self.iteration, e))
            elif next_state == TestJob.POST:
                try:
                    self.post()
                    self.iteration += 1
                    if self.test_job_status != vcsjob.ERROR and \
                            self.iteration <= nr_of_iterations:
                        next_state = TestJob.PRE
                    else:
                        next_state = TestJob.TEARDOWN
                except AveException, e:
                    next_state = TestJob.TEARDOWN
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run post in iteration '
                                            '%d. Ave Exception: %s\n%s'
                                            % (self.iteration, str(e),
                                               e.format_trace()))
                except Exception, e:
                    next_state = TestJob.TEARDOWN
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run post in iteration '
                                            '%d: %s' % (self.iteration, e))
            elif next_state == TestJob.TEARDOWN:
                try:
                    self.teardown()
                except AveException, e:
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run teardown. '
                                            'Ave Exception: %s\n%s' %
                                            (str(e), e.format_trace()))
                except Exception, e:
                    self.update_status(vcsjob.ERROR)
                    self.logger.log_it('e', 'Failed to run teardown: %s' % e)

                finished = True

    def execute(self, nr_of_iterations=1):
        if self.test_job_status == vcsjob.ERROR:
            sys.exit(self.test_job_status)

        self._execute(nr_of_iterations=nr_of_iterations)

        self.logger.log_it('i', 'Exiting test job with Status: %s' %
                                vcsjob.exit_to_str(self.test_job_status))
        sys.exit(self.test_job_status)

    def print_handset_info(self):
        self.logger.log_it('i', 'Print Allocated Handsets:')
        for jd in self.handset_workspace_data_dict.values():
            handset_profile = jd.handset.get_profile()
            self.logger.log_it('i', 'Print the handset [%s] profile:' % jd.serial)
            for key in handset_profile:
                self.logger.log_it('i',
                                   '   %s = %s' % (key, handset_profile[key]),
                                   jd.handset)

            label = jd.handset.get_build_label()
            sim = jd.handset.get_gsm_operator()

            self.logger.log_it('i', '   label = %s' % label, jd.handset)
            self.logger.log_it('i', '   SIM = %s' % sim, jd.handset)

    def find_suitable_label(self, handset=None):
        # Special handling for commit builds where we do not have any knowledge
        # of branch or label
        jd = self.get_handset_workspace_data(handset)
        label = jd.handset.get_build_label()
        if label == 'private':
            branch = self.branch
            if branch is not None:
                try:
                    label = ave.label.get_latest(branch)
                except Exception as e:
                    raise Exception('Failed to read label for job,'
                                    'original error: %s)' % str(e),
                                    jd.handset)
        return label

class HandsetWorkspaceData(object):

    def __init__(self, handset, workspace):
        self.handset = handset
        self.workspace = workspace
        self.results_directory = workspace.make_tempdir()
        self.sw = None
        self.hw = handset.get_property('ro.product.model')
        self.serial = handset.get_profile()['serial']
        try:
            # Reading imei info and matching 15 digit number
            resp = handset.shell('dumpsys iphonesubinfo')
            import re
            self.imei = re.findall('\d{15}', resp)[0]
        except:
            self.imei = ''
        self.instrumentation_report = None
        self.build_handler = None
        self.logcat_handler = None
        self.crash_handler = None
        self.run = None
        self.junit_test_completed = False

    # Add new variable if need
    def set(self, name, value):
        setattr(self, name, value)
