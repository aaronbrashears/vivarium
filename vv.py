#!/usr/bin/python

import argparse
import os.path
import sys

import vivarium.humus as humus
import vivarium.vivarium as vivarium

def _seed_parser(subparsers):
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
    seed_parser.set_defaults(func=_seed)
    return subparsers

def _seed(args):
    spawn = humus.Humus(args.spawn)
    if args.source is None: source = spawn
    else: source = humus.Humus(args.source)
    vivarium.seed(args.host, source, spawn, args.stdout)

def _copy_parser(subparsers):
    copy_parser = subparsers.add_parser(
        'copy', help='Copy a complete humus. NOT YET IMPLEMENTED.')
    copy_parser.add_argument(
        'from',
        action='store',
        help='Source configuration to use. Can be yaml file or a directory.')
    copy_parser.add_argument(
        'to',
        action='store',
        help="""
Destination for the copy. If the destination is a directory then the
configuration will use the file system back-end. If the destination is
a file or ends in .yaml, the yaml back-end will be used.""")
    copy_parser.set_defaults(func=_copy)
    return subparsers

def _copy(args):
    source = vivarium.Humus(args.source)
    destination = vivarium.Humus(args.destination)
    vivarium.copy(source, destination)

def _plant_parser(subparsers):
    plant_parser = subparsers.add_parser(
        'plant', help='Plant a seed on the local host.')
    plant_parser.add_argument(
        '-d', '--dest-dir',
        action='store',
        help='Destination directory for configuration. Default is "/".')
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
    plant_parser.set_defaults(func=_plant)
    return subparsers

def _plant(args):
    spawn = humus.Humus(args.spawn)
    vivarium.plant(args.host, spawn, args.dest_dir)

def main():
    description = """
Vivarium is a tool for managing small to medium distributed system
configuration. Vivarium is designed to be backed by zookeeper to store data though 
you can also use yaml or just a normal file system."""
    parser = argparse.ArgumentParser(description=description, epilog=None)
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
    subparsers = _seed_parser(subparsers)
    subparsers = _copy_parser(subparsers)
    subparsers = _plant_parser(subparsers)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
