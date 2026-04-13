"""TDEE, BMR, BMI and macro calculators using Mifflin-St Jeor equation."""

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Thiếu cân"
    if bmi < 25:
        return "Bình thường"
    if bmi < 30:
        return "Thừa cân"
    return "Béo phì"


def calc_bmr(weight_kg: float, height_cm: float, age: int, gender: str = "male") -> float:
    """Mifflin-St Jeor equation."""
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return base + 5 if gender == "male" else base - 161


def calc_tdee(bmr: float, activity_level: str) -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * multiplier)


def calc_bulk_calories(tdee: float, surplus_pct: float = 0.15) -> float:
    return round(tdee * (1 + surplus_pct))


def calc_macros(daily_calories: float, weight_kg: float) -> dict:
    protein_g = round(weight_kg * 2.0)
    fat_g = round(weight_kg * 1.0)

    protein_cal = protein_g * 4
    fat_cal = fat_g * 9
    carb_cal = daily_calories - protein_cal - fat_cal
    carbs_g = round(max(carb_cal / 4, 0))

    return {
        "protein": protein_g,
        "carbs": carbs_g,
        "fat": fat_g,
        "protein_cal": protein_cal,
        "carbs_cal": carbs_g * 4,
        "fat_cal": fat_cal,
    }


def full_calculation(weight_kg: float, height_cm: float, age: int,
                     activity_level: str = "moderate", gender: str = "male") -> dict:
    bmi = calc_bmi(weight_kg, height_cm)
    bmr = calc_bmr(weight_kg, height_cm, age, gender)
    tdee = calc_tdee(bmr, activity_level)
    daily_calories = calc_bulk_calories(tdee)
    macros = calc_macros(daily_calories, weight_kg)

    return {
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "bmr": round(bmr),
        "tdee": tdee,
        "daily_calories": daily_calories,
        **macros,
    }
