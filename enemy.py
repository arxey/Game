"""Паттерн «Состояние». Enemy делегирует поведение state.update()."""

import random

import pygame

from config import WIDTH, HEIGHT, label


class Patrol:
    name = 'патруль'
    color = (60, 180, 190)

    def update(self, enemy, player, dt):
        enemy.x += enemy.direction * 120 * dt
        if enemy.x < 20 or enemy.x > WIDTH - 20:
            enemy.x = max(20, min(WIDTH - 20, enemy.x))
            enemy.direction *= -1
        if abs(player.x - enemy.x) < 100:
            return Chase()
        return None


class Chase:
    name = 'погоня'
    color = (240, 160, 60)

    def update(self, enemy, player, dt):
        enemy.x += (player.x - enemy.x) * 2 * dt
        enemy.y += 60 * dt
        if enemy.y > HEIGHT / 2:
            return Attack()
        if abs(player.x - enemy.x) > 200:
            return Patrol()
        return None


class Attack:
    name = 'атака'
    color = (230, 70, 70)

    def update(self, enemy, player, dt):
        enemy.y += 400 * dt
        if enemy.y > HEIGHT + 20:
            enemy.respawn()
            return Patrol()
        return None


class Flee:
    name = 'бегство'
    color = (175, 110, 240)

    def __init__(self):
        self.timer = 2.0

    def update(self, enemy, player, dt):
        enemy.y -= 180 * dt
        self.timer -= dt
        if self.timer <= 1e-9:
            # Вернуть врага на игровое поле, а не оставлять патрулировать за экраном.
            enemy.respawn()
            return Patrol()
        return None


class Enemy:
    radius = 18

    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.respawn()

    def respawn(self):
        self.x = self.rng.uniform(25, WIDTH - 25)
        self.y = self.rng.uniform(150, 270)
        self.previous_x, self.previous_y = self.x, self.y
        self.direction = self.rng.choice((-1, 1))
        self.hp = 3
        self.state = Patrol()

    def update(self, player, dt):
        self.previous_x, self.previous_y = self.x, self.y
        next_state = self.state.update(self, player, dt)
        if next_state is not None:
            self.state = next_state

    def hit(self):
        self.hp = max(0, self.hp - 1)
        if self.hp == 1:
            self.state = Flee()
        return self.hp == 0

    def draw(self, screen, debug=False):
        x, y = round(self.x), round(self.y)
        color = self.state.color
        pygame.draw.polygon(screen, tuple(c // 4 for c in color),
                            [(x - 17, y - 8), (x, y - 17), (x + 17, y - 8), (x + 10, y + 12), (x, y + 18), (x - 10, y + 12)])
        pygame.draw.lines(screen, color, True,
                          [(x - 17, y - 8), (x, y - 17), (x + 17, y - 8), (x + 10, y + 12), (x, y + 18), (x - 10, y + 12)], 2)
        for i in range(self.hp):
            pygame.draw.circle(screen, color, (x - (self.hp - 1) * 4 + i * 8, y), 2)
        if debug:
            label(screen, self.state.name, x, y - 37, 12, color, center=True)
