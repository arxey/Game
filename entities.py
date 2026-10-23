"""Объекты с update(dt) и draw(screen): корабль, пули, частицы, бонусы."""

import math
import random

import pygame

from config import WIDTH, HEIGHT, CYAN, GOLD, RED, label


class Player:
    SPEED = 300
    COOLDOWN = .15
    radius = 17

    def __init__(self):
        self.x, self.y = WIDTH / 2, HEIGHT - 55
        self.previous_x, self.previous_y = self.x, self.y
        self.reload = 0.0
        self.lives = 3
        self.invulnerable = 0.0
        self.triple_time = 0.0

    @property
    def triple(self):
        return self.triple_time > 1e-9

    def update(self, dt, keys):
        self.previous_x, self.previous_y = self.x, self.y
        direction = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        self.x = max(20, min(WIDTH - 20, self.x + direction * self.SPEED * dt))
        # Отрицательный остаток нужен для точной частоты при кадрах 16–17 мс.
        self.reload -= dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.triple_time = max(0.0, self.triple_time - dt)

    def can_shoot(self):
        return self.reload <= 1e-9

    def activate_triple(self):
        self.triple_time = 5.0

    def hit(self):
        if self.lives == 0 or self.invulnerable > 1e-9:
            return False
        self.lives -= 1
        self.invulnerable = 1.5
        return True

    def draw(self, screen):
        x, y = round(self.x), round(self.y)
        if self.invulnerable > 0 and int(self.invulnerable * 12) % 2:
            return
        pygame.draw.polygon(screen, (29, 71, 101),
                            [(x, y - 21), (x - 19, y + 17), (x, y + 9), (x + 19, y + 17)])
        pygame.draw.lines(screen, CYAN, True,
                          [(x, y - 21), (x - 19, y + 17), (x, y + 9), (x + 19, y + 17)], 2)
        pygame.draw.circle(screen, (203, 249, 255), (x, y - 1), 4)
        pygame.draw.polygon(screen, GOLD, [(x - 5, y + 14), (x, y + 27), (x + 5, y + 14)])
        if self.triple:
            pygame.draw.circle(screen, GOLD, (x, y), 28, 1)


class Bullet:
    SPEED = 600
    radius = 4

    def __init__(self):
        self.active = False
        self.x = self.y = self.previous_x = self.previous_y = 0.0
        self.vx, self.vy = 0.0, -self.SPEED

    def launch(self, x, y, vx=0.0, vy=None):
        self.active = True
        self.x = self.previous_x = float(x)
        self.y = self.previous_y = float(y)
        self.vx = vx
        self.vy = -math.sqrt(self.SPEED ** 2 - vx ** 2) if vy is None else vy

    def update(self, dt):
        self.previous_x, self.previous_y = self.x, self.y
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -10 or self.y > HEIGHT + 10 or self.x < -10 or self.x > WIDTH + 10:
            self.active = False

    def draw(self, screen):
        color = RED if self.vy > 0 else CYAN
        pygame.draw.line(screen, color, (self.x, self.y + (9 if self.vy < 0 else -9)),
                         (self.x, self.y), 3)
        pygame.draw.circle(screen, (240, 250, 255), (self.x, self.y), 2)


class Particle:
    def __init__(self):
        self.active = False
        self.x = self.y = self.vx = self.vy = self.life = 0.0
        self.color = GOLD

    def launch(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(50, 250)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = random.uniform(.3, .8)
        self.color = color
        self.active = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 1e-9:
            self.active = False

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), 2 if self.life > .2 else 1)


class Bonus:
    radius = 13
    SPEED = 90

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.active = True

    def update(self, dt):
        self.y += self.SPEED * dt
        if self.y > HEIGHT + self.radius:
            self.active = False

    def draw(self, screen):
        rect = pygame.Rect(round(self.x) - 12, round(self.y) - 12, 24, 24)
        pygame.draw.rect(screen, (53, 43, 28), rect, border_radius=6)
        pygame.draw.rect(screen, GOLD, rect, width=2, border_radius=6)
        label(screen, '3', self.x, self.y - 11, 16, GOLD, center=True)
