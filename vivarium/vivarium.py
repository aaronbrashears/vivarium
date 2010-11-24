from copy import deepcopy
import errno
import os.path
import sys
import yaml

import humus

class IncludeLoopError(Exception):
    pass

class CircularDependencyError(Exception):
    pass

class TargetCollisionError(Exception):
    pass

class HostMismatch(Exception):
    pass

class Entity(object):
    def __init__(self, *args, **kwargs):
        # print("Entity init {0}".format(kwargs))
        self.name = kwargs['name']
        self._config = None

    def _load_config(self, source, configfile):
        self._load_config_checked(source, configfile, set())
        if self._config is None: self._config = {}

    def _load_config_checked(self, source, configfile, seen):
        self._config = yaml.load(configfile.read())
        includes = self._config.get('includes', [])
        # print("includes: {0}".format(includes))
        for include in includes:
            if include in seen: raise IncludeLoopError, seen
            seen.add(include)
            entity = Entity(name=include)
            with source.open(source.path_to_include(include)) as includefile:
                entity._load_config(source, includefile)
            # print("config: {0}".format(entity._config))
            self._config = _merge_dicts(entity._config, self._config)
            seen.remove(include)

class File(object):
    def __init__(self):
        self.destination = None
        self.owner = None
        self.group = None
        self.mode = None
        self._template = None
        # *TODO: add content as an alternate to templates
        # self._content = None

    def from_source(self, source, filename):
        with source.open(source.path_to_file(filename)) as file_def:
            config = yaml.load(file_def.read())
        self.destination = config['destination']
        self.owner = config.get('owner', 'root')
        self.group = config.get('group', 'root')
        self.mode = config.get('mode', 'u=rw,go=r')
        template = config['template']
        with source.open(source.path_to_template(template)) as contents:
            self._template = contents.read()
        return self

    def to_seed(self):
        seed = {}
        seed['destination'] = self.destination
        seed['owner'] = self.owner
        seed['group'] = self.group
        seed['mode'] = self.mode
        seed['template'] = self._template
        return seed

class Role(Entity):
    def __init__(self, *args, **kwargs):
        super(Role, self).__init__(*args, **kwargs)

    def from_source(self, source):
        with source.open(source.path_to_role(self.name)) as configfile:
            self._load_config(source, configfile)
        return self

    def to_seed(self):
        seed = {}
        seed['config'] = self._config
        return seed

    def targets(self, source, override_targets, override_env):
        """
        This method returns {targetname:Target} for this role
        specialization.
        """
        result = {}
        all_targets = _merge_dicts(self._config['targets'], override_targets)
        for targetname, value in all_targets.iteritems():
            steps = value['steps']
            depends = value.get('depends', None)
            env = _merge_dicts(value.get('env', {}), override_env)
            target = Target().from_source(source, steps, depends, env)
            result[targetname] = target
        return result

