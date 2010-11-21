from vivarium.vivarium import Action

def register(actions):
    actions['publish_presence'] = PublishPresence
    actions['watch_files'] = WatchFile

class PublishPresence(Action):
    def __init__(self, *args, **kwargs):
        super(PublishPresence, self).__init__(*args, **kwargs)

class WatchFile(Action):
    def __init__(self, *args, **kwargs):
        super(WatchFile, self).__init__(*args, **kwargs)
