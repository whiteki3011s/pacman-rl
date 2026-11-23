"""Ghost AI: the four classic target-tile behaviours.

Blinky chases Pac-Man's tile, Pinky aims 4 tiles ahead, Inky uses a vector
from Blinky, Clyde chases when far and retreats to his corner when close.
At every tile a ghost picks the legal move that gets closest to its target
and never reverses (except when its mode changes).
"""
from constants import DELTAS, OPPOSITE, UP, LEFT, DOWN, RIGHT

NAMES = ["Blinky", "Pinky", "Inky", "Clyde"]
# Classic tie-break order when two moves are equally good
TIE_ORDER = [UP, LEFT, DOWN, RIGHT]


class Ghost:
    def __init__(self, name, pos):
        self.name = name
        self.start = tuple(pos)
        self.pos = tuple(pos)
        self.mode = "scatter"        # 'scatter' | 'chase' | 'frightened'
        self.direction = None
        self.reverse_pending = False
        self.acc = 0.0               # fractional movement accumulator

    def reset(self, mode):
        self.pos = self.start
        self.mode = mode
        self.direction = None
        self.reverse_pending = False
        self.acc = 0.0


def corner(name, game):
    h, w = game.grid.shape
    return {"Blinky": (0, w - 1), "Pinky": (0, 0),
            "Inky": (h - 1, w - 1), "Clyde": (h - 1, 0)}[name]


def target_tile(ghost, game):
    """Return the (row, col) this ghost is currently heading for."""
    if ghost.mode == "scatter":
        return corner(ghost.name, game)
    pr, pc = game.pacman
    dr, dc = DELTAS[game.pacman_dir]
    if ghost.name == "Blinky":
        return (pr, pc)
    if ghost.name == "Pinky":
        return (pr + 4 * dr, pc + 4 * dc)
    if ghost.name == "Inky":
        pivot = (pr + 2 * dr, pc + 2 * dc)
        br, bc = game.ghosts[0].pos          # Blinky
        return (2 * pivot[0] - br, 2 * pivot[1] - bc)
    if ghost.name == "Clyde":
        r, c = ghost.pos
        if abs(pr - r) + abs(pc - c) > 8:
            return (pr, pc)
        return corner("Clyde", game)
    return (pr, pc)


def choose_move(ghost, game):
    """Return an action (UP/DOWN/LEFT/RIGHT) or None if the ghost is stuck."""
    legal = game.legal_moves(ghost.pos)
    if not legal:
        return None
    if ghost.reverse_pending:
        ghost.reverse_pending = False
        if ghost.direction is not None and OPPOSITE[ghost.direction] in legal:
            return OPPOSITE[ghost.direction]
    options = legal
    if ghost.direction is not None:
        no_rev = [a for a in legal if a != OPPOSITE[ghost.direction]]
        if no_rev:
            options = no_rev
    if ghost.mode == "frightened":
        return game.rng.choice(options)
    tr, tc = target_tile(ghost, game)
    r, c = ghost.pos

    other_pos = {g.pos for g in game.ghosts if g is not ghost}
    free_options = [a for a in options if (r + DELTAS[a][0], c + DELTAS[a][1]) not in other_pos]
    cand = free_options if free_options else options

    def score(a):
        dr, dc = DELTAS[a]
        nr, nc = r + dr, c + dc
        d = (nr - tr) ** 2 + (nc - tc) ** 2
        # Repulsion from other ghosts so they don't walk together
        repulse = sum(200 for g in game.ghosts if g is not ghost and abs(nr - g.pos[0]) + abs(nc - g.pos[1]) <= 1)
        return d + repulse

    return min(cand, key=lambda a: (score(a), TIE_ORDER.index(a)))
