from Cheetah.Template import Template
from copy import deepcopy
import errno
import grp
import netifaces
import os.path
import pwd
import shutil
import sys
import subprocess
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

class BadFilename(Exception):
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

class Enum(set):
    """
    Simple class to represent an enumeration. Really just a
    maintenance communication to note that there is a limited set of
    options for a value, what those options are, and to reduce typos.

    Usage:
    >>> animals = Enum('dog cat horse'.split())
    >>> animals.cat == 'cat'
    True
    """
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError, "Enumeration not found: {0}".format(name)

class File(object):
    IS = Enum(['regular', 'dir', 'sym', 'hard', 'absent'])

    def __init__(self):
        self.location = None
        self.type = None
        self.owner = None
        self.group = None
        self.mode = None

        # *TODO consider only defining these in sub-classes.
        self._template = None
        self._content = None
        self._target = None
        self._files = None

    def from_source(self, source, filename):
        with source.open(source.path_to_file(filename)) as file_def:
            config = yaml.load(file_def.read())
        location = config['location']
        return self._load_config(config, source, location)

    def from_seed(self, seed):
        self.location = seed['location']
        self.type = seed['type']
        self.owner = seed.get('owner', None)
        self.group = seed.get('group', None)
        self.mode = seed.get('mode', None)
        if self.type == File.IS.regular:
            try:
                self._template = seed['template']
            except KeyError:
                self._content = seed['content']
        elif self.type in (File.IS.sym, File.IS.hard):
            self._target = seed['target']
        elif self.type == File.IS.dir:
            self._files = []
            for file_def in seed['files']:
                self._files.append(File().from_seed(file_def))
        elif self.type is File.absent:
            pass
        else:
            msg = "Unkown file type: {0}"
            raise RuntimeError, msg.format(self.type)
        return self

    def to_seed(self):
        seed = {}
        seed['location'] = self.location
        seed['type'] = self.type
        if self.owner is not None:
            seed['owner'] = self.owner
        if self.group is not None:
            seed['group'] = self.group
        if self.mode is not None:
            seed['mode'] = self.mode
        if self._template is not None:
            seed['template'] = self._template
        if self._content is not None:
            seed['content'] = self._content
        if self._target is not None:
            seed['target'] = self._target
        if self._files is not None:
            seed['files'] = []
            for node in self._files:
                seed['files'].append(node.to_seed())
        return seed

    def sow(self, filename, ctxt):
        if self.type == File.IS.regular:
            self._sow_regular(filename, ctxt)
        elif self.type == File.IS.dir:
            self._sow_dir(filename, ctxt)

    def plant(self, src_filename, dst_filename, ctxt):
        def _remove(name):
            if os.path.islink(name) or os.path.isfile(name):
                os.unlink(name)
            elif os.path.isdir(name):
                shutil.rmtree(name)
            elif os.path.exists(name):
                msg = "Path is unknown type: {0}"
                raise RuntimeError, msg.format(name)
        def _finalize_file(location, uid, gid, mode):
            # print("finalize file {0}".format(location))
            if uid > -1 or gid > -1:
                os.chown(location, uid, gid)
            if mode is not None:
                os.chmod(location, mode)
        def _finalize_link(location, uid, gid, mode):
            # print("finalize link {0}".format(location))
            if uid > -1 or gid > -1:
                os.lchown(location, uid, gid)
            if mode is not None:
                os.lchmod(location, mode)
        def _inner_plant(node):
            uid, gid = node._uid_gid_owner()
            mode = node._file_mode()
            if node.type == File.IS.regular:
                _finalize_file(node.location, uid, gid, mode)
            elif node.type == File.IS.dir:
                for vvfile in node._files:
                    _inner_plant(vvfile)
                _finalize_file(node.location, uid, gid, mode)
                # fd = os.open(node.location, os.O_DIRECTORY | os.O_RDWR)
                # node._chown(fd)
                # node._chmod(fd)
                # os.close(fd)
            elif node.type == File.IS.sym:
                os.symlink(node._target, node.location)
                _finalize_link(node.location, uid, gid, mode)
            elif node.type == File.IS.hard:
                os.link(node._target, node.location)
                _finalize_link(node.location, uid, gid, mode)
            elif node.type == File.IS.absent:
                _remove(node.location)
        def _plant_dir(node, src_fname, dst_fname):
            # print("remove dir: {0}".format(dst_fname)
            _remove(dst_fname)
            # print "copy dir: {0} {1}".format(src_fname, dst_fname))
            shutil.copytree(src_fname, dst_fname, symlinks=True)
            _inner_plant(node)
        def _plant_file(node, src_fname, dst_fname):
            with open(src_fname, 'rb') as src:
                with open(dst_fname, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            uid, gid = node._uid_gid_owner()
            mode = node._file_mode()
            _finalize_file(node.location, uid, gid, mode)
        if self.type == File.IS.regular:
            ctxt.es.work(_plant_file, self, src_filename, dst_filename)
        elif self.type == File.IS.dir:
            ctxt.es.work(_plant_dir, self, src_filename, dst_filename)
        else:
            ctxt.es.work(_inner_plant, self)

    def _sow_regular(self, filename, ctxt):
        if self._content is not None:
            content = self._content
        else:
            tpl = Template(self._template, searchList=[ctxt.env])
            content = str(tpl)
        def _file_sow():
            # attempt to write to the file to get an IOError
            # if that will fail.
            # Naw, we should always be root and checking for
            # writeable differs between file types as well as
            # where they are in the tree. Do this later when we
            # determine that it is needed. 2010-12-13 Aaron
            #open(self.location, 'ab').close()
            with open(filename, 'w') as output:
                output.write(content)
        ctxt.es.work(_file_sow)

    def _sow_dir(self, filename, ctxt):
        ctxt.es.mkdir(filename)
        for node in self._files:
            node.sow(node.location, ctxt)

    def _load_config(self, config, source, location):
        self.location = location
        self.owner = config.get('owner', None)#'root')
        self.group = config.get('group', None)#'root')
        self.mode = config.get('mode', None)#'u=rw,go=r')

        # make sure there is only 1 type.
        markers = set(['template', 'content', 'target', 'absent', 'files'])
        keys = set(config.keys())
        cats = markers.intersection(keys)
        if len(cats) > 1:
            msg = "Multiple possible file types for '{0}': {1}"
            raise RuntimeError, msg.format(location, cats)
        try:
            cat = cats.pop()
        except KeyError:
            self.type = File.IS.regular
            self._content = ''
            return self
        if cat == 'template':
            self.type = File.IS.regular
            with source.open(source.path_to_content(config[cat])) as rep_file:
                self._template = rep_file.read()
        elif cat == 'content':
            self.type = File.IS.regular
            with source.open(source.path_to_content(config[cat])) as rep_file:
                self._content = rep_file.read()
        elif cat == 'files':
            self.type = File.IS.dir
            self._load_dir(config, source)
        elif cat == 'absent':
            self.type = File.IS.absent
        elif cat == 'target':
            if config.has_key('hard'):
                self.type = File.IS.hard
            else:
                self.type = File.IS.sym
            self._target = config['target']
        else:
            msg = 'Unable to infer file type: {0}'
            raise RuntimeError, msg.format(location)
        return self

    def _load_dir(self, config, source):
        self._files = []
        files = config.get('files', None)
        for sub, node in files.iteritems():
            if '/' in sub:
                raise BadFilename, "File in directory cannot contain '/'."
            location = os.path.join(self.location, sub)
            if isinstance(node, basestring):
                with source.open(source.path_to_file(node)) as file_def:
                    file_config = yaml.load(file_def.read())
                vvfile = File()._load_config(file_config, source, location)
            else:
                vvfile = File()._load_config(node, source, location)
            self._files.append(vvfile)

    @staticmethod
    def _is_int(mode_string):
        try:
            int(mode_string)
            return True
        except ValueError:
            pass
        return False

    @staticmethod
    def _parse_mode(mode_string):
        modes = mode_string.split(',')
        mode_bits = 0
        for mode in modes:
            affected, value = mode.split('=')
            mask = 0
            if 'u' in affected: mask |= 0b100111000000
            if 'g' in affected: mask |= 0b010000111000
            if 'o' in affected: mask |= 0b001000000111
            if 'a' in affected: mask |= 0b111111111111
            perm = 0
            if 'r' in value: perm |= 0b000100100100
            if 'w' in value: perm |= 0b000010010010
            if 'x' in value: perm |= 0b000001001001
            if 's' in value: perm |= 0b111000000000
            mode_bits |= (mask & perm)
        return mode_bits

    def _uid_gid_owner(self):
        uid = -1
        gid = -1
        if self.owner is not None:
            uid = pwd.getpwnam(self.owner)[2]
        if self.group is not None:
            gid = grp.getgrnam(self.group)[2]
        return uid, gid

    def _file_mode(self):
        mode = None
        if self.mode is not None:
            if File._is_int(self.mode):
                mode = string.atoi(self.mode, base=8)
            else:
                mode = File._parse_mode(self.mode)
        return mode

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
        self.stages = Host._build_stages(targets)
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

    @staticmethod
    def _build_stages(targets):
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
    _recursive_copy('/', source, destination)

def _recursive_copy(directory, src, dst):
    dst.makedirs(directory)
    contents = src.list(directory)
    for content in contents:
        node = os.path.join(directory, content)
        if src.isfile(node):
            with dst.open(node, 'w') as target:
                src_content = src.open(node).read()
                target.write(src_content)
        elif src.isdir(node):
            _recursive_copy(node, src, dst)

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
    the_seed = host.to_seed()
    if args.stdout:
        msg = "Configuration for {0}:".format(args.host)
        print(msg)
        print("="*len(msg))
        import pprint
        pprint.pprint(the_seed)
    else:
        serialized = yaml.dump(the_seed)
        with spawn.open(spawn.path_to_seed(args.host), 'w') as dest:
            dest.write(serialized)

def plant(args):
    spawn = humus.Humus(args.spawn)
    host = Host(name=args.host).from_spawn(spawn)
    es = Ecosystem(args.root_dir)
    if args.root_dir != '/':
        petri = PetriDish().culture(args=args).bootstrap()
    default_env = _get_default_env(args.host)
    host.plant(es, default_env, args)

def _get_default_env(host):
    env = {'HOST' :
               {'FQDN': host,
                'NDQF': _big_endian_fqdn(host),
                'SHORT': _shortname(host),
                'DOMAIN': _domainname(host),
                }
           }
    interfaces = netifaces.interfaces()
    netinfo = {}
    for iface in interfaces:
        ifaceinfo = {}
        info = netifaces.ifaddresses(iface)
        if info.has_key(netifaces.AF_INET):
            ifaceinfo['IPV4'] = info[netifaces.AF_INET]
        if info.has_key(netifaces.AF_INET6):
            ifaceinfo['IPV6'] = info[netifaces.AF_INET6]
        if info.has_key(netifaces.AF_LINK):
            ifaceinfo['LINK'] = info[netifaces.AF_LINK]
        if len(ifaceinfo):
            netinfo[iface] = ifaceinfo
    if len(netinfo):
        env['NET'] = netinfo
    return env

def _big_endian_fqdn(name):
    fqdn = name.split(name)
    fqdn.reverse()
    return '.'.join(fqdn)

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
        deps = dict([(item, (dep - ordered)) for item, dep in deps.items()
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

def jailed(worker):
    # Decorator for the Ecosystem class to make sure functionality
    # runs inside the ecosystem.
    def in_jail(*args,**kwargs):
        real_root = args[0]._enter_jail()
        try:
            worker(*args,**kwargs)
        finally:
            args[0]._escape_jail(real_root)
    return in_jail

class Ecosystem(object):
    def __init__(self, root_dir):
        self._root_dir = root_dir
        if not self._root_dir.startswith('/'):
            self._root_dir = os.path.realpath(self._root_dir)
        self._is_jailed = False

    @jailed
    def run(self, command):
        # print("run: {0}".format(command))
        env = None
        if self._is_jailed:
            env = {}
        return subprocess.call(command, env=env)

    @jailed
    def work(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    @jailed
    def mkdir(self, subdir):
        # print("******** MKDIR".format(subdir))
        try:
            os.makedirs(subdir)
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise

    def _enter_jail(self):
        """
        Go into jail if necessary. Returns an open file handle if that
        happened. Return None if no jail. This should only be called
        by the ``jailed`` decorator since this is a potentially
        destructive call with massive side effects.
        """
        if self._root_dir != '/' and not self._is_jailed:
            self._is_jailed = True
            real_root = os.open('/', os.O_RDONLY)
            os.chroot(self._root_dir)
            return real_root

    def _escape_jail(self, real_root):
        """
        Escape from jail if real_root is provided and not None. This
        should always be called with the reutrn value of
        ``enter_jail`` and only called from the ``jailed`` decorator.
        """
        if real_root is not None:
            os.fchdir(real_root)
            os.chroot(".")
            os.close(real_root)
        self._is_jailed = False

class PetriDish(object):
    __shared_state = {}
    def __init__(self):
        self.__dict__ = PetriDish.__shared_state
        if not hasattr(self, '_initialized'):
            self._initialize()

    def _initialize(self):
        self._environments = _find_local_plugins('environments')
        self._local_environment = None
        for name, germ in self._environments.iteritems():
            petri = germ(None)
            if petri.is_viable():
                print("Found viable {0} system.".format(name))
                self._local_environment = germ
                break
        self._initialized = True

    def culture(self, name=None, args=None):
        if name is None:
            return self._local_environment(args=args)
        return self._environments[name](args=args)
