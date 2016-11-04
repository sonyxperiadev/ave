# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

import os
import sys
import copy
import traceback
import json

import ave.config

from ave.relay.server        import RemoteRelayServer
from ave.relay.resource      import Relay
from ave.network.exceptions  import ConnectionClosed, ConnectionTimeout
from ave.workspace           import Workspace
from ave.broker.profile      import *
from ave.broker.session      import Session, RemoteSession

from constants  import *
from exceptions import *

def validate_profile(profile):
    if not isinstance(profile, Profile):
        try:
            profile = profile_factory(profile)
        except Exception, e:
            raise Exception('invalid profile: %s' % profile)
    return profile

class Allocator(object):
    ws_profile  = None # the profile used for all workspace allocation
    workspaces  = None # currently available workspaces
    equipment   = None
    stacks      = None
    allocations = None
    collateral  = None

    def __init__(self):
        self.equipment   = []
        self.stacks      = []
        self.allocations = {}  # Profile -> (RemoteSession,
                               #     [CollateralProfile, ...])
        self.collateral  = {}  # Profile -> [RemoteSession, ...]

    ### WORKSPACES #############################################################

    def set_ws_profile(self, profile):
        if 'uid' in profile:
            raise Exception(
                'cannot set generic workspace profile with uid: %s'
                % str(profile)
            )
        self.ws_profile = validate_profile(profile)

    def list_workspaces(self, profile):
        if not profile:
            return [w for w in self.equipment if isinstance(w, BaseWorkspaceProfile)]
        return [w for w in self.equipment if w.match(profile)]

    def list_resources(self, profile=None):
        result = self.list_equipment(profile)
        result.extend(self.list_workspaces(profile))
        return result

    def match_workspaces(self, profile):
        profile = validate_profile(profile)
        # check if the profile specifies the uid of an existing workspace, e.g.
        # to connect more than one handset to the same workspace.
        if profile in self.equipment:
            index    = self.equipment.index(profile)
            resource = self.equipment[index]
            if resource.match(profile):
                return resource
            raise Exception(
                'existing workspace does not fully match request: %s' % resource
            )
        # try matching the generic profile instead
        if not self.ws_profile.match(profile):
            raise Exception(
                'profile does not match generic configuration: %s'
                % str(self.ws_profile)
            )
        return self.ws_profile

    ### EQUIPMENT ##############################################################

    def allocate(self, resource, session, collateral):
        # check that the resource is not already allocated, except workspaces
        # which may be allocated to the same session multiple times.
        if isinstance(resource, BaseWorkspaceProfile):
            owner = self.get_owner(resource)
            if owner == session:
                pass
            elif owner == None:
                # workspaces have no collateral. add empty list
                self.allocations[resource] = (session, [])
            else:
                raise Busy('resource already allocated: %s' % resource)
            return
        # resource is real equipment:
        if resource in self.allocations:
            raise Busy('resource already allocated: %s' % resource)
        self.allocations[resource] = (session, collateral)
        for c in collateral:
            if c not in self.collateral:
                self.collateral[c] = []
            self.collateral[c].append(session)

    def list_equipment(self, profile=None):
        if not profile:
            return copy.copy(self.equipment)
        return [e for e in self.equipment if e.match(profile)]

    def list_available(self, profile):
        result = self.list_equipment(profile)
        result = [
            r for r in result
            if not (self.is_allocated(r) or self.has_collateral(r))
        ]
        return result

    def list_allocated(self, profile):
        result = self.list_equipment(profile)
        result = [
            r for r in result
            if (self.is_allocated(r))
        ]
        return result

    def list_allocations(self, session):
        result  = []
        for profile in self.allocations:
            if session in [None, self.get_owner(profile)]:
                result.append(profile)
        return result

    def list_collateral(self, session):
        result  = []
        for resource in self.allocations:
            if session in [None, self.get_owner(resource)]:
                result.extend(self.get_collateral(resource))
        return list(set(result))

    def is_available(self, profile):
        profile = validate_profile(profile)
        return (
            profile not in self.allocations
            and not self.has_collateral(profile)
        )

    def has_collateral(self, profile):
        if profile not in self.collateral:
            return False
        return self.collateral[profile] != []

    def is_allocated(self, profile):
        return profile in self.allocations

    def get_collateral(self, resource):
        if resource not in self.allocations: # TODO: write water proof tests
            raise Exception('INTERNAL ERROR: resource is not allocated')
        return self.allocations[resource][COLLATERAL]

    def get_owner(self, resource):
        try:
            return self.allocations[resource][SESSION]
        except:
            return None

    ### STACKS #################################################################

    def set_stacks(self, stacks):
        self.stacks = []
        if type(stacks) != list:
            raise Exception('stacks must be a list of list of profiles')
        for s in stacks:
            self.add_stack(s)

    def add_stack(self, stack):
        if type(stack) != list:
            raise Exception('stacks must be a list of list of profiles')
        checked = []
        for p in stack:
            checked.append(validate_profile(p))
        self.stacks.append(checked)

    def list_stacks(self):
        return self.stacks

    def find_collateral(self, allocation):
        result = []
        for a in allocation:
            if isinstance(a, BaseWorkspaceProfile):
                continue # no collateral is possible
            for stack in self.stacks:
                if a not in stack:
                    continue
                for s in stack:
                    result.append(s)
        # profiles in the allocation should not be included in the collateral
        return [r for r in result if r not in allocation]

    def match_stack(self, session, stack, profiles):
        tmp_stack = copy.deepcopy(stack)

        def in_stack(stack, profile):
            for equipment in stack:
                try:
                    equipment = self.fill_profile(equipment)
                except: # equipment temporarily unavailable
                    return False
                if equipment.match(profile):
                    stack.remove(equipment)
                    return True
            return False
        for p in profiles:
            if isinstance(p, BaseWorkspaceProfile):
                continue # not handled here. stacks don't contain workspaces
            if not in_stack(tmp_stack, p):
                return False
        return True

    ### ALLOCATION #############################################################

    def simple_allocation(self, profiles):
        intended = []
        for p in profiles:
            if isinstance(p, BaseWorkspaceProfile):
                continue # workspaces are handled elsewere
            equipment = self.list_equipment(p)
            if not equipment:
                raise NoSuch('no such resource: %s' % p)
            equipment = self.list_available(p)
            if not equipment:
                raise Busy('all such equipment busy: %s' % p)
            intended.append(equipment[0])

        # if any stack contains the intended allocation, then the rest of the
        # stack has to be marked as collateral to avoid that different clients
        # get control over different parts of the same stack. such situations
        # would presumably cause side effects between the jobs.
        collateral = self.find_collateral(intended)
        for resource in collateral:
            if self.is_allocated(resource):
                raise Busy( # collateral never includes workspaces
                    'equipment shares collateral with a prior allocation'
                )

        return intended, collateral

    def complex_allocation(self, profiles, session):
        candidates = []
        for stack in copy.deepcopy(self.stacks):
            if self.match_stack(session, stack, profiles):
                candidates.append(stack)

        new_candidates = []
        for stack in candidates:
            keep = True
            for i in range(len(stack)):
                equipment = stack[i]
                if not self.is_available(equipment):
                    keep = False
                    break # try next candidate
                # try to replace the profile found in the stack with a fuller
                # profile provided by the equipment lister. if this fails, then
                # the equipment is unlikely to be useful even if it is available
                # TODO: use external equipment lister and trust the fill blindly
                try:
                    stack[i] = self.fill_profile(equipment)
                except:
                    keep = False
                    break
            if keep:
                new_candidates.append(stack)
        candidates = new_candidates

        if not candidates:
            raise Busy('cannot allocate all equipment together')

        # try to pick the shortest stack to avoid allocating equipment that
        # wasn't even requested. call it the "intended allocation" (as opposed
        # to "collateral", below)
        candidates.sort(cmp=lambda x,y: len(x)-len(y))
        ok = False
        for intended in candidates:
            # if any stack contains any intended allocation, then the whole
            # stack has to be marked as collateral to avoid that different
            # clients get control over different parts of the same stack. such
            # situations would presumably cause side effects between the jobs.
            collateral = self.find_collateral(intended)
            for resource in collateral:
                if self.is_allocated(resource):
                    break
            ok = True
            break
        if not ok:
            raise Busy('cannot allocate all equipment together')
        # intended now holds the chosen stack

        return intended, collateral

    def deallocate(self, resource):
        for c in self.allocations[resource][COLLATERAL]:
            self.collateral[c].remove(self.allocations[resource][SESSION])
        del self.allocations[resource]

    def yield_resource(self, session, resource):
        if resource not in self.allocations:
            raise NoSuch('no such resource')
        owner = self.get_owner(resource)
        if not owner:
            raise NotAllocated('no one owns this resource: %s' % resource)
        if owner != session:
            raise NotOwner('not owner of this resource: %s' % resource)
        collateral = self.get_collateral(resource)
        self.deallocate(resource) # modify the internal record
        return collateral

    ### OTHER ##################################################################

    def get_full_equipment_status(self):
        return copy.copy(self.equipment), self.serialize()

    def fill_profile(self, profile):
        hash(profile) # raises exception if profile does not contain unique id
        return self.list_equipment(profile)[0]

    def close_session(self, session):
        release    = [] # profiles of resources to be deallocated
        collateral = []
        for resource in self.allocations:
            if self.get_owner(resource) == session[REMOTE]:
                release.append(resource)
        for resource in release:
            collateral.extend(self.get_collateral(resource))
            self.deallocate(resource)
        return release,collateral

