"""Request/response shapes. Everything the client sends is validated here before it reaches SQL."""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------ preferences

class Exclusion(Strict):
    term: Short                       # what to block, e.g. "prawn"
    reason: Note = ""


class SeasoningAllowance(Strict):
    """Seafood-derived seasonings allowed in small amounts, never as a visible/main ingredient."""
    term: Short
    max_per_portion: Short            # human-readable limit, e.g. "1 tbsp"


class Proteins(Strict):
    preferred: list[Short]
    acceptable: list[Short]
    plant_protein_role: Literal["accompaniment", "main_ok"] = "accompaniment"
    excluded_cuts: list[Short] = []   # e.g. pork tenderloin


class Seafood(Strict):
    excluded: list[Short]                         # fish, prawns, crustaceans, molluscs ...
    occasional: list[Short]                       # tinned tuna
    always_allowed_seasonings: list[Short]        # fish sauce, oyster sauce
    seasoning_only: list[SeasoningAllowance]      # worcestershire, shrimp paste, anchovy in a sauce


class Limits(Strict):
    gluten_meals_per_day_target: int = Field(1, ge=0, le=5)
    gluten_meals_per_day_max: int = Field(2, ge=0, le=5)
    ingredient_caps_g_per_portion: dict[Short, int] = {}   # {"spinach (raw)": 60}

    @model_validator(mode="after")
    def _order(self):
        if self.gluten_meals_per_day_max < self.gluten_meals_per_day_target:
            raise ValueError("gluten max cannot be below the target")
        for k, v in self.ingredient_caps_g_per_portion.items():
            if not 0 < v <= 2000:
                raise ValueError(f"cap for {k} must be 1-2000 g")
        return self


class Cooking(Strict):
    ability: Literal["beginner", "intermediate", "advanced", "expert"]
    equipment: list[Short]
    lunch_minutes_min: int = Field(ge=0, le=240)
    lunch_minutes_max: int = Field(ge=1, le=240)
    dinner_minutes_max: int = Field(ge=1, le=480)
    slow_cook_morning_prep: bool
    portions_usual_min: int = Field(ge=1, le=8)
    portions_usual_max: int = Field(ge=1, le=8)
    portions_occasional_max: int = Field(ge=1, le=12)
    assumed_staples: list[Short]
    style_notes: list[Note] = []

    @model_validator(mode="after")
    def _ranges(self):
        if self.lunch_minutes_min > self.lunch_minutes_max:
            raise ValueError("lunch minimum is above the maximum")
        if not self.portions_usual_min <= self.portions_usual_max <= self.portions_occasional_max:
            raise ValueError("portion ranges are out of order")
        return self


class Taste(Strict):
    favourite_cuisines: list[Short]
    likes: list[Short]
    dislikes: list[Short]
    notes: list[Note] = []


class Preferences(Strict):
    proteins: Proteins
    seafood: Seafood
    other_exclusions: list[Exclusion]
    allergies: list[Short] = []
    limits: Limits
    cooking: Cooking
    taste: Taste


# ------------------------------------------------------------------ profile

class ProfileIn(Strict):
    display_name: Short
    birth_date: dt.date | None = None
    sex: Literal["male", "female"] | None = None
    height_cm: Decimal | None = Field(None, gt=100, lt=250)
    preferences: Preferences


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    updated_at: dt.datetime


# ------------------------------------------------------------------ measurements

class MeasurementIn(Strict):
    measured_on: dt.date
    weight_kg: Decimal | None = Field(None, gt=30, lt=250, decimal_places=2)
    body_fat_pct: Decimal | None = Field(None, gt=2, lt=60, decimal_places=1)
    waist_cm: Decimal | None = Field(None, gt=40, lt=200, decimal_places=1)
    status: Literal["verified", "stated", "estimated"] = "stated"
    source: Note = ""

    @model_validator(mode="after")
    def _something(self):
        if self.weight_kg is None and self.body_fat_pct is None and self.waist_cm is None:
            raise ValueError("enter at least one measurement")
        if self.measured_on > dt.date.today() + dt.timedelta(days=1):
            raise ValueError("measurement date is in the future")
        return self


class MeasurementOut(MeasurementIn):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: uuid.UUID
    created_at: dt.datetime


# ------------------------------------------------------------------ targets

DAY_TYPES = ("rest", "standard", "long")


class DayType(Strict):
    carbs_g: int = Field(ge=0, le=1000)
    label: Short


class TargetIn(Strict):
    """A proposal. It is stored as 'proposed' and does nothing until approved."""
    phase: Literal["muscle_gain", "fat_loss_maintain_muscle", "maintenance"]
    kcal: int = Field(ge=1200, le=6000)
    protein_g: int = Field(ge=50, le=400)
    carbs_g: int = Field(ge=0, le=1000)
    fat_g: int = Field(ge=20, le=300)
    fibre_g: int | None = Field(None, ge=0, le=150)
    day_types: dict[Literal["rest", "standard", "long"], DayType] = {}
    rationale: Note
    effective_from: dt.date

    @model_validator(mode="after")
    def _energy_adds_up(self):
        # Atwater 4/4/9. Allow 3% for rounding; anything further means the numbers disagree.
        from_macros = 4 * self.protein_g + 4 * self.carbs_g + 9 * self.fat_g
        if abs(from_macros - self.kcal) > 0.03 * self.kcal:
            raise ValueError(f"macros give {from_macros} kcal but the target says {self.kcal}")
        if self.day_types and "standard" in self.day_types and self.day_types["standard"].carbs_g != self.carbs_g:
            raise ValueError("the standard day's carbs must equal the base carbs")
        order = [self.day_types[k].carbs_g for k in DAY_TYPES if k in self.day_types]
        if order != sorted(order):
            raise ValueError("day-type carbs must run rest <= standard <= long")
        return self


class TargetOut(TargetIn):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: uuid.UUID
    status: str
    origin: str
    created_at: dt.datetime
    decided_at: dt.datetime | None
    supersedes_id: uuid.UUID | None

    @field_validator("rationale", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return v or ""


class Decision(Strict):
    confirm: Literal[True]   # the client must say so explicitly


# ------------------------------------------------------------------ auth

class PasswordLogin(Strict):
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class PasskeyName(Strict):
    name: Short = "Phone"