class Host(Entity):
    class RoleSpec(object):
        def __init__(self, role_spec, general):
            self._config = role_spec
            self.role = general

        def targets(self, source, host_env):
            "Return ``Role.targets`` with overridden env."
            env = _merge_dicts(host_env, self._config.get('env', {}))
            spec_targets = self._config.get('targets', {})
            targets = self.role.targets(source, spec_targets, env)
            return targets

        def to_seed(self):
            seed = {}
            seed['config'] = self._config
            seed['role'] = self.role.to_seed()
            return seed

    def __init__(self, *args, **kwargs):
        super(Host, self).__init__(*args, **kwargs)
        self.roles = {}
        self.stages = []

    def from_source(self, source):
        with source.open(source.path_to_host(self.name)) as configfile:
            self._load_config(source, configfile)
            self._load_roles(source)
        self._gather(source)
        return self

    def to_seed(self):
        seed = {}
        seed['name'] = self.name
        seed['config'] = self._config
        roles = {}
        for name, rolespec in self.roles.iteritems():
            roles[name] = rolespec.to_seed()
        seed['roles'] = roles
        stages = []
        for stage in self.stages:
            steps = {}
            for key, value in stage.iteritems():
                steps[key] = value.to_seed()
            stages.append(steps)
        seed['stages'] = stages
        return seed

    def from_spawn(self, spawn):
        with spawn.open(spawn.path_to_seed(self.name)) as definition:
            config = yaml.load(definition.read())
        if self.name != config['name']:
            msg = 'Found definition for {0} when loading {1}.'
            raise HostMismatch, msg.format(config['name'], self.name)
        self._config = config['config']
        for rolename, value in config.get('roles', {}).iteritems():
            generic_role = Role(name=rolename)
            generic_role._config = value['role']['config']
            role_spec = Host.RoleSpec(value['config'], generic_role)
            self.roles[rolename] = role_spec
        self.stages = []
        for stage in config['stages']:
            targets = {}
            for name, value in stage.iteritems():
                target = Target().from_spawn(
                    value['steps'],
                    value['depends'],
                    value['env'])
                targets[name] = target
            self.stages.append(targets)
        return self

    def plant(self, es, default_env, args):
        for count, stage in enumerate(self.stages):
            print("Stage {0}".format(count))
            print("********")
            for name, target in stage.iteritems():
                print("Target: {0}".format(name))
                target.plant(name, es, default_env, args)

    def _gather(self, source):
        targets = self._find_targets(source)
        # for key, value in targets.iteritems():
        #     print("Target: {0} -- {1}".format(key, value.to_seed()))
        self.stages = self._build_stages(targets)
        return self

    def _find_targets(self, source):
        target_in = {}
        targets = {}
        env = self._config.get('env', {})
        for name, value in self._config.get('targets', {}).iteritems():
            steps = value['steps']
            depends = value.get('depends', None)
            target = Target().from_source(source, steps, depends, env)
            targets[name] = target
            target_in[name] = self.name
        for rolename, role in self.roles.iteritems():
            new_targets = role.targets(source, env)
            for key in new_targets.iterkeys():
                if targets.has_key(key):
                    raise TargetCollisionError, \
                        "{0} found in {1} and {2}".format(
                            key,
                            rolename,
                            target_in[key])
            targets.update(new_targets)
            target_in.update(dict([(key, rolename) for key in new_targets]))
        return targets

    def _build_stages(self, targets):
        # iterate over the targets and let them prep themselves for the spawn
        deps = {}
        for targetname, target in targets.iteritems():
            # print("{0} {1}".format(targetname, target.depends))
            deps[targetname] = set(target.depends) if target.depends else set()
        stages = []
        # print(deps)
        for targetnames in _topological_sort(deps):
            stage = {}
            for targetname in targetnames:
                stage[targetname] = targets[targetname]
            stages.append(stage)
        return stages

    def _load_roles(self, source):
        roles = self._config.get('roles', [])
        for name, spec in roles.iteritems():
            if spec is None: spec = {}
            generic_role = Role(name=name).from_source(source)
            role = Host.RoleSpec(spec, generic_role)
            self.roles[name] = role

class Target(object):
    class Step(object):
        def __init__(self, number, name, impl, parameters, data):
            self.number = number
            self.action_name = name
            self.action_impl = impl
            self.parameters = parameters
            self.data = data

        def to_seed(self):
            seed = {}
            seed['action'] = self.action_name
            seed['parameters'] = self.parameters
            seed['data'] = self.data
            return seed

    def __init__(self):
        self.steps = []
        self.depends = []
        self.env = {}

    def from_source(self, source, steps, depends, env):
        self.steps = []
        self.depends = depends
        self.env = env
        manager = ActionManager()
        for num, step in enumerate(steps):
            name = step['action']
            parameters = deepcopy(step)
            del parameters['action']
            action_impl = manager.action(name)
            data = action_impl.gather(source, parameters, env)
            the_step = Target.Step(num, name, action_impl, parameters, data)
            self.steps.append(the_step)
        return self

    def from_spawn(self, steps, depends, env):
        self.steps = []
        self.depends = depends
        self.env = env
        manager = ActionManager()
        for num, step in enumerate(steps):
            name = step['action']
            parameters = step['parameters']
            data = step['data']
            action_impl = manager.action(name)
            the_step = Target.Step(num, name, action_impl, parameters, data)
            self.steps.append(the_step)
        return self

    def to_seed(self):
        seed = {}
        steps = []
        for step in self.steps:
            steps.append(step.to_seed())
        seed['steps'] = steps
        seed['depends'] = self.depends
        seed['env'] = self.env
        return seed

    def plant(self, target_name, es, default_env, args):
        contexts = []
        for num, step in enumerate(self.steps):
            context = ActionContext(
                es,
                target_name,
                num,
                step.parameters,
                step.data,
                _merge_dicts(default_env, self.env),
                args)
            contexts.append(context)
        sow = []
        for step, context in zip(self.steps, contexts):
            sow.append(step.action_impl.sow(context))
        plant = []
        for step, context in zip(self.steps, contexts):
            plant.append(step.action_impl.plant(context))
        reap = []
        for step, context in zip(self.steps, contexts):
            reap.append(step.action_impl.reap(context))

