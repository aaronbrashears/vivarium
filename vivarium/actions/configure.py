def register(actions):
    actions['configure'] = Configure

class Configure(object):
    def __init__(self):
        pass

    def seed(self, source, env):
        rv = {}
        with source.open(source.path_to_template(env['template'])) as template:
            rv['template'] = template.read()
        return rv
