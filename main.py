"""Запуск: python main.py. Для автоматической проверки см. --help."""

import argparse
import os


def main():
    parser = argparse.ArgumentParser(description='Практика №3: Космический тир')
    parser.add_argument('--headless', action='store_true', help='запуск без дисплея для проверки')
    parser.add_argument('--frames', type=int, help='завершить после N кадров')
    parser.add_argument('--screenshot', help='сохранить последний кадр в PNG')
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error('--frames должен быть положительным')
    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

    import pygame
    from config import WIDTH, HEIGHT
    from game import Game

    pygame.display.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Космический тир · Практика №3')
        clock = pygame.time.Clock()
        game = Game()
        frame = 0
        limit = args.frames if args.frames is not None else (180 if args.headless else None)
        running = True
        while running:
            dt = min(clock.tick(game.fps_limit) / 1000.0, .05)
            for event in pygame.event.get():
                if not game.handle_event(event):
                    running = False
            if not running:
                break
            game.update(dt, pygame.key.get_pressed())
            game.draw(screen, clock.get_fps())
            pygame.display.flip()
            frame += 1
            if limit is not None and frame >= limit:
                running = False
        if args.screenshot and frame:
            pygame.image.save(screen, args.screenshot)
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
