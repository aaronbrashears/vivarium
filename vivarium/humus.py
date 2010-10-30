import os.path
import humusfs.yamlfs

class Humus(object):
    def __init__(self, location):
        if os.path.isdir(location):
            raise NotImplementedError
        elif os.path.isfile(location) or location.endswith('.yaml'):
            self._config = humusfs.yamlfs.YamlFS(location)
        else:
            msg = 'Unable to determine back-end from: {0}'.format(location)
            raise RuntimeError, msg
        sections = ['include', 'file', 'presence', 'role', 'template']
        for section in sections:
            self._setattr_path_to(section)
        host_sections = ['host', 'seed']
        for section in host_sections:
            self._setattr_path_to_host(section)

    def open(self, filename, mode='r'):
        return self._config.open(filename, mode)

    def _setattr_path_to(self, section):
        fn_name, top = Humus._fnname_and_top(section)
        fn = lambda resource: Humus._path_to(top, resource)
        setattr(self, fn_name, fn)

    def _setattr_path_to_host(self, section):
        fn_name, top = Humus._fnname_and_top(section)
        fn = lambda hostname: Humus._path_to_host(top, hostname)
        setattr(self, fn_name, fn)

    @staticmethod
    def _fnname_and_top(section):
        return 'path_to_{0}'.format(section), '/{0}s/'.format(section)

    @staticmethod
    def _path_to(prefix, path):
        filename = prefix + path
        filename = filename.replace('//', '/')
        return filename

    @staticmethod
    def _path_to_host(prefix, hostname):
        path = [prefix]
        path.extend(part for part in reversed(hostname.split('.')))
        return '/'.join(path).replace('//', '/')
