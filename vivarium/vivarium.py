from copy import deepcopy
import yaml

class IncludeLoopError(Exception):
    pass

class Entity(object):
    _include_stack = []

    def __init__(self, *args, **kwargs):
        #print "Entity init", kwargs
        self.name = kwargs['name']
        self._config = None

    @staticmethod
    def _assert_no_loop():
        seen = set()
        for include in Entity._include_stack:
            if include in seen: raise IncludeLoop, Entity._include_stack
            seen.add(include)

    def _load_config(self, source, configfile):
        self._config = yaml.load(configfile.read())
        includes = self._config.get('includes', [])
        for include in includes:
            Entity._include_stack.append(include)
            Entity._assert_no_loop()
            entity = Entity(name=include)
            entity._load_config(source, source.open_include(include))
            if entity._config: 
                self._config = _merge_dicts(entity._config, self._config)
            Entity._include_stack.pop()

class Role(Entity):
    def __init__(self, *args, **kwargs):
        super(Role, self).__init__(*args, **kwargs)

    def from_source(self, source):
        with source.open_role(self.name) as configfile:
            self._load_config(source, configfile)

class Host(Entity):
    class RoleSpec(object):
        def __init__(self, role_spec, general):
            self._config = role_spec
            self.role = general

    def __init__(self, *args, **kwargs):
        super(Host, self).__init__(*args, **kwargs)

    def from_source(self, source):
        with source.open_host(self.name) as configfile:
            self._load_config(source, configfile)
            self._load_roles(source)

    def _load_roles(self, source):
        roles = self._config.get('roles', [])
        self.roles = {}
        for name, spec in roles.iteritems():
            generic_role = Role(name=name)
            generic_role.from_source(source)
            role = Host.RoleSpec(spec, generic_role)
            self.roles[name] = role
            import pprint
            print name
            pprint.pprint(role._config)
            pprint.pprint(generic_role._config)

def copy(source, destination):
    raise NotImplementedError

def configure(hostname, source, dest_dir):
    host = Host(name=hostname)
    host.from_source(source)
    print host

def _is_dict_like(obj, require_set=False):
     """
     Returns ``True`` if an object appears to support the python dict
     operations. For my purposes, this means ``obj`` implements
     ``__getitem__`` and ``keys``.
 
     If ``require_set`` is ``True`` then the object must support
     ``__setitem__`` as well as ``__getitem__`` and ``keys``.
     """
     if require_set and not hasattr(obj, '__setitem__'): return False
     if hasattr(obj, 'keys') and hasattr(obj, '__getitem__'): return True
     else: return False

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
