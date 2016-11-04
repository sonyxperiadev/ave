# Copyright (C) 2013 Sony Mobile Communications Inc.
# All rights, including trade secret rights, reserved.

import ave.apk
import ave.cmd
import ave.git
import ave.ftpclient      as ftpclient
import ave.config

from ave.jenkins            import JenkinsJob, JenkinsBuild
from ave.profile            import Profile




import importlib

from ave.profile            import Profile
from base_workspace     import BaseWorkspaceProfile
from base_workspace     import BaseWorkspace
import base_workspace

def _cfg_find_subclass(info):
    import ave.config
    home = ave.config.load_etc()['home']
    cfg_path = BaseWorkspace.default_cfg_path(home)
    config = BaseWorkspace.load_config(cfg_path, home)

    if 'subclass' in config:
        subclass = config['subclass'][info]
        module = importlib.import_module("ave."+subclass.split('.')[0])
        return getattr(module,subclass.split('.')[1])
    return None

class WorkspaceProfile(BaseWorkspaceProfile):
    def __new__(cls, profile):
        subclass = _cfg_find_subclass("WorkspaceProfile")
        if subclass:
            return subclass(profile)
        return BaseWorkspaceProfile(profile)

def validate_configuration(config, home):
    subclass = _cfg_find_subclass("validate_configuration")
    if subclass:
        return subclass(config, home)
    return base_workspace.validate_configuration(config, home)

class Workspace(BaseWorkspace):
    def __new__(cls, uid=None, cfg_path=None, config=None, home=None):
        subclass = _cfg_find_subclass("Workspace")
        if subclass:
            return subclass(uid, cfg_path, config, home)
        return BaseWorkspace(uid, cfg_path, config, home)
