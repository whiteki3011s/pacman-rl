# Pac-Man + Reinforcement Learning (PPO)

A grid-based Pac-Man game built from scratch with 5 levels, ghost AI, a star
system (Candy-Crush style), human play, and a PPO agent trained with
Stable-Baselines3. The report/demo shows **before training vs after training**.

## Setup
```bash
pip install -r requirements.txt
python -m unittest discover tests -v      # 17 tests should pass
```

## Run
| What | Command |
|---|---|
| Play yourself (menu, stars, unlocks) | `python play.py` |
| Play one level | `python play.py --level 2` |
| Watch the hand-written bot | `python play.py --ai bfs --level 2` |
| Train PPO on level 1 | `python train.py --level 1 --timesteps 300000` |
| Train with 3-Star dynamic auto-advance | `python train.py --auto-advance --resume checkpoints/ppo_075.zip --timesteps 1500000` |
| Train with static curriculum (levels 1-5) | `python train.py --curriculum --timesteps 1500000` |
| Evaluate (random vs PPO vs bot) | `python evaluate.py --episodes 50` |
| Watch the trained agent | `python play.py --ai ppo --model checkpoints/ppo_100.zip --level 1` |
| Record before/after GIF | `python record.py --level 1 --model checkpoints/ppo_100.zip` |

Training writes `checkpoints/ppo_000.zip` (untrained) ... `ppo_100.zip` and
`results/train_log.csv`. `evaluate.py` then writes `results/results.csv`,
`before_after.png`, `checkpoint_progress.png`, `learning_curve.png`.
Free Colab works too (upload the folder, `pip install -r requirements.txt`).

## Project structure
```
constants.py   actions, scoring, timers
engine.py      headless deterministic game (no pygame)
ghosts.py      Blinky / Pinky / Inky / Clyde target-tile AI + scatter/chase/frightened
levels.py      level configs, star rules, progress.json, unlock logic
levels.json    per-level difficulty settings      levels/maze_01..05.txt  the mazes
observation.py (6,15,15) channel grid for the network
env.py         Gymnasium wrapper + reward constants (tune these first)
bots.py        RandomPolicy, BFSBot, PPOPolicy wrapper
train.py       PPO + small CNN, checkpoints at 0/25/50/75/100%, episode log
evaluate.py    metrics + charts      record.py  side-by-side GIF (Pillow)
play.py        pygame renderer, human + AI play, level select
tests/         unit tests
```

## Game rules
* Eat all pellets to clear a level. A normal ghost costs a life; a power pellet
  makes ghosts frightened (half speed) so you can eat them for +200.
* Scoring: pellet 10, power pellet 50, ghost 200, clear bonus 100 + time bonus.
  - Step penalty: -1 score per step taken (time decay).
  - Stationary penalty: -2 additional score if the agent stays stationary / blocked by a wall.
* **Stars:** 1 = cleared; 2 = cleared with >= 2 lives left; 3 = also reached the
  level's score threshold (fast clear and/or ghosts eaten).
* **Progression:** levels 1-2 open; level 3 needs 3 total stars, level 4 needs 6,
  level 5 needs 9 (stored in `progress.json`).
* Difficulty rises per level: 1 -> 4 ghosts, ghost speed 0.5 -> 1.0, shorter
  frightened time, denser mazes.
* Ghosts: Blinky targets Pac-Man, Pinky 4 tiles ahead, Inky uses a vector from
  Blinky, Clyde retreats when within 8 tiles.

## RL setup
* Observation: 6 channels (walls, pellets, power pellets, Pac-Man, ghosts, frightened ghosts), 15x15.
* Actions: UP / DOWN / LEFT / RIGHT. Reward: +1 pellet, +5 power, +10 ghost, -10 death, -0.01 per step, -0.05 stationary penalty, +50 clear.
* "Before" = uniform random agent (and the untrained `ppo_000` checkpoint). "After" = `ppo_100`.

## Baseline numbers (hand-written bot, 30 episodes/level, from my test run)
Random agent: 0% wins on all levels. BFS bot win rate: L1 100%, L2 100%, L3 ~97%, L4 ~50%, L5 ~50%.
This confirms the game is winnable and gets harder per level. PPO numbers come from *your* training run.

## Key Findings & Reward Shaping
* **Time & Stationary Penalty:** Adding a time decay penalty (`-1` score/step) and stationary penalty (`-2` score, `-0.05` RL reward) significantly improved learning. Without them, the agent cleared ~80% of pellets and then stalled in safe corners to run out the 600-step clock. With the penalties, stalling was eliminated, average reward surged to **+104+**, and the policy actively hunted pellets and frightened ghosts.
* **Curriculum vs Single-Level:** Sequential multi-level training causes catastrophic forgetting (e.g. Level 5 overwriting Level 1). Single-level training ensures dedicated policy mastery.

## If PPO does not learn
1. Train on level 1 only first (`--level 1`, 300k-500k steps) and look at `results/learning_curve.png`.
2. Tune the reward constants at the top of `env.py` (e.g. bigger R_PELLET, smaller R_STEP).
3. Train longer or use `--curriculum`. Report honest results: learning curves and limits are still a good project.
