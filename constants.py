"""Shared constants for the Pac-Man project."""

# Actions
UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3
DELTAS = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
ACTION_NAMES = {UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"}

# Maze characters
WALL, PELLET, POWER, PLAYER, GHOST_START, EMPTY = "#", ".", "o", "P", "G", " "

# Scoring
SCORE_PELLET = 10
SCORE_POWER = 50
SCORE_GHOST = 200
SCORE_WIN_BONUS = 100      # plus a time bonus (see engine)
SCORE_STEP_PENALTY = 1     # score decreases with each step taken (time decay)
SCORE_STATIONARY_PENALTY = 2  # additional score decrease if agent stays stationary (e.g. wall collision)

# Ghost mode timers (in game steps)
SCATTER_STEPS = 7
CHASE_STEPS = 20

DEFAULT_MAX_STEPS = 600
