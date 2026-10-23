"""Проверяем поведение паттернов, а не детали отрисовки."""

import unittest
from types import SimpleNamespace


class PoolTests(unittest.TestCase):
    def test_reuses_released_object_and_resets_only_on_launch(self):
        from pool import Pool
        pool = Pool(lambda: SimpleNamespace(active=False), 2)
        first, second = pool.get(), pool.get()
        self.assertIsNot(first, second)
        first.active = False
        self.assertIs(pool.get(), first)
        self.assertEqual(len(pool.items), 2)
        self.assertEqual(len(list(pool.active())), 2)

    def test_grows_only_when_every_item_is_active(self):
        from pool import Pool
        pool = Pool(lambda: SimpleNamespace(active=False), 1)
        pool.get()
        extra = pool.get()
        self.assertTrue(extra.active)
        self.assertEqual(len(pool.items), 2)
        for item in pool.active():
            item.active = False
        self.assertEqual(list(pool.active()), [])


class GridTests(unittest.TestCase):
    def test_near_includes_all_nine_cells_and_handles_negative_coordinates(self):
        from grid import Grid
        grid = Grid(48)
        neighbors = [SimpleNamespace(x=x, y=y) for x in (-1, 24, 49)
                     for y in (-1, 24, 49)]
        distant = SimpleNamespace(x=200, y=200)
        for obj in neighbors + [distant]:
            grid.add(obj)
        self.assertCountEqual(list(grid.near(24, 24)), neighbors)
        grid.clear()
        self.assertEqual(list(grid.near(24, 24)), [])

    def test_cell_boundary_does_not_hide_colliding_enemy(self):
        from grid import Grid
        grid = Grid(48)
        enemy = SimpleNamespace(x=47.5, y=100)
        grid.add(enemy)
        self.assertIn(enemy, list(grid.near(48.5, 100)))


class EventTests(unittest.TestCase):
    def test_events_are_deferred_and_delivered_in_order_to_subscribers(self):
        from event_queue import EventQueue
        queue = EventQueue()
        seen = []
        queue.subscribe('killed', lambda data: seen.append(('score', data)))
        queue.subscribe('killed', lambda data: seen.append(('sparks', data)))
        queue.post('killed', (1, 2))
        self.assertEqual(seen, [])
        queue.process()
        self.assertEqual(seen, [('score', (1, 2)), ('sparks', (1, 2))])
        queue.process()
        self.assertEqual(len(seen), 2)

    def test_event_posted_by_handler_waits_until_next_process(self):
        from event_queue import EventQueue
        queue = EventQueue()
        seen = []
        queue.subscribe('first', lambda data: queue.post('second', data))
        queue.subscribe('second', seen.append)
        queue.post('first', 7)
        queue.process()
        self.assertEqual(seen, [])
        queue.process()
        self.assertEqual(seen, [7])