class ShareAllocator(Allocator):
    remote_address  = None

    def __init__(self, address):
        Allocator.__init__(self)
        self.remote_address = address

    def set_equipment(self, equipment, allocations):
        self.equipment = []
        for e in equipment:
            self.equipment.append( profile_factory(e) )

        self.deserialize_allocations(allocations)
        self.calculate_collateral()

    # return a JSON compatible representation. instead of authkeys an index is
    # used to build the dictionary
    def serialize(self):
        result = {} # { index: [{'profile': profile, 'collateral': []}, ...] }
        index = 0
        for profile in self.allocations:
            collateral = self.allocations[profile][COLLATERAL]
            if index not in result:
                result[index] = []
            result[index].append({'profile':profile, 'collateral':collateral})
            index += 1
        return result

    def deserialize_allocations(self, allocations):
        DUMMY_SESSION = 0  # placeholder for RemoteSession object in Collateral
                           # and Allocation information
        #First remove all allocations
        old_allocations  = self.allocations
        self.allocations = {}

        # Put back allocations made through this broker a.k.a where Session
        # is a real RemoteSession object
        for a in old_allocations:
            allocoation = old_allocations[a]
            if type(allocoation[SESSION]) is RemoteSession:
                self.allocations[a] = old_allocations[a]

        for authkey in allocations:
            for allocation_info in allocations[authkey]:
                allocation_profile = profile_factory(
                    allocation_info['profile'])

                collateral = allocation_info['collateral']
                collateral_profiles = []
                for c in collateral:
                    c_p = profile_factory(c)
                    collateral_profiles.append(c_p)
                # allocation_profile and collateral_profiles are now built
                # Loop through all allocations, add allocations that are not
                # already in the allocation list
                if not allocation_profile in self.allocations:
                    self.allocations[allocation_profile] = \
                        (DUMMY_SESSION, collateral_profiles)

    def calculate_collateral(self):
        # clear collateral to start
        self.collateral = {}

        # loop through all allocations and add their collateral-data to the
        # collateral register
        for a in self.allocations:
            allocation = self.allocations[profile_factory(a)]
            session    = allocation[SESSION]
            collateral = allocation[COLLATERAL]
            for c in collateral:
                if not c in self.collateral:
                    self.collateral[c] = []
                self.collateral[c].append(session)

    def get_resources(self, profiles, session):
        # make a distinction between simple and complex allocations. simple ones
        # include at most one piece of physical equipment.
        if len([p for p in profiles if not isinstance(p, BaseWorkspaceProfile)]) > 1:
            intended, collateral = self.complex_allocation(profiles, session)
        else:
            intended, collateral = self.simple_allocation(profiles)

        for resource in intended:
            self.allocate(resource, session, collateral) # set internal records

        # let the broker know that the request can probably be satisfied, but
        # that it has to be retried at the share that has the resources
        raise Shared()

    def yield_resource(self, session, resource):
        _ = Allocator.yield_resource(self, session, resource)
        self.equipment.remove(resource)
        return [] # collateral not released

    def close_session(self, session):
        release,_ = Allocator.close_session(self, session)
        for r in release:
            self.equipment.remove(r)
        return [] # nothing to release

