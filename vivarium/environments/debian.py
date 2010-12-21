import errno
import os
import platform
import subprocess

def register(environments):
    environments['debian'] = Debian

class Debian(object):
    """
    An instance of this class represents a special test Debian installation.

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
    def __init__(self, args):
        self.args = args
        self.debargs = {}
        if hasattr(args, 'debian'):
            self.debargs = args.debian

    def is_viable(self):
        # Duck-typing all the way.
        deboot = subprocess.call(['debootstrap', '--version'])
        if deboot == 0:
            return True
        else:
            print("Debian not viable: {0}".format(rv))

    def bootstrap(self):
        root = self.args.root_dir
        if not root.startswith('/'):
            root = os.path.realpath(root)
        if root == '/':
            print("Targetting local host.")
            raise NotImplementedError, "Not implemeted yet for safety."
        if os.path.isdir(os.path.join(root, 'etc')):
            # *FIX: This is not even close to a thorough check. This
            # is just a useful shortcut at this early stage of
            # development while I focus on a single distro. 2010-11-21
            print("Found chroot target in {0}".format(root))
        else:
            if not os.path.isdir(root):
                os.makedirs(root)
            cmd=['debootstrap']
            if self.debargs.has_key('base_tarball'):
                cmd.append('--unpack-tarball')
                cmd.append(self.debargs['base_tarball'])
            if self.debargs.has_key('distribution'):
                cmd.append(self.debargs['distribution'])
            else:
                cmd.append(platform.dist()[2])
            cmd.append(root)
            if self.debargs.has_key('mirror'):
                cmd.append(self.debargs['mirror'])
            # print("Bootstrapping: {0}".format(' '.join(cmd)))
            subprocess.call(cmd)
