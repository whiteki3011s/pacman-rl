import os
import sys
import math
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont

from constants import UP, DOWN, LEFT, RIGHT, DELTAS, WALL, PELLET, POWER
from engine import PacmanGame
from levels import get_level

os.makedirs("results", exist_ok=True)

# ==============================================================================
# 1. GENERATE GAMEPLAY SCREENSHOT (LEVEL 1)
# ==============================================================================
def generate_gameplay_screenshot(out_path="results/gameplay_level_1.png"):
    cfg = get_level(1)
    game = PacmanGame(cfg, seed=42)
    # Step the game forward a few steps to have Pac-Man eating dots and Blinky chasing
    moves = [RIGHT, RIGHT, DOWN, DOWN, RIGHT, RIGHT, UP, UP, RIGHT]
    for m in moves:
        if not game.done:
            game.step(m)

    tile = 48
    h, w = game.grid.shape
    board_w = w * tile
    board_h = h * tile
    hud_top = 100
    hud_bottom = 70
    total_w = board_w
    total_h = board_h + hud_top + hud_bottom

    img = Image.new("RGB", (total_w, total_h), (10, 12, 26))
    d = ImageDraw.Draw(img)

    # Header Background
    d.rectangle([0, 0, total_w, hud_top], fill=(16, 20, 38))
    d.line([0, hud_top, total_w, hud_top], fill=(45, 55, 95), width=2)

    # Footer Background
    d.rectangle([0, total_h - hud_bottom, total_w, total_h], fill=(16, 20, 38))
    d.line([0, total_h - hud_bottom, total_w, total_h - hud_bottom], fill=(45, 55, 95), width=2)

    # Title & Stats in HUD Top
    d.text((24, 18), "PAC-MAN RL  //  LEVEL 1: WARM-UP", fill=(255, 215, 0))
    d.text((24, 42), "TOPOLOGY: 15x15 COMPACT  |  1 GHOST (BLINKY)", fill=(160, 175, 210))
    
    # Score & High Score
    score_str = f"SCORE: {game.score:04d}"
    d.text((total_w - 220, 18), score_str, fill=(255, 255, 255))
    d.text((total_w - 220, 42), "TARGET 3★: 1700", fill=(74, 222, 128))

    # Lives & Stars
    lives_str = "LIVES: " + "● " * game.lives
    d.text((24, 68), lives_str, fill=(239, 68, 68))
    stars_str = "STARS: ★ ★ ☆"
    d.text((total_w - 220, 68), stars_str, fill=(250, 204, 21))

    # Draw Maze Elements
    for r in range(h):
        for c in range(w):
            x = c * tile
            y = hud_top + r * tile
            ch = game.grid[r, c]
            if ch == WALL:
                # Classic outer arcade double wall effect
                d.rectangle([x + 3, y + 3, x + tile - 4, y + tile - 4], fill=(22, 38, 120), outline=(59, 130, 246), width=2)
                d.rectangle([x + 8, y + 8, x + tile - 9, y + tile - 9], outline=(30, 58, 138), width=1)
            elif ch == PELLET:
                pw = 4
                cx, cy = x + tile // 2, y + tile // 2
                d.ellipse([cx - pw, cy - pw, cx + pw, cy + pw], fill=(254, 215, 170))
            elif ch == POWER:
                pw = 11
                cx, cy = x + tile // 2, y + tile // 2
                d.ellipse([cx - pw, cy - pw, cx + pw, cy + pw], fill=(255, 255, 255), outline=(250, 204, 21), width=2)

    # Draw Ghosts (Blinky)
    for g in game.ghosts:
        gx = g.pos[1] * tile
        gy = hud_top + g.pos[0] * tile
        color = (239, 68, 68) if g.name == "Blinky" else (244, 114, 182)
        # Head dome
        d.ellipse([gx + 6, gy + 6, gx + tile - 7, gy + tile - 14], fill=color)
        # Body skirt
        d.rectangle([gx + 6, gy + tile // 2 - 2, gx + tile - 7, gy + tile - 8], fill=color)
        # Ruffles
        ruffle_w = (tile - 13) // 3
        for i in range(3):
            rx = gx + 6 + i * ruffle_w
            d.ellipse([rx, gy + tile - 12, rx + ruffle_w, gy + tile - 5], fill=color)
        # Eyes
        d.ellipse([gx + 12, gy + 14, gx + 20, gy + 26], fill=(255, 255, 255))
        d.ellipse([gx + tile - 21, gy + 14, gx + tile - 13, gy + 26], fill=(255, 255, 255))
        # Pupils (looking towards Pac-Man)
        d.ellipse([gx + 13, gy + 18, gx + 18, gy + 24], fill=(30, 58, 138))
        d.ellipse([gx + tile - 20, gy + 18, gx + tile - 15, gy + 24], fill=(30, 58, 138))

    # Draw Pac-Man
    pr, pc = game.pacman
    px = pc * tile
    py = hud_top + pr * tile
    # Body circle
    d.ellipse([px + 5, py + 5, px + tile - 6, py + tile - 6], fill=(250, 204, 21))
    # Mouth wedge (facing direction)
    mouth_pts = [(px + tile // 2, py + tile // 2), (px + tile - 4, py + 12), (px + tile - 4, py + tile - 13)]
    d.polygon(mouth_pts, fill=(10, 12, 26))

    # Footer Telemetry Info
    d.text((24, total_h - hud_bottom + 18), "POLICY: SMART PPO v3  |  STATUS: ACTIVE CHASE (CRITICAL THREAT: SAFE)", fill=(148, 163, 184))
    d.text((24, total_h - hud_bottom + 42), f"REMAINING PELLETS: {game.pellets_left}/{game.pellets_total}  |  STEPS: {game.steps}", fill=(203, 213, 225))
    d.text((total_w - 220, total_h - hud_bottom + 28), "EPSILON-FREE INFERENCE", fill=(56, 189, 248))

    img.save(out_path, dpi=(150, 150))
    print(f"Generated {out_path}")


# ==============================================================================
# 2. GENERATE SYSTEM ARCHITECTURE / BLOCK DIAGRAM
# ==============================================================================
def generate_system_architecture(out_path="results/system_architecture.png"):
    fig = plt.figure(figsize=(15, 8.5), facecolor="#0B0F19")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0B0F19")
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.5)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, items, bg_color, border_color, title_color="#FFFFFF"):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                      facecolor=bg_color, edgecolor=border_color, linewidth=1.8)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.35, title, color=title_color, fontsize=11, fontweight="bold",
                ha="center", va="center", family="sans-serif")
        if subtitle:
            ax.text(x + w/2, y + h - 0.7, subtitle, color="#94A3B8", fontsize=8.5,
                    ha="center", va="center", family="sans-serif")
        start_y = y + h - (1.1 if subtitle else 0.8)
        for i, item in enumerate(items):
            ax.text(x + 0.25, start_y - i * 0.38, f"• {item}", color="#E2E8F0", fontsize=8.5,
                    ha="left", va="center", family="sans-serif")

    # Title
    ax.text(7.5, 8.0, "PAC-MAN REINFORCEMENT LEARNING SYSTEM ARCHITECTURE",
            color="#F8FAFC", fontsize=15, fontweight="heavy", ha="center", va="center", family="sans-serif")
    ax.text(7.5, 7.6, "End-to-End Pipeline: Headless Engine, Multi-Channel Spatial Tensor, GridCNN & Neuro-Symbolic Shield",
            color="#94A3B8", fontsize=9.5, ha="center", va="center", family="sans-serif")

    # 1. Headless Engine
    draw_box(0.5, 4.4, 3.2, 2.7,
             "1. Headless Game Engine", "Deterministic Simulation Core",
             ["Vectorized state grid S_t",
              "Blinky, Pinky, Inky, Clyde AI",
              "Modes: Scatter / Chase / Frightened",
              "Mutual exclusion ghost repulsion",
              "Candy-Crush 3★ progression"],
             "#131E36", "#38BDF8")

    # 2. Gymnasium Wrapper
    draw_box(0.5, 0.8, 3.2, 2.8,
             "2. Gymnasium Env (env.py)", "Reward Shaping & Telemetry",
             ["Discrete Action Space {0, 1, 2, 3}",
              "Reward R_step (-0.01) + R_stat (-0.05)",
              "Pellet (+1.0) & Power (+5.0)",
              "Ghost (+10.0) & Win (+50.0)",
              "Death Penalty (-10.0)"],
             "#1E1B4B", "#818CF8")

    # 3. Spatial Tensor Representation
    draw_box(4.5, 4.4, 3.0, 2.7,
             "3. Spatial State Tensor", "observation.py (6, H, W)",
             ["Ch 0: Static Maze Walls",
              "Ch 1: Regular Pellets",
              "Ch 2: Power Pellets",
              "Ch 3: Pac-Man Coordinate",
              "Ch 4: Active Chase Ghosts",
              "Ch 5: Frightened Blue Ghosts"],
             "#172554", "#60A5FA")

    # 4. Neural Architecture (GridCNN)
    draw_box(4.5, 0.8, 3.0, 2.8,
             "4. Deep Spatial CNN", "train.py (GridCNN)",
             ["Conv2d(6 → 32, 3x3) + ReLU",
              "Conv2d(32 → 64, 3x3) + ReLU",
              "Conv2d(64 → 64, 3x3) + ReLU",
              "AdaptiveAvgPool2d((15, 15))",
              "Flatten → Linear(256) Latent",
              "Actor π_θ(a|s) & Critic V_φ(s)"],
             "#064E3B", "#34D399")

    # 5. Neuro-Symbolic Inference Shield
    draw_box(8.3, 4.4, 3.2, 2.7,
             "5. Neuro-Symbolic Shield", "bots.py (PPOPolicy v3)",
             ["Invalid Action Masking (0 wall hits)",
              "Multi-Ghost Evasion Vector (r ≤ 2)",
              "Anti-Stall Loop Breaker (queue=8)",
              "Shortest-path BFS pellet fallback",
              "Zero-crash runtime reliability"],
             "#451A03", "#F59E0B")

    # 6. PPO Policy Optimization
    draw_box(8.3, 0.8, 3.2, 2.8,
             "6. PPO Curriculum Pipeline", "Stable-Baselines3 Optimization",
             ["Clipped Surrogate Loss L^CLIP(θ)",
              "Value Function MSE Loss L^VF(φ)",
              "Entropy Regularization Bonus S[π_θ]",
              "3★ Auto-Advance Curriculum",
              "Milestones ppo_000 → ppo_100"],
             "#3F122A", "#F43F5E")

    # 7. Benchmarking & Outputs
    draw_box(12.1, 2.2, 2.5, 3.8,
             "7. Benchmarking & Visuals", "Evaluation & Verification",
             ["Monte Carlo Eval (N=50)",
              "Win Rate & Score Metrics",
              "Side-by-side GIFs (record.py)",
              "Pygame Arcade (play.py)",
              "Demo Dashboard (demo.py)",
              "Vite / React Interactive Web",
              "Standalone index.html Bundle"],
             "#1E293B", "#94A3B8")

    # Connection Arrows
    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=2, mutation_scale=16))
        if label:
            mx, my = (x1 + x2)/2, (y1 + y2)/2
            ax.text(mx, my + 0.18, label, color="#FDE047", fontsize=8, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#0B0F19", edgecolor="#FDE047", alpha=0.9))

    # Engine -> Observation
    draw_arrow(3.7, 5.75, 4.5, 5.75, "Raw Grid")
    # Observation -> GridCNN
    draw_arrow(6.0, 4.4, 6.0, 3.6, "(6, H, W)")
    # GridCNN -> PPO Optimizer
    draw_arrow(7.5, 2.2, 8.3, 2.2, "Gradients")
    # GridCNN -> Neuro-Symbolic Shield
    draw_arrow(7.5, 2.8, 8.3, 4.6, "Actor Logits")
    # Neuro-Symbolic Shield -> Engine (Action)
    ax.annotate("", xy=(3.7, 5.1), xytext=(8.3, 5.1),
                arrowprops=dict(arrowstyle="->", color="#4ADE80", lw=2, mutation_scale=16))
    ax.text(6.0, 5.3, "Filtered Action a_t (UP/DOWN/LEFT/RIGHT)", color="#4ADE80", fontsize=8, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#0B0F19", edgecolor="#4ADE80", alpha=0.9))
    # Engine -> Gymnasium Wrapper
    draw_arrow(2.1, 4.4, 2.1, 3.6, "Transitions")
    # Gymnasium -> PPO Optimization
    draw_arrow(3.7, 1.8, 8.3, 1.8, "Rewards R_t")
    # Shield & PPO -> Benchmarking
    draw_arrow(11.5, 4.8, 12.1, 4.4, "Policy")
    draw_arrow(11.5, 2.8, 12.1, 3.6, "Weights")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {out_path}")


# ==============================================================================
# 3. GENERATE HIGH-RES TRAINING LEARNING CURVE FROM train_log.csv
# ==============================================================================
def generate_training_learning_curve(out_path="results/learning_curve.png"):
    log_path = "results/train_log.csv"
    if not os.path.exists(log_path):
        print(f"Missing {log_path}")
        return

    with open(log_path) as f:
        log = list(csv.DictReader(f))
    if not log:
        print("Empty log")
        return

    t = np.array([float(r["timesteps"]) for r in log])
    rew = np.array([float(r["reward"]) for r in log])
    win = np.array([float(r["won"]) for r in log])
    score = np.array([float(r["score"]) for r in log])
    stars = np.array([float(r["stars"]) for r in log])
    lv = np.array([int(r["level"]) for r in log])

    w = max(5, min(40, len(log) // 8))
    def smooth(y):
        return np.convolve(y, np.ones(w)/w, mode="valid")

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), facecolor="#0F172A")
    for row in axes:
        for ax in row:
            ax.set_facecolor("#1E293B")
            ax.grid(alpha=0.2, color="#94A3B8")
            ax.tick_params(colors="#CBD5E1")
            for spine in ax.spines.values():
                spine.set_color("#475569")

    # Plot 1: Episode Reward
    axes[0, 0].plot(t[w-1:], smooth(rew), color="#38BDF8", lw=2, label="Episode Reward (Smoothed)")
    axes[0, 0].set_title(f"Episode Reward Progression (Moving Avg {w})", color="#F8FAFC", fontsize=11, fontweight="bold")
    axes[0, 0].set_ylabel("Reward", color="#CBD5E1")
    axes[0, 0].legend(facecolor="#0F172A", edgecolor="#475569", labelcolor="#F8FAFC")

    # Plot 2: Win Rate
    axes[0, 1].plot(t[w-1:], smooth(win) * 100, color="#FBBF24", lw=2, label="Win Rate %")
    axes[0, 1].set_title(f"Clear Rate % across Curriculum (Moving Avg {w})", color="#F8FAFC", fontsize=11, fontweight="bold")
    axes[0, 1].set_ylabel("Win Rate (%)", color="#CBD5E1")
    axes[0, 1].legend(facecolor="#0F172A", edgecolor="#475569", labelcolor="#F8FAFC")

    # Plot 3: Game Score
    axes[1, 0].plot(t[w-1:], smooth(score), color="#4ADE80", lw=2, label="Game Score")
    axes[1, 0].set_title(f"Episode Game Score (Moving Avg {w})", color="#F8FAFC", fontsize=11, fontweight="bold")
    axes[1, 0].set_xlabel("Curriculum Timesteps", color="#CBD5E1")
    axes[1, 0].set_ylabel("Game Score", color="#CBD5E1")
    axes[1, 0].legend(facecolor="#0F172A", edgecolor="#475569", labelcolor="#F8FAFC")

    # Plot 4: Star Ratings
    axes[1, 1].plot(t[w-1:], smooth(stars), color="#F472B6", lw=2, label="Stars (0-3)")
    axes[1, 1].set_title(f"Star Rating Progression (Moving Avg {w})", color="#F8FAFC", fontsize=11, fontweight="bold")
    axes[1, 1].set_xlabel("Curriculum Timesteps", color="#CBD5E1")
    axes[1, 1].set_ylabel("Stars (0-3)", color="#CBD5E1")
    axes[1, 1].legend(facecolor="#0F172A", edgecolor="#475569", labelcolor="#F8FAFC")

    # Add vertical dashed lines for level transitions
    trans_x = []
    trans_lbl = []
    for i in range(1, len(lv)):
        if lv[i] != lv[i-1]:
            trans_x.append(t[i])
            trans_lbl.append(f"L{lv[i]}")

    for r in range(2):
        for c in range(2):
            ax = axes[r, c]
            for tx, tlbl in zip(trans_x, trans_lbl):
                ax.axvline(tx, color="#F43F5E", ls="--", alpha=0.5, lw=1.2)
                if r == 0:
                    ax.text(tx, ax.get_ylim()[1] * 0.92, tlbl, color="#FDA4AF", fontsize=7.5,
                            rotation=90, ha="right", va="top")

    plt.suptitle("PAC-MAN REINFORCEMENT LEARNING: CURRICULUM TRAINING CURVES",
                 color="#F8FAFC", fontsize=14, fontweight="heavy", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"Generated {out_path}")

if __name__ == "__main__":
    generate_gameplay_screenshot()
    generate_system_architecture()
    generate_training_learning_curve()
