"""Play Pac-Man yourself (pygame) or watch an AI play.

  python play.py                         # level-select menu, keyboard play
  python play.py --level 3               # jump straight to level 3
  python play.py --ai bfs --level 2      # watch the hand-written bot
  python play.py --ai ppo --model checkpoints/ppo_100.zip --level 1

Controls: arrow keys / WASD to steer, P pause, ESC back/quit.
Candy-Crush rules: finish a level to earn 1-3 stars; later levels need a total
number of stars. Progress is stored in progress.json (AI runs never save).
"""
import argparse
import math
import random

import pygame

from bots import BFSBot, PPOPolicy, RandomPolicy
from constants import UP, DOWN, LEFT, RIGHT
from engine import PacmanGame
from levels import calc_stars, is_unlocked, load_levels, load_progress, save_progress, total_stars

TILE, HUD = 40, 80
BG, WALL_C, PELLET_C = (8, 8, 20), (33, 33, 200), (255, 200, 180)
GHOST_COLORS = {"Blinky": (255, 0, 0), "Pinky": (255, 184, 255),
                "Inky": (0, 255, 255), "Clyde": (255, 184, 82)}
KEYS = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
        pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}


def draw_star(screen, cx, cy, r, filled):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    if filled:
        pygame.draw.polygon(screen, (255, 215, 0), pts)
    else:
        pygame.draw.polygon(screen, (90, 90, 110), pts, 2)


def draw_stars(screen, cx, cy, count, r=12):
    for i in range(3):
        draw_star(screen, cx + (i - 1) * (2 * r + 4), cy, r, i < count)