class LocalAllocator(Allocator):
    home        = None
    ws_cfg      = None # do NOT use defaults for workspace configuration
    ws_profile  = None

    def __init__(self, home, ws_cfg):
        Allocator.__init__(self)
        self.home        = home
        self.ws_cfg      = ws_cfg
        self._relay_srv  = None # RemoteRelayServer
        self.testdrive   = None # TestDriveInterface
        try:
            from ave.positioning.spirent import NoConfig, BadConfig,\
            TestDriveInterface
            self.testdrive = TestDriveInterface(timeout=1, home=self.home)
            spirent_profile = self.testdrive.get_profile()
            self.equipment.append(spirent_profile)
        except ImportError:
            pass
        except NoConfig:
            pass # ignore. most users will not have a Spirent lab configuration
        except BadConfig, e:
            print('ERROR: Bad spirent configuration: %s' % e)

    def add_equipment(self, profiles):
        checked = []
        for p in profiles:
            checked.append(validate_profile(p))
        for p in checked:
            # equipment can be added more than once (updated)
            hash(p) # cause exception if not unique
            if p in self.equipment:
                if ('pretty' not in p) or (not p['pretty']):
                    for e in self.equipment:
                        if e == p and 'pretty' in e:
                            p['pretty'] = e['pretty']
                self.equipment.remove(p) # replace found item below
        self.equipment.extend(checked)

    # return a JSON compatible representation. all RemoteSession references are
    # reduced to their authkeys
    def serialize(self):
        result = {} # { authkey: [{'profile': profile, 'collateral': []}, ...] }
        for profile in self.allocations:
            authkey    = self.allocations[profile][SESSION].authkey
            collateral = self.allocations[profile][COLLATERAL]
            if authkey not in result:
                result[authkey] = []
            result[authkey].append({'profile':profile, 'collateral':collateral})
        return result

    def list_handsets(self, profile):
        if not profile:
            return [e for e in self.equipment if type(e) == HandsetProfile]
        if profile['type'] != 'handset':
            return []
        return [e for e in self.equipment if e.match(profile)]

    def list_beryllium_rigs(self, profile):
        if not profile:
            return [e for e in self.equipment if type(e) == BerylliumProfile]
        if profile['type'] != 'beryllium':
            return []
        return [e for e in self.equipment if e.match(profile)]

    def list_wlans(self, profile):
        if not profile:
            return [e for e in self.equipment if type(e) == WlanProfile]
        if profile['type'] != 'wlan':
            return []
        return [e for e in self.equipment if e.match(profile)]

    @property
    def relay_srv(self):
        admin = ave.config.load_authkeys(self.home)
        if not self._relay_srv:
            self._relay_srv = RemoteRelayServer(
                authkey=admin, timeout=0.1, home=self.home
            )
        try:
            self._relay_srv.ping()
        except (ConnectionClosed, ConnectionTimeout):
            # retry once. server may have changed port number so make sure to
            # reestablish the connection (create new RemoteRelayServer)
            try:
                self._relay_srv = RemoteRelayServer(
                    authkey=admin, timeout=0.1, home=self.home
                )
                self._relay_srv.ping()
            except Exception, e:
                return None
        except Exception:
            return None
        return self._relay_srv

    def list_relays(self, profile=None):
        if not profile:
            profile = {'type':'relay'}
        relays = [e for e in self.equipment if type(e) == RelayProfile]
        # match the profile against the list of relays. the unique identity of
        # the relay may be matched, as may all of the named circuits within it.
        result = []
        for r in relays:
            if r.match(profile): # binds to RelayProfile.match()
                result.append(r)
        return result

    def list_spirent_testdrives(self):
        # it is not possible to dynamically discover Spirent's control server
        # "TestDrive". one can connect to it on port 6800 to see if it is there
        # but that has the side effect of throwing out any manual test session
        # that may be ongoing. the best we can do is to check for the static
        # configuration file in ~/.ave/config and just trust it to be correct.
        if self.testdrive:
            return [self.testdrive.get_profile()]
        return []

    def list_testdrives(self, profile=None):
        testdrives = self.list_spirent_testdrives()
        if not profile:
            return testdrives
        result = []
        for t in testdrives:
            if t.match(profile):
                result.append(t)
        return result

    def deallocate_relay(self, resource):
        if self.relay_srv:
            relay = Relay(resource, home=self.home)
            try:
                relay.reset()
            except Exception, e:
                print('WARNING: could not reset deallocated relay: %s' % e)
        else:
            print('WARNING: relay server not running, cannot reset')

    def deallocate(self, resource):
        if isinstance(resource, BaseWorkspaceProfile):
            # delete the storage space for the workspace, but only if it is
            # found in the equipment list. otherwise it would be deleted more
            # than once during handover. only the broker that actually created
            # the workspace has it in its local allocator equipment list.
            if resource in self.equipment:
                workspace = Workspace(
                    uid=resource['uid'], config=self.ws_cfg, home=self.home
                )
                workspace.delete()
                self.equipment.remove(resource)
        # need special handling of relays: close all circuits in the group
        if resource['type'] == 'relay':
            self.deallocate_relay(resource)
        Allocator.deallocate(self, resource)

    def get_resources(self, profiles, session):
        # make a distinction between simple and complex allocations. simple ones
        # include at most one piece of physical equipment.
        if len([p for p in profiles if not isinstance(p, BaseWorkspaceProfile)]) > 1:
            intended, collateral = self.complex_allocation(profiles, session)
        else:
            intended, collateral = self.simple_allocation(profiles)

        # sort out workspace requests
        for p in profiles:
            if isinstance(p, BaseWorkspaceProfile):
                try:
                    intended.append(self.match_workspaces(p))
                except:
                    raise NoSuch('no such workspace')

        # minimize the profiles of all resources that are about to be allocated
        for i in range(len(intended)):
            for p in profiles:
                if type(intended[i]) == type(p):
                    intended[i] = intended[i].minimize(p)

        # allocate the equipment. this is the last point of possible failure
        for i in range(len(intended)):
            resource = intended[i]
            if isinstance(resource, BaseWorkspaceProfile):
                # must create the workspace now if it doesn't exist. otherwise
                # there's no UID to associate with the session
                if 'uid' not in resource:
                    # TODO: who deletes the new workspace if allocate() fails?
                    # currently this can't fail because only one workspace can
                    # be allocated and it's handled last of the intended. so if
                    # another allocation failed first, the Workspace object
                    # will never be created. it also doesn't work to trigger
                    # the problem by asking for a workspace with the same uid
                    # as one owned by a different session as such a workspace
                    # should not be deleted if the allocation fails. so, save
                    # this problem for a rainy day.
                    ws = Workspace(uid=None, config=self.ws_cfg, home=self.home)
                    resource = ws.get_profile()
                    intended[i] = resource # replace the anonymous profile
                    if resource not in self.equipment:
                        self.equipment.append(resource)
            self.allocate(resource, session, collateral) # set internal records
            session.add_resource(resource) # tell the session about it

        # put the resources in the order they were requested and reduce the
        # result so that only requested resources are present.
        visible = []
        for p in profiles:
            for i in intended:
                if i['type'] == p['type']:
                    visible.append(i)
                    intended.remove(i)
                    break

        result = {
            'address'  : session.address,
            'authkey'  : session.authkey,
            'resources': visible
        }
        return result

    def yield_resource(self, session, resource):
        collateral = Allocator.yield_resource(self, session, resource)
        released = [c for c in collateral if self.is_available(c)]
        released.append(resource)
        return released # some but not all collateral released

    def close_session(self, session):
        release,collateral = Allocator.close_session(self, session)
        release.extend(collateral)
        return release # release everything
