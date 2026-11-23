"""Interactive Prototype & Live AI Demonstration Dashboard.

Run this script to present your Reinforcement Learning Pac-Man project:
    python prototype_demo.py

Controls & Live Presentation Toggles:
  [1] - [3]      : Switch Level (1: Warm-up, 2: Twin Trouble, 3: Triple Chase)
  [P]            : Cycle Policy (Smart PPO -> Raw PPO -> Random -> BFS Oracle -> Human)
  [M]            : Toggle Action Masking (ON / OFF) - demonstrates 0 wall collisions
  [A]            : Toggle Anti-Stall Loop Breaker (ON / OFF) - demonstrates solving the hide tactic
  [E]            : Toggle Multi-Ghost Evasion Vector (ON / OFF)
  [SPACE]        : Pause / Resume simulation
  [N]            : Step 1 frame while paused (frame-by-frame analysis)
  [R]            : Restart current level
  [UP/DOWN/LEFT/RIGHT] : Steer Pac-Man in Human mode
  [+] / [-]      : Speed up / slow down simulation (FPS)
  [ESC]          : Quit prototype
"""
import math
import os
import random
import sys
from collections import deque

import pygame
import numpy as np

from constants import UP, DOWN, LEFT, RIGHT, DELTAS, PELLET, POWER
from engine import PacmanGame
from levels import get_level, calc_stars, total_stars, load_progress
from observation import make_observation

# ----------------- UI Constants & Colors -----------------
TILE = 40
BOARD_SIZE = 15 * TILE  # 600px
SIDEBAR_W = 380
TOTAL_W = BOARD_SIZE + SIDEBAR_W
TOTAL_H = BOARD_SIZE + 40  # 640px

# Palette
BG_COLOR = (10, 12, 24)
SIDEBAR_BG = (16, 20, 36)
CARD_BG = (24, 30, 52)
CARD_BORDER = (45, 55, 90)
WALL_C = (33, 55, 210)
PELLET_C = (255, 210, 190)
POWER_C = (255, 255, 255)
PACMAN_C = (255, 225, 0)
TEXT_WHITE = (245, 248, 255)
TEXT_MUTED = (140, 155, 185)
ACCENT_GREEN = (46, 204, 113)
ACCENT_RED = (231, 76, 60)
ACCENT_BLUE = (52, 152, 219)
ACCENT_YELLOW = (241, 196, 15)
ACCENT_PURPLE = (155, 89, 182)

GHOST_COLORS = {
    "Blinky": (255, 60, 60),
    "Pinky": (255, 160, 230),
    "Inky": (40, 220, 255),
    "Clyde": (255, 175, 70),
}
ACTION_NAMES = {UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"}
ARROW_CHARS = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}


