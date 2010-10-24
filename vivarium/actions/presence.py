def register(actions):
    actions['publish_presence'] = PublishPresence
    actions['watch_files'] = WatchFile

class PublishPresence(object):
    def __init__(self):
        pass

    def seed(self, source, env):
        pass

class WatchFile(object):
    def __init__(self):
        pass

    def seed(self, source, env):
        pass
