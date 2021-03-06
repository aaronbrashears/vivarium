from vivarium.vivarium import Action

def register(actions):
    actions['run'] = Run

class Run(Action):
    def __init__(self, *args, **kwargs):
        super(Run, self).__init__(*args, **kwargs)

    def sow(self, ctxt):
        print("Run: sowing step {0}".format(ctxt.number))
        if ctxt.params.has_key('command'):
            return True
        return False

    def plant(self, ctxt):
        print("Run: planting step {0}".format(ctxt.number))
        if ctxt.run(ctxt.params['command']) == 0:
            return True
        return False
