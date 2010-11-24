import errno
import os
import platform
import subprocess

from vivarium.vivarium import Environment

def register(environments):
    environments['debian'] = Debian

def jailed(worker):
    def in_jail(*args,**kwargs):
        if args[0].root != '/':
            real_root = os.open('/', os.O_RDONLY)
            os.chroot(args[0].root)
        try:
            worker(*args,**kwargs)
        finally:
            if args[0].root != '/':
                os.fchdir(real_root)
                os.chroot(".")
                os.close(real_root)
    return in_jail

class Debian(Environment):
    """
    An instance of this class represents installing into a debian
    based system.

    You can pass further configuration to this environment through the
    configuration file in a 'debian' sub-section. The keys which are
    currently in use are:

    base_tarball
      Absolute or relative path to a tarball for the desired
      distribution. Only used when configuring a non-root host such as
      when testing or in development.

    distribution
      The distribution to target, eg, lenny for a pure Debian system
      or lucid to set up a recent Ubuntu image. Only used when
      configuring a non-root host such as when testing or in
      development.

    mirror
      What mirror to use for downloading packages when configuring a
      non-root host.
    """
    def __init__(self, *args, **kwargs):
        super(Debian, self).__init__(*args, **kwargs)
        self.debargs = {}
        if hasattr(self.args, 'debian'):
            self.debargs = self.args.debian

    def is_viable(self):
        # Duck-typing all the way.
        apt = subprocess.call(['aptitude', '--version'])
        # only necessary for use in chroot.
        # deboot = subprocess.call(['debootstrap', '--version'])
        # if apt == deboot == 0:
        if apt == 0:
            return True
        else:
            print("Debian not viable: {0}".format(rv))

    def bootstrap(self):
        if self.root == '/':
            print("Targetting local host.")
            raise NotImplemented, "Not implemeted yet for safety."
        if os.path.isdir(os.path.join(self.root, 'etc')):
            # *FIX: This is not even close to a thorough check. This
            # is just a useful shortcut at this early stage of
            # development while I focus on a single distro. 2010-11-21
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
            # print("Bootstrapping: {0}".format(' '.join(cmd)))
            subprocess.call(cmd)

    def download_package(self, package):
        # print("Download: {0}".format(package))
        cmd=['aptitude','install','--download-only', package]
        return self.run(cmd)

    def install_package(self, package):
        # print("Install: {0}".format(package))
        cmd=['aptitude','install', package]
        return self.run(cmd)

    @jailed
    def run(self, command):
        # print("run: {0}".format(command))
        return subprocess.call(command)

    @jailed
    def work(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)