def draw_game(screen, game, cfg, fonts, paused=False):
    screen.fill(BG)
    h, w = game.grid.shape
    for r in range(h):
        for c in range(w):
            x, y = c * TILE, r * TILE
            ch = game.grid[r, c]
            if ch == "#":
                pygame.draw.rect(screen, WALL_C, (x + 2, y + 2, TILE - 4, TILE - 4), border_radius=8)
            elif ch == ".":
                pygame.draw.circle(screen, PELLET_C, (x + TILE // 2, y + TILE // 2), 3)
            elif ch == "o":
                pygame.draw.circle(screen, (255, 255, 255), (x + TILE // 2, y + TILE // 2), 9)
    for g in game.ghosts:
        x, y = g.pos[1] * TILE, g.pos[0] * TILE
        if g.mode == "frightened":
            blink = game.frightened_timer < 8 and game.steps % 2 == 0
            color = (255, 255, 255) if blink else (40, 40, 255)
        else:
            color = GHOST_COLORS[g.name]
        pygame.draw.circle(screen, color, (x + TILE // 2, y + TILE // 2 - 2), TILE // 2 - 4)
        pygame.draw.rect(screen, color, (x + 4, y + TILE // 2 - 2, TILE - 8, TILE // 2 - 4))
        for ex in (x + 13, x + 27):
            pygame.draw.circle(screen, (255, 255, 255), (ex, y + 15), 4)
            pygame.draw.circle(screen, (0, 0, 60), (ex, y + 15), 2)
    px, py = game.pacman[1] * TILE + TILE // 2, game.pacman[0] * TILE + TILE // 2
    pygame.draw.circle(screen, (255, 220, 0), (px, py), TILE // 2 - 3)
    if game.steps % 2 == 0:   # mouth
        dx, dy = {UP: (0, -1), DOWN: (0, 1), LEFT: (-1, 0), RIGHT: (1, 0)}[game.pacman_dir]
        tip = (px + dx * 18, py + dy * 18)
        side = (-dy * 10, dx * 10)
        pygame.draw.polygon(screen, BG, [(px, py), (tip[0] + side[0], tip[1] + side[1]),
                                         (tip[0] - side[0], tip[1] - side[1])])
    y0 = h * TILE
    screen.blit(fonts["m"].render(f"Level {cfg['id']}: {cfg['name']}", True, (255, 255, 255)), (12, y0 + 8))
    screen.blit(fonts["s"].render(f"Score {game.score}   Lives {'<3 ' * game.lives}   "
                                  f"Pellets left {game.pellets_left}", True, (230, 230, 230)), (12, y0 + 44))
    if paused:
        t = fonts["l"].render("PAUSED", True, (255, 255, 0))
        screen.blit(t, t.get_rect(center=(w * TILE // 2, h * TILE // 2)))


def end_screen(screen, game, cfg, stars, fonts, ai):
    w, h = screen.get_size()
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    screen.blit(shade, (0, 0))
    title = "LEVEL CLEARED!" if game.won else "GAME OVER"
    t = fonts["l"].render(title, True, (255, 255, 0) if game.won else (255, 80, 80))
    screen.blit(t, t.get_rect(center=(w // 2, h // 2 - 70)))
    draw_stars(screen, w // 2, h // 2 - 15, stars, r=22)
    s = fonts["m"].render(f"Score {game.score}", True, (255, 255, 255))
    screen.blit(s, s.get_rect(center=(w // 2, h // 2 + 40)))
    hint = fonts["s"].render("Press ENTER to continue", True, (200, 200, 200))
    screen.blit(hint, hint.get_rect(center=(w // 2, h // 2 + 85)))
    pygame.display.flip()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                return True
        pygame.time.wait(30)


def play_level(screen, clock, fonts, cfg, ai=None, speed=8):
    game = PacmanGame(cfg, seed=random.randrange(10 ** 6))
    current, desired, paused = LEFT, None, False
    last = pygame.time.get_ticks()
    interval = 1000 // speed
    while not game.done:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "quit"
                if e.key == pygame.K_p:
                    paused = not paused
                if e.key in KEYS:
                    desired = KEYS[e.key]
        now = pygame.time.get_ticks()
        if not paused and now - last >= interval:
            last = now
            if ai is not None:
                action = ai.act(game)
            else:
                if desired is not None and desired in game.legal_moves(game.pacman):
                    current = desired
                action = current
            game.step(action)
        draw_game(screen, game, cfg, fonts, paused)
        pygame.display.flip()
        clock.tick(60)
    stars = calc_stars(cfg, game.score, game.lives, game.won)
    if game.won and ai is None:
        save_progress(cfg["id"], stars)
    draw_game(screen, game, cfg, fonts)
    return "done" if end_screen(screen, game, cfg, stars, fonts, ai) else None


def level_select(screen, clock, fonts, levels):
    sel = 0
    w, h = screen.get_size()
    while True:
        progress = load_progress()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
                if e.key in (pygame.K_LEFT, pygame.K_a):
                    sel = (sel - 1) % len(levels)
                if e.key in (pygame.K_RIGHT, pygame.K_d):
                    sel = (sel + 1) % len(levels)
                if e.key in (pygame.K_RETURN, pygame.K_SPACE) and is_unlocked(levels[sel]["id"]):
                    return levels[sel]
        screen.fill(BG)
        t = fonts["l"].render("PAC-MAN", True, (255, 220, 0))
        screen.blit(t, t.get_rect(center=(w // 2, 60)))
        sub = fonts["s"].render(f"Total stars: {total_stars()}   |   arrows to choose, ENTER to play", True, (220, 220, 220))
        screen.blit(sub, sub.get_rect(center=(w // 2, 105)))
        n = len(levels)
        cw, gap = 100, 12
        x0 = (w - (n * cw + (n - 1) * gap)) // 2
        for i, cfg in enumerate(levels):
            x, y = x0 + i * (cw + gap), 170
            unlocked = is_unlocked(cfg["id"])
            color = (40, 40, 110) if unlocked else (35, 35, 45)
            pygame.draw.rect(screen, color, (x, y, cw, 190), border_radius=14)
            if i == sel:
                pygame.draw.rect(screen, (255, 220, 0), (x, y, cw, 190), 4, border_radius=14)
            num = fonts["l"].render(str(cfg["id"]), True, (255, 255, 255) if unlocked else (110, 110, 120))
            screen.blit(num, num.get_rect(center=(x + cw // 2, y + 45)))
            if unlocked:
                draw_stars(screen, x + cw // 2, y + 100, progress.get(cfg["id"], 0), r=10)
                nm = fonts["xs"].render(cfg["name"], True, (220, 220, 220))
                screen.blit(nm, nm.get_rect(center=(x + cw // 2, y + 145)))
            else:
                lk = fonts["xs"].render("LOCKED", True, (150, 150, 160))
                screen.blit(lk, lk.get_rect(center=(x + cw // 2, y + 100)))
                need = fonts["xs"].render(f"Need {cfg['stars_to_unlock']} stars", True, (150, 150, 160))
                screen.blit(need, need.get_rect(center=(x + cw // 2, y + 145)))
        pygame.display.flip()
        clock.tick(30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=None)
    ap.add_argument("--ai", choices=["none", "random", "bfs", "ppo"], default="none")
    ap.add_argument("--model", default=None, help="PPO .zip for --ai ppo")
    ap.add_argument("--raw", action="store_true", help="disable action masking and anti-stall routing for PPO")
    ap.add_argument("--speed", type=int, default=8, help="game steps per second")
    args = ap.parse_args()

    levels = load_levels()
    ai = {"none": None, "random": RandomPolicy(), "bfs": BFSBot()}.get(args.ai)
    if args.ai == "ppo":
        ai = PPOPolicy(args.model or "checkpoints/ppo_100.zip", masked=not args.raw, anti_stall=not args.raw)

    pygame.init()
    probe = PacmanGame(levels[0])
    h, w = probe.grid.shape
    screen = pygame.display.set_mode((max(w * TILE, 600), h * TILE + HUD))
    pygame.display.set_caption("Pac-Man RL")
    clock = pygame.time.Clock()
    fonts = {"l": pygame.font.SysFont("arial", 44, bold=True), "m": pygame.font.SysFont("arial", 26, bold=True),
             "s": pygame.font.SysFont("arial", 20), "xs": pygame.font.SysFont("arial", 14)}

    if args.level:
        cfg = next(c for c in levels if c["id"] == args.level)
        if ai is None and not is_unlocked(cfg["id"]):
            print(f"Level {cfg['id']} is locked: you need {cfg['stars_to_unlock']} stars.")
        else:
            play_level(screen, clock, fonts, cfg, ai, args.speed)
    else:
        while True:
            cfg = level_select(screen, clock, fonts, levels)
            if cfg is None or play_level(screen, clock, fonts, cfg, ai, args.speed) is None:
                break
    pygame.quit()


if __name__ == "__main__":
    main()