def copy(args):
    source = humus.Humus(args.source)
    destination = humus.Humus(args.destination)
    raise NotImplementedError

def seed(args):
    spawn = humus.Humus(args.spawn)
    if args.source is None: source = spawn
    else: source = humus.Humus(args.source)
    host = Host(name=args.host)
    try:
        host.from_source(source)
    except IOError:
        print("Unable to source host {0}".format(args.host))
        raise
    seed = host.to_seed()
    if args.stdout:
        msg = "Configuration for {0}:".format(args.host)
        print(msg)
        print("="*len(msg))
        import pprint
        pprint.pprint(seed)
    else:
        serialized = yaml.dump(seed)
        with spawn.open(spawn.path_to_seed(args.host), 'w') as dest:
            dest.write(serialized)

def plant(args):
    spawn = humus.Humus(args.spawn)
    host = Host(name=args.host).from_spawn(spawn)
    es = Ecosystem().es(args=args)
    es.bootstrap()
    default_env = {'HOST' :
                   {'FQDN': args.host,
                    'SHORT': _shortname(args.host),
                    'DOMAIN': _domainname(args.host),
                    }
                   }
    host.plant(es, default_env, args)

def _shortname(name):
    if '.' not in name: return name
    return name.split('.')[0]

def _domainname(name):
    if '.' not in name: return None
    return '.'.join(name.split('.')[1:])

def _is_dict_like(obj, require_set=False):
     """
     Returns ``True`` if an object appears to support the python dict
     operations. For my purposes, this means ``obj`` implements
     ``__getitem__`` and ``keys``.
 
     If ``require_set`` is ``True`` then the object must also support
     ``__setitem__``.
     """
     if require_set and not hasattr(obj, '__setitem__'): return False
     if hasattr(obj, 'keys') and hasattr(obj, '__getitem__'): return True
     else: return False

def _safe_merge_dicts(lesser, greater):
    if lesser is None: return greater
    if greater is None: return lesser
    return _merge_dicts(lesser, greater)

def _merge_dicts(lesser, greater):
    """
    Merge the two dict-like objects ``lesser`` and ``greater`` such
    that all keys from both are in returned merged dictionary. In the
    case of conflict, the value-type for ``greater`` is chosen. The
    dict-like objects are not modified in the operation.
    """
    dst = deepcopy(lesser)
    stack = [(dst, greater)]
    while stack:
        ll, gg = stack.pop()
        for key in gg:
            if key not in ll:
                ll[key] = deepcopy(gg[key])
            else:
                if _is_dict_like(gg[key]) and _is_dict_like(ll[key]):
                    stack.append((ll[key], gg[key]))
                else:
                    ll[key] = deepcopy(gg[key])
    return dst

def _topological_sort(deps):
    """
    Pass in a dict object ``deps`` with a keys as target and
    values as a set of dependencies. This function will yield a sorted
    list of targets which have no dependencies with each other or
    targets in further yields.

    Circular dependencies are detected by not having anything to yield
    yet the remaining data is not empty. This means that some
    iterations may succeed before raising a CircularDependencyError.
    """
    # Ignore self dependencies
    for k, v in deps.iteritems():
        v.discard(k)
    extra_items_in_deps = reduce(set.union, deps.values()) - set(deps.keys())
    deps.update(dict([(item, set()) for item in extra_items_in_deps]))
    while True:
        ordered = set(item for item,dep in deps.items() if not dep)
        if not ordered:
            break
        yield sorted(ordered)
        deps = dict([(item, (dep - ordered)) for item,dep in deps.items()
                     if item not in ordered])
    if deps:
        raise CircularDependencyError, deps

