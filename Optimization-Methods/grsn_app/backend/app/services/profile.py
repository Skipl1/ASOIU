import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.models import FitnessGoal, UserProfile
from app.services import nutrition
from app.services.serializers import goal_out


def get_profile(db: Session, user_id: uuid.UUID) -> UserProfile | None:
    return db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))


def energy_for(profile: UserProfile, goal: FitnessGoal | None) -> nutrition.EnergyProfile:
    delta = goal.calorie_correction if goal else 0
    return nutrition.energy_profile(
        profile.sex, profile.weight_kg, profile.height_cm, profile.age, profile.activity_level, delta
    )


def daily_targets(target_kcal: float, goal: FitnessGoal | None) -> dict:
    if goal is None:
        return nutrition.macro_targets_g(target_kcal, 20, 30, 50)
    return nutrition.macro_targets_g(target_kcal, goal.protein_pct, goal.fat_pct, goal.carb_pct)


def profile_out(user_id: uuid.UUID, profile: UserProfile | None) -> schemas.ProfileOut:
    if profile is None:
        return schemas.ProfileOut(user_id=user_id, is_complete=False)
    energy = energy_for(profile, profile.goal)
    return schemas.ProfileOut(
        id=profile.profile_id,
        user_id=user_id,
        is_complete=profile.goal is not None,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        gender=profile.sex,
        activity_level=profile.activity_level,
        goal=goal_out(profile.goal) if profile.goal else None,
        bmr=energy.bmr,
        tdee=energy.tdee,
        target_calories=energy.target,
        daily_targets=schemas.NutritionTotals(**daily_targets(energy.target, profile.goal)),
        updated_at=profile.updated_at,
    )
