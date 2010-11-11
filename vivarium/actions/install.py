from copy import deepcopy
from vivarium.vivarium import File
from vivarium.vivarium import Action

def register(actions):
    actions['install'] = Install

class Install(Action):
    def gather(self, source, parameters, env):
        rv = {}
        files = {}
        for filename in parameters.get('files', []):
            the_file = File().from_source(source, filename)
            files[filename] = the_file.to_seed()
        rv['files'] = files
        return rv
