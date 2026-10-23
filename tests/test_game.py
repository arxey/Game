import os
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import unittest
import random
from collections import defaultdict

import pygame


class GameTests(unittest.TestCase):
    def make_game(self):
        from game import Game
        return Game(seed=42)

    def test_thirty_seconds_of_firing_reuses_twenty_bullets_at_both_fps(self):
        totals = []
        for fps in (20, 60):
            game = self.make_game()
            game.enemies.clear()
            game.turrets.clear()
            keys = defaultdict(bool, {pygame.K_SPACE: True})
            for _ in range(30 * fps):
                game.update(1 / fps, keys)
            self.assertEqual(len(game.bullets.items), 20)
            self.assertEqual(game.shots_fired, 200)
            totals.append(game.shots_fired)
        self.assertEqual(totals, [200, 200])

    def test_hit_queues_fifteen_sparks_and_kill_adds_forty_and_score(self):
        game = self.make_game()
        enemy = game.enemies[0]
        game.on_hit(enemy)
        self.assertEqual(len(list(game.particles.active())), 0)
        game.events.process()
        self.assertEqual(len(list(game.particles.active())), 15)
        self.assertEqual(game.score, 0)
        game.on_hit(enemy)
        game.events.process()
        self.assertEqual(len(list(game.particles.active())), 30)
        game.on_hit(enemy)
        self.assertEqual(game.score, 0)
        game.events.process()
        self.assertEqual(game.score, 1)
        self.assertEqual(len(list(game.particles.active())), 85)

    def test_firing_preserves_fractional_cooldown_with_real_clock_ticks(self):
        durations = [.016] * 600 + [.017] * 1200
        random.Random(1).shuffle(durations)
        for frame_times in (durations, [.016] * 1875):
            game = self.make_game()
            game.enemies.clear()
            game.turrets.clear()
            for dt in frame_times:
                game.update(dt, defaultdict(bool, {pygame.K_SPACE: True}))
            self.assertEqual(game.shots_fired, 200)
            self.assertEqual(len(game.bullets.items), 20)

    def test_long_pause_does_not_accumulate_a_burst_of_shots(self):
        game = self.make_game()
        game.enemies.clear()
        game.turrets.clear()
        for _ in range(600):
            game.update(.05, defaultdict(bool))
        game.update(.05, defaultdict(bool, {pygame.K_SPACE: True}))
        self.assertEqual(game.shots_fired, 1)

    def test_death_event_preserves_hit_position_after_respawn(self):
        game = self.make_game()
        enemy = game.enemies[0]
        enemy.x, enemy.y, enemy.hp = 200, 240, 1
        game.on_hit(enemy)
        self.assertNotEqual((enemy.x, enemy.y), (200, 240))
        game.events.process()
        self.assertEqual({(p.x, p.y) for p in game.particles.active()}, {(200, 240)})

    def test_particle_pool_does_not_grow_after_repeated_separated_explosions(self):
        game = self.make_game()
        enemy = game.enemies[0]
        for _ in range(100):
            enemy.hp = 1
            game.on_hit(enemy)
            game.events.process()
            for particle in game.particles.active():
                particle.update(1)
        self.assertEqual(len(game.particles.items), 300)
        self.assertEqual(game.score, 100)
        self.assertGreater(len(game.bonuses), 0)
        self.assertLess(len(game.bonuses), 100)

    def test_grid_and_brute_force_produce_same_hits_with_fewer_checks(self):
        games = [self.make_game(), self.make_game()]
        for use_grid, game in zip((False, True), games):
            game.use_grid = use_grid
            game.turrets.clear()
            game.add_enemies(150)
            for index, enemy in enumerate(game.enemies):
                enemy.x = enemy.previous_x = 40 + index % 15 * 48
                enemy.y = enemy.previous_y = 130 + index // 15 * 36
            for index in range(0, 158, 4):
                enemy = game.enemies[index]
                game.bullets.get().launch(enemy.x, enemy.y)
            game.check_collisions()
        self.assertEqual([e.hp for e in games[0].enemies], [e.hp for e in games[1].enemies])
        self.assertLess(games[1].checks * 8, games[0].checks)

    def test_bullet_cannot_hit_respawned_enemy_again_in_same_frame(self):
        game = self.make_game()
        game.turrets.clear()
        game.enemies = game.enemies[:1]
        enemy = game.enemies[0]
        enemy.x = enemy.previous_x = 300
        enemy.y = enemy.previous_y = 180
        enemy.hp = 1
        game.bullets.get().launch(300, 180)
        # Перекрывает и старую и новую позицию: после смерти объект исключён.
        game.bullets.get().launch(300, 180)
        game.check_collisions()
        game.events.process()
        self.assertEqual(game.score, 1)
        self.assertEqual(enemy.hp, 3)

    def test_fast_bullet_detects_crossing_between_frames_in_both_modes(self):
        for use_grid in (False, True):
            game = self.make_game()
            game.use_grid = use_grid
            game.turrets.clear()
            game.enemies = game.enemies[:1]
            enemy = game.enemies[0]
            enemy.x = enemy.previous_x = 300
            enemy.y, enemy.previous_y = 350, 330
            bullet = game.bullets.get()
            bullet.launch(300, 355)
            bullet.update(.05)
            # Концы относительного отрезка: +25 и -25. Оба вне радиуса 22.
            game.check_collisions()
            self.assertFalse(bullet.active)
            self.assertEqual(enemy.hp, 2)

    def test_collecting_bonus_enables_three_bullets(self):
        from entities import Bonus
        game = self.make_game()
        game.enemies.clear()
        game.turrets.clear()
        game.bonuses.append(Bonus(game.player.x, game.player.y))
        game.update(0, defaultdict(bool))
        self.assertTrue(game.player.triple)
        game.update(0, defaultdict(bool, {pygame.K_SPACE: True}))
        self.assertEqual(len(list(game.bullets.active())), 3)
        self.assertEqual(len(game.bonuses), 0)

    def test_final_offscreen_segment_can_still_kill_visible_fleeing_enemy(self):
        from enemy import Flee
        for use_grid in (False, True):
            game = self.make_game()
            game.use_grid = use_grid
            game.turrets.clear()
            game.enemies = game.enemies[:1]
            enemy = game.enemies[0]
            enemy.x, enemy.y, enemy.hp = 300, 1, 1
            enemy.state = Flee()
            bullet = game.bullets.get()
            bullet.launch(300, 15)
            game.update(.05, defaultdict(bool))
            self.assertEqual(game.score, 1)
            self.assertFalse(bullet.active)

    def test_turret_bullet_costs_player_one_life(self):
        game = self.make_game()
        game.enemy_bullets.get().launch(game.player.x, game.player.y, vy=250)
        game.update(0, defaultdict(bool))
        self.assertEqual(game.player.lives, 2)
        self.assertEqual(len(list(game.enemy_bullets.active())), 0)

    def test_attacking_enemy_costs_one_life_then_respawns(self):
        from enemy import Attack
        game = self.make_game()
        enemy = game.enemies[0]
        enemy.state = Attack()
        enemy.x, enemy.y = game.player.x, game.player.y
        game.update(0, defaultdict(bool))
        self.assertEqual(game.player.lives, 2)
        self.assertLess(enemy.y, 300)

    def test_game_over_freezes_world_and_r_restarts(self):
        game = self.make_game()
        game.player.lives = 1
        game.enemy_bullets.get().launch(game.player.x, game.player.y, vy=250)
        game.update(0, defaultdict(bool))
        self.assertTrue(game.game_over)
        original_x = game.player.x
        game.update(.05, defaultdict(bool, {pygame.K_RIGHT: True}))
        self.assertEqual(game.player.x, original_x)
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertFalse(game.game_over)
        self.assertEqual(game.player.lives, 3)
        self.assertEqual(game.score, 0)

    def test_debug_keys_and_exactly_158_enemies_after_three_presses(self):
        game = self.make_game()
        for key in (pygame.K_F1, pygame.K_l, pygame.K_g):
            game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.assertTrue(game.debug)
        self.assertEqual(game.fps_limit, 20)
        self.assertFalse(game.use_grid)
        for _ in range(3):
            game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_EQUALS))
        self.assertEqual(len(game.enemies), 158)
        self.assertFalse(game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)))

    def test_large_dt_is_clamped_before_world_update(self):
        game = self.make_game()
        x = game.player.x
        game.update(2, defaultdict(bool, {pygame.K_RIGHT: True}))
        self.assertEqual(game.player.x, x + 15)

    def test_normal_debug_and_game_over_screens_render(self):
        game = self.make_game()
        screen = pygame.Surface((800, 600))
        game.draw(screen, 60)
        self.assertNotEqual(screen.get_at((400, 544))[:3], (8, 13, 28))
        game.debug = True
        game.draw(screen, 20)
        game.player.lives = 0
        game.draw(screen, 20)
