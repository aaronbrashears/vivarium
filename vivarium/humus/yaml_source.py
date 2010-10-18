import os.path
import cStringIO as stringio
import yaml

class Humus(object):
    def __init__(self, source):
        self._config = YamlFS(source)

    def _path_to_host(self, hostname):
        path = []
        path.extend(part for part in reversed(hostname.split('.')))
        return '/'.join(path)

    def open_host(self, hostname):
        return self._config.open(
            self._filename('/hosts/', self._path_to_host(hostname), "Host"))

    def open_role(self, name):
        return self._config.open(
            self._filename('/roles/', name, "Role"))

    def open_include(self, name):
        return self._config.open(
            self._filename('/includes/', name, "Include"))

    def _filename(self, prefix, path, debug_txt=None):
        filename = prefix + path
        filename = filename.replace('//', '/')
        #if debug_txt:
        #    print("{0} {1}".format(debug_txt, filename))
        return filename

class YamlFS(object):
    class File(object):
        def __init__(self, node, name):
            self._name = name
            self._node = node
            self._file = stringio.StringIO(node[name])
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
        def write(string):
            self._is_dirty = True
            self._file.write(str)
        def writelines(sequence):
            self._is_dirty = True
            self._file.writelines(sequence)
        def flush(self):
            self._file.flush()
            if self._is_dirty:
                self._node[self._name] = self._file.getvalue()
        def close(self):
            self.flush()
            self._file.close()

    def __init__(self, source):
        if isinstance(source, basestring):
            if os.path.isfile(source):
                self._fs = yaml.load(open(source))
            else:
                self._fs = yaml.load(source)
        else:
            self._fs = yaml.load(source.read())

    def open(self, filename):
        if filename.startswith('/'):
            filename = filename[1:]
        paths = filename.split('/')
        rv = self._fs
        for part in paths[:-1]:
            rv = rv[part]
        # *NOTE: split out so we can handle new files some day.
        return YamlFS.File(rv, paths[-1])
