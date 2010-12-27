from copy import deepcopy
import os.path
import stat
import string

from vivarium.vivarium import File
from vivarium.vivarium import Action

def register(actions):
    actions['install'] = Install

class Install(Action):
    _installables = ['files', 'packages', 'gems']

    def __init__(self, *args, **kwargs):
        super(Install, self).__init__(*args, **kwargs)
        self._dir = None

    def gather(self, source, parameters, env):
        rv = {}
        files = {}
        for filename in parameters.get('files', []):
            vvfile = File().from_source(source, filename)
            files[filename] = vvfile.to_seed()
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

    def _sow_files(self, files, ctxt):
        self._dir = self._work_dir(
            ctxt.args.stage_dir,
            ctxt.target_name,
            ctxt.number)
        ctxt.es.mkdir(self._dir)
        for file_def in files:
            filespec = ctxt.data['files'][file_def]
            # print("_sow_files: {0} - {1}".format(file_def, filespec))
            vvfile = File().from_seed(filespec)
            filename = self._working_filename(file_def)
            vvfile.sow(filename, ctxt)

    def _plant_files(self,  files, ctxt):
        for file_def in files:
            filespec = ctxt.data['files'][file_def]
            vvfile = File().from_seed(filespec)
            src_filename = self._working_filename(file_def)
            dst_filename = filespec['location']
            # print("PLANTFILES: {0} {1}".format(src_filename,dst_filename))
            vvfile.plant(src_filename, dst_filename, ctxt)

    def _reap_files(self, files, ctxt):
        # *TODO: clean up intermediary files and directories.
        pass

    def _sow_packages(self, packages, ctxt):
        for package in packages:
            cmd = ['aptitude','install','--download-only', package]
            # in a chroot, a lot of the package installs fail because
            # start/stop fails. Not sure how to resolve
            # this. 2010-12-11 Aaron
            # if not ctxt.es.run(cmd)
            #     msg = "Unable to fetch package: {0}"
            #     raise RuntimeError, msg.format(package)
            ctxt.es.run(cmd)

    def _plant_packages(self, packages, ctxt):
        for package in packages:
            cmd = ['aptitude','install', package]
            # in a chroot, a lot of the package installs fail because
            # start/stop fails. Not sure how to resolve
            # this. 2010-12-11 Aaron
            # if not ctxt.es.run(cmd)
            #     msg = "Unable to install package: {0}"
            #     raise RuntimeError, msg.format(package)
            ctxt.es.run(cmd)

    def _reap_packages(self, packages, ctxt):
        # *TODO: remove the package archive
        pass

    def _sow_gems(self, gems, ctxt):
        pass

    def _plant_gems(self, gems, ctxt):
        for gem in gems:
            cmd = ['gem','install']
            if isinstance(gem, basestring):
                cmd.append(gem)
            else:
                cmd.append(gem['name'])
                if gem.has_key('version'):
                    cmd.append('--version')
                    cmd.append(gem['version'])
            ctxt.es.run(cmd)

    def _reap_gems(self, packages, ctxt):
        pass
