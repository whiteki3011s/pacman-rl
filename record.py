"""Record a side-by-side GIF: 'before' agent vs 'after' agent on the same maze and seed.

  python record.py --level 1 --model checkpoints/ppo_100.zip
  python record.py --level 1                 # no model: random vs BFS bot
Pure Pillow (no pygame needed), so it also works on servers / Colab.
"""
import argparse

from PIL import Image, ImageDraw

from bots import BFSBot, PPOPolicy, RandomPolicy
from engine import PacmanGame
from levels import get_level

GHOST_COLORS = {"Blinky": (255, 0, 0), "Pinky": (255, 184, 255),
                "Inky": (0, 255, 255), "Clyde": (255, 184, 82)}


def draw_frame(game, label, tile=22):
    h, w = game.grid.shape
    img = Image.new("RGB", (w * tile, h * tile + 30), (8, 8, 20))
    d = ImageDraw.Draw(img)
    for r in range(h):
        for c in range(w):
            x, y = c * tile, r * tile
            ch = game.grid[r, c]
            if ch == "#":
                d.rectangle([x + 1, y + 1, x + tile - 2, y + tile - 2], fill=(33, 33, 200))
            elif ch == ".":
                d.ellipse([x + tile // 2 - 2, y + tile // 2 - 2, x + tile // 2 + 2, y + tile // 2 + 2],
                          fill=(255, 200, 180))
            elif ch == "o":
                d.ellipse([x + 5, y + 5, x + tile - 5, y + tile - 5], fill=(255, 255, 255))
    for g in game.ghosts:
        x, y = g.pos[1] * tile, g.pos[0] * tile
        if g.mode == "frightened":
            color = (255, 255, 255) if (game.frightened_timer < 8 and game.steps % 2) else (40, 40, 255)
        else:
            color = GHOST_COLORS[g.name]
        d.ellipse([x + 2, y + 2, x + tile - 2, y + tile - 2], fill=color)
        d.rectangle([x + 2, y + tile // 2, x + tile - 2, y + tile - 3], fill=color)
    pr, pc = game.pacman
    x, y = pc * tile, pr * tile
    d.ellipse([x + 2, y + 2, x + tile - 2, y + tile - 2], fill=(255, 220, 0))
    status = ""
    if game.done:
        status = "  CLEARED!" if game.won else "  GAME OVER"
    d.text((6, h * tile + 8), f"{label} | score {game.score} | lives {game.lives}{status}", fill=(255, 255, 255))
    return img


def record_game(policy, cfg, seed, label, every=2, max_frames=400):
    game = PacmanGame(cfg, seed=seed)
    frames = [draw_frame(game, label)]
    while not game.done and len(frames) < max_frames * every:
        game.step(policy.act(game))
        if game.steps % every == 0 or game.done:
            frames.append(draw_frame(game, label))
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--model", default=None, help="path to a PPO .zip; default: BFS bot")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="results/comparison.gif")
    ap.add_argument("--every", type=int, default=2, help="record every N game steps")
    args = ap.parse_args()
    cfg = get_level(args.level)

    left = record_game(RandomPolicy(args.seed), cfg, args.seed, "BEFORE: random", args.every)
    if args.model:
        right = record_game(PPOPolicy(args.model), cfg, args.seed, "AFTER: trained PPO", args.every)
    else:
        right = record_game(BFSBot(), cfg, args.seed, "BFS bot", args.every)
    n = max(len(left), len(right))
    left += [left[-1]] * (n - len(left))
    right += [right[-1]] * (n - len(right))
    frames = []
    for a, b in zip(left, right):
        canvas = Image.new("RGB", (a.width + b.width + 10, a.height), (0, 0, 0))
        canvas.paste(a, (0, 0))
        canvas.paste(b, (a.width + 10, 0))
        frames.append(canvas)
    frames += [frames[-1]] * 15   # hold the final frame
    frames[0].save(args.out, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    print(f"Saved {args.out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