# ----------------- Standalone Smart PPO Controller -----------------
class PrototypePPOController:
    """Configurable PPO controller allowing live toggling of individual components."""

    def __init__(self, model_path):
        import torch
        from stable_baselines3 import PPO
        self._torch = torch
        self.model = PPO.load(model_path, device="cpu") if isinstance(model_path, str) else model_path
        self.action_masking = True
        self.anti_stall = True
        self.evasion_vector = True
        self.stall_patience = 6

        # Tracking internal state
        self.recent_pos = deque(maxlen=8)
        self.steps_since_pellet = 0
        self.last_pellets = 0
        self.last_probs = np.array([0.25, 0.25, 0.25, 0.25])
        self.active_mode = "PPO Neural Policy"

    def reset(self):
        self.recent_pos.clear()
        self.steps_since_pellet = 0
        self.last_pellets = 0
        self.last_probs = np.array([0.25, 0.25, 0.25, 0.25])
        self.active_mode = "Initialized"

    def act(self, game):
        legal = game.legal_moves(game.pacman)
        if not legal:
            self.active_mode = "Trapped"
            return 0

        # 1. Neural Network Forward Pass
        obs = self._torch.as_tensor(make_observation(game)[None]).float()
        with self._torch.no_grad():
            dist = self.model.policy.get_distribution(obs)
            probs = dist.distribution.probs[0].cpu().numpy()
        self.last_probs = probs

        active_ghosts = [g for g in game.ghosts if g.mode != "frightened"]
        ghost_pos = {g.pos for g in active_ghosts}

        # 2. Suicide filtering (Instant Collision Prevention)
        if self.action_masking:
            safe_moves = [a for a in legal if (game.pacman[0] + DELTAS[a][0], game.pacman[1] + DELTAS[a][1]) not in ghost_pos]
            cand_moves = safe_moves if safe_moves else legal
        else:
            cand_moves = [UP, DOWN, LEFT, RIGHT]  # Unconstrained

        # 3. Multi-Ghost Proximity Evasion
        min_g_dist = min([abs(game.pacman[0] - g[0]) + abs(game.pacman[1] - g[1]) for g in ghost_pos] or [99])
        if self.evasion_vector and min_g_dist <= 2 and active_ghosts:
            self.active_mode = "CRITICAL EVASION (<=2 tiles)"
            return max(cand_moves, key=lambda a: min([abs(game.pacman[0] + DELTAS[a][0] - g[0]) + abs(game.pacman[1] + DELTAS[a][1] - g[1]) for g in ghost_pos] or [99]))

        # 4. Standard Masked Choice
        if self.action_masking:
            chosen = int(max(cand_moves, key=lambda a: probs[a]))
            self.active_mode = "Masked Neural Navigation"
        else:
            chosen = int(np.argmax(probs))
            self.active_mode = "Raw Neural Logits (Unmasked)"

        # 5. Anti-Stall Loop Breaker
        if game.pellets_left < self.last_pellets or game.steps == 0:
            self.steps_since_pellet = 0
            self.last_pellets = game.pellets_left
        else:
            self.steps_since_pellet += 1

        self.recent_pos.append(game.pacman)
        is_looping = self.recent_pos.count(game.pacman) >= 3

        if min_g_dist <= 3:
            self.active_mode = "PPO Threat Avoidance"
            return chosen

        if self.anti_stall and (is_looping or self.steps_since_pellet > self.stall_patience) and game.pellets_left > 0:
            q = deque([(game.pacman, None)])
            seen = {game.pacman}
            while q:
                pos, first_act = q.popleft()
                if pos != game.pacman and game.grid[pos] in (PELLET, POWER):
                    if first_act in cand_moves:
                        self.active_mode = "Anti-Stall Route Injection"
                        return first_act
                for a in game.legal_moves(pos):
                    dr, dc = DELTAS[a]
                    nxt = (pos[0] + dr, pos[1] + dc)
                    if nxt not in seen and nxt not in ghost_pos:
                        seen.add(nxt)
                        q.append((nxt, first_act if first_act is not None else a))

        return chosen


# ----------------- Drawing Utilities -----------------
def draw_star(surface, cx, cy, r, filled):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    if filled:
        pygame.draw.polygon(surface, ACCENT_YELLOW, pts)
    else:
        pygame.draw.polygon(surface, (70, 80, 110), pts, 2)


def draw_hud_card(surface, rect, title, fonts):
    pygame.draw.rect(surface, CARD_BG, rect, border_radius=10)
    pygame.draw.rect(surface, CARD_BORDER, rect, width=1, border_radius=10)
    if title:
        surface.blit(fonts["h3"].render(title, True, TEXT_MUTED), (rect[0] + 12, rect[1] + 8))


