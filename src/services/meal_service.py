"""Meal menu service — loads tier-based JSON menus."""
import json
import random
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "meals"


def load_menu(tier: str = "standard") -> dict:
    path = TEMPLATES_DIR / f"{tier}.json"
    if not path.exists():
        path = TEMPLATES_DIR / "standard.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_meal_for_type(menu: dict, meal_type: str,
                      option_idx: int | None = None) -> dict:
    meal_data = menu["meals"].get(meal_type)
    if not meal_data:
        return {}
    options = meal_data.get("options", [])
    if not options:
        return meal_data

    if option_idx is not None:
        chosen = options[option_idx % len(options)]
    else:
        chosen = random.choice(options)

    return {
        "label": meal_data["label"],
        "emoji": meal_data["emoji"],
        "time": meal_data["time"],
        **chosen,
    }


def get_full_day_menu(menu: dict) -> list[dict]:
    result = []
    for meal_type in menu["meals"]:
        meal = get_meal_for_type(menu, meal_type)
        meal["type"] = meal_type
        result.append(meal)
    return result
