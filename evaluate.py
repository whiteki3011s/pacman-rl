"""Compare agents on every level: random (before) vs PPO checkpoints (after) vs BFS bot.

  python evaluate.py --episodes 50
Outputs (in results/): results.csv + PNG charts.
"""
import argparse
import csv
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from bots import BFSBot, PPOPolicy, RandomPolicy
from engine import PacmanGame
from levels import calc_stars, load_levels


def run_episode(policy, cfg, seed):
    game = PacmanGame(cfg, seed=seed)
    while not game.done:
        game.step(policy.act(game))
    return {"won": int(game.won), "score": game.score, "lives": game.lives, "steps": game.steps,
            "pellets": game.pellets_total - game.pellets_left,
            "stars": calc_stars(cfg, game.score, game.lives, game.won)}


def evaluate_policy(make_policy, cfg, episodes):
    runs = [run_episode(make_policy(ep), cfg, seed=10_000 + ep) for ep in range(episodes)]
    return {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}


def smooth(y, w):
    y = np.asarray(y, dtype=float)
    if len(y) < w:
        return y
    return np.convolve(y, np.ones(w) / w, mode="valid")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--levels", type=int, nargs="*", default=None)
    ap.add_argument("--ckpt-dir", default="checkpoints")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    os.makedirs(args.results_dir, exist_ok=True)

    levels = [c for c in load_levels() if not args.levels or c["id"] in args.levels]
    policies = {"random": lambda ep: RandomPolicy(seed=ep)}
    ckpts = sorted(glob.glob(os.path.join(args.ckpt_dir, "ppo_*.zip")))
    for path in ckpts:
        try:
            ppo = PPOPolicy(path)
            policies[ppo.name] = (lambda p: (lambda ep: p))(ppo)
        except ImportError:
            print("stable-baselines3 not installed: skipping PPO checkpoints")
            break
    policies["bfs_bot"] = lambda ep: BFSBot()

    rows = []
    for cfg in levels:
        for name, make in policies.items():
            s = evaluate_policy(make, cfg, args.episodes)
            rows.append({"policy": name, "level": cfg["id"], "episodes": args.episodes,
                         "win_rate": s["won"], "avg_score": s["score"], "avg_steps": s["steps"],
                         "avg_pellets": s["pellets"], "avg_lives": s["lives"], "avg_stars": s["stars"]})
            print(f"L{cfg['id']} {name:8s} win={s['won']:.2f} score={s['score']:.0f} "
                  f"pellets={s['pellets']:.0f} stars={s['stars']:.2f}")
    with open(os.path.join(args.results_dir, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def val(policy, level, key):
        return next((r[key] for r in rows if r["policy"] == policy and r["level"] == level), None)

    lv_ids = [c["id"] for c in levels]
    ppo_names = sorted(n for n in policies if n.startswith("ppo_"))
    final = ppo_names[-1] if ppo_names else None

    # ---- Chart 1: before vs after (win rate, score, stars) -------------------------
    series = [("random", "Before: random agent", "#9a9a9a")]
    if final:
        series.append((final, "After: trained PPO", "#f5c518"))
    series.append(("bfs_bot", "Hand-written BFS bot", "#3b6fd8"))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, key, title in zip(axes, ["win_rate", "avg_score", "avg_stars"],
                              ["Win rate", "Average score", "Average stars (0-3)"]):
        width = 0.8 / len(series)
        for i, (pol, label, color) in enumerate(series):
            ax.bar(np.arange(len(lv_ids)) + i * width, [val(pol, l, key) for l in lv_ids],
                   width, label=label, color=color)
        ax.set_xticks(np.arange(len(lv_ids)) + width * (len(series) - 1) / 2)
        ax.set_xticklabels([f"L{l}" for l in lv_ids])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=len(series))
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(args.results_dir, "before_after.png"), dpi=150)
    plt.close(fig)

    # ---- Chart 2: progress across checkpoints ---------------------------------------
    if ppo_names:
        pcts = [int(n.split("_")[1]) for n in ppo_names]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        for l in lv_ids:
            axes[0].plot(pcts, [val(n, l, "win_rate") for n in ppo_names], marker="o", label=f"Level {l}")
            axes[1].plot(pcts, [val(n, l, "avg_score") for n in ppo_names], marker="o", label=f"Level {l}")
        axes[0].set_title("Win rate vs training progress")
        axes[1].set_title("Average score vs training progress")
        for ax in axes:
            ax.set_xlabel("% of training completed")
            ax.grid(alpha=0.3)
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(os.path.join(args.results_dir, "checkpoint_progress.png"), dpi=150)
        plt.close(fig)

    # ---- Chart 3: learning curve from training log ----------------------------------
    log_path = os.path.join(args.results_dir, "train_log.csv")
    if os.path.exists(log_path):
        with open(log_path) as f:
            log = list(csv.DictReader(f))
        if log:
            t = np.array([float(r["timesteps"]) for r in log])
            rew = np.array([float(r["reward"]) for r in log])
            win = np.array([float(r["won"]) for r in log])
            w = max(5, min(50, len(log) // 5))
            fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
            axes[0].plot(t[w - 1:], smooth(rew, w), color="#3b6fd8")
            axes[0].set_title(f"Learning curve: episode reward (moving avg {w})")
            axes[1].plot(t[w - 1:], smooth(win, w), color="#f5c518")
            axes[1].set_title(f"Training win rate (moving avg {w})")
            lv = [r["level"] for r in log]
            for i in range(1, len(lv)):
                if lv[i] != lv[i - 1]:
                    for ax in axes:
                        ax.axvline(t[i], color="red", ls="--", alpha=0.4)
            for ax in axes:
                ax.set_xlabel("Timesteps")
                ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(os.path.join(args.results_dir, "learning_curve.png"), dpi=150)
            plt.close(fig)
    print(f"Saved results.csv and charts to {args.results_dir}/")


if __name__ == "__main__":
    main()
