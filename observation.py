"""Turn a game state into a (6, H, W) float32 array for the neural network."""
import numpy as np
from constants import WALL, PELLET, POWER

N_CHANNELS = 6   # walls, pellets, power, pacman, ghosts, frightened ghosts


def make_observation(game):
    h, w = game.grid.shape
    obs = np.zeros((N_CHANNELS, h, w), dtype=np.float32)
    obs[0] = game.grid == WALL
    obs[1] = game.grid == PELLET
    obs[2] = game.grid == POWER
    obs[3, game.pacman[0], game.pacman[1]] = 1.0
    for g in game.ghosts:
        obs[5 if g.mode == "frightened" else 4, g.pos[0], g.pos[1]] = 1.0
    return obs
