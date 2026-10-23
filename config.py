"""Размеры, цвета, шрифты. Все скорости заданы в пикселях в секунду."""

from functools import lru_cache
from pathlib import Path

import pygame

WIDTH, HEIGHT = 800, 600
FPS = 60
CELL_SIZE = 48
BACKGROUND = (8, 13, 28)
TEXT = (220, 230, 245)
MUTED = (139, 158, 186)
CYAN = (80, 218, 232)
GOLD = (255, 200, 80)
RED = (235, 83, 105)


@lru_cache(maxsize=8)
def font(size=16):
    if not pygame.font.get_init():
        pygame.font.init()
    path = Path(__file__).parent / 'assets' / 'DejaVuSans.ttf'
    fallback = pygame.font.match_font('dejavusans,arial,liberationsans')
    return pygame.font.Font(str(path) if path.exists() else fallback, size)


def label(screen, text, x, y, size=16, color=TEXT, center=False):
    rendered = font(size).render(text, True, color)
    rect = rendered.get_rect()
    rect.midtop = (round(x), round(y)) if center else (0, 0)
    if not center:
        rect.topleft = (round(x), round(y))
    screen.blit(rendered, rect)
