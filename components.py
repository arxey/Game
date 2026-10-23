"""Турель собирается из компонентов, без наследования от Enemy."""

import random

import pygame

from config import WIDTH, label


class Health:
    def __init__(self, hp=3):
        self.maximum = self.hp = hp

    def damage(self):
        self.hp = max(0, self.hp - 1)
        return self.hp == 0

    def update(self, obj, dt):
        pass


class Shooter:
    def __init__(self, cooldown=1.2):
        self.cooldown = cooldown
        self.timer = cooldown

    def update(self, obj, dt):
        self.timer -= dt
        if self.timer <= 1e-9:
            obj.shoot(obj.x, obj.y + 20)
            self.timer += self.cooldown


class GameObject:
    def __init__(self, x, y, *components):
        self.x, self.y = x, y
        self.previous_x, self.previous_y = x, y
        self.components = list(components)

    def update(self, dt):
        for component in self.components:
            component.update(self, dt)


class TurretStyle:
    name = 'турель'
    color = (218, 128, 175)


class Turret(GameObject):
    radius = 18
    state = TurretStyle()

    def __init__(self, x, y, shoot, rng=None):
        self.health = Health(3)
        self.shooter = Shooter(1.2)
        super().__init__(x, y, self.health, self.shooter)
        self.shoot = shoot
        self.rng = rng if rng is not None else random.Random()

    @property
    def hp(self):
        return self.health.hp

    def hit(self):
        return self.health.damage()

    def respawn(self):
        self.x, self.y = self.rng.uniform(25, WIDTH - 25), self.rng.uniform(150, 230)
        self.previous_x, self.previous_y = self.x, self.y
        self.health.hp = self.health.maximum
        self.shooter.timer = self.shooter.cooldown

    def draw(self, screen, debug=False):
        x, y = round(self.x), round(self.y)
        color = self.state.color
        pygame.draw.rect(screen, (49, 30, 52), (x - 16, y - 14, 32, 28), border_radius=6)
        pygame.draw.rect(screen, color, (x - 16, y - 14, 32, 28), width=2, border_radius=6)
        pygame.draw.line(screen, color, (x, y), (x, y + 23), 5)
        for i in range(self.hp):
            pygame.draw.circle(screen, color, (x - (self.hp - 1) * 4 + i * 8, y - 5), 2)
        if debug:
            label(screen, self.state.name, x, y - 35, 12, color, center=True)
