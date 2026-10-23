"""Мир игры: обновление, столкновения, подписчики событий и HUD."""

import random
from dataclasses import dataclass

import pygame

from components import Turret
from config import WIDTH, HEIGHT, FPS, CELL_SIZE, BACKGROUND, TEXT, MUTED, CYAN, GOLD, RED, label
from enemy import Enemy, Attack
from entities import Player, Bullet, Particle, Bonus
from event_queue import EventQueue
from grid import Grid
from pool import Pool


@dataclass(frozen=True)
class HitEvent:
    """Снимок: возрождение врага не меняет уже опубликованное событие."""
    x: float
    y: float
    color: tuple


def swept_hit(first, second):
    """Пересечение кругов за кадр, включая быстрое встречное движение."""
    x0 = first.previous_x - second.previous_x
    y0 = first.previous_y - second.previous_y
    dx = (first.x - second.x) - x0
    dy = (first.y - second.y) - y0
    length_squared = dx * dx + dy * dy
    t = max(0.0, min(1.0, -(x0 * dx + y0 * dy) / length_squared)) if length_squared else 0
    return (x0 + dx * t) ** 2 + (y0 + dy * t) ** 2 <= (first.radius + second.radius) ** 2


def moved_items(pool, dt):
    """Отдать и последний отрезок объекта, выключившегося при движении."""
    for item in pool.active():
        item.update(dt)
        yield item


