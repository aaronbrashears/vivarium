The vivarium project is an effort to build a configuration management
system with pluggable back-ends and host configuration controllers to
facilitate testable, repeatable, documented deploys to small and
medium sized server farms.

Overview
========

The vivarium project was conceived, designed, and is being implemented
as a data driven configuration management system with pluggable data
storage, configuration actions, configuration controllers, and meant
to be backed by [ZooKeeper](http://hadoop.apache.org/zookeeper/
"ZooKeeper") for live configuration updates, presence updates and
presence subscriptions. Vivarium employs a declarative data driven
specification for how a host should be configured.

At this time, vivarium is under development when I can find spare time
in the evenings and weekends. It is not considered ready for use as
anything other than idle experimentation at this time.

The Source
----------

The source is where all roles, files, templates and other
configuration data are stored. Everything starts in the source. A
human is responsible for maintaining and specifying configuration in
the source. The first step of configuration will be to gather the data
found in the source for the host being configured.

The source is laid out with the various resources partitioned into
their own sections. Paths are separated with `/` when accessed through
the API with hosts in big endian ordering, eg, the host
`my.example.com` would be found in `/hosts/com/example/my`. The source
consists of the following top level sections:

    /
        /includes
        /files
        /hosts
        /roles
        /templates

The general work flow in the source is to edit the files source and
build the seed from that information which is then planted in in the
spawn.

The Spawn
---------

The spawn is where complete configurations for a particular host and
presence information are stored.

By default, the spawn shares space in the source though this is not
necessarily the case and not always desirable.

The spawn contains the sections:

    /
        /presence
        /seeds

Policy
------

The policy is used by vivarium on the configured host to ensure the
host conforms to the configuration specified.

This is a planned feature and not near implementation.

Use
===

Command Line
------------

Armed with the information in the overview you should be able to use
the command line tool `vv.py` to experiment. To get an idea of what
`vv.py` can do at this time:

    ./vv.py --help

The commands exposed by the top level help can be further explored by
asking for help on that command. For example:

    ./vv.py seed --help

Will give help on the `seed` command.

The help should always be up to date with the current state of
development.

Configuration File
------------------

Command line options can be provided in a configuration file. The
configuration file defaults to `~/.vivarium.yaml` and can be
overridden with the `--config-file` option. Values found in the
configuration file are treated as defaults with command line options
taking precedence. Options to commands by putting them in sections
with the same name as the command.

My vivarium configuration file currently looks like:

    seed:
        source: examples/basic.yaml
    plant:
        root_dir: lucid-chroot
    stage_dir: /tmp/stage
    debian:
        base_tarball: /var/cache/debootstrap/lucid.tgz

To examine how your configuration looks, all commands accept a
`--config` which will display the arguments as the command sees them
after parsing the configuration file and command line. With the
configuration above, the examining the configuration for the plant
command would produce:

    $ ./vv.py plant --root-dir=/tmp/root www.example.com seed --config

    debian: {'base_tarball': '/home/phoenix/tmp/lucid.tgz'}
    host: www.example.com
    plant: {'root_dir': 'lucid-chroot', 'stage_dir': '/tmp/stage'}
    root_dir: /tmp/root
    seed: {'source': 'examples/basic.yaml'}
    spawn: seed
    stage_dir: /tmp/stage

Notice the `root_dir` was chosen from the command line option while
the `stage_dir` was supplied by the plant sub-section. All of the
command line options will appear at the top level. Sections like
`debian` are useful for specialized configuration -- in this case, to
specify a base tarball for debootstrap to reduce package downloads
during development.

Configuration
=============

Host
----

To configure a host, the host must appear in the `/hosts` section of
the source with the host domain parts forming sub-directories in big
endian order. For example, the host `kdc-01.example.com` would appear
in the file located at `/hosts/com/example/kdc-01` in the source. The
`kdc-01` file can specify targets, roles, and environment.

Targets
-------

Targets specify a series of actions and an environment for
accomplishing a particular configuration. For example, a target can
declare the existence, contents, ownership, and permissions of a file
on the host. Targets can depend on other targets and vivarium will
automatically sort the targets so that all actions from dependent
targets are run prior starting a particular target.

During the planting process of taking a seed to a full configuration,
targets with no dependencies are built first in stage 0. Targets with
dependencies met by stage 0 will be built in stage 1 and so on until
all targets have completed. There is no defined ordering of target
construction inside of a stage and may even be built in parallel.

All actions in a target are carried out in three phases. All actions
are given the opportunity to prepare themselves during the `sow`
process, do their primary work in the `plant` process, and finally
perform any clean-up in the `reap process. For a particular target,
all actions will sow first, then all actions will plant, followed by
the all actions reaping.

Roles
-----

Roles are a collection of one or more targets and an environment for
that role. A role in the `/roles` section provides the general form
and actions necessary to fulfill that role. When a host has a role,
this is a role specialization where the environment for the
specialization takes precedence over the general role.

Environment
-----------

The environment is a data used to make decisions about behavior and
used when doing substitution into into templates. The environment is
structured data - usually key value mappings - which can contain
strings, numbers, lists and other maps. During the seed generation,
the environment is collected from the hosts, specialization, roles,
targets and merged in a priority order.

The order of precedence is:

    specialization > host > role > target

The merge works by taking combining key value maps where when keys
collide value maps are further merged and all other data is chosen in
precedence order.

The environment is declared in the `env` key inside any of the role
specializations, hosts, roles, and targets described above.

Includes
--------

Hosts and Roles can include small and large snippets of further
configuration by using the `includes` data directive which loads all
of the listed files into the current host or role. Included
configuration can also employ the `includes` directive.

Contribute
==========

Feel free to experiment and send feedback.
