import errno
import os

class FSFS(object):
    def __init__(self, base):
        self._base = os.path.realpath(base)

    def open(self, filename, mode):
        fullname = self._base + filename
        print("fullname: {0}".format(fullname))
        if FSFS._is_write(mode):
            FSFS._mkdir(os.path.dirname(fullname))
        return open(fullname, mode)

    @staticmethod
    def _is_write(mode):
        if mode.startswith('w'): return True
        elif mode.startswith('a'): return True
        elif mode.startswith('r+'): return True
        return False

    @staticmethod
    def _mkdir(path):
        print("path: {0}".format(path))
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise        
