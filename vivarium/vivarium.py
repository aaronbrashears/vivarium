from copy import deepcopy
import errno
import os.path
import sys
import yaml

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
            steps = {}
            for name, value in stage.iteritems():
                target = Target().from_spawn(
                    value['steps'],
                    value['depends'],
                    value['env'])
                steps[name] = target
            self.stages.append(steps)
        return self

    def plant(self, root_dir):
        for stage in self.stages:
            for name, target in stage.iteritems():
                print("Target: {0}".format(name))
                target.plant(root_dir)

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
        def __init__(self, name, parameters, data):
            self.action = name
            self.parameters = parameters
            self.data = data

        def to_seed(self):
            seed = {}
            seed['action'] = self.action
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
        for step in steps:
            name = step['action']
            parameters = deepcopy(step)
            del parameters['action']
            action_impl = manager.action(name)
            data = action_impl.gather(source, parameters, env)
            self.steps.append(Target.Step(name, parameters, data))
        return self

    def from_spawn(self, steps, depends, env):
        self.steps = []
        self.depends = depends
        self.env = env
        for step in steps:
            name = step['action']
            parameters = step['parameters']
            data = step['data']
            self.steps.append(Target.Step(name, parameters, data))
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

    def plant(self, root_dir):
        manager = ActionManager()
        # for action in self.actions:
        #     print

# class NamedTarget(object):
#     def __init__(self, name, target, action_data = None):
#         self.name = name
#         self.target = target
#         self._action_data = action_data

#     def to_seed(self):
#         seed = {}
#         seed['name'] = self.name
#         seed['target'] = self.target.to_seed()
#         seed['action_data'] = self._action_data
#         return seed

#     def gather_resources(self, source):
#         print("Gathering resources for {0}".format(self.name))
#         print("Actions: {0}".format(self.target.actions))
#         self._action_data = []
#         manager = ActionManager()
#         for action in self.target.actions:
#             name = action['action']
#             parameters = parameters = deepcopy(action)
#             del parameters['action']
#             action_impl = manager.action(name)
#             data = action_impl.from_source(source, parameters, self.target.env)
#             self._action_data.append(data)

def copy(source, destination):
    raise NotImplementedError

def seed(hostname, source, spawn, stdout):
    host = Host(name=hostname)
    try:
        host.from_source(source)
    except IOError:
        print("Unable to source host {0}".format(hostname))
        raise
    seed = host.to_seed()
    if stdout:
        print("Configuration for {0}:".format(hostname))
        import pprint
        pprint.pprint(seed)
    else:
        serialized = yaml.dump(seed)
        with spawn.open(spawn.path_to_seed(hostname), 'w') as dest:
            dest.write(serialized)

def plant(hostname, spawn, dest_dir):
    host = Host(name=hostname).from_spawn(spawn)
    # import pprint
    # pprint.pprint(host.to_seed())
    host.plant(dest_dir)

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
    plugins = {}
    plugin_files = [x[:-3] for x in os.listdir(path) if x.endswith(".py")]
    sys.path.insert(0, path)
    for plugin in plugin_files:
        mod = __import__(plugin)
        if hasattr(mod, 'register'):
            mod.register(plugins)
    sys.path.pop(0)
    return plugins

class Action(object):
    def gather(self, source, parameters, env):
        return {}

    def sow(self, parameters, data, env):
        return True

    def plant(self, parameters, data, env):
        return True

    def reap(self, parameters, data, env):
        return True

class ActionManager(object):
    __shared_state = {}
    def __init__(self):
        self.__dict__ = ActionManager.__shared_state
        if not hasattr(self, '_initialized'):
            self._actions = _find_local_plugins('actions')
            self._initialized = True

    def action(self, name):
        return self._actions[name]()

class Ecosystem(object):
    __shared_state = {}
    def __init__(self):
        self.__dict__ = Ecosystem.__shared_state
        if not hasattr(self, '_initialized'):
            self._environments = _find_local_plugins('environments')
            self._initialized = True

    def environment(self, name):
        return self._ennvironments[name]()