# ----------------- Main Prototype App -----------------
def run_prototype():
    pygame.init()
    pygame.display.set_caption("Pac-Man RL Interactive Prototype & AI Brain HUD")
    screen = pygame.display.set_mode((TOTAL_W, TOTAL_H))
    clock = pygame.time.Clock()

    # Fonts
    fonts = {
        "title": pygame.font.SysFont("Helvetica", 20, bold=True),
        "h2": pygame.font.SysFont("Helvetica", 16, bold=True),
        "h3": pygame.font.SysFont("Helvetica", 13, bold=True),
        "body": pygame.font.SysFont("Helvetica", 13),
        "mono": pygame.font.SysFont("Menlo", 12),
        "large": pygame.font.SysFont("Helvetica", 28, bold=True),
    }

    # Locate best checkpoints
    model_paths = [
        "checkpoints/level_3_3stars.zip",
        "checkpoints/level_2_final_ppo100.zip",
        "checkpoints/level_2_3stars.zip",
        "checkpoints/ppo_100.zip",
        "checkpoints/level_1_3stars.zip",
    ]
    best_ckpt = next((p for p in model_paths if os.path.exists(p)), None)
    if not best_ckpt:
        print("[!] No trained checkpoints found. Please train or provide checkpoints.")
        sys.exit(1)

    print(f"[Prototype] Initialized with checkpoint: {best_ckpt}")
    smart_ppo = PrototypePPOController(best_ckpt)

    from bots import BFSBot, RandomPolicy
    bfs_bot = BFSBot()
    random_bot = RandomPolicy()

    # State
    current_level_id = 3
    level_cfg = get_level(current_level_id)
    game = PacmanGame(level_cfg, seed=13)
    policy_mode = "Smart PPO"  # "Smart PPO", "Raw PPO", "Random", "BFS Oracle", "Human"
    smart_ppo.reset()

    paused = False
    step_once = False
    fps = 15
    human_dir = RIGHT

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_n:
                    step_once = True
                    paused = True
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    fps = min(60, fps + 5)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                    fps = max(5, fps - 5)
                elif event.key == pygame.K_r:
                    game = PacmanGame(level_cfg, seed=random.randint(1, 99999))
                    smart_ppo.reset()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    current_level_id = event.key - pygame.K_0
                    level_cfg = get_level(current_level_id)
                    game = PacmanGame(level_cfg, seed=random.randint(1, 99999))
                    smart_ppo.reset()
                elif event.key == pygame.K_p:
                    modes = ["Smart PPO", "Raw PPO", "Random", "BFS Oracle", "Human"]
                    policy_mode = modes[(modes.index(policy_mode) + 1) % len(modes)]
                    smart_ppo.action_masking = (policy_mode == "Smart PPO")
                    smart_ppo.anti_stall = (policy_mode == "Smart PPO")
                    smart_ppo.evasion_vector = (policy_mode == "Smart PPO")
                elif event.key == pygame.K_m:
                    smart_ppo.action_masking = not smart_ppo.action_masking
                elif event.key == pygame.K_a:
                    smart_ppo.anti_stall = not smart_ppo.anti_stall
                elif event.key == pygame.K_e:
                    smart_ppo.evasion_vector = not smart_ppo.evasion_vector
                elif policy_mode == "Human":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        human_dir = UP
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        human_dir = DOWN
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        human_dir = LEFT
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        human_dir = RIGHT

        # 2. Simulation Step
        if (not paused or step_once) and not game.done:
            step_once = False
            act = 0
            if policy_mode == "Smart PPO":
                act = smart_ppo.act(game)
            elif policy_mode == "Raw PPO":
                smart_ppo.action_masking = False
                smart_ppo.anti_stall = False
                smart_ppo.evasion_vector = False
                act = smart_ppo.act(game)
            elif policy_mode == "Random":
                act = random_bot.act(game)
            elif policy_mode == "BFS Oracle":
                act = bfs_bot.act(game)
            elif policy_mode == "Human":
                legal = game.legal_moves(game.pacman)
                act = human_dir if human_dir in legal else (game.pacman_dir if game.pacman_dir in legal else 0)

            game.step(act)

        # 3. Render Game Board (Left)
        screen.fill(BG_COLOR)
        h, w = game.grid.shape
        for r in range(h):
            for c in range(w):
                x, y = c * TILE, r * TILE
                ch = game.grid[r, c]
                if ch == "#":
                    pygame.draw.rect(screen, WALL_C, (x + 2, y + 2, TILE - 4, TILE - 4), border_radius=6)
                elif ch == ".":
                    pygame.draw.circle(screen, PELLET_C, (x + TILE // 2, y + TILE // 2), 3)
                elif ch == "o":
                    pygame.draw.circle(screen, POWER_C, (x + TILE // 2, y + TILE // 2), 8)

        # Ghosts
        for g in game.ghosts:
            x, y = g.pos[1] * TILE, g.pos[0] * TILE
            if g.mode == "frightened":
                blink = game.frightened_timer < 8 and game.steps % 2 == 0
                c = (255, 255, 255) if blink else (60, 80, 255)
            else:
                c = GHOST_COLORS.get(g.name, (200, 50, 50))
            pygame.draw.circle(screen, c, (x + TILE // 2, y + TILE // 2 - 3), TILE // 2 - 4)
            pygame.draw.rect(screen, c, (x + 4, y + TILE // 2 - 3, TILE - 8, TILE // 2 - 3))
            # Eyes
            pygame.draw.circle(screen, (255, 255, 255), (x + 13, y + 14), 4)
            pygame.draw.circle(screen, (255, 255, 255), (x + 27, y + 14), 4)
            pygame.draw.circle(screen, (10, 20, 60), (x + 13, y + 14), 2)
            pygame.draw.circle(screen, (10, 20, 60), (x + 27, y + 14), 2)

        # Pacman
        px, py = game.pacman[1] * TILE + TILE // 2, game.pacman[0] * TILE + TILE // 2
        pygame.draw.circle(screen, PACMAN_C, (px, py), TILE // 2 - 3)
        # Mouth animation
        if game.steps % 2 == 0:
            dx, dy = DELTAS.get(game.pacman_dir, (0, 0))
            tip = (px + dx * 16, py + dy * 16)
            side = (-dy * 9, dx * 9)
            pygame.draw.polygon(screen, BG_COLOR, [(px, py), (tip[0] + side[0], tip[1] + side[1]),
                                                   (tip[0] - side[0], tip[1] - side[1])])

        # Board Bottom Status Bar
        pygame.draw.rect(screen, (18, 22, 40), (0, BOARD_SIZE, BOARD_SIZE, 40))
        pygame.draw.line(screen, CARD_BORDER, (0, BOARD_SIZE), (BOARD_SIZE, BOARD_SIZE), 1)
        stars = calc_stars(level_cfg, game.score, game.lives, game.won)
        for i in range(3):
            draw_star(screen, 30 + i * 26, BOARD_SIZE + 20, 10, i < stars)

        status_text = f"Level {level_cfg['id']}: {level_cfg['name']}   |   FPS: {fps}"
        screen.blit(fonts["h3"].render(status_text, True, TEXT_WHITE), (120, BOARD_SIZE + 12))

        # 4. Render Sidebar Dashboard (Right)
        sb_x = BOARD_SIZE
        pygame.draw.rect(screen, SIDEBAR_BG, (sb_x, 0, SIDEBAR_W, TOTAL_H))
        pygame.draw.line(screen, CARD_BORDER, (sb_x, 0), (sb_x, TOTAL_H), 1)

        # Card 1: Header & Policy Selector
        draw_hud_card(screen, (sb_x + 15, 15, SIDEBAR_W - 30, 95), "ACTIVE POLICY & LEVEL", fonts)
        p_color = ACCENT_GREEN if policy_mode == "Smart PPO" else (ACCENT_YELLOW if policy_mode == "Raw PPO" else ACCENT_BLUE)
        screen.blit(fonts["large"].render(policy_mode, True, p_color), (sb_x + 28, 38))
        screen.blit(fonts["body"].render(f"Press [P] to cycle policy  |  [1-3] level", True, TEXT_MUTED), (sb_x + 28, 76))

        # Card 2: Live Performance Metrics
        draw_hud_card(screen, (sb_x + 15, 120, SIDEBAR_W - 30, 135), "GAMEPLAY TELEMETRY", fonts)
        metrics = [
            ("Score", f"{game.score:,}", ACCENT_YELLOW),
            ("Pellets Left", f"{game.pellets_left} / {game.pellets_total}", TEXT_WHITE),
            ("Lives", "<3 " * game.lives if game.lives > 0 else "0 (GAME OVER)", ACCENT_RED if game.lives <= 1 else ACCENT_GREEN),
            ("Step / Max", f"{game.steps} / 600", TEXT_MUTED),
        ]
        for idx, (label, val, col) in enumerate(metrics):
            gx = sb_x + 28 + (idx % 2) * 165
            gy = 145 + (idx // 2) * 48
            screen.blit(fonts["mono"].render(label.upper(), True, TEXT_MUTED), (gx, gy))
            screen.blit(fonts["h2"].render(val, True, col), (gx, gy + 16))

        # Card 3: Neural Network Confidence & Action Probabilities
        draw_hud_card(screen, (sb_x + 15, 265, SIDEBAR_W - 30, 160), "CNN POLICY HEAD (LIVE LOGITS)", fonts)
        probs = smart_ppo.last_probs
        legal_moves = game.legal_moves(game.pacman)
        best_a = int(np.argmax(probs))

        for a_idx, act_key in enumerate([UP, DOWN, LEFT, RIGHT]):
            bar_y = 295 + a_idx * 28
            name = ACTION_NAMES[act_key]
            prob = probs[act_key]
            is_legal = act_key in legal_moves

            # Action label
            lbl_color = TEXT_WHITE if is_legal else (100, 110, 135)
            screen.blit(fonts["mono"].render(f"{name:5s}", True, lbl_color), (sb_x + 28, bar_y))

            # Progress bar background
            bar_w = 190
            pygame.draw.rect(screen, (30, 38, 65), (sb_x + 85, bar_y + 3, bar_w, 14), border_radius=4)
            # Active fill
            fill_w = int(bar_w * prob)
            bar_color = ACCENT_GREEN if act_key == best_a and is_legal else (ACCENT_BLUE if is_legal else (160, 60, 60))
            if fill_w > 0:
                pygame.draw.rect(screen, bar_color, (sb_x + 85, bar_y + 3, fill_w, 14), border_radius=4)

            # Percentage text
            screen.blit(fonts["mono"].render(f"{prob * 100:4.1f}%", True, TEXT_MUTED), (sb_x + 285, bar_y))

        # Card 4: Algorithmic Ablation Toggles (Live Knobs)
        draw_hud_card(screen, (sb_x + 15, 435, SIDEBAR_W - 30, 105), "ABLATION CONTROLS (LIVE TOGGLE)", fonts)
        toggles = [
            ("[M] Action Masking", smart_ppo.action_masking),
            ("[A] Anti-Stall Loop Breaker", smart_ppo.anti_stall),
            ("[E] Multi-Ghost Evasion", smart_ppo.evasion_vector),
        ]
        for t_idx, (t_name, is_on) in enumerate(toggles):
            ty = 460 + t_idx * 24
            badge_color = ACCENT_GREEN if is_on else (90, 100, 120)
            badge_text = "ON" if is_on else "OFF"
            screen.blit(fonts["mono"].render(t_name, True, TEXT_WHITE), (sb_x + 28, ty))
            pygame.draw.rect(screen, badge_color, (sb_x + 285, ty, 42, 16), border_radius=4)
            screen.blit(fonts["mono"].render(badge_text, True, BG_COLOR if is_on else TEXT_WHITE), (sb_x + 295, ty + 1))

        # Card 5: AI Status & Subsystem Mode
        draw_hud_card(screen, (sb_x + 15, 550, SIDEBAR_W - 30, 75), "INTERNAL DECISION STATE", fonts)
        screen.blit(fonts["mono"].render(f"Subsystem: {smart_ppo.active_mode}", True, ACCENT_YELLOW), (sb_x + 28, 574))
        mode_note = "Press [SPACE] pause  |  [N] step  |  [R] reset"
        screen.blit(fonts["mono"].render(mode_note, True, TEXT_MUTED), (sb_x + 28, 595))

        # Overlay if Game Done
        if game.done:
            overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            res_text = "MAZE CLEARED!" if game.won else "GAME OVER"
            res_color = ACCENT_YELLOW if game.won else ACCENT_RED
            t_surf = fonts["large"].render(res_text, True, res_color)
            screen.blit(t_surf, t_surf.get_rect(center=(BOARD_SIZE // 2, BOARD_SIZE // 2 - 40)))

            final_stars = calc_stars(level_cfg, game.score, game.lives, game.won)
            for i in range(3):
                draw_star(screen, BOARD_SIZE // 2 + (i - 1) * 36, BOARD_SIZE // 2 + 10, 15, i < final_stars)

            sub_text = fonts["h3"].render(f"Final Score: {game.score:,}  |  Press [R] to replay", True, TEXT_WHITE)
            screen.blit(sub_text, sub_text.get_rect(center=(BOARD_SIZE // 2, BOARD_SIZE // 2 + 55)))

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


if __name__ == "__main__":
    run_prototype()
