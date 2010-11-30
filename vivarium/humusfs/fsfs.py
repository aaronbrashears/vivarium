import errno
import os

class FSFS(object):
    def __init__(self, base):
        self._base = os.path.realpath(base)

    def open(self, filename, mode):
        fullname = self._fullname(filename)
        if mode == 'w':
            FSFS._mkdir(os.path.dirname(fullname))
        elif mode != 'r':
            raise NotImplementedError, 'Please specify mode of r or w'
        return open(fullname, mode)

    def list(self, dirname):
        return os.listdir(self._fullname(dirname))

    def isfile(self, filename):
        return os.path.isfile(self._fullname(filename))

    def isdir(self, dirname):
        return os.path.isfile(self._fullname(dirname))

    def mkdirs(self, dirname):
        return os.path.mkdirs(self._fullname(dirname))

    def _fullname(self, name):
        return self._base + name

    @staticmethod
    def _is_write(mode):
        if mode.startswith('w'): return True
        elif mode.startswith('a'): return True
        elif mode.startswith('r+'): return True
        return False

    @staticmethod
    def _mkdir(path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise        
