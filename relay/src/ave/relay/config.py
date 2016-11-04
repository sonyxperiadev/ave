import os
import json
import copy

def check_serial(serial, config):
    if type(serial) not in [str, unicode]:
        raise Exception('config is not indexed by strings: %s' % config)
    if type(config[serial]) != dict:
        raise Exception(
            'config for serial "%s" is not a dictionary: %s'
            % (serial, config)
        )
    if 'groups' not in config[serial]:
        raise Exception('config contains no "groups" field: %s'% config)

def check_group(serial, group, config):
    if type(group) not in [str, unicode]:
        raise Exception('groups not indexed by strings: %s' % config) 
    if type(config[serial]['groups'][group]) != dict:
        raise Exception(
            'config for serial "%s", group "%s" is not a dictionary: %s'
            % (serial, group, config)
        )

def check_circuit(serial, group, circuit, config, num_ports):
    if type(circuit) not in [str, unicode]:
        raise Exception('circuits not indexed by strings: %s' % config)
    if type(config[serial]['groups'][group][circuit]) != int:
        raise Exception(
            'config for serial "%s", group "%s", circuit "%s" is not '
            'an integer: %s' % (serial, group, circuit, config)
        )
    governed = [
        # handset connectors
        'handset.power',
        'handset.volume.up',
        'handset.volume.down',
        'handset.battery',
        # usb pins from pc
        'usb.pc.vcc', # 5V
        'usb.pc.d+',  # D-
        'usb.pc.d-',  # D+
        'usb.pc.gnd', # GND
        'usb.pc.id',  # ID
        # usb pins from wall charger
        'usb.wall.vcc', # 5V
        'usb.wall.d+',  # D-
        'usb.wall.d-',  # D+
        'usb.wall.gnd', # GND
        'usb.wall.id'   # ID
    ]
    if circuit not in governed:
        governed = ', '.join(['"%s"' % g for g in governed])
        raise Exception(
            'config for serial "%s", group "%s", circuit identifier '
            '"%s" is invalid. must use goverend names: %s'
            % (serial, group, circuit, governed)
        )
    port = config[serial]['groups'][group][circuit]
    if port not in range(1, num_ports + 1):
        raise Exception(
            'config for serial "%s", group "%s", circuit "%s", port '
            '%d is out of bounds [1..%d]'
            % (serial, group, circuit, port, num_ports)
        )
    return port

def check_port(serial, port, seen, config):
    if port in seen:
        raise Exception(
            'config for serial "%s", port %d is used more than once: %s'
            % (serial, port, config[serial])
        )

def check_defaults(serial, config, num_ports):
    defaults = config[serial]['defaults']
    if type(defaults) != list:
        raise Exception(
            'config for serial "%s", defaults is not a list: %s'
            % (serial, config)
        )
    if len(defaults) != num_ports:
        raise Exception(
            'config for serial "%s", defaults is not a list with '
            'length == %d (%d)' % (serial, num_ports, len(defaults))
        )
    for value in defaults:
        if type(value) != int:
            raise Exception(
                'config for serial "%s", defaults is not a list of '
                'integers: %s' % (serial, defaults)
            )
        if value not in [0,1]:
            raise Exception(
                'config for serial "%s", defaults contain values out '
                'of bounds [0..1]: %s' % (serial, defaults)
            )

def validate_board_config(config, profile, num_ports):
    if type(config) != dict:
        raise Exception('config is not a dictionary: %s' % config)

    for serial in config.keys():
        check_serial(serial, config)
        seen = []
        for group in config[serial]['groups'].keys():
            check_group(serial, group, config)
            for circuit in config[serial]['groups'][group].keys():
                port = check_circuit(serial, group, circuit, config, num_ports)
                check_port(serial, port, seen, config)
                seen.append(port)
        if 'defaults' not in config[serial]:
            config[serial]['defaults'] = [1] * num_ports
        check_defaults(serial, config, num_ports)

    # check that the configuration covers the device. it must contain the
    # exact serial number from the profile, or a wildcard "*". it may have
    # both, in which case the exact match takes precedence. return a config
    # that describes only the profiled equipment
    if profile['serial'] not in config.keys():
        if '*' in config.keys():
            return copy.deepcopy(config['*'])
        raise Exception(
            'config contains no values for device with serial number %s: %s'
            % (profile['serial'], config)
        )
    return copy.deepcopy(config[profile['serial']])

def write_devantech_config(home, force=False):
    path = os.path.join(home, '.ave','config','devantech.json')
    if os.path.exists(path) and not force:
        raise Exception('will not overwrite existing file: %s' % path)
    with open(path, 'w') as f:
        config = {
            '*':{
                'groups': {
                    'a': {'usb.pc.vcc':1},
                    'b': {'usb.pc.vcc':2},
                    'c': {'usb.pc.vcc':3},
                    'd': {
                        'usb.pc.vcc'         :4,
                        'handset.battery'    :5,
                        'handset.power'      :6,
                        'handset.volume.up'  :7,
                        'handset.volume.down':8
                    }
                },
                "defaults":[1,1,1,1, 1,0,0,0]
            }
        }
        json.dump(config, f, indent=4)
    return path
