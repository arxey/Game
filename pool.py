"""Пул объектов: один и тот же класс используется для пуль и частиц."""


class Pool:
    def __init__(self, create, size):
        self.create = create
        self.items = [create() for _ in range(size)]
        self._cursor = 0

    def get(self):
        # Начинаем с места прошлого поиска, чтобы не сканировать каждый раз
        # занятое начало пула при запуске большого числа искр.
        size = len(self.items)
        for offset in range(size):
            index = (self._cursor + offset) % size
            item = self.items[index]
            if not item.active:
                item.active = True
                self._cursor = (index + 1) % size
                return item
        item = self.create()
        item.active = True
        self.items.append(item)
        self._cursor = 0
        return item

    def active(self):
        # Итератор не создаёт новый список на каждом кадре.
        return (item for item in self.items if item.active)