# proposal for new action syntax:
#
# boolean: true | false
# string: '...' | "..." | alphanum_with_underscores-or-hyphens.or.periods/or/slashes
# number: ...
# atomic: boolean | string | number
# value_list: atomic | atomic , value_list
# list: [ ] | [ value_list ]
# key: words_with_underscores-or-hyphens
# value: atomic | list | map
# key_value_list: key : value | key : value, key_value_list
# map: { } | { key_value_list }
# parameter_name: words_with_underscores-or-hyphens
# parameter_value: value
# parameter: parameter_name = parameter_value
# parameter_list: parameter | parameter, parameter_list
# function_name: words_with_underscores-or-hyphens
# call: function_name | function_name ( parameter_list )

def _find_local_plugins(subdir):
    my_dir = (os.path.dirname(os.path.realpath(__file__)))
    plugin_dir = os.path.join(my_dir, subdir)
    return _find_plugins(plugin_dir)

def _find_plugins(path):
    #print("Looking for plugins in {0}".format(path))
    plugins = {}
    plugin_files = [x[:-3] for x in os.listdir(path) if x.endswith(".py")]
    sys.path.insert(0, path)
    for plugin in plugin_files:
        mod = __import__(plugin)
        if hasattr(mod, 'register'):
            mod.register(plugins)
    sys.path.pop(0)
    return plugins

class ActionContext(object):
    def __init__(self, es, target_name, num, params, data, env, args):
        self.es = es
        self.target_name = target_name
        self.number = num
        self.params = params
        self.data = data
        self.env = env
        self.args = args

class Action(object):
    def gather(self, source, parameters, env):
        return {}

    def sow(self, context):
        return True

    def plant(self, context):
        return True

    def reap(self, context):
        return True

class ActionManager(object):
    __shared_state = {}
    def __init__(self):
        self.__dict__ = ActionManager.__shared_state
        if not hasattr(self, '_initialized'):
            self._actions = _find_local_plugins('actions')
            self._initialized = True

    def action(self, name, *args, **kwargs):
        return self._actions[name](*args, **kwargs)

class Environment(object):
    def __init__(self, *args, **kwargs):
        self.root = None
        self.args = kwargs.get('args', None)
        if self.args is not None:
            self.root = self.args.root_dir
            if not self.root.startswith('/'):
                self.root = os.path.realpath(self.root)

    #
    # Abstract interface
    #
    def is_viable(self):
        return False

    def bootstrap(self):
        raise NotImplementedError

    def download_package(self, package):
        raise NotImplementedError

    def install_package(self, package):
        raise NotImplementedError

    def run(self, command):
        raise NotImplementedError

    def work(self, callback, *args, **kwargs):
        raise NotImplementedError

    #
    # Utility methods
    #
    def mkdir(self, subdir):
        path = self._filename(subdir)
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise

    def open(self, filename, mode):
        fullname = self._filename(filename)
        return open(fullname, mode)

    def _filename(self, name):
        if name.startswith('/') and self.root != '/':
            name = name[1:]
        return os.path.join(self.root, name)

class Ecosystem(object):
    __shared_state = {}
    def __init__(self):
        self.__dict__ = Ecosystem.__shared_state
        if not hasattr(self, '_initialized'):
            self._initialize()

    def _initialize(self):
        self._environments = _find_local_plugins('environments')
        self._local_environment = None
        for name, germ in self._environments.iteritems():
            petri = germ()
            if petri.is_viable():
                print("Found viable {0} system.".format(name))
                self._local_environment = germ
                break
        self._initialized = True

    def es(self, name=None, args=None):
        if name is None:
            return self._local_environment(args=args)
        return self._environments[name](args=args)
