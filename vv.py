#!/usr/bin/python

import argparse
import os.path
import sys

import vivarium.humus.yaml_source as yaml_source
import vivarium.vivarium as vivarium

def _configure_parser(subparsers):
    configure_parser = subparsers.add_parser(
        'configure', 
        help='Configure a host.')
    dest_group = configure_parser.add_mutually_exclusive_group()
    dest_group.add_argument(
        '-d', '--dest-dir', 
        action='store', 
        default='/',
        help='Destination directory for configuration. Default is "/".')
    dest_group.add_argument(
        '--stdout', 
        action='store_true', 
        default=False,
        help='Emit configuration to stdout. NOT YET IMPLEMENTED.')
    configure_parser.add_argument(
        'source', 
        action='store', 
        help='Source configuration to use. Can be yaml file or a directory.')
    configure_parser.add_argument(
        'host', 
        action='store',
        help='The host to configure.')
    configure_parser.set_defaults(func=_configure)
    return subparsers

def _configure(args):
    source = _find_humus(args.source)
    if args.stdout:
        raise NotImplementedError, 'Not able to emit to stdout yet.'
    else:
        dest_dir = args.dest_dir
    vivarium.configure(args.host, source, dest_dir)

def _copy_parser(subparsers):
    copy_parser = subparsers.add_parser(
        'copy', help='Copy ')
    copy_parser.add_argument(
        'source', 
        action='store', 
        help='Source configuration to use. Can be yaml file or a directory.')
    copy_parser.add_argument(
        'destination', 
        action='store', 
        help='''
Destination for the configuration. If the destination is a directory then the
configuration will use the file system back-end. If the destination is a file
or ends in .yaml, the yaml back-end will be used.''')
    copy_parser.set_defaults(func=_copy)

def _copy(args):
    source = _find_humus(args.source)
    destination = _find_humus(args.destination)
    vivarium.copy(source, destination)

def _find_humus(name):
    if os.path.isdir(name):
        raise NotImplementedError
    elif os.path.isfile(name) or name.endswith('.yaml'):
        return yaml_source.Humus(name)
    else:
        print('Unable to determine back-end from: {0}'.format(name))
        sys.exit(1)

def main():
    description = '''
Vivarium is a tool for managing small to medium distributed system
configuration. Vivarium is designed to be backed by zookeeper to store data though 
you can also use yaml or just a normal file system.'''
    parser = argparse.ArgumentParser(description=description, epilog=None)
    parser.add_argument(
        '-v', '--version', 
        action='version', 
        version='%(prog)s 0.1')
    subparsers = parser.add_subparsers(help='commands')
    subparsers = _configure_parser(subparsers)
    subparsers = _copy_parser(subparsers)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
