"""Gymnasium wrapper around the Pac-Man engine."""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from engine import PacmanGame, ascii_state
from levels import calc_stars, get_level, load_levels
from observation import make_observation, N_CHANNELS

# ---- Reward shaping: tune these first if the agent does not learn ----------
R_PELLET = 1.0
R_POWER = 5.0
R_GHOST = 10.0
R_DEATH = -10.0
R_STEP = -0.01
R_STATIONARY = -0.05
R_WIN = 50.0


class PacmanEnv(gym.Env):
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, level_id=1, random_level=False, max_level=None, render_mode=None):
        super().__init__()
        self.level_id = level_id
        self.random_level = random_level
        self.level_pool = [c for c in load_levels() if max_level is None or c["id"] <= max_level]
        self.render_mode = render_mode
        probe = PacmanGame(get_level(level_id), seed=0)
        h, w = probe.grid.shape
        self.observation_space = spaces.Box(0.0, 1.0, shape=(N_CHANNELS, h, w), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.game = probe

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if self.random_level:
            cfg = self.level_pool[int(self.np_random.integers(len(self.level_pool)))]
        else:
            cfg = get_level(self.level_id)
        self.cfg = cfg
        self.game = PacmanGame(cfg, seed=int(self.np_random.integers(0, 2**31 - 1)))
        return make_observation(self.game), self._info()

    def step(self, action):
        ev = self.game.step(int(action))
        reward = (R_STEP + (R_STATIONARY if ev.get("stationary") else 0.0)
                  + R_PELLET * ev["pellets"] + R_POWER * ev["power"]
                  + R_GHOST * ev["ghosts_eaten"]
                  + (R_DEATH if ev["died"] else 0.0) + (R_WIN if ev["won"] else 0.0))
        terminated = bool(self.game.done and not self.game.truncated)
        truncated = bool(self.game.truncated)
        return make_observation(self.game), float(reward), terminated, truncated, self._info()

    def set_level(self, level_id):
        self.level_id = level_id
        self.cfg = get_level(level_id)

    def get_level_id(self):
        return self.level_id

    def _info(self):
        g = self.game
        stars = calc_stars(self.cfg, g.score, g.lives, g.won) if hasattr(self, "cfg") else 0
        return {"score": g.score, "won": g.won, "lives": g.lives,
                "pellets_eaten": g.pellets_total - g.pellets_left,
                "steps": g.steps, "level": self.cfg["id"] if hasattr(self, "cfg") else self.level_id,
                "stars": stars}

    def render(self):
        return ascii_state(self.game)
