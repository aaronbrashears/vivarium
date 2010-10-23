from copy import deepcopy
import yaml

class IncludeLoopError(Exception):
    pass

class CircularDependencyError(Exception):
    pass

class TargetCollisionError(Exception):
    pass

class Entity(object):
    def __init__(self, *args, **kwargs):
        #print("Entity init {0}".format(kwargs))
        self.name = kwargs['name']
        self._config = None

    def _load_config(self, source, configfile):
        self._load_config_checked(source, configfile, set())
        if self._config is None: self._config = {}

    def _load_config_checked(self, source, configfile, seen):
        self._config = yaml.load(configfile.read())
        includes = self._config.get('includes', [])
        for include in includes:
            if include in seen: raise IncludeLoopError, seen
            seen.add(include)
            entity = Entity(name=include)
            entity._load_config(source, source.open_include(include))
            self._config = _merge_dicts(entity._config, self._config)
            seen.remove(include)

class Role(Entity):
    def __init__(self, *args, **kwargs):
        super(Role, self).__init__(*args, **kwargs)

    def from_source(self, source):
        with source.open_role(self.name) as configfile:
            self._load_config(source, configfile)
        return self

    def packages(self, overrides):
        return _merge_dicts(self._config.get('packages', {}), overrides)

    def targets(self, overrides):
        """
        This method returns {targetname:Target} for this role
        specialization.
        """
        result = {}
        for targetname, value in self._config['targets'].iteritems():
            actions = value['actions']
            depends = value.get('depends', None)
            env = _merge_dicts(value.get('env', {}), overrides)
            #print(targetname)
            #print("  actions: {0}".format(actions))
            #print("  depends: {0}".format(depends))
            #print("      env: {0}".format(env))
            result[targetname] = Target(actions, depends, env)
        return result

class Host(Entity):
    class RoleSpec(object):
        def __init__(self, role_spec, general):
            self.config = role_spec
            self.role = general

        def packages(self, host_packages):
            "Return all packages."
            packages = _merge_dicts(
                host_packages,
                self.config.get('packages', {}))
            return self.role.packages(packages)

        def targets(self, host_env):
            "Return ``Role.targets`` with overridden env."
            env = _merge_dicts(host_env, self.config.get('env', {}))
            return self.role.targets(env)

    def __init__(self, *args, **kwargs):
        super(Host, self).__init__(*args, **kwargs)
        self.roles = {}

    def from_source(self, source):
        with source.open_host(self.name) as configfile:
            self._load_config(source, configfile)
            self._load_roles(source)
        return self

    def seed(self):
        packages, targets = self._find_targets()
        stages = self._build_stages(targets)
        for stage in stages:
            for step in stage:
                print("Collecting resources for {0}".format(step.keys()[0]))
                #step.values()[0].seed()
        # *TODO: iterate over stages and collect resources.

    def _find_targets(self):
        packages = {}
        targets = {}
        targetrole = {}
        for rolename, role in self.roles.iteritems():
            new_packages = role.packages(self._config.get('packages', {}))
            packages = _merge_dicts(packages, new_packages)
            new_targets = role.targets(self._config.get('env', {}))
            for key in new_targets.iterkeys():
                if targets.has_key(key):
                    raise TargetCollisionError, \
                        "{0} found in {1} and {2}".format(
                            key,
                            rolename,
                            targetrole[key])
            targets.update(new_targets)
            targetrole.update(dict([(key, rolename) for key in new_targets]))
        return packages, targets

    def _build_stages(self, targets):
        # iterate over the targets and let them prep themselves for the spawn
        deps = {}
        for targetname, target in targets.iteritems():
            #print("{0} {1}".format(targetname, target.depends))
            deps[targetname] = set(target.depends) if target.depends else set()
        stages = []
        #print(deps)
        for targetnames in _topological_sort(deps):
            stage = []
            for targetname in targetnames:
                stage.append({targetname : targets[targetname]})
            stages.append(stage)
        # import pprint
        # pprint.pprint(stages)
        return stages

    def _load_roles(self, source):
        roles = self._config.get('roles', [])
        for name, spec in roles.iteritems():
            generic_role = Role(name=name)
            generic_role.from_source(source)
            role = Host.RoleSpec(spec, generic_role)
            self.roles[name] = role

class Target(object):
    def __init__(self, actions, depends, env):
        self.actions = actions
        self.depends = depends
        self.env = env

def copy(source, destination):
    raise NotImplementedError

def configure(hostname, source, dest_dir):
    host = Host(name=hostname)
    host.from_source(source)
    spawn = host.seed()
    print(host)

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
