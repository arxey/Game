"""Пространственное разбиение: своя клетка и восемь соседних."""


class Grid:
    def __init__(self, cell_size=48):
        self.cell_size = cell_size
        self.cells = {}

    def cell_of(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def clear(self):
        self.cells.clear()

    def add(self, obj):
        self.cells.setdefault(self.cell_of(obj.x, obj.y), []).append(obj)

    def near(self, x, y):
        cx, cy = self.cell_of(x, y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                yield from self.cells.get((cx + dx, cy + dy), ())
