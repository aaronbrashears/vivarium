import errno
import os

class FSFS(object):
    def __init__(self, base):
        self._base = os.path.realpath(base)

    def open(self, filename, mode):
        if mode == 'w':
            self.makedirs(os.path.dirname(filename))
        elif mode != 'r':
            raise NotImplementedError, 'Please specify mode of r or w'
        return open(self._fullname(filename), mode)

    def list(self, dirname):
        return os.listdir(self._fullname(dirname))

    def isfile(self, filename):
        return os.path.isfile(self._fullname(filename))

    def isdir(self, dirname):
        return os.path.isdir(self._fullname(dirname))

    def makedirs(self, dirname):
        try:
            return os.makedirs(self._fullname(dirname))
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise

    def _fullname(self, name):
        return self._base + name

    @staticmethod
    def _is_write(mode):
        if mode.startswith('w'): return True
        elif mode.startswith('a'): return True
        elif mode.startswith('r+'): return True
        return False
