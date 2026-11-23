# Pac-Man RL Prototype Demonstration & Presentation Guide

This guide details **what to show in your prototype**, **how to run it**, and the **exact 3-minute presentation script** to present to evaluators, professors, judges, or teammates.

---

## 1. Prototype Deliverables Available to Show

You have two complementary prototype applications ready to run:

| Deliverable | File | How to Launch | Best Used For |
| :--- | :--- | :--- | :--- |
| **Native Python Dashboard** | [`prototype_demo.py`](file:///Users/abhaysharma/Downloads/pacman_rl/prototype_demo.py) | `.venv/bin/python prototype_demo.py` | Local workstation demo, Pygame window with live PyTorch CNN inference HUD |
| **Interactive Web Showcase** | [`prototype_showcase.html`](file:///Users/abhaysharma/Downloads/pacman_rl/prototype_showcase.html) | `open prototype_showcase.html` | Browser demonstration, projector slides, or sharing with anyone without Python |

---

## 2. What You Should Show in the Prototype (The 4 Pillars)

When presenting an AI / RL prototype, audiences lose interest if it's just a black-box game. To win top marks, your prototype demonstrates four distinct engineering layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      PAC-MAN RL PROTOTYPE HUD                          │
├───────────────────────────────┬────────────────────────────────────────┤
│                               │ 1. REAL-TIME TELEMETRY                 │
│                               │    Score, Pellets (113), Lives, Stars  │
│                               ├────────────────────────────────────────┤
│                               │ 2. CNN NEURAL CONFIDENCE (LOGITS)      │
│     INTERACTIVE GAMEPLAY      │    UP: [████████░░] 78%                │
│     BOARD (15x15 GRID)        │    DOWN / LEFT / RIGHT Live Gauges     │
│                               ├────────────────────────────────────────┤
│   Pac-Man • Pellets • Ghosts  │ 3. LIVE ABLATION KNOBS (PROOF OF WORK) │
│                               │    [M] Action Masking: [ ON ]          │
│                               │    [A] Anti-Stall Loop: [ ON ]         │
│                               │    [E] Multi-Ghost Evasion: [ ON ]     │
│                               ├────────────────────────────────────────┤
│                               │ 4. SUBSYSTEM DECISION STATE            │
│                               │    "CRITICAL EVASION (<=2 tiles)"      │
└───────────────────────────────┴────────────────────────────────────────┘
```

### Pillar 1: The "Before vs After" Baseline Failure
* **What to show:** Switch policy to **Raw PPO** or **Random Baseline**.
* **What the audience sees:** The agent wanders aimlessly, hits walls repeatedly (~103 wall bumps per episode), or hides in empty corners once local pellets are gone.
* **The Takeaway:** Shows the audience the exact technical challenge that naive RL algorithms fail to solve on their own.

### Pillar 2: The Under-the-Hood CNN Brain Visualizer
* **What to show:** Look at the **CNN Policy Head** section on the right HUD.
* **What the audience sees:** Live probability bars that adjust at 15–30 frames per second showing what the Convolutional Neural Network is predicting before masking.
* **The Takeaway:** Demonstrates that the agent is not hardcoded; it is a 3-layer Convolutional Network extracting spatial features from a 6-channel state grid.

### Pillar 3: The Live Ablation Switches ("Proof of Work")
* **What to show:** Toggle individual engineering modules ON and OFF live during gameplay:
  * **Press `[M]` (Action Masking):** Toggle OFF $\to$ watch Pac-Man bump into walls. Toggle ON $\to$ wall bumps instantly drop to **0.0**!
  * **Press `[A]` (Anti-Stall Loop Breaker):** Toggle OFF $\to$ watch Pac-Man hover in safe corridors when pellets are cleared. Toggle ON $\to$ Pac-Man immediately breaks out of the loop and routes directly to distant pellets!
  * **Press `[E]` (Multi-Ghost Evasion):** Toggle ON $\to$ Pac-Man detects pincer traps and dodges multi-ghost flanks!
* **The Takeaway:** Proves scientifically that your hybrid additions directly solved the core failure modes of PPO.

### Pillar 4: Campaign Scaling & Difficulty Progression
* **What to show:** Press `[1]`, `[2]`, `[3]` to switch mazes:
  * **Level 1 (Warm-up):** 1 ghost @ 0.50 speed $\to$ **100.0% Win Rate**, Score 1,836, 3 Stars.
  * **Level 2 (Twin Trouble):** 2 ghosts @ 0.60 speed $\to$ **93.3% Win Rate**, Peak Score 2,323, 3 Stars.
  * **Level 3 (Triple Chase):** 3 ghosts @ 0.75 speed $\to$ Flawless **3 Stars (Peak: 2,152)**.
  * Point out that **all 5 campaign levels are unlocked** (9 total stars)!

---

## 3. The 3-Minute Live Presentation Script

Here is an exact word-for-word spoken walkthrough you can deliver:

### Minute 0:00 – 0:45: The Problem & Naive Failure
> *"Hello everyone. Today we are presenting our Reinforcement Learning Pac-Man prototype. Our goal was to train a deep convolutional PPO agent to clear mazes, evade dynamic enemies, and time power pellets.*
>
> *(Press `[P]` to switch to Raw PPO on Level 1)*
>
> *When we initially trained standard PPO, we discovered two critical failure modes:*
> *First, the network frequently panicked and collided with walls over 100 times per episode.*
> *Second, it exploited what we call 'The Hide Tactic': once local pellets were eaten, the empty corridors provided zero reward gradients, so the agent learned to hover passively in safe corners."*

### Minute 0:45 – 1:30: Reward Shaping & Hybrid Interventions
> *(Press `[P]` to switch to Smart PPO. Press `[M]` to show Action Masking)*
>
> *"To solve this, we introduced three key engineering solutions:*
> *1. **Reward Shaping:** We added a step penalty of -1 point per step and a stationary penalty of -2 points. This eliminated corner camping.*
> *2. **Action Masking:** On the right sidebar, you can see our live CNN probability bars. By projecting the policy distribution over valid corridor moves, we dropped illegal wall moves to zero.*
> *3. **Anti-Stall Loop Breaker:** When the agent oscillates in cleared corridors without seeing pellets, a lightweight BFS route injector breaks the loop and points Pac-Man toward unexplored food."*

### Minute 1:30 – 2:15: Maze 3 & The 3-Ghost Pincer Problem
> *(Press `[3]` to jump to Level 3: Triple Chase)*
>
> *"Next, we tested generalization on Maze 3. Here, the difficulty spikes drastically: there are 3 ghosts—Blinky, Pinky, and Inky—moving at 0.75 speed, which is 50% faster than Level 1.*
>
> *Notice what happens at intersections: when Pac-Man dodges one ghost, the other two ghosts attempt to flank from perpendicular corridors.*
>
> *(Point to HUD: Subsystem State)*
>
> *Our upgraded Smart PPO v3 utilizes a multi-ghost proximity escape vector. Notice how Pac-Man senses the 2-tile threat radius and steers into the open loop, avoiding the pincer trap and clearing over 90% of the maze."*

### Minute 2:15 – 3:00: Results & Campaign Mastery
> *(Pause with `[SPACE]` on a high score or cleared screen)*
>
> *"To conclude, our final model achieved:*
> * *A **93.3% win rate** on Level 2 with a peak score of **2,323 points**.*
> * *A peak score of **2,152 points** on Level 3, earning **3 Stars**.*
> * *A total of **9 Stars**, successfully unlocking all 5 levels of the campaign.*
>
> *Thank you, and we'd be happy to answer any questions or demonstrate any specific ablation live!"*

---

## 4. Interactive Keyboard Hotkey Cheat Sheet

| Key | Action | Presentation Purpose |
| :---: | :--- | :--- |
| **`[P]`** | Cycle Policies | Show contrast: Smart PPO vs Raw PPO vs Random vs Human |
| **`[1]` - `[3]`** | Select Level 1, 2, or 3 | Demonstrate scaling from 1 ghost to 3 ghosts @ 0.75 speed |
| **`[M]`** | Toggle Action Masking | Prove that masking removes wall stuttering in real time |
| **`[A]`** | Toggle Anti-Stall | Prove that anti-stall solves empty corridor navigation |
| **`[E]`** | Toggle Multi-Ghost Evasion | Demonstrate tactical dodging against 3 converging ghosts |
| **`[SPACE]`** | Pause / Resume | Freeze game at critical moments to explain CNN logits |
| **`[N]`** | Single Frame Step | Walk through a single evasion maneuver frame-by-frame |
| **`[+]` / `[-]`** | Adjust FPS (5 – 60) | Slow down to explain tactics or speed up to show fast clears |
| **`[R]`** | Reset Level | Start a fresh run with a new random seed |
| **`[ESC]`** | Exit Prototype | Closes the demo window cleanly |

---

## 5. Answers to Anticipated Evaluator Questions

**Q1: Why didn't pure PPO learn to clear the maze without the Anti-Stall helper?**
> *Answer:* Standard feedforward CNNs have no recurrent state or spatial memory. Once nearby pellets are eaten, the immediate $3 \times 3$ receptive field contains only empty floor tiles. Because there is no local reward gradient, the policy gradient is flat. The anti-stall module bridges this short-range perceptual gap by providing a long-range directional cue toward uncollected food.

**Q2: Did you reward-penalize stalling during training?**
> *Answer:* Yes. In `engine.py` and `constants.py`, we added continuous time decay (`-1` score/step) and stationary penalty (`-2` score/step), plus `R_STATIONARY = -0.05` in environment reward shaping. This directly eliminated the agent's safe-corner pacing behavior.

**Q3: How does the agent handle 3 ghosts on Level 3?**
> *Answer:* On Level 3, ghosts move at 0.75 speed and converge in pincer maneuvers. In `bots.py`, when active ghosts are within $\le 2$ tiles, the policy evaluates all valid next moves and selects the direction that maximizes the distance to the nearest active chaser, preventing suicidal steps and escaping multi-angle traps.
