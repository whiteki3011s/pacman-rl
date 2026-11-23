"""Train a PPO agent on the Pac-Man environment.

Examples
  python train.py --level 1 --timesteps 300000
  python train.py --curriculum --timesteps 1000000     # levels 1..5 in order
Outputs
  checkpoints/ppo_000.zip, ppo_025.zip, ... ppo_100.zip   (0% = untrained)
  results/train_log.csv                                    (one row per episode)
"""
import argparse
import csv
import os

import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from env import PacmanEnv
from levels import load_levels

CHECKPOINT_PCTS = [25, 50, 75, 100]


class GridCNN(BaseFeaturesExtractor):
    """Small CNN for multi-channel grids (handles 15x15 up to 31x28 arcade standard)."""

    def __init__(self, observation_space, features_dim=256):
        super().__init__(observation_space, features_dim)
        channels = observation_space.shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(channels, 32, 3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((15, 15)),
            nn.Flatten())
        self.linear = nn.Sequential(nn.Linear(64 * 15 * 15, features_dim), nn.ReLU())

    def forward(self, obs):
        return self.linear(self.cnn(obs))


class TrainingCallback(BaseCallback):
    """Saves checkpoints at fixed % of training, logs every finished episode,
    and automatically introduces new mazes when 3 stars are achieved."""

    def __init__(self, total_timesteps, ckpt_dir, log_path, auto_advance=False,
                 start_level=1, max_level=5, min_3stars=1, eval_interval=25_000, resume=False):
        super().__init__()
        self.total = total_timesteps
        self.ckpt_dir = ckpt_dir
        self.auto_advance = auto_advance
        self.current_level = start_level
        self.max_level = max_level
        self.min_3stars = min_3stars
        self.three_star_count = 0
        self.eval_interval = eval_interval
        self.last_eval = 0
        self.pending = list(CHECKPOINT_PCTS)
        file_mode = "a" if resume and os.path.exists(log_path) else "w"
        self.log_file = open(log_path, file_mode, newline="")
        self.log = csv.writer(self.log_file)
        if file_mode == "w":
            self.log.writerow(["timesteps", "reward", "length", "level", "score", "won", "stars"])

    def _evaluate_smart(self, num_episodes=5):
        import numpy as np
        from bots import PPOPolicy
        from engine import PacmanGame
        from levels import get_level, calc_stars
        cfg = get_level(self.current_level)
        policy = PPOPolicy(self.model, masked=True, anti_stall=True)
        scores, stars_list, wins = [], [], []
        for ep in range(num_episodes):
            game = PacmanGame(cfg, seed=20000 + ep)
            while not game.done:
                game.step(policy.act(game))
            st = calc_stars(cfg, game.score, game.lives, game.won)
            scores.append(game.score)
            stars_list.append(st)
            wins.append(int(game.won))
        return float(np.mean(scores)), float(np.mean(wins)), int(max(stars_list)), float(np.mean(stars_list))

    def _on_step(self):
        # Periodic smart evaluation to detect 3-star mastery
        if self.auto_advance and (self.num_timesteps - self.last_eval >= self.eval_interval):
            self.last_eval = self.num_timesteps
            avg_s, win_r, max_st, avg_st = self._evaluate_smart(num_episodes=5)
            print(f"[{self.num_timesteps} steps] L{self.current_level} Smart Eval: win_rate={win_r:.2f}, avg_score={avg_s:.0f}, max_stars={max_st}")
            if max_st >= 3:
                next_level = self.current_level + 1
                ckpt_name = os.path.join(self.ckpt_dir, f"level_{self.current_level}_3stars")
                self.model.save(ckpt_name)
                print(f"\n{'='*70}")
                print(f"★★★ 3 STARS ACHIEVED ON LEVEL {self.current_level}! (Eval Score: {avg_s:.0f}, Max Stars: {max_st}) ★★★")
                print(f"Saved milestone checkpoint: {ckpt_name}.zip")
                if next_level <= self.max_level:
                    print(f"Introducing NEW MAZE: Level {next_level}!")
                    print(f"{'='*70}\n")
                    self.current_level = next_level
                    self.three_star_count = 0
                    self.training_env.env_method("set_level", next_level)
                else:
                    print(f"All levels up to Level {self.max_level} mastered with 3 Stars!")
                    print(f"{'='*70}\n")
        for info in self.locals.get("infos", []):
            if "episode" in info:
                stars = info.get("stars", 0)
                level = info.get("level", self.current_level)
                score = info.get("score", 0)
                won = int(bool(info.get("won")))
                self.log.writerow([self.num_timesteps, round(info["episode"]["r"], 3),
                                   info["episode"]["l"], level, score, won, stars])
                self.log_file.flush()

                # Automatically introduce new maze as soon as 3 stars are achieved!
                if self.auto_advance and stars >= 3 and level == self.current_level:
                    self.three_star_count += 1
                    if self.three_star_count >= self.min_3stars:
                        next_level = self.current_level + 1
                        ckpt_name = os.path.join(self.ckpt_dir, f"level_{self.current_level}_3stars")
                        self.model.save(ckpt_name)
                        print(f"\n{'='*70}")
                        print(f"★★★ 3 STARS ACHIEVED ON LEVEL {self.current_level}! (Score: {score}) ★★★")
                        print(f"Saved milestone checkpoint: {ckpt_name}.zip")
                        if next_level <= self.max_level:
                            print(f"Introducing NEW MAZE: Level {next_level}!")
                            print(f"{'='*70}\n")
                            self.current_level = next_level
                            self.three_star_count = 0
                            self.training_env.env_method("set_level", next_level)
                        else:
                            print(f"All levels up to Level {self.max_level} mastered with 3 Stars!")
                            print(f"{'='*70}\n")

        while self.pending and self.num_timesteps >= self.total * self.pending[0] / 100:
            pct = self.pending.pop(0)
            self.model.save(os.path.join(self.ckpt_dir, f"ppo_{pct:03d}"))
            print(f"[checkpoint] saved ppo_{pct:03d} at {self.num_timesteps} steps")
        return True

    def _on_training_end(self):
        if not self.log_file.closed:
            self.log_file.flush()

    def close(self):
        if hasattr(self, "log_file") and not self.log_file.closed:
            self.log_file.close()

    def __del__(self):
        self.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-level", type=int, default=None, help="curriculum start level")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--curriculum", action="store_true", help="train on levels 1..N in order")
    ap.add_argument("--auto-advance", action="store_true", help="introduce new mazes dynamically as soon as 3 stars are achieved")
    ap.add_argument("--resume", default=None, help="path to existing PPO checkpoint to resume training from")
    ap.add_argument("--max-level", type=int, default=10)
    ap.add_argument("--timesteps", type=int, default=300_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ckpt-dir", default="checkpoints")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()

    os.makedirs(args.ckpt_dir, exist_ok=True)
    os.makedirs(args.results_dir, exist_ok=True)

    tb_dir = None
    try:
        import tensorboard  # noqa: F401
        tb_dir = os.path.join(args.results_dir, "tensorboard")
    except ImportError:
        pass

    def load_or_create_model(target_env, resume_path):
        if not resume_path:
            m = PPO("CnnPolicy", target_env, seed=args.seed, verbose=1, tensorboard_log=tb_dir,
                    n_steps=1024, batch_size=256, n_epochs=4, gamma=0.99, ent_coef=0.01,
                    learning_rate=3e-4,
                    policy_kwargs=dict(features_extractor_class=GridCNN,
                                       features_extractor_kwargs=dict(features_dim=256)))
            m.save(os.path.join(args.ckpt_dir, "ppo_000"))
            return m

        print(f"Resuming model from {resume_path}...")
        try:
            m = PPO.load(resume_path, env=target_env, tensorboard_log=tb_dir)
            return m
        except Exception as e:
            print(f"Transferring weights from {resume_path} to environment space {target_env.observation_space.shape}...")
            tmp = PPO.load(resume_path, device="cpu")
            m = PPO("CnnPolicy", target_env, seed=args.seed, verbose=1, tensorboard_log=tb_dir,
                    n_steps=1024, batch_size=256, n_epochs=4, gamma=0.99, ent_coef=0.01,
                    learning_rate=3e-4,
                    policy_kwargs=dict(features_extractor_class=GridCNN,
                                       features_extractor_kwargs=dict(features_dim=256)))
            m.policy.load_state_dict(tmp.policy.state_dict(), strict=False)
            return m

    if args.auto_advance:
        start_level = args.start_level or args.level
        env = Monitor(PacmanEnv(level_id=start_level))
        model = load_or_create_model(env, args.resume)

        callback = TrainingCallback(args.timesteps, args.ckpt_dir,
                                    os.path.join(args.results_dir, "train_log.csv"),
                                    auto_advance=True, start_level=start_level, max_level=args.max_level,
                                    resume=bool(args.resume))
        try:
            print(f"=== Training with 3-Star Dynamic Maze Introduction (Starting at Level {start_level}) ===")
            model.learn(args.timesteps, callback=callback, reset_num_timesteps=not bool(args.resume),
                        tb_log_name="ppo_pacman_autoadvance", progress_bar=False)
            model.save(os.path.join(args.ckpt_dir, "ppo_100"))
            print("Done. Run: python evaluate.py")
        finally:
            callback.close()
        return

    start_lv = args.start_level or (args.level if not args.curriculum else 1)
    stages = list(range(start_lv, args.max_level + 1)) if args.curriculum else [args.level]
    per_stage = args.timesteps // len(stages)
    total = per_stage * len(stages)

    env = Monitor(PacmanEnv(level_id=stages[0]))
    model = load_or_create_model(env, args.resume)

    callback = TrainingCallback(total, args.ckpt_dir, os.path.join(args.results_dir, "train_log.csv"),
                                start_level=stages[0], resume=bool(args.resume))

    try:
        for i, level in enumerate(stages):
            print(f"=== Training on level {level} for {per_stage} steps ===")
            if i > 0:
                stage_env = Monitor(PacmanEnv(level_id=level))
                if stage_env.observation_space != model.observation_space:
                    print(f"\n[Tier Transition] Transferring weights from {model.observation_space.shape} to {stage_env.observation_space.shape} (Compact 15x15 -> Arcade Standard 28x31).")
                    model.save(os.path.join(args.ckpt_dir, f"level_{stages[i-1]}_final"))
                    tmp_policy = model.policy
                    model = PPO("CnnPolicy", stage_env, seed=args.seed, verbose=1, tensorboard_log=tb_dir,
                                n_steps=1024, batch_size=256, n_epochs=4, gamma=0.99, ent_coef=0.01,
                                learning_rate=3e-4,
                                policy_kwargs=dict(features_extractor_class=GridCNN,
                                                   features_extractor_kwargs=dict(features_dim=256)))
                    model.policy.load_state_dict(tmp_policy.state_dict(), strict=False)
                    callback.init_callback(model)
                else:
                    model.set_env(stage_env)
            model.learn(per_stage, callback=callback, reset_num_timesteps=(i == 0 and not bool(args.resume)),
                        tb_log_name="ppo_pacman", progress_bar=False)
        model.save(os.path.join(args.ckpt_dir, "ppo_100"))
        print("Done. Run: python evaluate.py")
    finally:
        callback.close()


if __name__ == "__main__":
    main()
