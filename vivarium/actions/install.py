from Cheetah.Template import Template
from copy import deepcopy
import grp
import os.path
import pwd
import shutil
import stat
import string

from vivarium.vivarium import File
from vivarium.vivarium import Action

def register(actions):
    actions['install'] = Install

class Install(Action):
    _installables = ['files', 'packages']

    def __init__(self, *args, **kwargs):
        super(Install, self).__init__(*args, **kwargs)
        self._dir = None

    def gather(self, source, parameters, env):
        rv = {}
        files = {}
        for filename in parameters.get('files', []):
            the_file = File().from_source(source, filename)
            files[filename] = the_file.to_seed()
        rv['files'] = files
        return rv

    def sow(self, ctxt):
        print("Install: sowing step {0}".format(ctxt.number))
        fnmap = self._mk_fn_map('sow')
        for key, value in ctxt.params.iteritems():
            fnmap[key](value, ctxt)
        return True

    def plant(self, ctxt):
        print("Install: planting step {0}".format(ctxt.number))
        fnmap = self._mk_fn_map('plant')
        for key, value in ctxt.params.iteritems():
            fnmap[key](value, ctxt)
        return True

    def reap(self, ctxt):
        print("Install: reaping step {0}".format(ctxt.number))
        fnmap = self._mk_fn_map('reap')
        for key, value in ctxt.params.iteritems():
            fnmap[key](value, ctxt)
        return True

    @staticmethod
    def _fn_name(prefix, install):
        return '_{0}_{1}'.format(prefix, install)

    def _mk_fn_map(self, prefix):
        fnmap = {}
        for install in Install._installables:
            fnmap[install] = getattr(self, Install._fn_name(prefix, install))
        return fnmap

    def _work_dir(self, stage_dir, target_name, number):
        sub_dir = "step-{0:03}".format(number)
        temp_dir = os.path.join(stage_dir, target_name, sub_dir)
        # print("work dir: {0}".format(temp_dir))
        return temp_dir

    def _working_filename(self, name):
        return os.path.join(self._dir, name.replace('/','%'))

    @staticmethod
    def _is_int(mode_string):
        try:
            int(mode_string)
            return True
        except ValueError:
            pass
        return False

    @staticmethod
    def _parse_mode(mode_string):
        modes = mode_string.split(',')
        mode_bits = 0
        for mode in modes:
            affected, value = mode.split('=')
            mask = 0
            if 'u' in affected: mask |= 0b100111000000
            if 'g' in affected: mask |= 0b010000111000
            if 'o' in affected: mask |= 0b001000000111
            if 'a' in affected: mask |= 0b111111111111
            perm = 0
            if 'r' in value: perm |= 0b000100100100
            if 'w' in value: perm |= 0b000010010010
            if 'x' in value: perm |= 0b000001001001
            if 's' in value: perm |= 0b111000000000
            mode_bits |= (mask & perm)
        return mode_bits

    @staticmethod
    def _chown(fd, filespec):
        # *NOTE: This method should be moved to the the ecosystem
        # since the owner and group are potentially different in a
        # chroot environment. 2010-11-21 AB
        uid = -1
        gid = -1
        owner = filespec.get('owner', None)
        group = filespec.get('group', None)
        if owner:
            uid = pwd.getpwnam(owner)[2]
        if group:
            gid = grp.getgrnam(group)[2]
        if owner or group:
            os.fchown(fd, uid, gid)

    @staticmethod
    def _chmod(fd, filespec):
        if filespec.has_key('mode'):
            mode = filespec['mode']
            if Install._is_int(mode):
                mode = string.atoi(mode, base=8)
            else:
                mode = Install._parse_mode(mode)
            os.fchmod(fd, mode)

    def _sow_files(self, files, ctxt):
        self._dir = self._work_dir(
            ctxt.args.stage_dir,
            ctxt.target_name,
            ctxt.number)
        ctxt.es.mkdir(self._dir)
        for fl in files:
            # make sure we can write to the destination
            filespec = ctxt.data['files'][fl]
            # print("{0}: {1}".format(fl, filespec))
            if 'content' in filespec:
                content = filespec['content']
            else:
                tpl = Template(filespec['template'], searchList=[ctxt.env])
                content = str(tpl)
            filename = self._working_filename(fl)
            def _file_sow():
                open(filespec['destination'], 'ab').close()
                with open(filename, 'w') as output:
                    output.write(content)
            ctxt.es.work(_file_sow)

    def _plant_files(self,  files, ctxt):
        for fl in files:
            filespec = ctxt.data['files'][fl]
            src_filename = self._working_filename(fl)
            dst_filename = filespec['destination']
            def _file_plant():
                with open(src_filename, 'rb') as src:
                    with open(dst_filename, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                        fd = dst.fileno()
                        Install._chown(fd, filespec)
                        Install._chmod(fd, filespec)
            ctxt.es.work(_file_plant)

    def _reap_files(self, files, ctxt):
        # *TODO: clean up intermediary files and directories.
        pass

    def _sow_packages(self, packages, ctxt):
        for package in packages:
            ctxt.es.download_package(package)

    def _plant_packages(self, packages, ctxt):
        for package in packages:
            ctxt.es.install_package(package)

    def _reap_packages(self, packages, ctxt):
        # *TODO: remove the package archive
        pass
