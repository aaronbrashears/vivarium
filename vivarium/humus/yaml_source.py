import os.path
import cStringIO as stringio
import yaml

class Humus(object):
    def __init__(self, filename):
        self._config = YamlFS(filename)
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

class YamlFS(object):
    class File(object):
        def __init__(self, node, name, mode, yamlfs):
            self._name = name
            self._node = node
            if 'r' == mode:
                self._file = stringio.StringIO(node[name])
            elif 'w' == mode:
                self._file = stringio.StringIO()
            else:
                raise NotImplementedError, 'Please specify mode of r or w'
            self._yamlfs = yamlfs
            self._is_dirty = False
            self.next = self._file.next
            self.read = self._file.read
            self.readline = self._file.readline
            self.readlines = self._file.readlines
            self.seek = self._file.seek
            self.tell = self._file.tell

        def __enter__(self):
            return self
        def __exit__(self, type, value, traceback):
            self.close()
        def write(self, string):
            self._is_dirty = True
            self._file.write(string)
        def writelines(self, sequence):
            self._is_dirty = True
            self._file.writelines(sequence)
        def flush(self):
            self._file.flush()
            if self._is_dirty:
                self._node[self._name] = self._file.getvalue()
                self._yamlfs._sync()
        def close(self):
            self.flush()
            self._file.close()

    def __init__(self, filename):
        self._filename = filename
        self._fs = yaml.load(open(self._filename))

    def open(self, filename, mode):
        if filename.startswith('/'):
            filename = filename[1:]
        paths = filename.split('/')
        if mode == 'w':
            self._mkdir(paths[:-1])
        rv = self._fs
        for part in paths[:-1]:
            rv = rv[part]
        # *NOTE: split out so we can handle new files.
        return YamlFS.File(rv, paths[-1], mode, self)

    def _sync(self):
        yaml.dump(self._fs, stream=open(self._filename, 'w'))

    def _mkdir(self, path):
        step = self._fs
        for part in path:
            next = step.get(part, None)
            if next is None:
                step[part] = {}
                next = step[part]
            step = next
            if isinstance(step, basestring):
                raise OSError, 17
