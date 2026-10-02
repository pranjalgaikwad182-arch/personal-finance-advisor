from datetime import date
from models import db, SavingsGoal, SavingsContribution, User
from services.financial_analyzer import calculate_total_income, calculate_total_expenses


def get_savings_advice(user_id: int) -> dict:
    """
    Generates intelligent savings guidance and emergency fund adequacy calculations.
    """
    user = db.session.get(User, user_id)
    user_type = user.user_type if user else "Salaried Professional"

    today = date.today()
    income = calculate_total_income(user_id, today.month, today.year)
    expenses = calculate_total_expenses(user_id, today.month, today.year)

    goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    total_target = sum(g.target_amount for g in goals)
    total_saved = sum(g.current_amount for g in goals)
    total_monthly_required = sum(g.monthly_required for g in goals)

    # Emergency fund runway target months based on persona
    emergency_months_map = {
        "Student": 3,
        "Salaried Professional": 6,
        "Freelancer": 9,  # Freelancers face volatile cash flows, recommend 9 months
        "Household Manager": 6,
    }
    recommended_months = emergency_months_map.get(user_type, 6)
    target_emergency_fund = round(expenses * recommended_months, 2) if expenses > 0 else round(income * 0.5 * recommended_months, 2)

    # Check existing emergency fund
    emergency_goals = [g for g in goals if "emergency" in g.name.lower()]
    current_emergency_savings = sum(g.current_amount for g in emergency_goals) if emergency_goals else 0.0

    runway_months = round(current_emergency_savings / expenses, 1) if expenses > 0 else 0.0

    projections = []
    for g in goals:
        projections.append({
            "id": g.id,
            "name": g.name,
            "target_amount": g.target_amount,
            "current_amount": g.current_amount,
            "progress_pct": g.progress_pct,
            "remaining_amount": g.remaining_amount,
            "deadline": g.target_date.isoformat(),
            "months_remaining": g.months_remaining,
            "monthly_required": g.monthly_required,
            "status": "Completed" if g.current_amount >= g.target_amount else g.status,
        })

    return {
        "user_type": user_type,
        "total_target": round(total_target, 2),
        "total_saved": round(total_saved, 2),
        "overall_progress_pct": round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0,
        "total_monthly_required": round(total_monthly_required, 2),
        "target_emergency_fund": target_emergency_fund,
        "current_emergency_savings": round(current_emergency_savings, 2),
        "recommended_runway_months": recommended_months,
        "current_runway_months": runway_months,
        "projections": projections,
    }


def get_goal_projections(goal: SavingsGoal) -> dict:
    """Detailed monthly projections for an individual goal."""
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "progress_pct": goal.progress_pct,
        "remaining_amount": goal.remaining_amount,
        "months_remaining": goal.months_remaining,
        "monthly_required": goal.monthly_required,
        "status": "Completed" if goal.current_amount >= goal.target_amount else goal.status,
    }
