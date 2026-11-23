"""Run with:  python -m unittest discover tests -v"""
import json
import os
import sys
import tempfile
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from constants import UP, DOWN, LEFT, RIGHT, SCORE_STEP_PENALTY, SCORE_STATIONARY_PENALTY
from engine import PacmanGame, load_maze
from ghosts import target_tile, choose_move
from levels import calc_stars, load_levels, save_progress, is_unlocked, total_stars
from bots import BFSBot, RandomPolicy
from observation import make_observation

LEVELS = load_levels()


def cfg_with(maze, **kw):
    c = dict(LEVELS[0], maze=maze)
    c.update(kw)
    return c


class TestEngine(unittest.TestCase):
    def tiny(self, rows, **kw):
        path = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        path.write("\n".join(rows) + "\n")
        path.close()
        return PacmanGame(cfg_with(path.name, **kw), seed=1)

    def test_wall_blocks_movement(self):
        g = self.tiny(["#####", "#P.G#", "#####"], ghosts=0)
        g.step(UP)
        self.assertEqual(g.pacman, (1, 1))

    def test_pellet_eating_and_score(self):
        g = self.tiny(["#######", "#P..#G#", "#######"], ghosts=0)
        before = g.pellets_left
        ev = g.step(RIGHT)
        self.assertEqual(ev["pellets"], 1)
        self.assertEqual(g.pellets_left, before - 1)
        self.assertEqual(g.score, 10 - SCORE_STEP_PENALTY)

    def test_score_decreases_over_time(self):
        g = self.tiny(["########", "#P   .#G#", "########"], ghosts=0)
        g.score = 20
        g.step(RIGHT)  # moved into empty space
        self.assertEqual(g.score, 20 - SCORE_STEP_PENALTY)

    def test_stationary_penalty(self):
        g = self.tiny(["#####", "#P.G#", "#####"], ghosts=0)
        g.score = 20
        ev = g.step(UP)  # wall collision, stationary
        self.assertTrue(ev["stationary"])
        self.assertEqual(g.score, 20 - (SCORE_STEP_PENALTY + SCORE_STATIONARY_PENALTY))

    def test_win_when_all_pellets_eaten(self):
        g = self.tiny(["#####", "#P.G#", "#####"], ghosts=0)
        ev = g.step(RIGHT)
        self.assertTrue(ev["won"] and g.won and g.done)

    def test_power_pellet_frightens_ghosts(self):
        g = self.tiny(["#########", "#Po....G#", "#########"], ghosts=1, frightened_steps=10)
        g.step(RIGHT)
        self.assertEqual(g.ghosts[0].mode, "frightened")
        self.assertGreater(g.frightened_timer, 0)

    def test_ghost_collision_costs_life(self):
        g = self.tiny(["#######", "#P.G..#", "#######"], ghosts=1, ghost_speed=0.0, lives=3)
        g.step(RIGHT)
        ev = g.step(RIGHT)
        self.assertTrue(ev["died"])
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.pacman, g.pacman_start)

    def test_eating_frightened_ghost(self):
        g = self.tiny(["#########", "#Po.G...#", "#########"], ghosts=1, ghost_speed=0.0, frightened_steps=20)
        g.step(RIGHT)
        g.step(RIGHT)
        ev = g.step(RIGHT)
        self.assertEqual(ev["ghosts_eaten"], 1)

    def test_deterministic_with_seed(self):
        def run():
            g = PacmanGame(LEVELS[2], seed=5)
            p = RandomPolicy(3)
            for _ in range(150):
                if g.done:
                    break
                g.step(p.act(g))
            return g.score, g.pacman, [x.pos for x in g.ghosts]
        self.assertEqual(run(), run())


class TestGhosts(unittest.TestCase):
    def setUp(self):
        self.g = PacmanGame(dict(LEVELS[3]), seed=0)   # 4 ghosts
        self.g.pacman = (7, 7)
        self.g.pacman_dir = RIGHT
        for gh in self.g.ghosts:
            gh.mode = "chase"

    def test_blinky_targets_pacman(self):
        self.assertEqual(target_tile(self.g.ghosts[0], self.g), (7, 7))

    def test_pinky_targets_four_ahead(self):
        self.assertEqual(target_tile(self.g.ghosts[1], self.g), (7, 11))

    def test_inky_uses_blinky_vector(self):
        bl = self.g.ghosts[0].pos
        self.assertEqual(target_tile(self.g.ghosts[2], self.g), (2 * 7 - bl[0], 2 * 9 - bl[1]))

    def test_clyde_retreats_when_close(self):
        cl = self.g.ghosts[3]
        cl.pos = (7, 8)
        self.assertEqual(target_tile(cl, self.g), (14, 0))
        cl.pos = (0, 0)
        self.assertEqual(target_tile(cl, self.g), (7, 7))

    def test_ghosts_never_enter_walls(self):
        for _ in range(200):
            self.g.step(RIGHT)
            for gh in self.g.ghosts:
                self.assertNotEqual(self.g.grid[gh.pos], "#")


class TestLevels(unittest.TestCase):
    def test_star_rules(self):
        c = LEVELS[0]
        self.assertEqual(calc_stars(c, 2000, 3, False), 0)
        self.assertEqual(calc_stars(c, 100, 1, True), 1)
        self.assertEqual(calc_stars(c, 100, 2, True), 2)
        self.assertEqual(calc_stars(c, c["star3_min_score"], 3, True), 3)

    def test_unlock_progression(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "progress.json")
            self.assertTrue(is_unlocked(1, p))
            self.assertFalse(is_unlocked(3, p))
            save_progress(1, 2, p)
            save_progress(2, 1, p)
            self.assertTrue(is_unlocked(3, p))        # 3 stars total
            save_progress(1, 1, p)                    # lower score never reduces best
            self.assertEqual(total_stars(p), 3)

    def test_all_mazes_valid(self):
        for cfg in LEVELS:
            grid = load_maze(cfg["maze"])
            if cfg["id"] <= 5:
                self.assertEqual(grid.shape, (15, 15))
            else:
                self.assertEqual(grid.shape, (31, 28))
            self.assertEqual((grid == "P").sum(), 1)
            self.assertGreaterEqual((grid == "G").sum(), cfg["ghosts"])
            start = tuple(np.argwhere(grid == "P")[0])
            seen, q = {start}, deque([start])
            while q:
                r, c = q.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (r + dr, c + dc)
                    if grid[n] != "#" and n not in seen:
                        seen.add(n)
                        q.append(n)
            self.assertEqual(len(seen), int((grid != "#").sum()), f"maze {cfg['id']} not connected")


class TestAgents(unittest.TestCase):
    def test_bfs_bot_clears_level_one(self):
        g = PacmanGame(LEVELS[0], seed=1)
        bot = BFSBot()
        while not g.done:
            g.step(bot.act(g))
        self.assertTrue(g.won)

    def test_observation_shape(self):
        obs = make_observation(PacmanGame(LEVELS[0], seed=0))
        self.assertEqual(obs.shape, (6, 15, 15))
        self.assertEqual(obs[3].sum(), 1.0)


if __name__ == "__main__":
    unittest.main()
