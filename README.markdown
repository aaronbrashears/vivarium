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
presence subscriptions.

At this time, vivarium is under development when I can find spare time
in the evenings and weekends. It is not considered ready for use as
anything other than idle experimentation at this time.

The Source
----------

Everything starts in the source. The source is where all definitions
for hosts, roles, environment and packages will be found. The first
step of configuration will be to gather the data found in the source
starting with the host being configured.

The source is laid out with the various resources partitioned into
their own sections. Paths are separated with `/` when accessed through
the API with hosts in big endian ordering, eg, the host
'my.example.com' would be found in `/hosts/com/example/my`. The source
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

    ./vv.py configure --help

Will give help on the `configure` command.

The help should always be up to date with the current state of
development.

Contribute
==========

Feel free to experiment and send feedback.
