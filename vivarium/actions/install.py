from copy import deepcopy
from vivarium.vivarium import File

def register(actions):
    actions['install'] = Install

class Install(object):
    def __init__(self):
        pass

    def gather(self, source, parameters, env):
        rv = {}
        files = {}
        for filename in parameters.get('files', []):
            the_file = File().from_source(source, filename)
            files[filename] = the_file.to_seed()
        rv['files'] = files
        return rv
