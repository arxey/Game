"""Воспроизводимое сравнение: python benchmark.py > docs/benchmark.json.

Замеры update+draw выполняются в памяти без дисплея и не равны реальному FPS.
"""

import json
import os
import platform
import time
from collections import defaultdict

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

from game import Game


def collision_comparison():
    results = {}
    outcomes = []
    for use_grid in (False, True):
        game = Game(seed=42)
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
        results['grid_checks' if use_grid else 'brute_checks'] = game.checks
        outcomes.append([enemy.hp for enemy in game.enemies])
    results['same_hits'] = outcomes[0] == outcomes[1]
    results['reduction'] = round(results['brute_checks'] / max(1, results['grid_checks']), 2)
    results['enemies'] = 158
    results['bullets'] = 40
    return results


def frame_comparison():
    results = []
    screen = pygame.Surface((800, 600))
    for count in (158, 508):
        game = Game(seed=42)
        game.add_enemies(count - 8)
        # Бессмертие исключительно в стенде, чтобы game over не заморозил нагрузку.
        game.player.invulnerable = 1000
        keys = defaultdict(bool, {pygame.K_SPACE: True})
        start = time.perf_counter()
        frames = 300
        for _ in range(frames):
            game.update(1 / 60, keys)
            game.draw(screen, 60)
        results.append({'enemies': count, 'turrets': 2, 'frames': frames,
                        'mean_update_draw_ms': round((time.perf_counter() - start) * 1000 / frames, 3),
                        'bullet_pool': len(game.bullets.items),
                        'particle_pool': len(game.particles.items)})
    return results


if __name__ == '__main__':
    print(json.dumps({'python': platform.python_version(), 'pygame_ce': pygame.version.ver,
                      'collision_fixture': collision_comparison(),
                      'headless_frames': frame_comparison(),
                      'note': 'CPU update+draw into Surface; no window, vsync or real display FPS.'},
                     ensure_ascii=False, indent=2))
