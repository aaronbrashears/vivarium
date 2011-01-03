#!/usr/bin/python

import argparse
import os.path
import socket
import sys
import yaml

import vivarium.vivarium as vivarium

def _config_parser(subparsers, defaults):
    config_parser = subparsers.add_parser(
        'config',
        help='Manage configuration information.')
    config_parser.set_defaults(func=_config, **defaults)
    return subparsers

def _config(args):
    for name, value in args._get_kwargs():
        if name == 'config': continue
        if not hasattr(value, '__call__'):
            print('{0}: {1}'.format(name, value))

def _add_config_option(parser):
    parser.add_argument(
        '--config',
        action='store_true',
        default=False,
        help='Emit application configuration information and exit.')

def _show_parsed_config(args):
    if args.config:
        _config(args)
        return True
    return False

def _env_parser(subparsers, defaults):
    env_parser = subparsers.add_parser(
        'env',
        help='Show default environment.')
    env_parser.add_argument(
        'host',
        nargs='?',
        action='store',
        default = socket.getfqdn(),
        help='Hostname. Network values come from localhost.')
    _add_config_option(env_parser)
    env_parser.set_defaults(func=_env, **defaults)
    return subparsers

def _env(args):
    if not _show_parsed_config(args):
        from pprint import pprint
        pprint(vivarium.get_default_env(args.host))

def _seed_parser(subparsers, defaults):
    seed_parser = subparsers.add_parser(
        'seed',
        help="""
Given a hostname in the form 'my.example.com', gather all roles,
environments, packages, templates, and files to generate the seed
for the spawn.""")
    seed_parser.add_argument(
        'host',
        action='store',
        help='Host to generate the seed.')
    seed_parser.add_argument(
        'spawn',
        action='store',
        help='Spawn and source to use. Can be yaml file or a directory.')
    seed_parser.add_argument(
        '--source', '-s',
        action='store',
        default=None,
        help='The source spawn to use if different from the spawn.')
    seed_parser.add_argument(
        '--stdout',
        action='store_true',
        default=False,
        help='Emit configuration to stdout.')
    _add_config_option(seed_parser)
    seed_parser.set_defaults(func=_seed, **defaults)
    return subparsers

def _seed(args):
    _show_parsed_config(args) or vivarium.seed(args)

def _copy_parser(subparsers, defaults):
    copy_parser = subparsers.add_parser(
        'copy', help='Copy a complete humus. NOT YET IMPLEMENTED.')
    copy_parser.add_argument(
        'source',
        action='store',
        help='Source configuration to use. Can be yaml file or a directory.')
    copy_parser.add_argument(
        'destination',
        action='store',
        help="""
Destination for the copy. If the destination is a directory then the
configuration will use the file system back-end. If the destination is
a file or ends in .yaml, the yaml back-end will be used.""")
    _add_config_option(copy_parser)
    copy_parser.set_defaults(func=_copy, **defaults)
    return subparsers

def _copy(args):
    _show_parsed_config(args) or vivarium.copy(args)

def _plant_parser(subparsers, defaults):
    plant_parser = subparsers.add_parser(
        'plant', help='Plant a seed on the local host.')
    plant_parser.add_argument(
        '-r', '--root-dir',
        action='store',
        default='/',
        help='Target directory for the plant operation.')
    plant_parser.add_argument(
        '-s', '--stage-dir',
        action='store',
        default='/tmp',
        help='Directory for plant temporary files.')
    # plant_parser.add_argument(
    #     '--dry-run',
    #     action='store_true',
    #     default=False,
    #     help='Destination directory for configuration. Default is "/".')
    plant_parser.add_argument(
        'host',
        action='store',
        help='Host to generate the seed.')
    plant_parser.add_argument(
        'spawn',
        action='store',
        help='Spawn to use. Can be yaml file or a directory.')
    _add_config_option(plant_parser)
    plant_parser.set_defaults(func=_plant, **defaults)
    return subparsers

def _plant(args):
    _show_parsed_config(args) or vivarium.plant(args)

def _initial_parser(defaults = {}):
    description = """
Vivarium is a tool for managing small to medium distributed system
configuration. Vivarium is designed to be backed by zookeeper to store
data though you can also use yaml or just a normal file system."""
    parser = argparse.ArgumentParser(description=description, epilog=None)
    if len(defaults) > 0:
        parser.set_defaults(**defaults)
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1')
    subparsers = parser.add_subparsers(
        title='Commands',
        description="""
To get usage for a particular command:

  %(prog)s {command} --help""",
        help='commands')
    subparsers = _config_parser(subparsers, defaults.get('config', {}))
    subparsers = _env_parser(subparsers, defaults.get('env', {}))
    subparsers = _seed_parser(subparsers, defaults.get('seed', {}))
    subparsers = _copy_parser(subparsers, defaults.get('copy', {}))
    subparsers = _plant_parser(subparsers, defaults.get('plant', {}))
    return parser

def _parse_arguments():
    parser = _initial_parser()
    configname = os.path.expanduser('~/.vivarium.yaml')
    parser.add_argument(
        '-c', '--config-file',
        action='store',
        default=configname,
        help='Configuration file.')
    args = parser.parse_args()
    if os.path.exists(args.config_file):
        defaults = yaml.load(open(args.config_file).read())
        parser = _initial_parser(defaults)
        args = parser.parse_args()
    return args

def main():
    args = _parse_arguments()
    args.func(args)

if __name__ == '__main__':
    main()
