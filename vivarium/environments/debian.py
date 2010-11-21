import errno
import os
import platform
import subprocess

from vivarium.vivarium import Environment

def register(environments):
    environments['debian'] = Debian

class Debian(Environment):
    def __init__(self, *args, **kwargs):
        super(Debian, self).__init__(*args, **kwargs)
        self.debargs = {}
        if hasattr(self.args, 'debian'):
            self.debargs = self.args.debian

    def is_viable(self):
        # Duck-typing all the way.
        apt = subprocess.call(['aptitude', '--version'])
        deboot = subprocess.call(['debootstrap', '--version'])
        if apt == deboot == 0:
            return True
        else:
            print("Debian not viable: {0}".format(rv))

    def bootstrap(self):
        if self.root == '/':
            print("Targetting local host.")
            raise NotImplemented, "Not implemeted yet for safety."
        if os.path.isdir(os.path.join(self.root, 'etc')):
            print("Found chroot target in {0}".format(self.root))
        else:
            if not os.path.isdir(self.root):
                os.makedirs(self.root)
            cmd=['debootstrap']
            if self.debargs.has_key('base_tarball'):
                cmd.append('--unpack-tarball')
                cmd.append(self.debargs['base_tarball'])
            if self.debargs.has_key('distribution'):
                cmd.append(self.debargs['distribution'])
            else:
                cmd.append(platform.dist()[2])
            cmd.append(self.root)
            if self.debargs.has_key('mirror'):
                cmd.append(self.debargs['mirror'])
            print("Command: {0}".format(' '.join(cmd)))
            subprocess.call(cmd)

    def mkdir(self, subdir):
        path = self._filename(subdir)
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST: pass
            else: raise

    def open(self, filename, mode):
        fullname = self._filename(filename)
        return open(fullname, mode)

    def _filename(self, name):
        if name.startswith('/') and self.root != '/':
            name = name[1:]
        return os.path.join(self.root, name)
