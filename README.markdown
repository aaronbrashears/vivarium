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

Configuration
=============

Host
----

To configure a host, the host must appear in the `/hosts` section of
the source with the host domain parts forming subdirectories in big
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
