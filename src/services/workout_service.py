"""Workout program service — loads PPL JSON, manages workout state."""
import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "workouts"


def load_program(program_name: str = "ppl") -> dict:
    path = TEMPLATES_DIR / f"{program_name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_today_workout(program: dict, day_index: int) -> tuple[str, list[dict]]:
    schedule = program["schedule"]
    day_type = schedule[day_index % len(schedule)]
    if day_type == "rest":
        return "rest", []
    exercises = program["days"][day_type]["exercises"]
    return day_type, exercises
