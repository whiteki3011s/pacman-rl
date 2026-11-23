"""Headless, deterministic Pac-Man engine (no pygame, no gym).

Usage:
    game = PacmanGame(level_cfg, seed=0)
    events = game.step(action)   # action in {UP, DOWN, LEFT, RIGHT}
"""
import os
import random
import numpy as np

from constants import *
from ghosts import Ghost, NAMES, choose_move

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_maze(path):
    full = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    with open(full) as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip("\n")]
    width = max(len(ln) for ln in lines)
    return np.array([list(ln.ljust(width)) for ln in lines], dtype="<U1")


class PacmanGame:
    def __init__(self, level_cfg, seed=0):
        self.cfg = level_cfg
        self.seed = seed
        self.max_steps = level_cfg.get("max_steps", DEFAULT_MAX_STEPS)
        self.template = load_maze(level_cfg["maze"])
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self):
        self.rng = random.Random(self.seed)
        grid = self.template.copy()
        starts = [tuple(p) for p in np.argwhere(grid == GHOST_START)]
        self.pacman_start = tuple(np.argwhere(grid == PLAYER)[0])
        grid[grid == PLAYER] = EMPTY
        grid[grid == GHOST_START] = EMPTY
        self.grid = grid
        self.global_mode = "scatter"
        self.mode_timer = SCATTER_STEPS
        n = min(self.cfg["ghosts"], len(starts), 4)
        self.ghosts = [Ghost(NAMES[i], starts[i]) for i in range(n)]
        self.pacman = self.pacman_start
        self.pacman_dir = LEFT
        self.score = 0
        self.lives = self.cfg["lives"]
        self.frightened_timer = 0
        self.pellets_total = int(np.isin(grid, [PELLET, POWER]).sum())
        self.pellets_left = self.pellets_total
        self.steps = 0
        self.done = False
        self.won = False
        self.truncated = False

    # ---------------------------------------------------------------- helpers
    def legal_moves(self, pos):
        h, w = self.grid.shape
        out = []
        for a, (dr, dc) in DELTAS.items():
            r, c = pos[0] + dr, pos[1] + dc
            if 0 <= r < h and 0 <= c < w and self.grid[r, c] != WALL:
                out.append(a)
        return out

    def _set_mode(self, ghost, mode):
        if ghost.mode != mode:
            if mode != "frightened" or ghost.mode != "frightened":
                ghost.reverse_pending = True
            ghost.mode = mode

    def _lose_life(self, events):
        self.lives -= 1
        events["died"] = True
        self.frightened_timer = 0
        self.pacman = self.pacman_start
        self.pacman_dir = LEFT
        for g in self.ghosts:
            g.reset(self.global_mode)
        if self.lives <= 0:
            self.done = True

    def _collisions(self, events):
        for g in self.ghosts:
            if g.pos == self.pacman:
                if g.mode == "frightened":
                    self.score += SCORE_GHOST
                    events["ghosts_eaten"] += 1
                    g.reset(self.global_mode)
                else:
                    self._lose_life(events)
                    return

    # ------------------------------------------------------------------- step
    def step(self, action):
        events = {"pellets": 0, "power": 0, "ghosts_eaten": 0,
                  "died": False, "won": False, "stationary": False}
        if self.done:
            return events
        self.steps += 1

        # 1. Pac-Man moves (blocked by walls = stays in place)
        if action in self.legal_moves(self.pacman):
            dr, dc = DELTAS[action]
            self.pacman = (self.pacman[0] + dr, self.pacman[1] + dc)
            self.pacman_dir = action
            cell = self.grid[self.pacman]
            if cell == PELLET:
                self.grid[self.pacman] = EMPTY
                self.score += SCORE_PELLET
                self.pellets_left -= 1
                events["pellets"] += 1
            elif cell == POWER:
                self.grid[self.pacman] = EMPTY
                self.score += SCORE_POWER
                self.pellets_left -= 1
                events["power"] += 1
                self.frightened_timer = self.cfg["frightened_steps"]
                for g in self.ghosts:
                    self._set_mode(g, "frightened")
        else:
            events["stationary"] = True

        # Time and stationary penalties to score
        penalty = SCORE_STEP_PENALTY + (SCORE_STATIONARY_PENALTY if events["stationary"] else 0)
        self.score = max(0, self.score - penalty)

        self._collisions(events)

        # 2. Ghosts move (frightened ghosts are half speed)
        if not self.done:
            for g in self.ghosts:
                speed = self.cfg["ghost_speed"] * (0.5 if g.mode == "frightened" else 1.0)
                g.acc += speed
                while g.acc >= 1.0:
                    g.acc -= 1.0
                    a = choose_move(g, self)
                    if a is not None:
                        dr, dc = DELTAS[a]
                        g.pos = (g.pos[0] + dr, g.pos[1] + dc)
                        g.direction = a
            self._collisions(events)

        # 3. Timers
        if not self.done:
            if self.frightened_timer > 0:
                self.frightened_timer -= 1
                if self.frightened_timer == 0:
                    for g in self.ghosts:
                        if g.mode == "frightened":
                            g.mode = self.global_mode
            else:
                self.mode_timer -= 1
                if self.mode_timer <= 0:
                    self.global_mode = "chase" if self.global_mode == "scatter" else "scatter"
                    self.mode_timer = CHASE_STEPS if self.global_mode == "chase" else SCATTER_STEPS
                    for g in self.ghosts:
                        if g.mode != "frightened":
                            self._set_mode(g, self.global_mode)

        # 4. End conditions
        if not self.done and self.pellets_left == 0:
            self.won = self.done = True
            events["won"] = True
            self.score += SCORE_WIN_BONUS + max(0, self.max_steps - self.steps) // 2
        if not self.done and self.steps >= self.max_steps:
            self.done = self.truncated = True
        return events


def ascii_state(game):
    rows = [list(r) for r in game.grid]
    for g in game.ghosts:
        rows[g.pos[0]][g.pos[1]] = "g" if g.mode == "frightened" else "G"
    rows[game.pacman[0]][game.pacman[1]] = "P"
    return "\n".join("".join(r) for r in rows)


if __name__ == "__main__":
    import json
    cfg = json.load(open(os.path.join(BASE_DIR, "levels.json")))[0]
    g = PacmanGame(cfg, seed=0)
    for _ in range(40):
        g.step(random.choice([UP, DOWN, LEFT, RIGHT]))
    print(ascii_state(g))
    print(f"score={g.score} lives={g.lives} pellets_left={g.pellets_left} steps={g.steps}")
