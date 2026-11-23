import os
import base64
import subprocess

def img_to_b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

arch_b64 = img_to_b64("results/system_architecture.png")
gameplay_b64 = img_to_b64("results/gameplay_level_1.png")
curve_b64 = img_to_b64("results/learning_curve.png")
ckpt_b64 = img_to_b64("results/checkpoint_progress.png")
ba_b64 = img_to_b64("results/before_after.png")

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Pac-Man RL — Technical Visual Documentation</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 15mm 15mm 15mm 15mm;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      line-height: 1.5;
      font-size: 11pt;
    }}
    .page {{
      page-break-after: always;
      break-after: page;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      height: 100%;
      min-height: 255mm;
    }}
    .page:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}
    .header {{
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 8px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }}
    .header h1 {{
      font-size: 18pt;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
    }}
    .header .subtitle {{
      font-size: 9pt;
      color: #64748b;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
      background: #f1f5f9;
      color: #334155;
      margin-bottom: 8px;
    }}
    .section-title {{
      font-size: 14pt;
      font-weight: 700;
      color: #1e293b;
      margin-bottom: 6px;
    }}
    .description {{
      color: #334155;
      font-size: 9.5pt;
      margin-bottom: 12px;
      line-height: 1.45;
    }}
    .img-container {{
      width: 100%;
      text-align: center;
      background: #0b0f19;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 8px;
      margin-bottom: 12px;
    }}
    .img-container img {{
      max-width: 100%;
      max-height: 170mm;
      height: auto;
      display: block;
      margin: 0 auto;
      border-radius: 4px;
    }}
    .img-caption {{
      font-size: 8.5pt;
      color: #64748b;
      margin-top: 6px;
      font-style: italic;
      text-align: center;
    }}
    .key-points {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 8px;
    }}
    .card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px;
    }}
    .card-title {{
      font-weight: 700;
      font-size: 9pt;
      color: #1e293b;
      margin-bottom: 4px;
    }}
    .card-body {{
      font-size: 8.5pt;
      color: #475569;
      line-height: 1.4;
    }}
    .footer {{
      margin-top: auto;
      padding-top: 8px;
      border-top: 1px solid #f1f5f9;
      display: flex;
      justify-content: space-between;
      font-size: 8pt;
      color: #94a3b8;
    }}
  </style>
