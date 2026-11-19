"""Starting data, taken from the approved specification (19 Nov 2026) and coach/state.json in
the ironman-training repo. Inserted once by migration 0002; edit through the app afterwards."""
import datetime as dt

PROFILE = {
    "display_name": "Dan",
    "birth_date": dt.date(2002, 11, 20),
    "sex": "male",
    "height_cm": 188,
    "preferences": {
        "proteins": {
            "preferred": ["chicken", "beef mince", "eggs"],
            "acceptable": ["pork", "lamb", "steak", "Greek yoghurt", "whey protein", "milk", "cheese",
                           "beans", "lentils", "tofu"],
            "plant_protein_role": "accompaniment",
            "excluded_cuts": ["pork tenderloin"],
        },
        "seafood": {
            "excluded": ["fish", "prawns", "shrimp", "crustaceans", "molluscs", "squid", "mussels",
                         "clams", "scallops", "crab", "lobster", "fish stock", "dashi"],
            "occasional": ["tinned tuna"],
            "always_allowed_seasonings": ["fish sauce", "oyster sauce"],
            "seasoning_only": [
                {"term": "Worcestershire sauce", "max_per_portion": "1 tbsp"},
                {"term": "shrimp paste (in curry paste)", "max_per_portion": "1 tbsp of paste"},
                {"term": "anchovy (melted into a sauce)", "max_per_portion": "2 fillets"},
            ],
        },
        "other_exclusions": [
            {"term": "cottage cheese", "reason": "Declined 26 Sep 2026, confirmed 19 Nov 2026"},
            {"term": "kidney beans", "reason": "Confirmed 19 Nov 2026"},
        ],
        "allergies": [],
        "limits": {
            "gluten_meals_per_day_target": 1,
            "gluten_meals_per_day_max": 2,
            "ingredient_caps_g_per_portion": {"spinach (raw)": 60},
        },
        "cooking": {
            "ability": "advanced",
            "equipment": ["oven", "hob", "air fryer", "microwave", "food processor", "blender",
                          "slow cooker", "pressure cooker", "rice cooker", "grill"],
            "lunch_minutes_min": 10,
            "lunch_minutes_max": 20,
            "dinner_minutes_max": 60,
            "slow_cook_morning_prep": True,
            "portions_usual_min": 1,
            "portions_usual_max": 2,
            "portions_occasional_max": 4,
            "assumed_staples": ["olive oil", "salt", "black pepper", "garlic", "onions", "herbs", "spices"],
            "style_notes": [
                "Cooks from scratch: homemade sauces, dressings, marinades and spice blends.",
                "Convenience ingredients are fine when they genuinely help.",
                "Assume a competent cook: searing, deglazing, reductions, emulsions, seasoning balance.",
                "Plating suggestions welcome but not a priority.",
                "Repeating a good meal 2-3 times a week is fine.",
            ],
        },
        "taste": {
            "favourite_cuisines": ["Italian", "Thai"],
            "likes": ["pasta", "pizza", "rich, well-developed sauces", "strong seasoning", "spicy food",
                      "restaurant-quality meals", "healthier versions of indulgent dishes"],
            "dislikes": ["fishy Mediterranean-style dishes"],
            "notes": ["Italian cuisine is a favourite: never exclude it as 'Mediterranean'."],
        },
    },
}

MEASUREMENTS = [
    {"measured_on": dt.date(2026, 11, 12), "weight_kg": "79.55", "status": "verified",
     "source": "Fitdays smart scale, 08:06 12 Nov 2026 (coach/state.json)"},
]

# Confirmed 19 Nov 2026: 3,455 kcal average, carbs moved by day type, weekly average held.
ACTIVE_TARGET = {
    "phase": "muscle_gain",
    "status": "active",
    "origin": "stated",
    "kcal": 3455,
    "protein_g": 175,
    "carbs_g": 475,
    "fat_g": 95,
    "fibre_g": None,
    "day_types": {
        "rest": {"carbs_g": 400, "label": "Rest or very light"},
        "standard": {"carbs_g": 475, "label": "Standard training"},
        "long": {"carbs_g": 575, "label": "Long or hard session"},
    },
    "rationale": ("Stated Oct 2026, confirmed by Dan 19 Nov 2026 for Phase 1 (muscle gain). "
                  "Carbs shift by day type; the app scales them so the weekly average stays at 3,455 kcal."),
    "effective_from": dt.date(2026, 11, 19),
}