class Game:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.debug = False
        self.use_grid = True
        self.fps_limit = FPS
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = Pool(Bullet, 20)
        self.enemy_bullets = Pool(Bullet, 20)
        self.particles = Pool(Particle, 300)
        self.enemies = []
        self.add_enemies(8)
        self.turrets = [Turret(110, 155, self.fire_enemy_bullet, self.rng),
                        Turret(WIDTH - 110, 155, self.fire_enemy_bullet, self.rng)]
        self.bonuses = []
        self.grid = Grid(CELL_SIZE)
        self.score = self.checks = self.shots_fired = 0
        self._was_firing = False
        self.events = EventQueue()
        self.events.subscribe('enemy_hit', self._hit_sparks)
        self.events.subscribe('enemy_killed', self._add_score)
        self.events.subscribe('enemy_killed', self._death_sparks)
        self.events.subscribe('enemy_killed', self._drop_bonus)
        self.stars = [[self.rng.uniform(0, WIDTH), self.rng.uniform(0, HEIGHT),
                       self.rng.uniform(15, 65)] for _ in range(90)]
        self._veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._veil.fill((4, 8, 20, 215))

    @property
    def game_over(self):
        return self.player.lives == 0

    def add_enemies(self, count=50):
        self.enemies.extend(Enemy(self.rng) for _ in range(count))

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_F1:
            self.debug = not self.debug
        elif event.key == pygame.K_l:
            self.fps_limit = 20 if self.fps_limit == FPS else FPS
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.add_enemies(50)
        elif event.key == pygame.K_g:
            self.use_grid = not self.use_grid
        elif event.key == pygame.K_r and self.game_over:
            self.reset()
        return True

    def fire_enemy_bullet(self, x, y):
        self.enemy_bullets.get().launch(x, y, vy=250)

    def fire_player(self):
        velocities = (-180, 0, 180) if self.player.triple else (0,)
        for vx in velocities:
            self.bullets.get().launch(self.player.x, self.player.y - 24, vx=vx)
            self.shots_fired += 1
        # При удержании пробела переносим остаток, при новом нажатии
        # начинаем отсчёт с фактического первого выстрела.
        remainder = self.player.reload if self._was_firing else 0.0
        self.player.reload = self.player.COOLDOWN + remainder

    def update(self, dt, keys):
        if self.game_over:
            return
        dt = max(0.0, min(dt, .05))
        self.player.update(dt, keys)
        if keys[pygame.K_SPACE] and self.player.can_shoot():
            self.fire_player()
        self._was_firing = bool(keys[pygame.K_SPACE])
        if not self._was_firing:
            self.player.reload = max(0.0, self.player.reload)
        for star in self.stars:
            star[1] = (star[1] + star[2] * dt) % HEIGHT
        for enemy in self.enemies:
            enemy.update(self.player, dt)
        for turret in self.turrets:
            turret.update(dt)
        for particle in self.particles.active():
            particle.update(dt)
        for bonus in self.bonuses:
            bonus.update(dt)
            if bonus.active and (bonus.x - self.player.x) ** 2 + (bonus.y - self.player.y) ** 2 <= (bonus.radius + self.player.radius) ** 2:
                bonus.active = False
                self.player.activate_triple()
        self.bonuses[:] = [bonus for bonus in self.bonuses if bonus.active]
        self.check_collisions(moved_items(self.bullets, dt))
        self._player_collisions(moved_items(self.enemy_bullets, dt))
        # Подписчики меняют счёт и создают эффекты после обхода столкновений.
        self.events.process()

    def _candidates(self, bullet):
        if not self.use_grid:
            yield from self.enemies
            yield from self.turrets
            return
        seen = set()
        for x, y in ((bullet.x, bullet.y), (bullet.previous_x, bullet.previous_y)):
            for enemy in self.grid.near(x, y):
                if enemy not in seen:
                    seen.add(enemy)
                    yield enemy

    def check_collisions(self, bullets=None):
        targets = self.enemies + self.turrets
        self.grid.clear()
        for target in targets:
            self.grid.add(target)
        self.checks = 0
        resolved = set()
        # Сохраняем порядок полного перебора даже при перекрывающихся врагах.
        order = {target: index for index, target in enumerate(targets)}
        if bullets is None:
            bullets = self.bullets.active()
        for bullet in bullets:
            candidates = self._candidates(bullet)
            if self.use_grid:
                candidates = sorted(candidates, key=order.__getitem__)
            for enemy in candidates:
                if enemy in resolved:
                    continue
                self.checks += 1
                if swept_hit(bullet, enemy):
                    bullet.active = False
                    if self.on_hit(enemy):
                        resolved.add(enemy)
                    break

    def _player_collisions(self, bullets):
        for bullet in bullets:
            if swept_hit(bullet, self.player):
                bullet.active = False
                self.player.hit()
        for enemy in self.enemies:
            if isinstance(enemy.state, Attack) and swept_hit(enemy, self.player):
                self.player.hit()
                enemy.respawn()

    def on_hit(self, enemy):
        """Урон и публикация; счёт, взрыв и бонусы выполняют подписчики."""
        killed = enemy.hit()
        event = HitEvent(enemy.x, enemy.y, enemy.state.color)
        self.events.post('enemy_hit', event)
        if killed:
            self.events.post('enemy_killed', event)
            enemy.respawn()
        return killed

    def _sparks(self, event, count, color):
        for _ in range(count):
            self.particles.get().launch(event.x, event.y, color)

    def _hit_sparks(self, event):
        self._sparks(event, 15, event.color)

    def _death_sparks(self, event):
        self._sparks(event, 40, GOLD)

    def _add_score(self, event):
        self.score += 1

    def _drop_bonus(self, event):
        if self.rng.random() < .25:
            self.bonuses.append(Bonus(event.x, event.y))

    def draw(self, screen, fps=0):
        screen.fill(BACKGROUND)
        for x, y, speed in self.stars:
            shade = int(65 + speed * 1.8)
            pygame.draw.circle(screen, (shade, shade, min(255, shade + 30)),
                               (round(x), round(y)), 2 if speed > 55 else 1)
        if self.debug:
            for x in range(0, WIDTH, CELL_SIZE):
                pygame.draw.line(screen, (23, 36, 55), (x, 105), (x, HEIGHT))
            for y in range(0, HEIGHT, CELL_SIZE):
                pygame.draw.line(screen, (23, 36, 55), (0, y), (WIDTH, y))
        for enemy in self.enemies:
            enemy.draw(screen, self.debug)
        for turret in self.turrets:
            turret.draw(screen, self.debug)
        for bonus in self.bonuses:
            bonus.draw(screen)
        self.player.draw(screen)
        for pool in (self.bullets, self.enemy_bullets, self.particles):
            for item in pool.active():
                item.draw(screen)
        self._draw_hud(screen, fps)
        if self.game_over:
            screen.blit(self._veil, (0, 0))
            label(screen, 'ИГРА ОКОНЧЕНА', WIDTH / 2, 230, 32, TEXT, center=True)
            label(screen, f'Счёт: {self.score}', WIDTH / 2, 283, 24, GOLD, center=True)
            label(screen, 'R — новая игра     Esc — выход', WIDTH / 2, 335, 17, MUTED, center=True)

    def _draw_hud(self, screen, fps):
        pygame.draw.rect(screen, (12, 20, 37), (0, 0, WIDTH, 106))
        pygame.draw.line(screen, (34, 61, 80), (0, 105), (WIDTH, 105))
        label(screen, 'КОСМИЧЕСКИЙ ТИР', 18, 10, 22, CYAN)
        label(screen, f'СЧЁТ  {self.score:04d}', 480, 14, 18, GOLD)
        label(screen, f'ЖИЗНИ  {self.player.lives} / 3', 642, 16, 15, RED)
        label(screen, f'FPS  {fps:.0f} / {self.fps_limit}', 18, 43, 14)
        label(screen, f'Враги: {len(self.enemies)}   Турели: {len(self.turrets)}', 205, 43, 14)
        label(screen, 'F1: ' + ('отладка включена' if self.debug else 'показать отладку'), 565, 43, 13, MUTED)
        label(screen, f'Пули: {sum(1 for _ in self.bullets.active())} / {len(self.bullets.items)}', 18, 65, 13, MUTED)
        label(screen, f'Частицы: {sum(1 for _ in self.particles.active())} / {len(self.particles.items)}', 205, 65, 13, MUTED)
        label(screen, f'Пули турелей: {sum(1 for _ in self.enemy_bullets.active())} / {len(self.enemy_bullets.items)}', 450, 65, 13, MUTED)
        mode = 'СЕТКА 48 px' if self.use_grid else 'ПОЛНЫЙ ПЕРЕБОР'
        label(screen, f'Проверки пуля–враг: {self.checks}   |   G: {mode}', 18, 85, 13, CYAN)
        if self.player.triple:
            label(screen, f'ТРОЙНОЙ ОГОНЬ  {self.player.triple_time:.1f} c', 565, 85, 12, GOLD)
        pygame.draw.rect(screen, (12, 20, 37), (0, HEIGHT - 25, WIDTH, 25))
        label(screen, '← → движение   Пробел огонь   F1 отладка   L 20 FPS   = +50 врагов   G сетка   Esc выход',
              WIDTH / 2, HEIGHT - 20, 12, MUTED, center=True)
