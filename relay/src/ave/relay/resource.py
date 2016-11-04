# Copyright (C) 2014 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import ave.config

from ave.relay.server       import RemoteRelayServer
from ave.network.exceptions import ConnectionClosed, Restarting

class Relay(RemoteRelayServer):
    profile = None

    def __init__(self, profile, address=None, home=None):
        if not home:
            home = ave.config.load_etc()['home']
        admin = ave.config.load_authkeys(home)['admin']
        RemoteRelayServer.__init__(self, address, authkey=admin, home=home)
        self.profile = profile

    def get_profile(self):
        return self.profile

    def set_circuit(self, circuit, high):
        if circuit not in self.profile['circuits']:
            raise Exception('named circuit not in allocated relay: %s'% circuit)
        try:
            return self.set_board_circuit(self.profile, circuit, high)
        except (ConnectionClosed, Restarting), e:
            self._connection = None # force reconnect and retry once
            return self.set_board_circuit(self.profile, circuit, high)

    def reset(self):
        try:
            return self.reset_board_group(self.profile)
        except (ConnectionClosed, Restarting), e:
            self._connection = None # force reconnect and retry once
            return self.reset_board_group(self.profile)
