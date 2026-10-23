import os
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import random
import unittest
from collections import defaultdict
from types import SimpleNamespace

import pygame


class EntityTests(unittest.TestCase):
    def test_player_travels_300_pixels_at_20_and_60_fps(self):
        from entities import Player
        for fps in (20, 60):
            player = Player()
            player.x = 100
            for _ in range(fps):
                player.update(1 / fps, defaultdict(bool, {pygame.K_RIGHT: True}))
            self.assertAlmostEqual(player.x, 400)

    def test_player_stays_inside_screen(self):
        from entities import Player
        player = Player()
        player.update(10, defaultdict(bool, {pygame.K_LEFT: True}))
        self.assertEqual(player.x, 20)

    def test_bullet_moves_600_pixels_per_second_and_releases_itself(self):
        from entities import Bullet
        bullet = Bullet()
        bullet.launch(100, 500)
        bullet.update(.05)
        self.assertEqual((bullet.x, bullet.y), (100, 470))
        bullet.update(1)
        self.assertFalse(bullet.active)
        bullet.launch(200, 300)
        self.assertTrue(bullet.active)
        self.assertEqual((bullet.x, bullet.y), (200, 300))

    def test_particle_expires_and_launch_resets_lifetime(self):
        from entities import Particle
        particle = Particle()
        particle.launch(20, 30, (60, 180, 190))
        particle.update(1)
        self.assertFalse(particle.active)
        particle.launch(40, 50, (230, 70, 70))
        self.assertTrue(particle.active)
        self.assertGreater(particle.life, 0)
        self.assertEqual(particle.color, (230, 70, 70))

    def test_triple_bonus_expires_after_five_seconds(self):
        from entities import Player
        player = Player()
        player.activate_triple()
        for _ in range(99):
            player.update(.05, defaultdict(bool))
        self.assertTrue(player.triple)
        player.update(.05, defaultdict(bool))
        self.assertFalse(player.triple)

    def test_player_invulnerability_prevents_multiple_losses_in_one_frame(self):
        from entities import Player
        player = Player()
        self.assertTrue(player.hit())
        self.assertFalse(player.hit())
        self.assertEqual(player.lives, 2)
        player.update(1.5, defaultdict(bool))
        self.assertTrue(player.hit())
        self.assertEqual(player.lives, 1)


class StateTests(unittest.TestCase):
    def setUp(self):
        from enemy import Enemy
        self.enemy = Enemy(random.Random(4))
        self.enemy.x, self.enemy.y = 100, 180
        self.enemy.direction = 1
        self.player = SimpleNamespace(x=700)

    def test_patrol_moves_at_120_and_enters_chase_when_player_is_close(self):
        from enemy import Chase
        self.enemy.update(self.player, .05)
        self.assertEqual(self.enemy.x, 106)
        self.player.x = 110
        self.enemy.update(self.player, .05)
        self.assertIsInstance(self.enemy.state, Chase)

    def test_chase_returns_to_patrol_when_player_escapes(self):
        from enemy import Chase, Patrol
        self.enemy.state = Chase()
        self.enemy.update(self.player, .05)
        self.assertIsInstance(self.enemy.state, Patrol)

    def test_chase_below_half_screen_enters_attack(self):
        from enemy import Chase, Attack
        self.enemy.state = Chase()
        self.enemy.y = 301
        self.player.x = self.enemy.x
        self.enemy.update(self.player, .05)
        self.assertIsInstance(self.enemy.state, Attack)

    def test_attack_dives_at_400_then_respawns(self):
        from enemy import Attack, Patrol
        self.enemy.state = Attack()
        self.enemy.update(self.player, .05)
        self.assertEqual(self.enemy.y, 200)
        self.enemy.y = 619
        self.enemy.update(self.player, .05)
        self.assertIsInstance(self.enemy.state, Patrol)
        self.assertLess(self.enemy.y, 300)

    def test_one_hp_enters_flee_and_returns_after_two_seconds(self):
        from enemy import Flee, Patrol
        self.enemy.hit()
        self.enemy.hit()
        self.assertEqual(self.enemy.hp, 1)
        self.assertIsInstance(self.enemy.state, Flee)
        original_y = self.enemy.y
        for _ in range(39):
            self.enemy.update(self.player, .05)
        self.assertLess(self.enemy.y, original_y)
        self.assertIsInstance(self.enemy.state, Flee)
        self.enemy.update(self.player, .05)
        self.assertIsInstance(self.enemy.state, Patrol)
        self.assertEqual(self.enemy.hp, 3)


class ComponentTests(unittest.TestCase):
    def test_turret_components_shoot_on_timer_and_health_takes_damage(self):
        from components import Turret
        shots = []
        turret = Turret(120, 140, lambda x, y: shots.append((x, y)))
        for _ in range(23):
            turret.update(.05)
        self.assertEqual(shots, [])
        turret.update(.05)
        self.assertEqual(shots, [(120, 160)])
        turret.hit()
        self.assertEqual(turret.hp, 2)
        self.assertEqual((turret.x, turret.y), (120, 140))