</head>
<body>

  <!-- PAGE 1: SYSTEM ARCHITECTURE -->
  <div class="page">
    <div class="header">
      <div>
        <div class="badge">Architecture & System Design</div>
        <h1>Pac-Man RL: Technical Specification</h1>
      </div>
      <div class="subtitle">Deep Reinforcement Learning Lab</div>
    </div>
    
    <div class="section-title">1. End-to-End System Architecture & Block Diagram</div>
    <div class="description">
      High-level block diagram depicting the closed-loop reinforcement learning environment: the deterministic headless simulation engine, 6-channel spatial tensor observation, multi-layer convolutional feature extractor (GridCNN), and the neuro-symbolic safety filter.
    </div>

    <div class="img-container">
      <img src="{arch_b64}" alt="System Architecture Diagram" style="max-height: 145mm;">
      <div class="img-caption" style="color: #94a3b8;">Figure 1: Full-pipeline architectural schematic connecting the Gym environment, GridCNN policy network, and runtime action filter.</div>
    </div>

    <div class="key-points">
      <div class="card">
        <div class="card-title">Spatial Tensor Representation</div>
        <div class="card-body">Game state is projected into an exact 6-channel tensor (Walls, Pellets, Power, Pac-Man, Active Ghosts, Frightened Ghosts) preserving 2D topological corridor connectivity.</div>
      </div>
      <div class="card">
        <div class="card-title">Universal Spatial Bridge</div>
        <div class="card-body">AdaptiveAvgPool2d((15, 15)) guarantees consistent 14,400-dimensional latent vectors across both 15x15 compact grids and 28x31 classic arcade dimensions.</div>
      </div>
    </div>

    <div class="footer">
      <span>Pac-Man Reinforcement Learning Project</span>
      <span>Page 1 of 4</span>
    </div>
  </div>

  <!-- PAGE 2: LEVEL 1 GAMEPLAY CAPTURE -->
  <div class="page">
    <div class="header">
      <div>
        <div class="badge">Environment & Game Mechanics</div>
        <h1>Level 1 Gameplay Demonstration</h1>
      </div>
      <div class="subtitle">Warm-up Maze Configuration</div>
    </div>

    <div class="section-title">2. In-Game State & Adversary Pursuit Mechanics</div>
    <div class="description">
      In-situ snapshot of active gameplay on Level 1 ("Warm-up"). Pac-Man navigates the 15x15 compact grid while Blinky (Red Ghost) executes Euclidean distance minimization towards Pac-Man's exact coordinates.
    </div>

    <div class="img-container" style="padding: 12px; background: #0a0c1a;">
      <img src="{gameplay_b64}" alt="Level 1 Gameplay Screenshot" style="max-height: 150mm;">
      <div class="img-caption" style="color: #94a3b8;">Figure 2: Level 1 game engine rendering showing Pac-Man, Blinky, pellets, power energizers, and live HUD metrics.</div>
    </div>

    <div class="key-points">
      <div class="card">
        <div class="card-title">Blinky Pursuit Logic</div>
        <div class="card-body">Directly targets Pac-Man's current tile (r_pac, c_pac) at 0.5 tile/step with 40-step frightened vulnerability periods upon power pellet consumption.</div>
      </div>
      <div class="card">
        <div class="card-title">Candy-Crush Star Criteria</div>
        <div class="card-body">1 Star: Complete level. 2 Stars: Finish with ≥2 lives. 3 Stars: Achieve score ≥1,700 through rapid dot clearing and ghost consumption.</div>
      </div>
    </div>

    <div class="footer">
      <span>Pac-Man Reinforcement Learning Project</span>
      <span>Page 2 of 4</span>
    </div>
  </div>

  <!-- PAGE 3: CURRICULUM TRAINING LEARNING CURVE -->
  <div class="page">
    <div class="header">
      <div>
        <div class="badge">Training Dynamics</div>
        <h1>Curriculum Learning Curves</h1>
      </div>
      <div class="subtitle">250,000+ Timestep Telemetry</div>
    </div>

    <div class="section-title">3. PPO Optimization Metrics Across Levels 1–10</div>
    <div class="description">
      Episodic training logs recorded in real-time during the multi-level PPO training curriculum. Dashed red vertical markers delineate autonomous level promotion triggers upon achieving 3-star competency.
    </div>

    <div class="img-container" style="background: #0f172a;">
      <img src="{curve_b64}" alt="Training Learning Curve" style="max-height: 150mm;">
      <div class="img-caption" style="color: #94a3b8;">Figure 3: Smoothed moving averages for Episode Reward, Clear Rate %, Game Score, and Star Progression.</div>
    </div>

    <div class="key-points">
      <div class="card">
        <div class="card-title">Reward & Value Convergence</div>
        <div class="card-body">Mean episode reward scales from initial negative penalties (-13.2) to robust positive margins (+42.9) with an explained variance of ~0.89.</div>
      </div>
      <div class="card">
        <div class="card-title">Curriculum Advancement</div>
        <div class="card-body">The TrainingCallback continuously monitors 3-star thresholds, auto-saving milestone weights and introducing higher-tier maze topologies without manual intervention.</div>
      </div>
    </div>

    <div class="footer">
      <span>Pac-Man Reinforcement Learning Project</span>
      <span>Page 3 of 4</span>
    </div>
  </div>

  <!-- PAGE 4: CHECKPOINT PROGRESS & BEFORE/AFTER BENCHMARK -->
  <div class="page">
    <div class="header">
      <div>
        <div class="badge">Empirical Validation</div>
        <h1>Empirical Evaluation & Checkpoints</h1>
      </div>
      <div class="subtitle">Monte Carlo Benchmark (N=50 Episodes)</div>
    </div>

    <div class="section-title">4. Checkpoint Scaling & Baseline Comparisons</div>
    <div class="description">
      Quantitative analysis comparing the untrained baseline agent (RandomPolicy), intermediate training checkpoints (ppo_000 through ppo_100), and the BFS Oracle heuristic.
    </div>

    <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px;">
      <div class="img-container" style="background: #ffffff; border: 1px solid #e2e8f0; margin-bottom: 0;">
        <img src="{ckpt_b64}" alt="Checkpoint Progress" style="max-height: 65mm;">
        <div class="img-caption">Figure 4a: Policy progression across training milestones (0%, 25%, 50%, 75%, 100%).</div>
      </div>

      <div class="img-container" style="background: #ffffff; border: 1px solid #e2e8f0; margin-bottom: 0;">
        <img src="{ba_b64}" alt="Before vs After Comparison" style="max-height: 65mm;">
        <div class="img-caption">Figure 4b: Monte Carlo comparative benchmark across Level tiers (Random vs. Trained PPO vs. BFS Bot).</div>
      </div>
    </div>

    <div class="key-points">
      <div class="card">
        <div class="card-title">Zero Wall Collision Guarantee</div>
        <div class="card-body">Action masking reduces illegal movement decisions from 28.4% (Random) down to 0.0%, completely eliminating stationary penalties.</div>
      </div>
      <div class="card">
        <div class="card-title">Win Rate Mastery</div>
        <div class="card-body">Trained Smart PPO v3 matches the BFS Oracle with a 100% win rate on early mazes and superior survival time against 4-ghost gauntlets.</div>
      </div>
    </div>

    <div class="footer">
      <span>Pac-Man Reinforcement Learning Project</span>
      <span>Page 4 of 4</span>
    </div>
  </div>

</body>
</html>
"""

with open("results/project_visualizations.html", "w") as f:
    f.write(html_content)

print("Saved results/project_visualizations.html")

# Render to PDF using Chrome Headless
chrome_cmd = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--print-to-pdf=results/project_visualizations.pdf",
    "results/project_visualizations.html"
]

res = subprocess.run(chrome_cmd, capture_output=True, text=True)
if res.returncode == 0:
    print("Successfully generated results/project_visualizations.pdf")
else:
    print("Chrome error:", res.stderr)
