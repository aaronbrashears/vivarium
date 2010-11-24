import errno
import cStringIO as stringio
import yaml

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
        try:
            self._fs = yaml.load(open(self._filename))
        except IOError as exc:
            if exc.errno == errno.ENOENT: self._fs = {}
            else: raise

    def open(self, filename, mode = 'r'):
        if filename.startswith('/'):
            filename = filename[1:]
        paths = filename.split('/')
        if mode == 'w':
            self.mkdirs(paths[:-1])
        rv = self._fs
        try:
            for part in paths[:-1]:
                rv = rv[part]
        except KeyError:
            raise IOError, errno.ENOENT
        # *NOTE: split out so we can handle new files.
        return YamlFS.File(rv, paths[-1], mode, self)

    def list(self, dirname):
        directory = self._descend_path(dirname)
        return directory.keys()

    def isfile(self, filename):
        fl = self._descend_path(filename)
        return isinstance(fl, basestring)

    def isdir(self, dirname):
        dr = self._descend_path(dirname)
        return isinstance(dr, dict)

    def mkdirs(self, path):
        step = self._fs
        for part in path:
            next = step.get(part, None)
            if next is None:
                step[part] = {}
                next = step[part]
            step = next
            if isinstance(step, basestring):
                raise OSError, errno.EEXIST

    def _descend_path(self, path):
        paths = path.split('/')
        paths = [path for path in paths if len(path) > 0]
        node = self._fs
        try:
            for part in paths:
                node = node[part]
        except KeyError:
            raise IOError, errno.ENOENT
        return node

    def _sync(self):
        yaml.dump(self._fs, stream=open(self._filename, 'w'))
