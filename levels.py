"""Level configs, star rating and Candy-Crush-style progression."""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_PATH = os.path.join(BASE_DIR, "levels.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "progress.json")


def load_levels(path=LEVELS_PATH):
    with open(path) as f:
        return json.load(f)


def get_level(level_id, path=LEVELS_PATH):
    for cfg in load_levels(path):
        if cfg["id"] == level_id:
            return cfg
    raise KeyError(f"No level with id {level_id}")


def calc_stars(cfg, score, lives, won):
    """0 = failed, 1 = cleared, 2 = cleared with enough lives left,
    3 = both of the above and a high score (fast clear / ghosts eaten)."""
    if not won:
        return 0
    stars = 1
    if lives >= cfg["star2_min_lives"]:
        stars = 2
        if score >= cfg["star3_min_score"]:
            stars = 3
    return stars


def load_progress(path=PROGRESS_PATH):
    if os.path.exists(path):
        with open(path) as f:
            return {int(k): v for k, v in json.load(f).get("stars", {}).items()}
    return {}


def save_progress(level_id, stars, path=PROGRESS_PATH):
    """Keep the best star count per level."""
    prog = load_progress(path)
    prog[level_id] = max(stars, prog.get(level_id, 0))
    with open(path, "w") as f:
        json.dump({"stars": {str(k): v for k, v in prog.items()}}, f, indent=2)
    return prog


def total_stars(path=PROGRESS_PATH):
    return sum(load_progress(path).values())


def is_unlocked(level_id, progress_path=PROGRESS_PATH, levels_path=LEVELS_PATH):
    cfg = get_level(level_id, levels_path)
    return total_stars(progress_path) >= cfg["stars_to_unlock"]
