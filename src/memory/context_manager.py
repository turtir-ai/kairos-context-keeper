class ContextManager:
    def __init__(self):
        self.context = {}
    def update(self, key, value):
        self.context[key] = value 