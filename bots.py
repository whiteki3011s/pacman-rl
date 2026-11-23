"""Simple non-learning policies used as baselines.

RandomPolicy  - the 'before training' agent (uniform random over 4 actions).
BFSBot        - hand-written strategy: walk to the nearest pellet, avoid ghosts.
All policies expose act(game) -> action.
"""
import os
import random
from collections import deque

from constants import DELTAS, WALL, PELLET, POWER


class RandomPolicy:
    name = "random"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def act(self, game):
        return self.rng.randrange(4)


class BFSBot:
    name = "bfs_bot"

    def __init__(self, danger_radius=2):
        self.danger_radius = danger_radius

    def _danger_tiles(self, game):
        danger = set()
        for g in game.ghosts:
            if g.mode == "frightened":
                continue
            r, c = g.pos
            for dr in range(-self.danger_radius, self.danger_radius + 1):
                for dc in range(-self.danger_radius, self.danger_radius + 1):
                    if abs(dr) + abs(dc) <= self.danger_radius:
                        danger.add((r + dr, c + dc))
        return danger

    def act(self, game):
        danger = self._danger_tiles(game)
        start = game.pacman
        queue = deque([(start, None)])
        seen = {start}
        while queue:
            pos, first = queue.popleft()
            if pos != start and game.grid[pos] in (PELLET, POWER):
                return first
            for a in game.legal_moves(pos):
                dr, dc = DELTAS[a]
                n = (pos[0] + dr, pos[1] + dc)
                if n in seen or n in danger:
                    continue
                seen.add(n)
                queue.append((n, first if first is not None else a))
        # No safe path to a pellet: step to the legal move farthest from ghosts
        legal = game.legal_moves(start)
        if not legal:
            return 0

        def safety(a):
            dr, dc = DELTAS[a]
            n = (start[0] + dr, start[1] + dc)
            if not game.ghosts:
                return 0
            return min(abs(n[0] - g.pos[0]) + abs(n[1] - g.pos[1]) for g in game.ghosts)

        return max(legal, key=safety)


class PPOPolicy:
    """Wraps a trained Stable-Baselines3 PPO model with action masking and anti-stall routing."""

    def __init__(self, path, deterministic=True, masked=True, anti_stall=True, stall_patience=6):
        import torch
        from stable_baselines3 import PPO
        from observation import make_observation
        self._torch = torch
        self._obs = make_observation
        if isinstance(path, str):
            self.model = PPO.load(path, device="cpu")
            self.name = os.path.splitext(os.path.basename(path))[0]
        else:
            self.model = path
            self.name = "in_memory_ppo"
        self.masked = masked
        self.anti_stall = anti_stall
        self.stall_patience = stall_patience
        self.recent_pos = deque(maxlen=8)
        self.steps_since_pellet = 0
        self.last_pellets = 0

    def act(self, game):
        legal = game.legal_moves(game.pacman)
        if not legal:
            return 0

        active_ghosts = [g for g in game.ghosts if g.mode != "frightened"]
        ghost_pos = {g.pos for g in active_ghosts}

        # Filter suicide moves (stepping directly into active ghosts)
        safe_moves = [a for a in legal if (game.pacman[0] + DELTAS[a][0], game.pacman[1] + DELTAS[a][1]) not in ghost_pos]
        cand_moves = safe_moves if safe_moves else legal

        # If ghost is within critical threat radius (<= 2 tiles), prioritize multi-ghost escape vector
        min_g_dist = min([abs(game.pacman[0] - g[0]) + abs(game.pacman[1] - g[1]) for g in ghost_pos] or [99])
        if min_g_dist <= 2:
            return max(cand_moves, key=lambda a: min([abs(game.pacman[0] + DELTAS[a][0] - g[0]) + abs(game.pacman[1] + DELTAS[a][1] - g[1]) for g in ghost_pos] or [99]))

        obs = self._torch.as_tensor(self._obs(game)[None]).float()
        with self._torch.no_grad():
            dist = self.model.policy.get_distribution(obs)
            probs = dist.distribution.probs[0].cpu().numpy()

        chosen = int(max(cand_moves, key=lambda a: probs[a])) if self.masked else int(self.model.predict(self._obs(game), deterministic=self.deterministic)[0])

        if not self.anti_stall:
            return chosen

        # Track progress
        if game.pellets_left < self.last_pellets or game.steps == 0:
            self.steps_since_pellet = 0
            self.last_pellets = game.pellets_left
        else:
            self.steps_since_pellet += 1

        self.recent_pos.append(game.pacman)
        is_looping = self.recent_pos.count(game.pacman) >= 3

        # If ghost is within medium evasion range (<= 3 tiles), prioritize PPO's trained reflex
        if min_g_dist <= 3:
            return chosen

        # If stalling (looping or no pellets collected for > patience steps in empty space), route toward nearest pellet avoiding ghost paths
        if (is_looping or self.steps_since_pellet > self.stall_patience) and game.pellets_left > 0:
            q = deque([(game.pacman, None)])
            seen = {game.pacman}
            while q:
                pos, first_act = q.popleft()
                if pos != game.pacman and game.grid[pos] in (PELLET, POWER):
                    if first_act in cand_moves:
                        return first_act
                for a in game.legal_moves(pos):
                    dr, dc = DELTAS[a]
                    nxt = (pos[0] + dr, pos[1] + dc)
                    if nxt not in seen and nxt not in ghost_pos:
                        seen.add(nxt)
                        q.append((nxt, first_act if first_act is not None else a))

        return chosen
