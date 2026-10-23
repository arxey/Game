"""Очередь событий: отправитель не знает подписчиков."""


class EventQueue:
    def __init__(self):
        self.events = []
        self.handlers = {}

    def subscribe(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)

    def post(self, name, data):
        self.events.append((name, data))

    def process(self):
        # События, созданные подписчиками, останутся до следующего process().
        pending, self.events = self.events, []
        for name, data in pending:
            for handler in self.handlers.get(name, ()):
                handler(data)
