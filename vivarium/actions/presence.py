from vivarium.vivarium import Action

def register(actions):
    actions['publish_presence'] = PublishPresence
    actions['watch_files'] = WatchFile

class PublishPresence(Action):
    pass

class WatchFile(Action):
    pass
